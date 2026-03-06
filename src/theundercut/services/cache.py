"""
Shared helpers for API/worker cache coordination.
"""

from __future__ import annotations

from typing import Iterable, Optional

from theundercut.adapters.redis_cache import redis_client


ANALYTICS_CACHE_PREFIX = "analytics:v1"
SESSION_CACHE_PREFIX = "session:v1"
SCHEDULE_CACHE_PREFIX = "schedule:v1"
WEEKEND_CACHE_PREFIX = "weekend:v1"
HISTORY_CACHE_PREFIX = "history:v1"
STRATEGY_CACHE_PREFIX = "strategy"


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


def normalize_session_type(session_type: str) -> str:
    """Normalize session type for cache key consistency."""
    return session_type.lower().replace(" ", "_")


def session_cache_key(season: int, rnd: int, session_type: str) -> str:
    """Build the canonical Redis key for session results."""
    normalized = normalize_session_type(session_type)
    return f"{SESSION_CACHE_PREFIX}:{season}:{rnd}:{normalized}"


def schedule_cache_key(season: int, rnd: int) -> str:
    """Build the canonical Redis key for race weekend schedule."""
    return f"{SCHEDULE_CACHE_PREFIX}:{season}:{rnd}"


def weekend_cache_key(season: int, rnd: int) -> str:
    """Build the canonical Redis key for aggregated weekend data."""
    return f"{WEEKEND_CACHE_PREFIX}:{season}:{rnd}"


def history_cache_key(season: int, circuit_id: str) -> str:
    """Build the canonical Redis key for circuit history."""
    return f"{HISTORY_CACHE_PREFIX}:{season}:{circuit_id}"


def invalidate_session_cache(season: int, rnd: int, session_type: Optional[str] = None) -> None:
    """
    Remove cached session results for a race.
    If session_type is provided, only invalidate that session.
    Otherwise, invalidate all sessions for the race.
    """
    if session_type:
        # Normalize the session type the same way as cache key generation
        normalized = normalize_session_type(session_type)
        key = session_cache_key(season, rnd, normalized)
        redis_client.delete(key)
    else:
        pattern = f"{SESSION_CACHE_PREFIX}:{season}:{rnd}:*"
        keys = list(redis_client.scan_iter(match=pattern))
        if keys:
            redis_client.delete(*keys)

    # Also invalidate the aggregated weekend cache
    weekend_key = weekend_cache_key(season, rnd)
    redis_client.delete(weekend_key)


def invalidate_schedule_cache(season: int, rnd: int) -> None:
    """Remove cached schedule for a race weekend."""
    key = schedule_cache_key(season, rnd)
    redis_client.delete(key)
    # Also invalidate the aggregated weekend cache
    weekend_key = weekend_cache_key(season, rnd)
    redis_client.delete(weekend_key)


def strategy_cache_key(season: int, rnd: int, driver: Optional[str] = None) -> str:
    """Build the canonical Redis key for strategy scores."""
    if driver:
        return f"{STRATEGY_CACHE_PREFIX}:{season}:{rnd}:{driver.upper()}"
    return f"{STRATEGY_CACHE_PREFIX}:{season}:{rnd}"


def invalidate_strategy_cache(season: int, rnd: int) -> None:
    """Remove all cached strategy score payloads for a race."""
    pattern = f"{STRATEGY_CACHE_PREFIX}:{season}:{rnd}*"
    keys = list(redis_client.scan_iter(match=pattern))
    if keys:
        redis_client.delete(*keys)


def invalidate_race_weekend_cache(season: int, rnd: int) -> None:
    """
    Invalidate all caches for a race weekend.
    Called when CalendarEvent status changes or classifications are amended.
    """
    invalidate_analytics_cache(season, rnd)
    invalidate_session_cache(season, rnd)
    invalidate_schedule_cache(season, rnd)
    invalidate_strategy_cache(season, rnd)


__all__ = [
    "analytics_cache_key",
    "invalidate_analytics_cache",
    "ANALYTICS_CACHE_PREFIX",
    "session_cache_key",
    "schedule_cache_key",
    "weekend_cache_key",
    "history_cache_key",
    "strategy_cache_key",
    "invalidate_session_cache",
    "invalidate_schedule_cache",
    "invalidate_strategy_cache",
    "invalidate_race_weekend_cache",
    "SESSION_CACHE_PREFIX",
    "SCHEDULE_CACHE_PREFIX",
    "WEEKEND_CACHE_PREFIX",
    "HISTORY_CACHE_PREFIX",
    "STRATEGY_CACHE_PREFIX",
]
