"""Pre-season testing API endpoints."""

from __future__ import annotations

import json
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.models import TestingEvent, TestingSession, TestingLap, TestingStint

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600  # 10 minutes for active events
COMPLETED_CACHE_TTL_SECONDS = 86400  # 24 hours for completed events

router = APIRouter(
    prefix="/api/v1/testing",
    tags=["testing"],
)


def _format_lap_time(ms: Optional[float]) -> Optional[str]:
    """Format milliseconds as M:SS.mmm string."""
    if ms is None:
        return None
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"


def _testing_events_cache_key(season: int) -> str:
    """Cache key for testing events list."""
    return f"testing:events:{season}"


def _testing_day_cache_key(season: int, event_id: str, day: int, drivers: Optional[List[str]] = None) -> str:
    """Cache key for testing day data."""
    driver_hash = "_".join(sorted(drivers)) if drivers else "all"
    return f"testing:day:{season}:{event_id}:{day}:{driver_hash}"


def _testing_laps_cache_key(season: int, event_id: str, day: int, drivers: Optional[List[str]], offset: int, limit: int) -> str:
    """Cache key for paginated testing laps."""
    driver_hash = "_".join(sorted(drivers)) if drivers else "all"
    return f"testing:laps:{season}:{event_id}:{day}:{driver_hash}:{offset}:{limit}"


@router.get("/{season}")
def get_testing_events(
    season: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get all testing events for a season."""
    print(f"DEBUG: season={season}, type={type(season)}", flush=True)

    cache_key = _testing_events_cache_key(season)
    cached = redis_client.get(cache_key)
    if cached:
        print(f"DEBUG: returning cached result", flush=True)
        return json.loads(cached)

    print(f"DEBUG: no cache, querying DB", flush=True)

    # Query testing events for the season
    stmt = select(TestingEvent).where(TestingEvent.season == season).order_by(TestingEvent.start_date)
    events = db.execute(stmt).scalars().all()
    print(f"DEBUG: ORM query returned {len(events)} events", flush=True)

    # Also try raw SQL
    from sqlalchemy import text
    raw = db.execute(text("SELECT COUNT(*) FROM testing_events WHERE season = :s"), {"s": season}).scalar()
    print(f"DEBUG: Raw SQL count for season {season}: {raw}", flush=True)

    # Build response
    events_data = []
    for event in events:
        events_data.append({
            "event_id": event.event_id,
            "event_name": event.event_name,
            "circuit_id": event.circuit_id,
            "circuit_name": _get_circuit_name(event.circuit_id),
            "start_date": event.start_date.isoformat() if event.start_date else None,
            "end_date": event.end_date.isoformat() if event.end_date else None,
            "total_days": event.total_days,
            "status": event.status,
        })

    payload = {
        "season": season,
        "events": events_data,
    }

    # Cache with appropriate TTL (don't cache empty results)
    if events_data:
        ttl = CACHE_TTL_SECONDS
        redis_client.setex(cache_key, ttl, json.dumps(payload))

    return payload


@router.get("/{season}/{event_id}/{day}")
def get_testing_day(
    season: int,
    event_id: str,
    day: int,
    drivers: Optional[List[str]] = Query(
        default=None,
        description="Optional list of driver codes to filter (e.g., VER, HAM)",
    ),
    include_laps: bool = Query(
        default=False,
        description="Include full lap data in response (can be large)",
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get detailed testing data for a specific day."""
    cache_key = _testing_day_cache_key(season, event_id, day, drivers)
    if not include_laps:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    # Find the testing event
    event_stmt = select(TestingEvent).where(
        TestingEvent.season == season,
        TestingEvent.event_id == event_id,
    )
    event = db.execute(event_stmt).scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail=f"Testing event not found: {event_id}")

    # Find the session for this day
    session_stmt = select(TestingSession).where(
        TestingSession.event_id == event.id,
        TestingSession.day == day,
    )
    session = db.execute(session_stmt).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail=f"Testing day {day} not found for event {event_id}")

    # Build driver results
    results = _build_driver_results(db, session.id, drivers)

    # Build response
    payload = {
        "season": season,
        "event_id": event_id,
        "event_name": event.event_name,
        "circuit_id": event.circuit_id,
        "day": day,
        "date": session.date.isoformat() if session.date else None,
        "status": session.status,
        "results": results,
        "laps": [],
    }

    # Include laps if requested
    if include_laps:
        payload["laps"] = _fetch_laps(db, session.id, drivers, offset=0, limit=5000)

    # Cache (skip if including laps - those are fetched via separate endpoint)
    if not include_laps:
        ttl = COMPLETED_CACHE_TTL_SECONDS if session.status == "completed" else CACHE_TTL_SECONDS
        redis_client.setex(cache_key, ttl, json.dumps(payload))

    return payload


@router.get("/{season}/{event_id}/{day}/laps")
def get_testing_laps(
    season: int,
    event_id: str,
    day: int,
    drivers: Optional[List[str]] = Query(
        default=None,
        description="Optional list of driver codes to filter",
    ),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=500, ge=1, le=1000, description="Max laps to return"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get paginated lap data for a testing day."""
    cache_key = _testing_laps_cache_key(season, event_id, day, drivers, offset, limit)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Find the testing event and session
    event_stmt = select(TestingEvent).where(
        TestingEvent.season == season,
        TestingEvent.event_id == event_id,
    )
    event = db.execute(event_stmt).scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail=f"Testing event not found: {event_id}")

    session_stmt = select(TestingSession).where(
        TestingSession.event_id == event.id,
        TestingSession.day == day,
    )
    session = db.execute(session_stmt).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail=f"Testing day {day} not found for event {event_id}")

    # Get total count
    count_stmt = select(func.count(TestingLap.id)).where(TestingLap.session_id == session.id)
    if drivers:
        count_stmt = count_stmt.where(TestingLap.driver.in_(drivers))
    total = db.execute(count_stmt).scalar() or 0

    # Fetch laps
    laps = _fetch_laps(db, session.id, drivers, offset, limit)

    payload = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "laps": laps,
    }

    # Cache with appropriate TTL
    ttl = COMPLETED_CACHE_TTL_SECONDS if session.status == "completed" else CACHE_TTL_SECONDS
    redis_client.setex(cache_key, ttl, json.dumps(payload))

    return payload


def _build_driver_results(db: Session, session_id: int, drivers: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Build driver results with best lap and stints."""
    # Get all drivers who have laps in this session
    driver_stmt = select(TestingLap.driver, TestingLap.team).where(
        TestingLap.session_id == session_id
    ).distinct()
    if drivers:
        driver_stmt = driver_stmt.where(TestingLap.driver.in_(drivers))

    driver_rows = db.execute(driver_stmt).all()

    results = []
    for driver_code, team in driver_rows:
        # Get best lap for this driver
        best_lap_stmt = select(TestingLap).where(
            TestingLap.session_id == session_id,
            TestingLap.driver == driver_code,
            TestingLap.lap_time_ms.isnot(None),
            TestingLap.is_valid == True,
        ).order_by(TestingLap.lap_time_ms).limit(1)
        best_lap = db.execute(best_lap_stmt).scalar_one_or_none()

        # Get total laps
        total_laps_stmt = select(func.count(TestingLap.id)).where(
            TestingLap.session_id == session_id,
            TestingLap.driver == driver_code,
        )
        total_laps = db.execute(total_laps_stmt).scalar() or 0

        # Get stints
        stints_stmt = select(TestingStint).where(
            TestingStint.session_id == session_id,
            TestingStint.driver == driver_code,
        ).order_by(TestingStint.stint_number)
        stints = db.execute(stints_stmt).scalars().all()

        stints_data = []
        for stint in stints:
            stints_data.append({
                "stint_number": stint.stint_number,
                "compound": stint.compound,
                "lap_count": stint.lap_count,
                "avg_pace_ms": stint.avg_pace_ms,
                "avg_pace_formatted": _format_lap_time(stint.avg_pace_ms),
            })

        results.append({
            "driver": driver_code,
            "team": team,
            "best_lap_ms": best_lap.lap_time_ms if best_lap else None,
            "best_lap_formatted": _format_lap_time(best_lap.lap_time_ms) if best_lap else None,
            "best_lap_compound": best_lap.compound if best_lap else None,
            "total_laps": total_laps,
            "stints": stints_data,
        })

    # Sort by best lap time and add position + gaps
    results.sort(key=lambda x: x["best_lap_ms"] if x["best_lap_ms"] else float("inf"))

    leader_time = results[0]["best_lap_ms"] if results and results[0]["best_lap_ms"] else None
    for i, result in enumerate(results):
        result["position"] = i + 1
        if leader_time and result["best_lap_ms"]:
            gap = result["best_lap_ms"] - leader_time
            result["gap_ms"] = gap if gap > 0 else None
            result["gap_formatted"] = f"+{gap/1000:.3f}" if gap > 0 else None
        else:
            result["gap_ms"] = None
            result["gap_formatted"] = None

    return results


def _fetch_laps(db: Session, session_id: int, drivers: Optional[List[str]], offset: int, limit: int) -> List[Dict[str, Any]]:
    """Fetch paginated laps for a session."""
    stmt = select(TestingLap).where(
        TestingLap.session_id == session_id
    ).order_by(TestingLap.driver, TestingLap.lap_number)

    if drivers:
        stmt = stmt.where(TestingLap.driver.in_(drivers))

    stmt = stmt.offset(offset).limit(limit)
    laps = db.execute(stmt).scalars().all()

    return [
        {
            "driver": lap.driver,
            "lap_number": lap.lap_number,
            "lap_time_ms": lap.lap_time_ms,
            "lap_time_formatted": _format_lap_time(lap.lap_time_ms),
            "compound": lap.compound,
            "stint": lap.stint_number,
            "is_valid": lap.is_valid,
            "sector_1_ms": lap.sector_1_ms,
            "sector_2_ms": lap.sector_2_ms,
            "sector_3_ms": lap.sector_3_ms,
        }
        for lap in laps
    ]


def _get_circuit_name(circuit_id: str) -> str:
    """Get display name for a circuit."""
    circuit_names = {
        "bahrain": "Bahrain International Circuit",
        "albert_park": "Albert Park Circuit",
        "barcelona": "Circuit de Barcelona-Catalunya",
        "catalunya": "Circuit de Barcelona-Catalunya",
        "silverstone": "Silverstone Circuit",
        "monza": "Autodromo Nazionale Monza",
    }
    return circuit_names.get(circuit_id, circuit_id.replace("_", " ").title())
