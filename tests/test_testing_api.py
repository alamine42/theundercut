"""Tests for pre-season testing API endpoints."""

import json
import datetime
import pytest
from fastapi.testclient import TestClient

from theundercut.api.main import app
from theundercut.models import TestingEvent, TestingSession, TestingLap, TestingStint


class DummyRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


@pytest.fixture
def mock_redis():
    """Fixture providing a mock Redis client."""
    return DummyRedis()


@pytest.fixture
def client(mock_redis, monkeypatch):
    """Fixture providing a test client with mocked Redis."""
    monkeypatch.setattr("theundercut.api.v1.testing.redis_client", mock_redis)
    return TestClient(app)


def seed_testing_data(session):
    """Seed test data for testing API tests."""
    # Create a testing event
    event = TestingEvent(
        season=2024,
        event_id="pre_season_test",
        event_name="Pre-Season Testing",
        circuit_id="bahrain",
        total_days=3,
        start_date=datetime.date(2024, 2, 21),
        end_date=datetime.date(2024, 2, 23),
        status="completed",
    )
    session.add(event)
    session.flush()

    # Create testing sessions for each day
    sessions = []
    for day in range(1, 4):
        ts = TestingSession(
            event_id=event.id,
            day=day,
            date=datetime.date(2024, 2, 20 + day),
            status="completed",
        )
        session.add(ts)
        session.flush()
        sessions.append(ts)

    # Add laps for day 1
    laps = [
        TestingLap(
            session_id=sessions[0].id,
            driver="VER",
            team="Red Bull Racing",
            lap_number=1,
            lap_time_ms=91234.5,
            compound="SOFT",
            stint_number=1,
            is_valid=True,
        ),
        TestingLap(
            session_id=sessions[0].id,
            driver="VER",
            team="Red Bull Racing",
            lap_number=2,
            lap_time_ms=90123.4,
            compound="SOFT",
            stint_number=1,
            is_valid=True,
        ),
        TestingLap(
            session_id=sessions[0].id,
            driver="HAM",
            team="Mercedes",
            lap_number=1,
            lap_time_ms=91500.0,
            compound="MEDIUM",
            stint_number=1,
            is_valid=True,
        ),
        TestingLap(
            session_id=sessions[0].id,
            driver="HAM",
            team="Mercedes",
            lap_number=2,
            lap_time_ms=90800.0,
            compound="MEDIUM",
            stint_number=1,
            is_valid=True,
        ),
        TestingLap(
            session_id=sessions[0].id,
            driver="LEC",
            team="Ferrari",
            lap_number=1,
            lap_time_ms=92000.0,
            compound="HARD",
            stint_number=1,
            is_valid=True,
        ),
        # Invalid lap (track limits)
        TestingLap(
            session_id=sessions[0].id,
            driver="LEC",
            team="Ferrari",
            lap_number=2,
            lap_time_ms=89000.0,
            compound="SOFT",
            stint_number=2,
            is_valid=False,
        ),
    ]
    session.add_all(laps)

    # Add stints for day 1
    stints = [
        TestingStint(
            session_id=sessions[0].id,
            driver="VER",
            team="Red Bull Racing",
            stint_number=1,
            compound="SOFT",
            lap_count=10,
            avg_pace_ms=90500.0,
        ),
        TestingStint(
            session_id=sessions[0].id,
            driver="HAM",
            team="Mercedes",
            stint_number=1,
            compound="MEDIUM",
            lap_count=12,
            avg_pace_ms=91000.0,
        ),
        TestingStint(
            session_id=sessions[0].id,
            driver="LEC",
            team="Ferrari",
            stint_number=1,
            compound="HARD",
            lap_count=8,
            avg_pace_ms=92000.0,
        ),
        TestingStint(
            session_id=sessions[0].id,
            driver="LEC",
            team="Ferrari",
            stint_number=2,
            compound="SOFT",
            lap_count=5,
            avg_pace_ms=89500.0,
        ),
    ]
    session.add_all(stints)

    session.commit()
    return event, sessions


class TestGetTestingEvents:
    """Tests for GET /api/v1/testing/{season}"""

    def test_returns_events_for_season(self, client, session_factory, monkeypatch):
        """Test that get_testing_events returns all events for a season."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        # Seed data
        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024")

        assert resp.status_code == 200
        body = resp.json()
        assert body["season"] == 2024
        assert len(body["events"]) == 1
        assert body["events"][0]["event_id"] == "pre_season_test"
        assert body["events"][0]["event_name"] == "Pre-Season Testing"
        assert body["events"][0]["circuit_id"] == "bahrain"
        assert body["events"][0]["total_days"] == 3
        assert body["events"][0]["status"] == "completed"

        app.dependency_overrides.clear()

    def test_returns_empty_for_no_events(self, client, session_factory, monkeypatch):
        """Test that get_testing_events returns empty list when no events exist."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        resp = client.get("/api/v1/testing/2025")

        assert resp.status_code == 200
        body = resp.json()
        assert body["season"] == 2025
        assert body["events"] == []

        app.dependency_overrides.clear()

    def test_uses_cache(self, client, mock_redis, session_factory, monkeypatch):
        """Test that get_testing_events uses Redis cache."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        # Pre-populate cache
        cached_data = {
            "season": 2024,
            "events": [{"event_id": "cached_event", "event_name": "Cached Event"}],
        }
        mock_redis.store["testing:events:2024"] = json.dumps(cached_data)

        resp = client.get("/api/v1/testing/2024")

        assert resp.status_code == 200
        body = resp.json()
        assert body["events"][0]["event_id"] == "cached_event"

        app.dependency_overrides.clear()


class TestGetTestingDay:
    """Tests for GET /api/v1/testing/{season}/{event_id}/{day}"""

    def test_returns_day_data(self, client, session_factory, monkeypatch):
        """Test that get_testing_day returns correct day data."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["season"] == 2024
        assert body["event_id"] == "pre_season_test"
        assert body["day"] == 1
        assert body["status"] == "completed"

        # Check results
        results = body["results"]
        assert len(results) == 3  # VER, HAM, LEC

        # VER should be P1 (best lap 90123.4)
        ver = next(r for r in results if r["driver"] == "VER")
        assert ver["position"] == 1
        assert ver["best_lap_ms"] == 90123.4
        assert ver["team"] == "Red Bull Racing"
        assert ver["gap_formatted"] is None  # Leader has no gap

        # HAM should be P2
        ham = next(r for r in results if r["driver"] == "HAM")
        assert ham["position"] == 2
        assert ham["best_lap_ms"] == 90800.0
        assert ham["gap_ms"] == pytest.approx(676.6, abs=0.1)

        # Check stints
        assert len(ver["stints"]) == 1
        assert ver["stints"][0]["compound"] == "SOFT"

        app.dependency_overrides.clear()

    def test_filters_by_drivers(self, client, session_factory, monkeypatch):
        """Test that get_testing_day filters by driver codes."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/1?drivers=VER&drivers=HAM")

        assert resp.status_code == 200
        body = resp.json()
        results = body["results"]

        # Should only have VER and HAM
        driver_codes = [r["driver"] for r in results]
        assert "VER" in driver_codes
        assert "HAM" in driver_codes
        assert "LEC" not in driver_codes

        app.dependency_overrides.clear()

    def test_returns_404_for_invalid_event(self, client, session_factory, monkeypatch):
        """Test that get_testing_day returns 404 for non-existent event."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        resp = client.get("/api/v1/testing/2024/nonexistent_event/1")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()

    def test_returns_404_for_invalid_day(self, client, session_factory, monkeypatch):
        """Test that get_testing_day returns 404 for non-existent day."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/5")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()


class TestGetTestingLaps:
    """Tests for GET /api/v1/testing/{season}/{event_id}/{day}/laps"""

    def test_returns_paginated_laps(self, client, session_factory, monkeypatch):
        """Test that get_testing_laps returns paginated lap data."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/1/laps?limit=10")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 6  # All laps
        assert body["offset"] == 0
        assert body["limit"] == 10
        assert len(body["laps"]) == 6

        # Check lap structure
        lap = body["laps"][0]
        assert "driver" in lap
        assert "lap_number" in lap
        assert "lap_time_ms" in lap
        assert "compound" in lap
        assert "is_valid" in lap

        app.dependency_overrides.clear()

    def test_filters_by_drivers(self, client, session_factory, monkeypatch):
        """Test that get_testing_laps filters by driver codes."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/1/laps?drivers=VER")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2  # Only VER laps

        for lap in body["laps"]:
            assert lap["driver"] == "VER"

        app.dependency_overrides.clear()

    def test_pagination_offset(self, client, session_factory, monkeypatch):
        """Test that pagination offset works correctly."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        with session_factory() as session:
            seed_testing_data(session)

        resp = client.get("/api/v1/testing/2024/pre_season_test/1/laps?offset=2&limit=2")

        assert resp.status_code == 200
        body = resp.json()
        assert body["offset"] == 2
        assert body["limit"] == 2
        assert len(body["laps"]) == 2
        assert body["total"] == 6  # Total count unchanged

        app.dependency_overrides.clear()

    def test_returns_404_for_invalid_event(self, client, session_factory, monkeypatch):
        """Test that get_testing_laps returns 404 for non-existent event."""
        from theundercut.adapters.db import get_db

        def _override_dependency():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = _override_dependency

        resp = client.get("/api/v1/testing/2024/nonexistent_event/1/laps")

        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestHelperFunctions:
    """Tests for helper functions in testing API."""

    def test_format_lap_time(self):
        """Test _format_lap_time utility function."""
        from theundercut.api.v1.testing import _format_lap_time

        # Standard lap time
        assert _format_lap_time(90123.456) == "1:30.123"

        # Sub-minute time
        assert _format_lap_time(45678.123) == "0:45.678"

        # None
        assert _format_lap_time(None) is None

    def test_get_circuit_name(self):
        """Test _get_circuit_name utility function."""
        from theundercut.api.v1.testing import _get_circuit_name

        # Known circuit
        assert _get_circuit_name("bahrain") == "Bahrain International Circuit"
        assert _get_circuit_name("silverstone") == "Silverstone Circuit"

        # Unknown circuit - should title-case
        assert _get_circuit_name("unknown_circuit") == "Unknown Circuit"
