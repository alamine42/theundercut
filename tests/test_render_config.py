"""Tests for render.yaml infrastructure configuration (UND-44, UND-45, UND-51, UND-57, UND-58, UND-62).

Validates the Render deployment configuration structure, ensuring
all services have required fields, env var references are consistent,
service connectivity is properly configured, environment variables
are valid, and infrastructure deployment is sound.
"""

import re

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


class TestFrontendEnvVarValidation:
    """Validate frontend environment variable configuration (UND-62)."""

    def test_fastapi_url_is_present(self, web_render_config):
        svc = web_render_config["services"][0]
        env_keys = [e["key"] for e in svc.get("envVars", [])]
        assert "FASTAPI_URL" in env_keys, "FASTAPI_URL must be configured"

    def test_next_public_ga_id_is_present(self, web_render_config):
        svc = web_render_config["services"][0]
        env_keys = [e["key"] for e in svc.get("envVars", [])]
        assert "NEXT_PUBLIC_GA_ID" in env_keys, (
            "NEXT_PUBLIC_GA_ID must be configured for analytics"
        )

    def test_node_env_is_production(self, web_render_config):
        svc = web_render_config["services"][0]
        node_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "NODE_ENV"),
            None,
        )
        assert node_env is not None, "NODE_ENV must be configured"
        assert node_env.get("value") == "production", (
            "NODE_ENV should be 'production' in deployment config"
        )

    def test_fastapi_url_sync_is_false(self, web_render_config):
        """FASTAPI_URL should use sync: false so it can be set per-environment."""
        svc = web_render_config["services"][0]
        fastapi_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "FASTAPI_URL"),
            None,
        )
        assert fastapi_env is not None
        assert fastapi_env.get("sync") is False, (
            "FASTAPI_URL should have sync: false for per-environment configuration"
        )

    def test_ga_id_sync_is_false(self, web_render_config):
        """GA ID should use sync: false so it can vary per-environment."""
        svc = web_render_config["services"][0]
        ga_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "NEXT_PUBLIC_GA_ID"),
            None,
        )
        assert ga_env is not None
        assert ga_env.get("sync") is False, (
            "NEXT_PUBLIC_GA_ID should have sync: false"
        )

    def test_all_env_vars_have_key_field(self, web_render_config):
        """Every env var entry must have a 'key' field."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            assert "key" in env, f"Env var entry missing 'key': {env}"

    def test_env_var_keys_are_uppercase(self, web_render_config):
        """Environment variable keys should follow UPPER_SNAKE_CASE convention."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            key = env["key"]
            assert key == key.upper(), (
                f"Env var key '{key}' should be uppercase"
            )


class TestFrontendDeploymentConfig:
    """Validate frontend deployment configuration (UND-51)."""

    def test_build_command_exists(self, web_render_config):
        svc = web_render_config["services"][0]
        assert "buildCommand" in svc, "Frontend must have a buildCommand"

    def test_start_command_exists(self, web_render_config):
        svc = web_render_config["services"][0]
        assert "startCommand" in svc, "Frontend must have a startCommand"

    def test_build_command_installs_deps(self, web_render_config):
        """Build command should install dependencies before building."""
        svc = web_render_config["services"][0]
        build_cmd = svc["buildCommand"]
        assert "npm install" in build_cmd, (
            "buildCommand should include 'npm install' to install dependencies"
        )

    def test_build_command_runs_build(self, web_render_config):
        """Build command should include npm run build."""
        svc = web_render_config["services"][0]
        build_cmd = svc["buildCommand"]
        assert "npm run build" in build_cmd, (
            "buildCommand should include 'npm run build'"
        )

    def test_start_command_uses_npm_start(self, web_render_config):
        svc = web_render_config["services"][0]
        assert svc["startCommand"] == "npm start", (
            "startCommand should be 'npm start'"
        )

    def test_health_check_path_is_root(self, web_render_config):
        """Health check should target the root path."""
        svc = web_render_config["services"][0]
        assert svc.get("healthCheckPath") == "/", (
            "healthCheckPath should be '/' for the frontend"
        )

    def test_auto_deploy_is_enabled(self, web_render_config):
        svc = web_render_config["services"][0]
        assert svc.get("autoDeploy") is True, (
            "autoDeploy should be true for continuous deployment"
        )

    def test_service_type_is_web(self, web_render_config):
        svc = web_render_config["services"][0]
        assert svc.get("type") == "web"

    def test_service_has_name(self, web_render_config):
        svc = web_render_config["services"][0]
        assert "name" in svc and svc["name"], "Service must have a non-empty name"

    def test_plan_is_specified(self, web_render_config):
        svc = web_render_config["services"][0]
        assert "plan" in svc, "Service must specify a plan"


class TestBackendEnvVarValidation:
    """Validate backend environment variable configuration (UND-57)."""

    def test_database_url_uses_from_database(self, render_config):
        """DATABASE_URL should be sourced from the database service."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        db_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "DATABASE_URL"
        )
        assert "fromDatabase" in db_env, (
            "DATABASE_URL should use 'fromDatabase' to reference the database service"
        )
        assert db_env["fromDatabase"]["property"] == "connectionString", (
            "DATABASE_URL should use the 'connectionString' property"
        )

    def test_redis_url_uses_from_service(self, render_config):
        """REDIS_URL should be sourced from the keyvalue service."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        redis_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "REDIS_URL"
        )
        assert "fromService" in redis_env, (
            "REDIS_URL should use 'fromService' to reference the keyvalue service"
        )
        assert redis_env["fromService"]["type"] == "keyvalue"
        assert redis_env["fromService"]["property"] == "connectionString"

    def test_secret_key_is_auto_generated(self, render_config):
        """SECRET_KEY should be auto-generated by Render."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        secret_env = next(
            (e for e in api.get("envVars", []) if e["key"] == "SECRET_KEY"),
            None,
        )
        assert secret_env is not None, "SECRET_KEY must be configured"
        assert secret_env.get("generateValue") is True, (
            "SECRET_KEY should use generateValue: true for secure generation"
        )

    def test_api_has_all_critical_env_vars(self, render_config):
        """API service must have all critical environment variables."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        env_keys = {e["key"] for e in api.get("envVars", [])}
        required_keys = {"DATABASE_URL", "REDIS_URL", "SECRET_KEY"}
        missing = required_keys - env_keys
        assert not missing, f"API service missing critical env vars: {missing}"

    def test_workers_have_all_critical_env_vars(self, render_config):
        """Worker services must have access to the same critical env vars."""
        required_keys = {"DATABASE_URL", "REDIS_URL", "SECRET_KEY"}
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                env_keys = {e["key"] for e in svc.get("envVars", [])}
                missing = required_keys - env_keys
                assert not missing, (
                    f"Worker {svc['name']} missing critical env vars: {missing}"
                )

    def test_env_var_keys_are_valid_identifiers(self, render_config):
        """All env var keys should be valid shell identifiers."""
        pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")
        for svc in render_config["services"]:
            for env in svc.get("envVars", []):
                key = env["key"]
                assert pattern.match(key), (
                    f"Env var key '{key}' in {svc['name']} is not a valid identifier"
                )


class TestInfrastructureDeployment:
    """Validate infrastructure deployment configuration (UND-58)."""

    def test_frontend_has_health_check(self, render_config):
        """Frontend service must have a health check path."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert "healthCheckPath" in frontend, (
            "Frontend must have a healthCheckPath for deployment validation"
        )

    def test_frontend_fastapi_url_is_valid(self, render_config):
        """Frontend's FASTAPI_URL should be a valid HTTPS URL."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        fastapi_env = next(
            (e for e in frontend.get("envVars", []) if e["key"] == "FASTAPI_URL"),
            None,
        )
        assert fastapi_env is not None, "Frontend must have FASTAPI_URL"
        url = fastapi_env.get("value", "")
        assert url.startswith("https://"), (
            f"FASTAPI_URL should use HTTPS in production, got: {url}"
        )

    def test_api_uses_docker_env(self, render_config):
        """API service should use Docker environment."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        assert api.get("env") == "docker", (
            "API service should use docker environment"
        )

    def test_api_has_docker_command(self, render_config):
        """API service should have a Docker command configured."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        cmd = api.get("dockerCommand", "")
        assert "uvicorn" in cmd, "API dockerCommand should use uvicorn"
        assert "--host 0.0.0.0" in cmd, (
            "API should bind to 0.0.0.0 for container access"
        )

    def test_all_docker_services_have_repo(self, render_config):
        """All docker-based services must reference a repo."""
        for svc in render_config["services"]:
            if svc.get("env") == "docker":
                assert "repo" in svc, (
                    f"Docker service {svc['name']} must have a 'repo' URL"
                )

    def test_workers_use_docker_env(self, render_config):
        """Worker services should use Docker environment."""
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                assert svc.get("env") == "docker", (
                    f"Worker {svc['name']} should use docker environment"
                )

    def test_workers_have_docker_commands(self, render_config):
        """Worker services should have Docker commands."""
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                assert "dockerCommand" in svc, (
                    f"Worker {svc['name']} must have a dockerCommand"
                )

    def test_database_is_defined(self, render_config):
        """At least one database must be defined."""
        assert len(render_config.get("databases", [])) > 0, (
            "Infrastructure must include at least one database"
        )

    def test_database_has_valid_config(self, render_config):
        """Database must have essential configuration."""
        for db in render_config["databases"]:
            assert "name" in db, "Database must have a name"
            assert "plan" in db, "Database must have a plan"
            assert "databaseName" in db, "Database must have a databaseName"
            assert "user" in db, "Database must have a user"

    def test_keyvalue_service_exists(self, render_config):
        """A keyvalue (Redis) service must exist."""
        kv_services = [
            s for s in render_config["services"]
            if s["type"] == "keyvalue"
        ]
        assert len(kv_services) > 0, (
            "Infrastructure must include a keyvalue (Redis) service"
        )

    def test_disk_mounts_configured_for_docker_services(self, render_config):
        """Docker services that need persistent storage should have disk mounts."""
        for svc in render_config["services"]:
            if svc.get("env") == "docker" and svc["type"] in ("web", "worker"):
                assert "disk" in svc, (
                    f"Docker service {svc['name']} should have a disk mount"
                )
                disk = svc["disk"]
                assert "mountPath" in disk, (
                    f"Disk for {svc['name']} must have a mountPath"
                )
                assert "sizeGB" in disk, (
                    f"Disk for {svc['name']} must have a sizeGB"
                )
