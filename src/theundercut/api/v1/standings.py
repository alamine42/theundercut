"""Season standings API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.services.standings import fetch_season_standings

CACHE_TTL_SECONDS = 600  # 10 minutes

router = APIRouter(
    prefix="/api/v1/standings",
    tags=["standings"],
)


@router.get("/{season}")
def get_season_standings(season: int, db: Session = Depends(get_db)):
    """
    Get driver and constructor championship standings for a season.

    Returns points, wins, last-5 performance, positions gained, and more.
    """
    cache_key = f"standings:v1:{season}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    payload = fetch_season_standings(db, season)
    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload
