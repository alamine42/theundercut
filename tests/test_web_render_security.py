"""Tests for web/render.yaml sensitive configuration exposure (UND-35).

Validates that the frontend deployment configuration does not contain
hardcoded secrets, credentials, or sensitive values that could be
exploited if the repository is public.
"""

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def web_render_config():
    path = ROOT / "web" / "render.yaml"
    if not path.exists():
        pytest.skip("web/render.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def web_render_raw():
    path = ROOT / "web" / "render.yaml"
    if not path.exists():
        pytest.skip("web/render.yaml not found")
    return path.read_text()


class TestNoHardcodedSecrets:
    """Verify no secrets or credentials are hardcoded (UND-35)."""

    SENSITIVE_PATTERNS = [
        "password",
        "secret",
        "token",
        "api_key",
        "api-key",
        "private_key",
        "private-key",
        "credentials",
    ]

    def test_no_sensitive_env_var_values(self, web_render_config):
        """Env vars with sensitive-sounding names should not have hardcoded values."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            key = env.get("key", "").lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in key:
                    assert "value" not in env, (
                        f"Env var '{env['key']}' looks sensitive and should "
                        "not have a hardcoded 'value' in render.yaml"
                    )

    def test_fastapi_url_not_hardcoded(self, web_render_config):
        """FASTAPI_URL should use sync:false, not a hardcoded value."""
        svc = web_render_config["services"][0]
        fastapi_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "FASTAPI_URL"),
            None,
        )
        assert fastapi_env is not None
        assert "value" not in fastapi_env, (
            "FASTAPI_URL should not be hardcoded — use sync:false for Render dashboard"
        )
        assert fastapi_env.get("sync") is False

    def test_ga_id_not_hardcoded(self, web_render_config):
        """NEXT_PUBLIC_GA_ID should use sync:false, not a hardcoded value."""
        svc = web_render_config["services"][0]
        ga_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "NEXT_PUBLIC_GA_ID"),
            None,
        )
        assert ga_env is not None
        assert "value" not in ga_env, (
            "GA ID should not be hardcoded — use sync:false for Render dashboard"
        )

    def test_node_env_value_is_acceptable(self, web_render_config):
        """NODE_ENV=production is acceptable (not a secret)."""
        svc = web_render_config["services"][0]
        node_env = next(
            (e for e in svc.get("envVars", []) if e["key"] == "NODE_ENV"),
            None,
        )
        assert node_env is not None
        # NODE_ENV=production is fine — it's not sensitive
        if "value" in node_env:
            assert node_env["value"] in ("production", "development", "test"), (
                f"NODE_ENV has unexpected value: {node_env['value']}"
            )


class TestNoInternalUrlExposure:
    """Verify internal URLs and architecture details are not exposed (UND-35)."""

    def test_no_internal_ip_addresses(self, web_render_raw):
        """Config should not contain internal IP addresses."""
        import re
        # Match private IPs: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
        private_ip = re.compile(
            r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
            r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|'
            r'192\.168\.\d{1,3}\.\d{1,3})\b'
        )
        matches = private_ip.findall(web_render_raw)
        assert len(matches) == 0, (
            f"Config should not contain private IP addresses: {matches}"
        )

    def test_no_database_connection_strings(self, web_render_raw):
        """Config should not contain database connection strings."""
        lower = web_render_raw.lower()
        assert "postgresql://" not in lower, "Should not contain postgres connection string"
        assert "mysql://" not in lower, "Should not contain mysql connection string"
        assert "redis://" not in lower, "Should not contain redis connection string"

    def test_no_aws_or_cloud_keys(self, web_render_raw):
        """Config should not contain cloud provider access keys."""
        assert "AKIA" not in web_render_raw, "Should not contain AWS access key prefix"
        assert "sk-" not in web_render_raw or "sk-" in "disk:", (
            "Should not contain API secret keys"
        )


class TestDeploymentConfigStructure:
    """Verify deployment config follows security best practices (UND-35)."""

    def test_sensitive_vars_use_sync_false(self, web_render_config):
        """Sensitive env vars should use sync:false (set via Render dashboard)."""
        svc = web_render_config["services"][0]
        # These vars should be set via dashboard, not in yaml
        dashboard_vars = {"FASTAPI_URL", "NEXT_PUBLIC_GA_ID"}
        for env in svc.get("envVars", []):
            if env["key"] in dashboard_vars:
                assert env.get("sync") is False, (
                    f"{env['key']} should use sync:false to be set via dashboard"
                )

    def test_no_generate_value_in_frontend(self, web_render_config):
        """Frontend should not have generateValue (that's for backend secrets)."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            assert "generateValue" not in env, (
                f"Frontend env var '{env['key']}' should not use generateValue"
            )

    def test_no_from_database_in_frontend(self, web_render_config):
        """Frontend should not reference databases directly."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            assert "fromDatabase" not in env, (
                f"Frontend env var '{env['key']}' should not reference a database"
            )

    def test_no_from_service_in_frontend(self, web_render_config):
        """Frontend should not reference backend services directly."""
        svc = web_render_config["services"][0]
        for env in svc.get("envVars", []):
            assert "fromService" not in env, (
                f"Frontend env var '{env['key']}' should not reference a service"
            )
