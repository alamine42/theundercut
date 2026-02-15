"""
Shared helpers for API/worker cache coordination.
"""

from __future__ import annotations

from typing import Iterable, Optional

from theundercut.adapters.redis_cache import redis_client


ANALYTICS_CACHE_PREFIX = "analytics:v1"


def analytics_cache_key(
    season: int,
    rnd: int,
    drivers: Optional[Iterable[str]] = None,
) -> str:
    """
    Build the canonical Redis key for race analytics payloads.
    Drivers list is sorted so `/api/v1/analytics` can cache per filter combo.
    """
    if drivers:
        driver_part = ",".join(sorted(set(drivers)))
    else:
        driver_part = "all"
    return f"{ANALYTICS_CACHE_PREFIX}:{season}:{rnd}:{driver_part}"


def invalidate_analytics_cache(season: int, rnd: int) -> None:
    """
    Remove all cached payloads for a race (covers every driver filter combo).
    """
    pattern = f"{ANALYTICS_CACHE_PREFIX}:{season}:{rnd}:*"
    keys = list(redis_client.scan_iter(match=pattern))
    if not keys:
        return
    redis_client.delete(*keys)


__all__ = ["analytics_cache_key", "invalidate_analytics_cache", "ANALYTICS_CACHE_PREFIX"]
