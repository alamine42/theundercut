"""Tests for the Race Weekend API endpoints."""
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from theundercut.api.main import app
from theundercut.adapters.db import get_db
from theundercut.models import CalendarEvent, SessionClassification


class DummyRedis:
    """Simple in-memory Redis mock for testing."""
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    def scan_iter(self, match=None):
        if match:
            pattern = match.replace("*", "")
            return [k for k in self.store.keys() if pattern in k]
        return list(self.store.keys())


def _override_dependency(session_factory):
    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    return _get_db


def seed_race_weekend(session, season=2026, rnd=1):
    """Seed a complete race weekend with calendar events and session classifications."""
    now = datetime.utcnow()

    # Create calendar events for a standard weekend
    sessions = [
        ("fp1", now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=1), "completed"),
        ("fp2", now - timedelta(days=2) + timedelta(hours=4), now - timedelta(days=2) + timedelta(hours=5), "completed"),
        ("fp3", now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=1), "completed"),
        ("qualifying", now - timedelta(days=1) + timedelta(hours=4), now - timedelta(days=1) + timedelta(hours=5), "ingested"),
        ("race", now + timedelta(hours=2), now + timedelta(hours=4), "scheduled"),
    ]

    calendar_events = []
    for sess_type, start, end, status in sessions:
        event = CalendarEvent(
            season=season,
            round=rnd,
            session_type=sess_type,
            start_ts=start,
            end_ts=end,
            status=status,
        )
        calendar_events.append(event)

    session.add_all(calendar_events)

    # Add session classifications for completed sessions
    classifications = [
        # FP1 results
        SessionClassification(season=season, round=rnd, session_type="fp1", driver_code="VER", driver_name="Max Verstappen", team="Red Bull", position=1, time_ms=90123, gap_ms=None, laps=25),
        SessionClassification(season=season, round=rnd, session_type="fp1", driver_code="NOR", driver_name="Lando Norris", team="McLaren", position=2, time_ms=90234, gap_ms=111, laps=28),
        SessionClassification(season=season, round=rnd, session_type="fp1", driver_code="LEC", driver_name="Charles Leclerc", team="Ferrari", position=3, time_ms=90345, gap_ms=222, laps=22),
        # FP2 results
        SessionClassification(season=season, round=rnd, session_type="fp2", driver_code="NOR", driver_name="Lando Norris", team="McLaren", position=1, time_ms=89500, gap_ms=None, laps=30),
        SessionClassification(season=season, round=rnd, session_type="fp2", driver_code="VER", driver_name="Max Verstappen", team="Red Bull", position=2, time_ms=89600, gap_ms=100, laps=28),
        SessionClassification(season=season, round=rnd, session_type="fp2", driver_code="HAM", driver_name="Lewis Hamilton", team="Ferrari", position=3, time_ms=89700, gap_ms=200, laps=26),
        # FP3 results
        SessionClassification(season=season, round=rnd, session_type="fp3", driver_code="VER", driver_name="Max Verstappen", team="Red Bull", position=1, time_ms=89000, gap_ms=None, laps=18),
        SessionClassification(season=season, round=rnd, session_type="fp3", driver_code="LEC", driver_name="Charles Leclerc", team="Ferrari", position=2, time_ms=89150, gap_ms=150, laps=20),
        SessionClassification(season=season, round=rnd, session_type="fp3", driver_code="NOR", driver_name="Lando Norris", team="McLaren", position=3, time_ms=89200, gap_ms=200, laps=19),
        # Qualifying results
        SessionClassification(season=season, round=rnd, session_type="qualifying", driver_code="VER", driver_name="Max Verstappen", team="Red Bull", position=1, time_ms=88500, gap_ms=None, q1_time_ms=89500, q2_time_ms=89000, q3_time_ms=88500),
        SessionClassification(season=season, round=rnd, session_type="qualifying", driver_code="NOR", driver_name="Lando Norris", team="McLaren", position=2, time_ms=88600, gap_ms=100, q1_time_ms=89600, q2_time_ms=89100, q3_time_ms=88600),
        SessionClassification(season=season, round=rnd, session_type="qualifying", driver_code="LEC", driver_name="Charles Leclerc", team="Ferrari", position=3, time_ms=88700, gap_ms=200, q1_time_ms=89700, q2_time_ms=89200, q3_time_ms=88700),
    ]

    session.add_all(classifications)
    session.commit()
    return season, rnd


def seed_completed_race_weekend(session, *, season=2026, rnd=2, hours_since_race_end=12):
    """Seed a weekend where the race finished in the past."""
    now = datetime.utcnow()
    race_end = now - timedelta(hours=hours_since_race_end)
    race_start = race_end - timedelta(hours=2)

    sessions = [
        ("fp1", now - timedelta(days=4), now - timedelta(days=4) + timedelta(hours=1), "completed"),
        ("fp2", now - timedelta(days=3), now - timedelta(days=3) + timedelta(hours=1), "completed"),
        ("fp3", now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=1), "completed"),
        ("qualifying", now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=1), "ingested"),
        ("race", race_start, race_end, "ingested"),
    ]

    for sess_type, start, end, status in sessions:
        event = CalendarEvent(
            season=season,
            round=rnd,
            session_type=sess_type,
            start_ts=start,
            end_ts=end,
            status=status,
        )
        session.add(event)

    session.commit()
    return season, rnd


def test_race_schedule_endpoint(session_factory, monkeypatch):
    """Test GET /api/v1/race/{season}/{round}/schedule returns schedule."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/race/2026/1/schedule")
    assert resp.status_code == 200

    body = resp.json()
    assert body["season"] == 2026
    assert body["round"] == 1
    assert len(body["sessions"]) == 5
    assert body["is_sprint_weekend"] is False

    # Verify session types
    session_types = [s["session_type"] for s in body["sessions"]]
    assert "fp1" in session_types
    assert "qualifying" in session_types
    assert "race" in session_types

    app.dependency_overrides.clear()


def test_race_schedule_not_found(session_factory, monkeypatch):
    """Test GET /api/v1/race/{season}/{round}/schedule returns 404 when not found."""
    SessionLocal = session_factory

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/race/2026/99/schedule")
    assert resp.status_code == 404

    app.dependency_overrides.clear()


def test_session_results_endpoint(session_factory, monkeypatch):
    """Test GET /api/v1/race/{season}/{round}/session/{type}/results returns results."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    # Test FP1 results
    resp = client.get("/api/v1/race/2026/1/session/fp1/results")
    assert resp.status_code == 200

    body = resp.json()
    assert body["season"] == 2026
    assert body["round"] == 1
    assert body["session_type"] == "fp1"
    assert len(body["results"]) == 3
    assert body["results"][0]["driver_code"] == "VER"
    assert body["results"][0]["position"] == 1

    app.dependency_overrides.clear()


def test_qualifying_results_endpoint(session_factory, monkeypatch):
    """Test qualifying results include Q1/Q2/Q3 times."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/race/2026/1/session/qualifying/results")
    assert resp.status_code == 200

    body = resp.json()
    assert body["session_type"] == "qualifying"
    result = body["results"][0]
    assert result["q1_time"] is not None
    assert result["q2_time"] is not None
    assert result["q3_time"] is not None

    app.dependency_overrides.clear()


def test_session_results_not_found(session_factory, monkeypatch):
    """Test GET session results returns 404 for non-existent session."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    # Race has no results yet (status is "scheduled")
    resp = client.get("/api/v1/race/2026/1/session/race/results")
    assert resp.status_code == 404

    app.dependency_overrides.clear()


def test_weekend_aggregated_endpoint(session_factory, monkeypatch):
    """Test GET /api/v1/race/{season}/{round}/weekend returns aggregated data."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/race/2026/1/weekend")
    assert resp.status_code == 200

    body = resp.json()
    assert body["schedule"] is not None
    assert body["schedule"]["season"] == 2026
    assert body["schedule"]["round"] == 1
    assert len(body["schedule"]["sessions"]) == 5

    # Check session results are included
    assert "sessions" in body
    assert body["sessions"]["fp1"] is not None
    assert body["sessions"]["fp2"] is not None
    assert body["sessions"]["qualifying"] is not None
    # Race not completed yet
    assert body["sessions"]["race"] is None

    # Check meta
    assert "meta" in body
    assert body["meta"]["stale"] is False
    assert body["timeline"]["state"] == "during-weekend"
    assert body["timeline"]["is_active"] is True
    assert body["timeline"]["next_session"]["session_type"] == "race"

    app.dependency_overrides.clear()


def test_weekend_endpoint_caching(session_factory, monkeypatch):
    """Test that weekend endpoint uses caching."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_race_weekend(db)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)

    # First request should populate cache
    resp1 = client.get("/api/v1/race/2026/1/weekend")
    assert resp1.status_code == 200
    assert len(dummy_cache.store) > 0

    # Modify cache to verify second request uses it
    cache_key = next(k for k in dummy_cache.store.keys() if "weekend" in k)
    # Use a valid WeekendResponse structure for cache verification
    cached_weekend = {
        "schedule": None,
        "history": {"circuit_id": "cached_circuit", "circuit_name": None, "previous_year": None},
        "sessions": {},
        "meta": {"last_updated": "2026-01-01T00:00:00", "stale": False, "errors": ["cached"]},
    }
    dummy_cache.store[cache_key] = json.dumps(cached_weekend)

    resp2 = client.get("/api/v1/race/2026/1/weekend")
    assert resp2.json()["meta"]["errors"] == ["cached"]

    app.dependency_overrides.clear()


def test_weekend_timeline_post_race(session_factory, monkeypatch):
    """Timeline should report post-race within 24h of race end."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_completed_race_weekend(db, hours_since_race_end=6)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)
    resp = client.get("/api/v1/race/2026/2/weekend")
    body = resp.json()

    assert body["timeline"]["state"] == "post-race"
    assert body["timeline"]["is_active"] is True

    app.dependency_overrides.clear()


def test_weekend_timeline_off_week_after_window(session_factory, monkeypatch):
    """Timeline should transition to off-week once the 24h window passes."""
    SessionLocal = session_factory
    db = SessionLocal()
    seed_completed_race_weekend(db, rnd=3, hours_since_race_end=36)

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.race.redis_client", dummy_cache)

    client = TestClient(app)
    resp = client.get("/api/v1/race/2026/3/weekend")
    body = resp.json()

    assert body["timeline"]["state"] == "off-week"
    assert body["timeline"]["is_active"] is False

    app.dependency_overrides.clear()
