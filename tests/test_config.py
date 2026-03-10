"""Tests for configuration parsing and environment variable handling (UND-43).

Verifies that Settings loads correctly from environment variables,
applies defaults, handles edge cases like missing or empty values,
and validates environment variable dependency chains across services.
"""

import pytest
from unittest.mock import patch

from theundercut.config import Settings, get_settings, _env


class TestEnvHelper:
    """Tests for the _env helper function."""

    def test_returns_env_value_when_set(self):
        with patch.dict("os.environ", {"TEST_KEY": "hello"}):
            assert _env("TEST_KEY", "default") == "hello"

    def test_returns_default_when_not_set(self):
        with patch.dict("os.environ", {}, clear=True):
            assert _env("MISSING_KEY", "fallback") == "fallback"

    def test_returns_default_when_empty_string(self):
        with patch.dict("os.environ", {"EMPTY_KEY": ""}):
            assert _env("EMPTY_KEY", "fallback") == "fallback"

    def test_returns_none_default(self):
        with patch.dict("os.environ", {}, clear=True):
            assert _env("MISSING_KEY", None) is None


class TestGetSettings:
    """Tests for the get_settings factory function."""

    def setup_method(self):
        # Clear lru_cache between tests
        get_settings.cache_clear()

    def test_defaults_when_no_env_vars(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        assert settings.environment == "local"
        assert "localhost" in settings.database_url
        assert "localhost" in settings.redis_url
        assert settings.secret_key == "dev-secret-key"
        assert settings.stripe_secret_key is None
        assert settings.stripe_webhook_secret is None

    def test_postgres_url_rewritten_to_postgresql(self):
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgres://user:pass@host:5432/db",
        }, clear=True):
            settings = get_settings()
        assert settings.database_url.startswith("postgresql://")
        assert "postgres://" not in settings.database_url

    def test_postgresql_url_not_double_rewritten(self):
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        }, clear=True):
            settings = get_settings()
        assert settings.database_url == "postgresql://user:pass@host:5432/db"

    def test_custom_redis_url(self):
        with patch.dict("os.environ", {
            "REDIS_URL": "redis://:password@redis-host:6380/1",
        }, clear=True):
            settings = get_settings()
        assert settings.redis_url == "redis://:password@redis-host:6380/1"

    def test_custom_environment(self):
        with patch.dict("os.environ", {"APP_ENV": "production"}, clear=True):
            settings = get_settings()
        assert settings.environment == "production"

    def test_custom_cache_dir(self):
        with patch.dict("os.environ", {
            "FASTF1_CACHE_DIR": "/tmp/test_cache",
        }, clear=True):
            settings = get_settings()
        assert str(settings.fastf1_cache_dir) == "/tmp/test_cache"

    def test_settings_is_frozen(self):
        get_settings.cache_clear()
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        with pytest.raises(AttributeError):
            settings.environment = "changed"

    def test_stripe_keys_loaded(self):
        with patch.dict("os.environ", {
            "STRIPE_SECRET_KEY": "sk_test_123",
            "STRIPE_WEBHOOK_SECRET": "whsec_456",
        }, clear=True):
            settings = get_settings()
        assert settings.stripe_secret_key == "sk_test_123"
        assert settings.stripe_webhook_secret == "whsec_456"


class TestEnvVarDependencies:
    """Tests for environment variable dependency chain validation (UND-43).

    Validates that the application handles environment variable dependencies
    correctly across different environments and that missing or invalid
    values are handled gracefully.
    """

    def setup_method(self):
        get_settings.cache_clear()

    def test_database_url_dependency_with_render_format(self):
        """Render provides postgres:// URLs; app should rewrite to postgresql://."""
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgres://theundercut:pass@host:5432/theundercut",
        }, clear=True):
            settings = get_settings()
        assert settings.database_url.startswith("postgresql://"), (
            "Render-provided postgres:// URL should be rewritten to postgresql://"
        )

    def test_redis_url_dependency_from_render(self):
        """REDIS_URL from Render keyvalue service should be accepted as-is."""
        render_redis = "redis://:password@oregon-redis.render.com:6379"
        with patch.dict("os.environ", {
            "REDIS_URL": render_redis,
        }, clear=True):
            settings = get_settings()
        assert settings.redis_url == render_redis

    def test_secret_key_from_render_generated_value(self):
        """SECRET_KEY from Render's generateValue should be accepted."""
        with patch.dict("os.environ", {
            "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
        }, clear=True):
            settings = get_settings()
        assert settings.secret_key == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

    def test_all_render_env_vars_together(self):
        """All Render-provided env vars should work together without conflict."""
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgres://theundercut:pass@db-host:5432/theundercut",
            "REDIS_URL": "redis://:pass@redis-host:6379",
            "SECRET_KEY": "render-generated-key-123",
            "APP_ENV": "production",
        }, clear=True):
            settings = get_settings()
        assert settings.database_url.startswith("postgresql://")
        assert "redis-host" in settings.redis_url
        assert settings.secret_key == "render-generated-key-123"
        assert settings.environment == "production"

    def test_missing_database_url_falls_back_to_localhost(self):
        """Missing DATABASE_URL should default to localhost for local dev."""
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        assert "localhost" in settings.database_url, (
            "Missing DATABASE_URL should default to localhost"
        )

    def test_missing_redis_url_falls_back_to_localhost(self):
        """Missing REDIS_URL should default to localhost for local dev."""
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        assert "localhost" in settings.redis_url, (
            "Missing REDIS_URL should default to localhost"
        )

    def test_missing_secret_key_falls_back_to_dev_default(self):
        """Missing SECRET_KEY should default to dev secret (not production-safe)."""
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        assert settings.secret_key == "dev-secret-key", (
            "Missing SECRET_KEY should default to 'dev-secret-key'"
        )

    def test_empty_database_url_falls_back_to_default(self):
        """Empty DATABASE_URL should be treated as missing."""
        with patch.dict("os.environ", {"DATABASE_URL": ""}, clear=True):
            settings = get_settings()
        assert "localhost" in settings.database_url, (
            "Empty DATABASE_URL should fall back to localhost default"
        )

    def test_empty_redis_url_falls_back_to_default(self):
        """Empty REDIS_URL should be treated as missing."""
        with patch.dict("os.environ", {"REDIS_URL": ""}, clear=True):
            settings = get_settings()
        assert "localhost" in settings.redis_url, (
            "Empty REDIS_URL should fall back to localhost default"
        )

    def test_empty_secret_key_falls_back_to_default(self):
        """Empty SECRET_KEY should be treated as missing."""
        with patch.dict("os.environ", {"SECRET_KEY": ""}, clear=True):
            settings = get_settings()
        assert settings.secret_key == "dev-secret-key"

    def test_production_env_with_all_deps(self):
        """Production environment should work when all dependencies are provided."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql://user:pass@prod-db:5432/app",
            "REDIS_URL": "redis://:pass@prod-redis:6379",
            "SECRET_KEY": "prod-secret-key-very-long-and-secure",
            "STRIPE_SECRET_KEY": "sk_live_xxx",
            "STRIPE_WEBHOOK_SECRET": "whsec_xxx",
        }, clear=True):
            settings = get_settings()
        assert settings.environment == "production"
        assert "prod-db" in settings.database_url
        assert "prod-redis" in settings.redis_url
        assert settings.secret_key == "prod-secret-key-very-long-and-secure"
        assert settings.stripe_secret_key == "sk_live_xxx"
        assert settings.stripe_webhook_secret == "whsec_xxx"

    def test_local_env_defaults_are_consistent(self):
        """Local dev defaults should form a consistent set."""
        with patch.dict("os.environ", {}, clear=True):
            settings = get_settings()
        # All defaults should reference localhost
        assert "localhost" in settings.database_url
        assert "localhost" in settings.redis_url
        # Environment should be 'local'
        assert settings.environment == "local"
        # Dev secret should be present
        assert settings.secret_key == "dev-secret-key"

    def test_partial_env_vars_still_work(self):
        """Providing only some env vars should not break others' defaults."""
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://custom:pass@custom-host:5432/db",
        }, clear=True):
            settings = get_settings()
        assert "custom-host" in settings.database_url
        # Other vars should still have defaults
        assert "localhost" in settings.redis_url
        assert settings.secret_key == "dev-secret-key"

    def test_settings_caching(self):
        """get_settings should return cached instance (lru_cache)."""
        get_settings.cache_clear()
        with patch.dict("os.environ", {}, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()
        assert settings1 is settings2, (
            "get_settings should return the same cached instance"
        )

    def test_database_url_preserves_query_params(self):
        """DATABASE_URL with query parameters should preserve them."""
        url = "postgres://user:pass@host:5432/db?sslmode=require"
        with patch.dict("os.environ", {"DATABASE_URL": url}, clear=True):
            settings = get_settings()
        assert "sslmode=require" in settings.database_url
        assert settings.database_url.startswith("postgresql://")
