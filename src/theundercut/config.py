"""Centralised configuration helpers for The Undercut.

Use `get_settings()` instead of calling `os.getenv` around the codebase so
running locally vs. Render uses a consistent source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Optional

_DEFAULT_DB = "postgresql+psycopg2://theundercut:secret@localhost:5432/theundercut"
_DEFAULT_REDIS = "redis://localhost:6379/0"
_DEFAULT_SECRET = "dev-secret-key"
_DEFAULT_CACHE_DIR = "/data/cache"


def _env(key: str, default: Optional[str]) -> Optional[str]:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    redis_url: str
    secret_key: str
    fastf1_cache_dir: Path
    stripe_secret_key: Optional[str]
    stripe_webhook_secret: Optional[str]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings so modules share a single config instance."""
    cache_path = Path(_env("FASTF1_CACHE_DIR", _DEFAULT_CACHE_DIR))
    return Settings(
        environment=_env("APP_ENV", "local") or "local",
        database_url=_env("DATABASE_URL", _DEFAULT_DB) or _DEFAULT_DB,
        redis_url=_env("REDIS_URL", _DEFAULT_REDIS) or _DEFAULT_REDIS,
        secret_key=_env("SECRET_KEY", _DEFAULT_SECRET) or _DEFAULT_SECRET,
        fastf1_cache_dir=cache_path,
        stripe_secret_key=_env("STRIPE_SECRET_KEY", None),
        stripe_webhook_secret=_env("STRIPE_WEBHOOK_SECRET", None),
    )


__all__ = ["Settings", "get_settings"]
