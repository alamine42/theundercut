"""Tests for circuit analytics API endpoints."""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from theundercut.api.main import app


class DummyRedis:
    """Mock Redis client for testing."""
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


# Sample Jolpica API responses
SAMPLE_CIRCUITS = [
    {
        "circuitId": "silverstone",
        "circuitName": "Silverstone Circuit",
        "Location": {"country": "UK", "locality": "Silverstone"},
    },
    {
        "circuitId": "monza",
        "circuitName": "Autodromo Nazionale Monza",
        "Location": {"country": "Italy", "locality": "Monza"},
    },
]

SAMPLE_RACES = [
    {
        "round": "12",
        "season": "2024",
        "raceName": "British Grand Prix",
        "date": "2024-07-07",
        "Circuit": {"circuitId": "silverstone"},
    },
    {
        "round": "16",
        "season": "2024",
        "raceName": "Italian Grand Prix",
        "date": "2024-09-01",
        "Circuit": {"circuitId": "monza"},
    },
]

SAMPLE_CIRCUIT_INFO = {
    "circuitId": "silverstone",
    "circuitName": "Silverstone Circuit",
    "Location": {"country": "UK", "locality": "Silverstone", "lat": "52.0786", "long": "-1.01694"},
    "url": "https://en.wikipedia.org/wiki/Silverstone_Circuit",
}

SAMPLE_RACE_RESULTS = [
    {
        "season": "2024",
        "round": "12",
        "raceName": "British Grand Prix",
        "date": "2024-07-07",
        "Results": [
            {
                "position": "1",
                "points": "25",
                "Driver": {"code": "HAM", "givenName": "Lewis", "familyName": "Hamilton"},
                "Constructor": {"name": "Mercedes"},
                "FastestLap": {"rank": "1", "Time": {"time": "1:30.510"}},
            },
            {
                "position": "2",
                "points": "18",
                "Driver": {"code": "VER", "givenName": "Max", "familyName": "Verstappen"},
                "Constructor": {"name": "Red Bull"},
            },
        ],
    },
    {
        "season": "2023",
        "round": "11",
        "raceName": "British Grand Prix",
        "date": "2023-07-09",
        "Results": [
            {
                "position": "1",
                "points": "25",
                "Driver": {"code": "VER", "givenName": "Max", "familyName": "Verstappen"},
                "Constructor": {"name": "Red Bull"},
                "FastestLap": {"rank": "1", "Time": {"time": "1:28.139"}},
            },
        ],
    },
]

SAMPLE_QUALIFYING = {
    "season": "2024",
    "round": "12",
    "QualifyingResults": [
        {
            "position": "1",
            "Driver": {"code": "RUS"},
            "Q1": "1:26.241",
            "Q2": "1:25.819",
            "Q3": "1:25.819",
        },
    ],
}


@pytest.fixture
def mock_redis():
    """Fixture providing a mock Redis client."""
    return DummyRedis()


@pytest.fixture
def client(mock_redis, monkeypatch):
    """Fixture providing a test client with mocked Redis."""
    monkeypatch.setattr("theundercut.api.v1.circuits.redis_client", mock_redis)
    return TestClient(app)


def test_get_circuits_list(client, monkeypatch):
    """Test that get_circuits returns all circuits for a season."""
    mock_response_circuits = MagicMock()
    mock_response_circuits.status_code = 200
    mock_response_circuits.json.return_value = {
        "MRData": {"CircuitTable": {"Circuits": SAMPLE_CIRCUITS}}
    }
    mock_response_circuits.raise_for_status = MagicMock()

    mock_response_races = MagicMock()
    mock_response_races.status_code = 200
    mock_response_races.json.return_value = {
        "MRData": {"RaceTable": {"Races": SAMPLE_RACES}}
    }
    mock_response_races.raise_for_status = MagicMock()

    def mock_get(url):
        if "circuits.json" in url:
            return mock_response_circuits
        return mock_response_races

    with patch("theundercut.api.v1.circuits.httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        mock_client.return_value.__enter__.return_value = mock_client_instance

        resp = client.get("/api/v1/circuits/2024")

    assert resp.status_code == 200
    body = resp.json()
    assert body["season"] == 2024
    assert len(body["circuits"]) == 2
    assert body["circuits"][0]["circuit_id"] == "silverstone"
    assert body["circuits"][0]["round"] == 12
    assert body["circuits"][1]["circuit_id"] == "monza"


def test_get_circuits_caching(client, mock_redis, monkeypatch):
    """Test that circuits endpoint uses Redis caching."""
    # Pre-populate cache
    cached_data = {
        "season": 2024,
        "circuits": [{"circuit_id": "cached_circuit", "name": "Cached"}],
    }
    mock_redis.store["circuits:v1:2024"] = json.dumps(cached_data)

    resp = client.get("/api/v1/circuits/2024")

    assert resp.status_code == 200
    body = resp.json()
    assert body["circuits"][0]["circuit_id"] == "cached_circuit"


def test_get_circuit_detail(client, monkeypatch, session_factory):
    """Test that get_circuit_detail returns full circuit analytics."""
    from theundercut.adapters.db import get_db

    def _override_dependency():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_dependency

    mock_circuit_info = MagicMock()
    mock_circuit_info.status_code = 200
    mock_circuit_info.json.return_value = {
        "MRData": {"CircuitTable": {"Circuits": [SAMPLE_CIRCUIT_INFO]}}
    }
    mock_circuit_info.raise_for_status = MagicMock()

    mock_results = MagicMock()
    mock_results.status_code = 200
    mock_results.json.return_value = {
        "MRData": {"total": "2", "RaceTable": {"Races": SAMPLE_RACE_RESULTS}}
    }
    mock_results.raise_for_status = MagicMock()

    mock_qualifying = MagicMock()
    mock_qualifying.status_code = 200
    mock_qualifying.json.return_value = {
        "MRData": {"RaceTable": {"Races": [SAMPLE_QUALIFYING]}}
    }
    mock_qualifying.raise_for_status = MagicMock()

    mock_schedule = MagicMock()
    mock_schedule.status_code = 200
    mock_schedule.json.return_value = {
        "MRData": {"RaceTable": {"Races": SAMPLE_RACES}}
    }
    mock_schedule.raise_for_status = MagicMock()

    def mock_get(url):
        if "/circuits/silverstone.json" in url:
            return mock_circuit_info
        if "/results.json" in url:
            return mock_results
        if "/qualifying.json" in url:
            return mock_qualifying
        if "2024.json" in url:
            return mock_schedule
        return mock_results

    with patch("theundercut.api.v1.circuits.httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        mock_client.return_value.__enter__.return_value = mock_client_instance

        resp = client.get("/api/v1/circuits/2024/silverstone")

    assert resp.status_code == 200
    body = resp.json()

    assert body["circuit"]["id"] == "silverstone"
    assert body["circuit"]["name"] == "Silverstone Circuit"
    assert body["season"] == 2024

    # Check race info
    assert body["race_info"]["winner"] == "HAM"
    assert body["race_info"]["pole"] == "RUS"
    assert body["race_info"]["fastest_lap"] == "HAM"

    # Check historical winners
    assert len(body["historical_winners"]) >= 1
    assert body["historical_winners"][0]["year"] == 2024
    assert body["historical_winners"][0]["driver"] == "HAM"

    # Check driver stats
    assert len(body["driver_stats"]) > 0

    app.dependency_overrides.clear()


def test_get_circuit_detail_not_found(client, monkeypatch, session_factory):
    """Test that get_circuit_detail returns error for invalid circuit."""
    from theundercut.adapters.db import get_db

    def _override_dependency():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_dependency

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "MRData": {"CircuitTable": {"Circuits": []}}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("theundercut.api.v1.circuits.httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        resp = client.get("/api/v1/circuits/2024/nonexistent")

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("error") == "Circuit not found"

    app.dependency_overrides.clear()


def test_get_circuit_trends(client, monkeypatch):
    """Test that get_circuit_trends returns multi-season lap times."""
    mock_results = MagicMock()
    mock_results.status_code = 200
    mock_results.json.return_value = {
        "MRData": {"total": "2", "RaceTable": {"Races": SAMPLE_RACE_RESULTS}}
    }
    mock_results.raise_for_status = MagicMock()

    mock_qualifying = MagicMock()
    mock_qualifying.status_code = 200
    mock_qualifying.json.return_value = {
        "MRData": {"total": "1", "RaceTable": {"Races": [SAMPLE_QUALIFYING]}}
    }
    mock_qualifying.raise_for_status = MagicMock()

    def mock_get(url):
        if "/qualifying.json" in url:
            return mock_qualifying
        return mock_results

    with patch("theundercut.api.v1.circuits.httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = mock_get
        mock_client.return_value.__enter__.return_value = mock_client_instance

        resp = client.get("/api/v1/circuits/trends/silverstone")

    assert resp.status_code == 200
    body = resp.json()

    assert body["circuit_id"] == "silverstone"
    assert len(body["trends"]) >= 1

    # Check 2024 trend data
    trend_2024 = next((t for t in body["trends"] if t["year"] == 2024), None)
    assert trend_2024 is not None
    assert trend_2024["winner"] == "HAM"
    assert trend_2024["fastest_lap_driver"] == "HAM"
    assert trend_2024["fastest_lap_time"] == "1:30.510"


def test_get_circuit_trends_caching(client, mock_redis):
    """Test that circuit trends endpoint uses Redis caching."""
    cached_data = {
        "circuit_id": "silverstone",
        "trends": [{"year": 2024, "winner": "CACHED"}],
    }
    mock_redis.store["circuit_trends:v1:silverstone"] = json.dumps(cached_data)

    resp = client.get("/api/v1/circuits/trends/silverstone")

    assert resp.status_code == 200
    body = resp.json()
    assert body["trends"][0]["winner"] == "CACHED"


def test_parse_lap_time_to_ms():
    """Test lap time parsing utility function."""
    from theundercut.api.v1.circuits import _parse_lap_time_to_ms

    # Standard format: 1:23.456
    assert _parse_lap_time_to_ms("1:23.456") == 83456

    # Seconds only: 23.456
    assert _parse_lap_time_to_ms("23.456") == 23456

    # Empty string
    assert _parse_lap_time_to_ms("") is None

    # None
    assert _parse_lap_time_to_ms(None) is None

    # Invalid format
    assert _parse_lap_time_to_ms("invalid") is None
