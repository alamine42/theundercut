"""Tests for render.yaml infrastructure configuration (UND-44, UND-45).

Validates the Render deployment configuration structure, ensuring
all services have required fields, env var references are consistent,
and service connectivity is properly configured.
"""

import pytest
import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def render_config():
    config_path = ROOT / "render.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def web_render_config():
    config_path = ROOT / "web" / "render.yaml"
    if not config_path.exists():
        pytest.skip("web/render.yaml not found")
    with open(config_path) as f:
        return yaml.safe_load(f)


class TestRenderYamlStructure:
    """Validate the top-level render.yaml has correct structure."""

    def test_has_services_key(self, render_config):
        assert "services" in render_config

    def test_has_databases_key(self, render_config):
        assert "databases" in render_config

    def test_services_is_list(self, render_config):
        assert isinstance(render_config["services"], list)

    def test_databases_is_list(self, render_config):
        assert isinstance(render_config["databases"], list)


class TestServiceDefinitions:
    """Validate each service has required fields."""

    def test_all_services_have_type(self, render_config):
        for svc in render_config["services"]:
            assert "type" in svc, f"Service {svc.get('name', '?')} missing 'type'"

    def test_all_services_have_name(self, render_config):
        for svc in render_config["services"]:
            assert "name" in svc, f"Service missing 'name'"

    def test_all_services_have_plan(self, render_config):
        for svc in render_config["services"]:
            assert "plan" in svc, f"Service {svc.get('name', '?')} missing 'plan'"

    def test_service_types_are_valid(self, render_config):
        valid_types = {"web", "worker", "keyvalue", "cron"}
        for svc in render_config["services"]:
            assert svc["type"] in valid_types, (
                f"Service {svc['name']} has invalid type '{svc['type']}'"
            )

    def test_service_names_are_unique(self, render_config):
        names = [svc["name"] for svc in render_config["services"]]
        assert len(names) == len(set(names)), "Duplicate service names found"


class TestServiceConnectivity:
    """Validate inter-service references are correct (UND-44)."""

    def test_api_has_database_url(self, render_config):
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        env_keys = [e["key"] for e in api.get("envVars", [])]
        assert "DATABASE_URL" in env_keys

    def test_api_has_redis_url(self, render_config):
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        env_keys = [e["key"] for e in api.get("envVars", [])]
        assert "REDIS_URL" in env_keys

    def test_redis_reference_matches_keyvalue_service(self, render_config):
        """Ensure the Redis URL env var references the correct keyvalue service."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        redis_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "REDIS_URL"
        )
        referenced_name = redis_env["fromService"]["name"]
        kv_names = [
            s["name"] for s in render_config["services"]
            if s["type"] == "keyvalue"
        ]
        assert referenced_name in kv_names, (
            f"REDIS_URL references '{referenced_name}' but no keyvalue service with that name exists"
        )

    def test_database_reference_matches_database(self, render_config):
        """Ensure DATABASE_URL references a defined database."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        db_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "DATABASE_URL"
        )
        referenced_name = db_env["fromDatabase"]["name"]
        db_names = [d["name"] for d in render_config.get("databases", [])]
        assert referenced_name in db_names, (
            f"DATABASE_URL references '{referenced_name}' but no database with that name exists"
        )

    def test_worker_shares_api_env_vars(self, render_config):
        """Workers should have the same env var keys as the API."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        api_keys = {e["key"] for e in api.get("envVars", [])}
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                worker_keys = {e["key"] for e in svc.get("envVars", [])}
                assert api_keys == worker_keys, (
                    f"Worker {svc['name']} env vars {worker_keys} differ from API {api_keys}"
                )


class TestDatabaseDefinitions:
    """Validate database configuration (UND-45)."""

    def test_database_has_name(self, render_config):
        for db in render_config["databases"]:
            assert "name" in db

    def test_database_has_plan(self, render_config):
        for db in render_config["databases"]:
            assert "plan" in db

    def test_database_names_are_unique(self, render_config):
        names = [db["name"] for db in render_config["databases"]]
        assert len(names) == len(set(names))


class TestFrontendConfig:
    """Validate the web/render.yaml frontend configuration (UND-43)."""

    def test_has_services(self, web_render_config):
        assert "services" in web_render_config

    def test_frontend_has_fastapi_url(self, web_render_config):
        svc = web_render_config["services"][0]
        env_keys = [e["key"] for e in svc.get("envVars", [])]
        assert "FASTAPI_URL" in env_keys, "Frontend missing FASTAPI_URL env var"

    def test_frontend_has_health_check(self, web_render_config):
        svc = web_render_config["services"][0]
        assert "healthCheckPath" in svc

    def test_frontend_uses_node_runtime(self, web_render_config):
        svc = web_render_config["services"][0]
        assert svc.get("runtime") == "node"
