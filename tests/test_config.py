"""Tests for configuration parsing and environment variable handling (UND-43).

Verifies that Settings loads correctly from environment variables,
applies defaults, and handles edge cases like missing or empty values.
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
