"""End-to-end tests for the homepage."""

import json
import pytest
from fastapi.testclient import TestClient

from theundercut.api.main import app
from theundercut.adapters.db import get_db
from theundercut.models import LapTime
from tests.conftest import seed_sample_race


class DummyRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


def _override_dependency(session_factory):
    """Create a dependency override for database session."""
    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    return _get_db


def _seed_homepage_data(session):
    """Seed data needed for homepage tests."""
    # Add race data for 2024 and 2025
    # 2024 - several races
    for rnd in [1, 5, 10]:
        race_id = f"2024-{rnd}"
        session.add_all([
            LapTime(race_id=race_id, driver="VER", lap=1, lap_ms=90000),
            LapTime(race_id=race_id, driver="VER", lap=2, lap_ms=89000),
            LapTime(race_id=race_id, driver="VER", lap=3, lap_ms=88000),
            LapTime(race_id=race_id, driver="HAM", lap=1, lap_ms=91000),
            LapTime(race_id=race_id, driver="HAM", lap=2, lap_ms=90000),
            LapTime(race_id=race_id, driver="HAM", lap=3, lap_ms=89500),
            LapTime(race_id=race_id, driver="LEC", lap=1, lap_ms=92000),
            LapTime(race_id=race_id, driver="LEC", lap=2, lap_ms=91000),
            LapTime(race_id=race_id, driver="LEC", lap=3, lap_ms=90000),
        ])

    # 2025 - latest season with British GP (round 12)
    for rnd in [1, 5, 12]:
        race_id = f"2025-{rnd}"
        session.add_all([
            LapTime(race_id=race_id, driver="VER", lap=1, lap_ms=89000),
            LapTime(race_id=race_id, driver="VER", lap=2, lap_ms=88000),
            LapTime(race_id=race_id, driver="VER", lap=3, lap_ms=87000),
            LapTime(race_id=race_id, driver="NOR", lap=1, lap_ms=89500),
            LapTime(race_id=race_id, driver="NOR", lap=2, lap_ms=88500),
            LapTime(race_id=race_id, driver="NOR", lap=3, lap_ms=87500),
            LapTime(race_id=race_id, driver="HAM", lap=1, lap_ms=90000),
            LapTime(race_id=race_id, driver="HAM", lap=2, lap_ms=89000),
            LapTime(race_id=race_id, driver="HAM", lap=3, lap_ms=88000),
        ])

    session.commit()


class TestHomepageE2E:
    """End-to-end tests for homepage functionality."""

    def test_homepage_renders_successfully(self, session_factory, monkeypatch):
        """Homepage should render with 200 status (not redirect)."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

        app.dependency_overrides.clear()

    def test_homepage_contains_latest_race_section(self, session_factory, monkeypatch):
        """Homepage should display the Latest Race section."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        assert "Latest Race" in html
        # Should show British GP (round 12) as latest for 2025
        assert "Round 12" in html or "British Grand Prix" in html

        app.dependency_overrides.clear()

    def test_homepage_contains_podium_finishers(self, session_factory, monkeypatch):
        """Homepage should display podium finishers (P1, P2, P3)."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        # Should show position markers
        assert 'class="podium-position p1"' in html
        assert 'class="podium-position p2"' in html
        assert 'class="podium-position p3"' in html

        # Should show driver codes from our seeded data
        assert "VER" in html

        app.dependency_overrides.clear()

    def test_homepage_contains_standings_tables(self, session_factory, monkeypatch):
        """Homepage should display driver and constructor standings tables."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        # Should have standings section
        assert "Championship Standings" in html
        assert "driver-standings" in html
        assert "constructor-standings" in html

        app.dependency_overrides.clear()

    def test_homepage_has_analytics_link(self, session_factory, monkeypatch):
        """Homepage should have a link to view full analytics."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        # Should have link to analytics page
        assert "View Full Analytics" in html
        assert "/analytics/2025/12" in html  # Link to latest race analytics

        app.dependency_overrides.clear()

    def test_homepage_has_standings_link(self, session_factory, monkeypatch):
        """Homepage should have a link to full standings page."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        # Should have link to standings page
        assert "Full Standings" in html
        assert "/standings/2025" in html

        app.dependency_overrides.clear()

    def test_homepage_displays_current_season(self, session_factory, monkeypatch):
        """Homepage should display the current season year."""
        SessionLocal = session_factory
        session = SessionLocal()
        _seed_homepage_data(session)
        session.close()

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        html = resp.text

        # Should show 2025 as current season (latest with data)
        assert "2025" in html

        app.dependency_overrides.clear()

    def test_homepage_handles_empty_database(self, session_factory, monkeypatch):
        """Homepage should handle gracefully when no data exists."""
        SessionLocal = session_factory
        # Don't seed any data

        app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
        dummy_cache = DummyRedis()
        monkeypatch.setattr("theundercut.api.v1.standings.redis_client", dummy_cache)

        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text

        # Should show fallback content
        assert "No race data available" in html or "2024" in html  # Default season

        app.dependency_overrides.clear()
