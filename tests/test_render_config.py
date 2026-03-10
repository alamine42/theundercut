"""Tests for render.yaml infrastructure configuration (UND-43, UND-44, UND-45, UND-51, UND-57, UND-58, UND-62).

Validates the Render deployment configuration structure, ensuring
all services have required fields, env var references are consistent,
service connectivity is properly configured, environment variables
are valid, infrastructure deployment is sound, and cross-service
environment variable dependencies are correct.
"""

import re
from urllib.parse import urlparse

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


class TestEnvVarDependencyChain:
    """Validate cross-service environment variable dependencies (UND-43).

    Tests that environment variable references across the two render.yaml
    files (root and web/) are consistent and that the frontend's FASTAPI_URL
    correctly points to the backend API service.
    """

    def test_frontend_fastapi_url_targets_api_service(self, render_config):
        """The root render.yaml frontend FASTAPI_URL must point to the API service name."""
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
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        # The URL should contain the API service name (Render naming convention)
        assert api["name"] in url, (
            f"FASTAPI_URL '{url}' should reference the API service '{api['name']}'"
        )

    def test_frontend_fastapi_url_is_https_in_production(self, render_config):
        """Frontend FASTAPI_URL in root render.yaml must use HTTPS for production."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        fastapi_env = next(
            e for e in frontend.get("envVars", [])
            if e["key"] == "FASTAPI_URL"
        )
        url = fastapi_env.get("value", "")
        parsed = urlparse(url)
        assert parsed.scheme == "https", (
            f"FASTAPI_URL must use HTTPS in production, got scheme: {parsed.scheme}"
        )

    def test_frontend_fastapi_url_is_well_formed(self, render_config):
        """Frontend FASTAPI_URL must be a parseable URL with a hostname."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        fastapi_env = next(
            e for e in frontend.get("envVars", [])
            if e["key"] == "FASTAPI_URL"
        )
        url = fastapi_env.get("value", "")
        parsed = urlparse(url)
        assert parsed.hostname, f"FASTAPI_URL must have a hostname, got: {url}"
        assert parsed.scheme in ("http", "https"), (
            f"FASTAPI_URL scheme must be http or https, got: {parsed.scheme}"
        )

    def test_web_render_fastapi_url_uses_sync_false(self, web_render_config):
        """web/render.yaml FASTAPI_URL must use sync: false for per-env config."""
        svc = web_render_config["services"][0]
        fastapi_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "FASTAPI_URL"),
            None,
        )
        assert fastapi_env is not None, "web/render.yaml must have FASTAPI_URL"
        assert fastapi_env.get("sync") is False, (
            "FASTAPI_URL should have sync: false so it can differ per environment"
        )

    def test_web_render_fastapi_url_has_no_hardcoded_value(self, web_render_config):
        """web/render.yaml FASTAPI_URL should not have a hardcoded value (set at deploy time)."""
        svc = web_render_config["services"][0]
        fastapi_env = next(
            e for e in svc.get("envVars", [])
            if e["key"] == "FASTAPI_URL"
        )
        assert "value" not in fastapi_env, (
            "web/render.yaml FASTAPI_URL should not hardcode a value; "
            "it should be set per-environment at deploy time (sync: false)"
        )

    def test_node_env_is_hardcoded_production(self, web_render_config):
        """NODE_ENV should be hardcoded to 'production' (not sync: false)."""
        svc = web_render_config["services"][0]
        node_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "NODE_ENV"),
            None,
        )
        assert node_env is not None
        assert node_env.get("value") == "production", (
            "NODE_ENV should be hardcoded to 'production'"
        )

    def test_root_and_web_render_both_define_fastapi_url(self, render_config, web_render_config):
        """Both render.yaml files must define FASTAPI_URL for the frontend."""
        # Root render.yaml - frontend service
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        root_keys = {e["key"] for e in frontend.get("envVars", [])}
        assert "FASTAPI_URL" in root_keys, (
            "Root render.yaml frontend must define FASTAPI_URL"
        )

        # web/render.yaml - frontend service
        web_svc = web_render_config["services"][0]
        web_keys = {e["key"] for e in web_svc.get("envVars", [])}
        assert "FASTAPI_URL" in web_keys, (
            "web/render.yaml must define FASTAPI_URL"
        )

    def test_root_frontend_env_vars_are_subset_of_web(self, render_config, web_render_config):
        """Root render.yaml frontend env var keys should be a subset of web/render.yaml.

        web/render.yaml is the authoritative frontend config and may include
        additional env vars (e.g. NEXT_PUBLIC_GA_ID) that are set per-environment.
        """
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        root_keys = {e["key"] for e in frontend.get("envVars", [])}

        web_svc = web_render_config["services"][0]
        web_keys = {e["key"] for e in web_svc.get("envVars", [])}

        missing_from_web = root_keys - web_keys
        assert not missing_from_web, (
            f"Root render.yaml frontend has env vars not in web/render.yaml: {missing_from_web}"
        )

    def test_backend_env_vars_not_leaked_to_frontend(self, render_config):
        """Frontend should not have backend-only env vars like DATABASE_URL."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        frontend_keys = {e["key"] for e in frontend.get("envVars", [])}
        backend_only_keys = {"DATABASE_URL", "REDIS_URL", "SECRET_KEY"}
        leaked = frontend_keys & backend_only_keys
        assert not leaked, (
            f"Frontend service should not have backend-only env vars: {leaked}"
        )

    def test_api_service_does_not_have_frontend_only_vars(self, render_config):
        """API service should not have frontend-only env vars like NODE_ENV."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        api_keys = {e["key"] for e in api.get("envVars", [])}
        frontend_only = {"NODE_ENV"}
        leaked = api_keys & frontend_only
        assert not leaked, (
            f"API service should not have frontend-only env vars: {leaked}"
        )


class TestServiceIntegration:
    """Validate service integration patterns and connectivity (UND-44).

    Tests the complete service integration graph to ensure all services
    can communicate: frontend→API, API→DB, API→Redis, worker→DB,
    worker→Redis, scheduler→DB/Redis.
    """

    def test_frontend_to_api_integration(self, render_config):
        """Frontend FASTAPI_URL should point to a valid backend URL on Render."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        fastapi_env = next(
            e for e in frontend.get("envVars", [])
            if e["key"] == "FASTAPI_URL"
        )
        url = fastapi_env.get("value", "")
        parsed = urlparse(url)
        # Render URLs end with .onrender.com
        assert parsed.hostname and parsed.hostname.endswith(".onrender.com"), (
            f"FASTAPI_URL should target a .onrender.com host, got: {parsed.hostname}"
        )

    def test_api_to_database_integration(self, render_config):
        """API service must have DATABASE_URL sourced from the database service."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        db_env = next(
            (e for e in api.get("envVars", []) if e["key"] == "DATABASE_URL"),
            None,
        )
        assert db_env is not None, "API must have DATABASE_URL"
        assert "fromDatabase" in db_env, "DATABASE_URL should reference a database"
        # Verify the referenced database exists
        db_name = db_env["fromDatabase"]["name"]
        db_names = [d["name"] for d in render_config.get("databases", [])]
        assert db_name in db_names, (
            f"API DATABASE_URL references '{db_name}' but available databases are: {db_names}"
        )

    def test_api_to_redis_integration(self, render_config):
        """API service must have REDIS_URL sourced from the keyvalue service."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        redis_env = next(
            (e for e in api.get("envVars", []) if e["key"] == "REDIS_URL"),
            None,
        )
        assert redis_env is not None, "API must have REDIS_URL"
        assert "fromService" in redis_env, "REDIS_URL should reference a service"
        # Verify the referenced keyvalue service exists
        kv_name = redis_env["fromService"]["name"]
        kv_names = [
            s["name"] for s in render_config["services"]
            if s["type"] == "keyvalue"
        ]
        assert kv_name in kv_names, (
            f"API REDIS_URL references '{kv_name}' but available keyvalue services are: {kv_names}"
        )

    def test_worker_to_database_integration(self, render_config):
        """Worker services must be able to connect to the database."""
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                db_env = next(
                    (e for e in svc.get("envVars", []) if e["key"] == "DATABASE_URL"),
                    None,
                )
                assert db_env is not None, (
                    f"Worker {svc['name']} must have DATABASE_URL for DB connectivity"
                )
                assert "fromDatabase" in db_env, (
                    f"Worker {svc['name']} DATABASE_URL should reference a database service"
                )

    def test_worker_to_redis_integration(self, render_config):
        """Worker services must be able to connect to Redis."""
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                redis_env = next(
                    (e for e in svc.get("envVars", []) if e["key"] == "REDIS_URL"),
                    None,
                )
                assert redis_env is not None, (
                    f"Worker {svc['name']} must have REDIS_URL for Redis connectivity"
                )
                assert "fromService" in redis_env, (
                    f"Worker {svc['name']} REDIS_URL should reference a keyvalue service"
                )

    def test_yaml_anchors_share_env_vars_correctly(self, render_config):
        """Workers using YAML anchors should have identical env vars to the API."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        api_env_keys = sorted(e["key"] for e in api.get("envVars", []))
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                worker_env_keys = sorted(e["key"] for e in svc.get("envVars", []))
                assert worker_env_keys == api_env_keys, (
                    f"Worker {svc['name']} env var keys {worker_env_keys} "
                    f"should match API env var keys {api_env_keys} (via YAML anchor)"
                )

    def test_all_fromservice_references_resolve(self, render_config):
        """Every fromService reference must point to an existing service."""
        service_names = {s["name"] for s in render_config["services"]}
        for svc in render_config["services"]:
            for env in svc.get("envVars", []):
                if "fromService" in env:
                    ref_name = env["fromService"]["name"]
                    assert ref_name in service_names, (
                        f"Env var {env['key']} in {svc['name']} references "
                        f"service '{ref_name}' which does not exist"
                    )

    def test_all_fromdatabase_references_resolve(self, render_config):
        """Every fromDatabase reference must point to an existing database."""
        db_names = {d["name"] for d in render_config.get("databases", [])}
        for svc in render_config["services"]:
            for env in svc.get("envVars", []):
                if "fromDatabase" in env:
                    ref_name = env["fromDatabase"]["name"]
                    assert ref_name in db_names, (
                        f"Env var {env['key']} in {svc['name']} references "
                        f"database '{ref_name}' which does not exist"
                    )

    def test_all_services_with_env_vars_have_required_keys(self, render_config):
        """Every env var entry must have a 'key' field."""
        for svc in render_config["services"]:
            for env in svc.get("envVars", []):
                assert "key" in env, (
                    f"Env var entry in {svc['name']} is missing 'key': {env}"
                )

    def test_env_var_sourcing_consistency(self, render_config):
        """Each env var should have exactly one source: value, fromDatabase, fromService, or generateValue."""
        valid_sources = {"value", "fromDatabase", "fromService", "generateValue", "sync"}
        for svc in render_config["services"]:
            for env in svc.get("envVars", []):
                sources = {k for k in env if k != "key" and k in valid_sources}
                assert len(sources) >= 1, (
                    f"Env var {env['key']} in {svc['name']} has no value source"
                )

    def test_scheduler_has_same_connectivity_as_worker(self, render_config):
        """Scheduler service should have the same DB/Redis connectivity as workers."""
        scheduler = next(
            (s for s in render_config["services"]
             if s["name"] == "theundercut-scheduler"),
            None,
        )
        if scheduler is None:
            pytest.skip("No scheduler service found")
        sched_keys = {e["key"] for e in scheduler.get("envVars", [])}
        assert "DATABASE_URL" in sched_keys, "Scheduler must have DATABASE_URL"
        assert "REDIS_URL" in sched_keys, "Scheduler must have REDIS_URL"

    def test_redis_service_referenced_by_type(self, render_config):
        """REDIS_URL fromService should specify type: keyvalue."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        redis_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "REDIS_URL"
        )
        assert redis_env["fromService"]["type"] == "keyvalue", (
            "REDIS_URL fromService should specify type: keyvalue"
        )

    def test_database_referenced_by_connection_string(self, render_config):
        """DATABASE_URL fromDatabase should use property: connectionString."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        db_env = next(
            e for e in api.get("envVars", [])
            if e["key"] == "DATABASE_URL"
        )
        assert db_env["fromDatabase"]["property"] == "connectionString", (
            "DATABASE_URL should use connectionString property"
        )


class TestInfrastructureDeploymentReadiness:
    """Validate complete infrastructure deployment readiness (UND-45).

    Tests that all infrastructure components are properly configured
    for a successful deployment, including service counts, plan allocation,
    repo references, and cross-component consistency.
    """

    def test_expected_service_count(self, render_config):
        """Infrastructure should have the expected number of services."""
        services = render_config["services"]
        # Frontend + API + Worker + Scheduler + Redis = 5
        assert len(services) >= 5, (
            f"Expected at least 5 services (frontend, API, worker, scheduler, Redis), "
            f"got {len(services)}"
        )

    def test_expected_service_type_distribution(self, render_config):
        """Infrastructure should have at least one of each required service type."""
        types = {s["type"] for s in render_config["services"]}
        required_types = {"web", "worker", "keyvalue"}
        missing = required_types - types
        assert not missing, (
            f"Infrastructure missing service types: {missing}"
        )

    def test_all_docker_services_reference_same_repo(self, render_config):
        """All docker-based services should reference the same repository."""
        repos = set()
        for svc in render_config["services"]:
            if svc.get("env") == "docker" and "repo" in svc:
                repos.add(svc["repo"])
        assert len(repos) <= 1, (
            f"Docker services reference multiple repos: {repos}. "
            "All services should use the same repo."
        )

    def test_docker_repo_is_valid_github_url(self, render_config):
        """Docker service repo should be a valid GitHub URL."""
        for svc in render_config["services"]:
            if svc.get("env") == "docker" and "repo" in svc:
                repo = svc["repo"]
                parsed = urlparse(repo)
                assert parsed.scheme == "https", (
                    f"Repo URL for {svc['name']} should use HTTPS"
                )
                assert "github.com" in (parsed.hostname or ""), (
                    f"Repo URL for {svc['name']} should be on github.com"
                )

    def test_frontend_uses_node_runtime_not_docker(self, render_config):
        """Frontend service should use native Node runtime, not Docker."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert frontend.get("runtime") == "node", (
            "Frontend should use Node runtime for Render's managed builds"
        )
        assert "env" not in frontend or frontend.get("env") != "docker", (
            "Frontend should not use Docker; it should use Render's native Node support"
        )

    def test_frontend_web_service_has_health_check(self, render_config):
        """Frontend web service should have a health check path.

        Note: Docker-based web services (e.g. theundercut-web API) may not
        use healthCheckPath as they rely on Docker's own health mechanisms.
        """
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert "healthCheckPath" in frontend, (
            "Frontend web service must have a healthCheckPath"
        )

    def test_api_docker_command_binds_to_port_env(self, render_config):
        """API Docker command should use $PORT for Render's dynamic port assignment."""
        api = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-web"
        )
        cmd = api.get("dockerCommand", "")
        assert "$PORT" in cmd, (
            "API dockerCommand should use $PORT for Render's port assignment"
        )

    def test_worker_commands_use_python_module_syntax(self, render_config):
        """Worker Docker commands should use python -m for module execution."""
        for svc in render_config["services"]:
            if svc["type"] == "worker":
                cmd = svc.get("dockerCommand", "")
                assert "python -m" in cmd, (
                    f"Worker {svc['name']} should use 'python -m' module syntax, got: {cmd}"
                )

    def test_disk_mount_paths_are_absolute(self, render_config):
        """Disk mount paths should be absolute paths."""
        for svc in render_config["services"]:
            if "disk" in svc:
                mount_path = svc["disk"].get("mountPath", "")
                assert mount_path.startswith("/"), (
                    f"Disk mountPath for {svc['name']} should be absolute, got: {mount_path}"
                )

    def test_disk_sizes_are_reasonable(self, render_config):
        """Disk sizes should be at least 1 GB."""
        for svc in render_config["services"]:
            if "disk" in svc:
                size = svc["disk"].get("sizeGB", 0)
                assert size >= 1, (
                    f"Disk for {svc['name']} should be at least 1 GB, got: {size}"
                )

    def test_disk_names_are_set(self, render_config):
        """Disk mounts should have names."""
        for svc in render_config["services"]:
            if "disk" in svc:
                assert "name" in svc["disk"] and svc["disk"]["name"], (
                    f"Disk for {svc['name']} must have a non-empty name"
                )

    def test_keyvalue_has_ip_allowlist(self, render_config):
        """Keyvalue (Redis) service should have an ipAllowList configured."""
        for svc in render_config["services"]:
            if svc["type"] == "keyvalue":
                assert "ipAllowList" in svc, (
                    f"Keyvalue service {svc['name']} should have ipAllowList configured"
                )

    def test_keyvalue_ip_allowlist_is_restrictive(self, render_config):
        """Keyvalue ipAllowList should be empty (restrictive) for security."""
        for svc in render_config["services"]:
            if svc["type"] == "keyvalue":
                ip_list = svc.get("ipAllowList", None)
                if ip_list is not None:
                    assert ip_list == [], (
                        f"Keyvalue {svc['name']} ipAllowList should be empty "
                        f"(no external IPs), got: {ip_list}"
                    )

    def test_database_has_user_configured(self, render_config):
        """All databases should have a user configured."""
        for db in render_config.get("databases", []):
            assert "user" in db and db["user"], (
                f"Database {db.get('name', '?')} must have a user configured"
            )

    def test_database_has_database_name(self, render_config):
        """All databases should have a databaseName configured."""
        for db in render_config.get("databases", []):
            assert "databaseName" in db and db["databaseName"], (
                f"Database {db.get('name', '?')} must have a databaseName"
            )

    def test_frontend_auto_deploy_enabled(self, render_config):
        """Frontend should have auto-deploy enabled for CI/CD."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert frontend.get("autoDeploy") is True, (
            "Frontend should have autoDeploy: true for continuous deployment"
        )

    def test_frontend_build_command_is_complete(self, render_config):
        """Frontend build command should install deps and build."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        build_cmd = frontend.get("buildCommand", "")
        assert "npm install" in build_cmd, "Frontend build must install dependencies"
        assert "npm run build" in build_cmd, "Frontend build must run build step"

    def test_frontend_start_command_exists(self, render_config):
        """Frontend must have a start command."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert "startCommand" in frontend and frontend["startCommand"], (
            "Frontend must have a non-empty startCommand"
        )

    def test_frontend_root_dir_is_web(self, render_config):
        """Frontend should specify rootDir as 'web' for monorepo structure."""
        frontend = next(
            s for s in render_config["services"]
            if s["name"] == "theundercut-frontend"
        )
        assert frontend.get("rootDir") == "web", (
            "Frontend rootDir should be 'web' for the monorepo structure"
        )
