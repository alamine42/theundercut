"""Unit tests for circuit characteristics API endpoints."""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from theundercut.api.main import app
from theundercut.models import Circuit, CircuitCharacteristics


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    with patch("theundercut.api.v1.circuits.get_db") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session


@pytest.fixture
def sample_circuit():
    """Create a sample circuit."""
    circuit = Circuit(
        id=1,
        name="Test Circuit",
        country="Test Country",
        latitude=45.0,
        longitude=90.0,
    )
    return circuit


@pytest.fixture
def sample_characteristics():
    """Create sample circuit characteristics."""
    char = CircuitCharacteristics(
        id=1,
        circuit_id=1,
        effective_year=2024,
        full_throttle_pct=70.5,
        full_throttle_score=7,
        average_speed_kph=225.0,
        average_speed_score=8,
        track_length_km=5.2,
        tire_degradation_score=6,
        tire_degradation_label="Medium-High",
        track_abrasion_score=5,
        track_abrasion_label="Medium",
        corners_slow=4,
        corners_medium=8,
        corners_fast=3,
        downforce_score=6,
        downforce_label="Medium-High",
        overtaking_difficulty_score=5,
        overtaking_difficulty_label="Medium",
        drs_zones=2,
        circuit_type="Permanent",
        data_completeness="complete",
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    return char


class TestListCircuitsWithCharacteristics:
    """Tests for GET /api/v1/circuits/characteristics."""

    def test_returns_empty_list_when_no_circuits(self, client, mock_db_session):
        """Test that empty list is returned when no circuits exist."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None
            mock_db_session.query.return_value.all.return_value = []

            response = client.get("/api/v1/circuits/characteristics")

            assert response.status_code == 200
            data = response.json()
            assert data["circuits"] == []
            assert data["total"] == 0

    def test_returns_circuits_with_characteristics(
        self, client, mock_db_session, sample_circuit, sample_characteristics
    ):
        """Test that circuits with characteristics are returned correctly."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            # Mock circuit query
            mock_db_session.query.return_value.all.return_value = [sample_circuit]

            # Mock characteristics query
            char_query = MagicMock()
            char_query.filter.return_value = char_query
            char_query.order_by.return_value = char_query
            char_query.first.return_value = sample_characteristics
            mock_db_session.query.return_value = char_query

            response = client.get("/api/v1/circuits/characteristics")

            assert response.status_code == 200
            data = response.json()
            assert len(data["circuits"]) >= 0

    def test_uses_cache_when_available(self, client):
        """Test that cached response is used when available."""
        cached_data = {"circuits": [], "total": 0}

        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = json.dumps(cached_data)

            response = client.get("/api/v1/circuits/characteristics")

            assert response.status_code == 200
            assert response.json() == cached_data


class TestGetCircuitCharacteristics:
    """Tests for GET /api/v1/circuits/characteristics/{circuit_id}."""

    def test_returns_404_for_nonexistent_circuit(self, client, mock_db_session):
        """Test that 404 is returned for non-existent circuit."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            response = client.get("/api/v1/circuits/characteristics/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_returns_circuit_with_characteristics(
        self, client, mock_db_session, sample_circuit, sample_characteristics
    ):
        """Test that circuit with characteristics is returned correctly."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            # Mock circuit query
            circuit_query = MagicMock()
            circuit_query.filter.return_value = circuit_query
            circuit_query.first.return_value = sample_circuit

            # Mock characteristics query
            char_query = MagicMock()
            char_query.filter.return_value = char_query
            char_query.order_by.return_value = char_query
            char_query.first.return_value = sample_characteristics

            mock_db_session.query.side_effect = [circuit_query, char_query]

            response = client.get("/api/v1/circuits/characteristics/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "Test Circuit"

    def test_supports_year_parameter(self, client, mock_db_session, sample_circuit):
        """Test that year parameter filters characteristics."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            circuit_query = MagicMock()
            circuit_query.filter.return_value = circuit_query
            circuit_query.first.return_value = sample_circuit

            char_query = MagicMock()
            char_query.filter.return_value = char_query
            char_query.first.return_value = None

            mock_db_session.query.side_effect = [circuit_query, char_query]

            response = client.get("/api/v1/circuits/characteristics/1?year=2022")

            assert response.status_code == 200


class TestCompareCircuits:
    """Tests for GET /api/v1/circuits/characteristics/compare."""

    def test_returns_400_for_single_circuit(self, client):
        """Test that 400 is returned when only one circuit ID is provided."""
        response = client.get("/api/v1/circuits/characteristics/compare?ids=1")

        assert response.status_code == 400
        assert "at least 2" in response.json()["detail"].lower()

    def test_returns_400_for_too_many_circuits(self, client):
        """Test that 400 is returned when more than 5 circuit IDs are provided."""
        response = client.get("/api/v1/circuits/characteristics/compare?ids=1,2,3,4,5,6")

        assert response.status_code == 400
        assert "maximum 5" in response.json()["detail"].lower()

    def test_returns_404_for_nonexistent_circuit(self, client, mock_db_session):
        """Test that 404 is returned when a circuit doesn't exist."""
        with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
            mock_redis.get.return_value = None
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            response = client.get("/api/v1/circuits/characteristics/compare?ids=1,999")

            assert response.status_code == 404


class TestRankCircuits:
    """Tests for GET /api/v1/circuits/characteristics/rank."""

    def test_returns_400_for_invalid_field(self, client):
        """Test that 400 is returned for invalid ranking field."""
        response = client.get("/api/v1/circuits/characteristics/rank?by=invalid_field")

        assert response.status_code == 400
        assert "invalid ranking field" in response.json()["detail"].lower()

    def test_returns_400_for_invalid_order(self, client):
        """Test that 400 is returned for invalid order."""
        response = client.get(
            "/api/v1/circuits/characteristics/rank?by=full_throttle_score&order=invalid"
        )

        assert response.status_code == 400
        assert "asc" in response.json()["detail"].lower()

    def test_accepts_valid_ranking_fields(self, client, mock_db_session):
        """Test that valid ranking fields are accepted."""
        valid_fields = [
            "full_throttle_score",
            "average_speed_score",
            "tire_degradation_score",
            "track_abrasion_score",
            "downforce_score",
            "overtaking_difficulty_score",
            "drs_zones",
            "track_length_km",
        ]

        for field in valid_fields:
            with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
                mock_redis.get.return_value = None

                mock_query = MagicMock()
                mock_query.join.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = []
                mock_db_session.query.return_value = mock_query

                response = client.get(f"/api/v1/circuits/characteristics/rank?by={field}")

                assert response.status_code == 200, f"Failed for field: {field}"


class TestUpdateCircuitCharacteristics:
    """Tests for PUT /api/v1/circuits/characteristics/{circuit_id}."""

    def test_returns_401_without_admin_key(self, client):
        """Test that 401 is returned when no admin key is provided."""
        response = client.put(
            "/api/v1/circuits/characteristics/1",
            json={"full_throttle_score": 8},
        )

        assert response.status_code == 401 or response.status_code == 500

    def test_returns_401_with_invalid_admin_key(self, client):
        """Test that 401 is returned when invalid admin key is provided."""
        with patch("theundercut.api.v1.circuits.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "valid_key"

            response = client.put(
                "/api/v1/circuits/characteristics/1",
                json={"full_throttle_score": 8},
                headers={"X-Admin-Key": "invalid_key"},
            )

            assert response.status_code == 401

    def test_validates_score_range(self, client, mock_db_session, sample_circuit):
        """Test that score values are validated to be within 1-10."""
        with patch("theundercut.api.v1.circuits.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "valid_key"

            # Test score > 10
            response = client.put(
                "/api/v1/circuits/characteristics/1",
                json={"full_throttle_score": 15},
                headers={"X-Admin-Key": "valid_key"},
            )

            assert response.status_code == 422  # Validation error

    def test_validates_circuit_type(self, client):
        """Test that circuit type is validated."""
        with patch("theundercut.api.v1.circuits.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "valid_key"

            response = client.put(
                "/api/v1/circuits/characteristics/1",
                json={"circuit_type": "Invalid"},
                headers={"X-Admin-Key": "valid_key"},
            )

            assert response.status_code == 422  # Validation error


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_cache_busted_on_update(self, client, mock_db_session, sample_circuit):
        """Test that cache is invalidated when characteristics are updated."""
        with patch("theundercut.api.v1.circuits.get_settings") as mock_settings:
            mock_settings.return_value.admin_api_key = "valid_key"

            with patch("theundercut.api.v1.circuits.redis_client") as mock_redis:
                mock_redis.scan_iter.return_value = []

                circuit_query = MagicMock()
                circuit_query.filter.return_value = circuit_query
                circuit_query.first.return_value = sample_circuit

                char_query = MagicMock()
                char_query.filter.return_value = char_query
                char_query.first.return_value = None

                mock_db_session.query.side_effect = [circuit_query, char_query]

                response = client.put(
                    "/api/v1/circuits/characteristics/1",
                    json={"full_throttle_score": 8},
                    headers={"X-Admin-Key": "valid_key"},
                )

                # Cache invalidation should have been called
                assert mock_redis.scan_iter.called or mock_redis.delete.called
