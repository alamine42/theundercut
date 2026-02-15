"""Analytics API endpoints (laps, stints, grades)."""

from __future__ import annotations

import json
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.services.analytics import fetch_race_analytics
from theundercut.services.cache import analytics_cache_key

CACHE_TTL_SECONDS = 300

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
)


@router.get("/{season}/{round}")
def get_race_analytics(
    season: int,
    round: int,
    drivers: Optional[List[str]] = Query(
        default=None,
        description="Optional list of driver codes (e.g. VER, HAM) to filter",
    ),
    db: Session = Depends(get_db),
):
    key = analytics_cache_key(season, round, drivers)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    payload = fetch_race_analytics(db, season, round, drivers)
    redis_client.setex(key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload
