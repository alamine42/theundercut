"""Tests for docker-compose.dev.yml configuration (UND-28).

Validates the Docker Compose dev configuration structure, service
definitions, and security settings.
"""

import pytest
import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def compose_config():
    path = ROOT / "docker-compose.dev.yml"
    if not path.exists():
        pytest.skip("docker-compose.dev.yml not found")
    with open(path) as f:
        return yaml.safe_load(f)


class TestComposeStructure:
    """Validate docker-compose.dev.yml has correct structure."""

    def test_has_services(self, compose_config):
        assert "services" in compose_config

    def test_has_db_service(self, compose_config):
        assert "db" in compose_config["services"]

    def test_has_redis_service(self, compose_config):
        assert "redis" in compose_config["services"]


class TestPostgresService:
    """Validate PostgreSQL service configuration."""

    def test_uses_postgres_image(self, compose_config):
        db = compose_config["services"]["db"]
        assert "postgres" in db["image"]

    def test_has_environment(self, compose_config):
        db = compose_config["services"]["db"]
        assert "environment" in db

    def test_has_postgres_user(self, compose_config):
        env = compose_config["services"]["db"]["environment"]
        assert "POSTGRES_USER" in env

    def test_has_postgres_password(self, compose_config):
        env = compose_config["services"]["db"]["environment"]
        assert "POSTGRES_PASSWORD" in env

    def test_has_postgres_db(self, compose_config):
        env = compose_config["services"]["db"]["environment"]
        assert "POSTGRES_DB" in env

    def test_has_port_mapping(self, compose_config):
        db = compose_config["services"]["db"]
        assert "ports" in db

    def test_port_bound_to_localhost(self, compose_config):
        db = compose_config["services"]["db"]
        ports = db["ports"]
        for port in ports:
            assert "127.0.0.1" in str(port), (
                f"Port {port} should be bound to 127.0.0.1 for security"
            )


class TestRedisService:
    """Validate Redis service configuration."""

    def test_uses_redis_image(self, compose_config):
        redis = compose_config["services"]["redis"]
        assert "redis" in redis["image"]

    def test_has_port_mapping(self, compose_config):
        redis = compose_config["services"]["redis"]
        assert "ports" in redis

    def test_port_bound_to_localhost(self, compose_config):
        redis = compose_config["services"]["redis"]
        ports = redis["ports"]
        for port in ports:
            assert "127.0.0.1" in str(port), (
                f"Port {port} should be bound to 127.0.0.1 for security"
            )

    def test_has_auth_configured(self, compose_config):
        redis = compose_config["services"]["redis"]
        command = redis.get("command", "")
        assert "requirepass" in str(command), (
            "Redis should have --requirepass configured"
        )
