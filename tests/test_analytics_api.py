import json

import pytest
from fastapi.testclient import TestClient

from theundercut.api.main import app
from theundercut.adapters.db import get_db
from tests.conftest import seed_sample_race


class DummyRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


def _override_dependency(session_factory):
    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    return _get_db


def test_analytics_endpoint_returns_payload(session_factory, monkeypatch):
    SessionLocal = session_factory
    seed_sample_race(SessionLocal())

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.analytics.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/analytics/2024/1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["laps"]) == 4
    assert dummy_cache.store  # cache populated

    # force cache hit with new payload
    key = next(iter(dummy_cache.store))
    dummy_cache.store[key] = json.dumps({"cached": True})
    resp_cached = client.get("/api/v1/analytics/2024/1")
    assert resp_cached.json() == {"cached": True}

    app.dependency_overrides.clear()


def test_analytics_endpoint_driver_filter(session_factory, monkeypatch):
    SessionLocal = session_factory
    seed_sample_race(SessionLocal())

    app.dependency_overrides[get_db] = _override_dependency(SessionLocal)
    dummy_cache = DummyRedis()
    monkeypatch.setattr("theundercut.api.v1.analytics.redis_client", dummy_cache)

    client = TestClient(app)

    resp = client.get("/api/v1/analytics/2024/1", params={"drivers": ["VER", "VER"]})
    assert resp.status_code == 200
    body = resp.json()
    assert {lap["driver"] for lap in body["laps"]} == {"VER"}

    app.dependency_overrides.clear()
