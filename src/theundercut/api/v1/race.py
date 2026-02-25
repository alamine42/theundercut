# src/theundercut/api/v1/race.py
import json
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.models import LapTime, CalendarEvent, SessionClassification, Race, Circuit, Season
from theundercut.services.cache import (
    session_cache_key,
    schedule_cache_key,
    weekend_cache_key,
    history_cache_key,
    SESSION_CACHE_PREFIX,
)


# --- Pydantic models for responses ---

class RaceSession(BaseModel):
    session_type: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str


class RaceWeekendSchedule(BaseModel):
    season: int
    round: int
    race_name: Optional[str] = None
    circuit_id: Optional[str] = None
    circuit_name: Optional[str] = None
    circuit_country: Optional[str] = None
    is_sprint_weekend: bool
    sessions: list[RaceSession]


class SessionResult(BaseModel):
    position: int
    driver_code: str
    driver_name: Optional[str] = None
    team: Optional[str] = None
    time: Optional[str] = None
    gap: Optional[str] = None
    laps: Optional[int] = None
    points: Optional[int] = None
    q1_time: Optional[str] = None
    q2_time: Optional[str] = None
    q3_time: Optional[str] = None
    eliminated_in: Optional[str] = None


class SessionResultsResponse(BaseModel):
    season: int
    round: int
    session_type: str
    results: list[SessionResult]


class HistoricalDriver(BaseModel):
    driver_code: str
    driver_name: Optional[str] = None
    team: Optional[str] = None


class CircuitHistory(BaseModel):
    circuit_id: str
    circuit_name: Optional[str] = None
    previous_year: Optional[dict] = None


class WeekendMeta(BaseModel):
    last_updated: str
    stale: bool
    errors: list[str]


class WeekendResponse(BaseModel):
    schedule: Optional[RaceWeekendSchedule] = None
    history: Optional[CircuitHistory] = None
    sessions: dict[str, Optional[SessionResultsResponse]]
    meta: WeekendMeta


router = APIRouter(
    prefix="/api/v1/race",
    tags=["race"],
    responses={404: {"description": "Race not found"}},
)


# --- Helper functions ---

def _format_lap_time(ms: Optional[float]) -> Optional[str]:
    """Format milliseconds to M:SS.mmm format."""
    if ms is None:
        return None
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"


def _format_gap(gap_ms: Optional[float]) -> Optional[str]:
    """Format gap in milliseconds to +X.XXX format."""
    if gap_ms is None or gap_ms == 0:
        return None
    return f"+{gap_ms / 1000:.3f}"


def _get_circuit_info(season: int, rnd: int, db: Session) -> dict:
    """Get circuit info from Race and Circuit tables."""
    # Try to get from Race table with Circuit join
    race = (
        db.query(Race, Circuit)
        .join(Season, Race.season_id == Season.id)
        .outerjoin(Circuit, Race.circuit_id == Circuit.id)
        .filter(Season.year == season, Race.round_number == rnd)
        .first()
    )

    if race:
        race_obj, circuit_obj = race
        return {
            "circuit_id": circuit_obj.name.lower().replace(" ", "_") if circuit_obj else f"circuit_{season}_{rnd}",
            "circuit_name": circuit_obj.name if circuit_obj else None,
            "circuit_country": circuit_obj.country if circuit_obj else None,
            "race_name": race_obj.slug.replace("-", " ").title() if race_obj.slug else None,
        }

    # Fallback to calendar event if Race not found
    event = (
        db.query(CalendarEvent)
        .filter_by(season=season, round=rnd)
        .first()
    )
    if event:
        return {
            "circuit_id": f"circuit_{season}_{rnd}",
            "circuit_name": None,
            "circuit_country": None,
            "race_name": None,
        }
    return {"circuit_id": None, "circuit_name": None, "circuit_country": None, "race_name": None}

@router.get("/{season}/{round}/laps")
def get_laps(
    season: int,
    round: int,
    drivers: list[str] = Query(
        default=None,
        description="Optional list of driver codes (e.g. VER, HAM) to filter laps",
    ),
    db: Session = Depends(get_db),
):
    """
    Return lap-time records for a given race.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2024)
    round : int
        FIA round number within that season
    drivers : list[str], optional
        One or more driver codes to filter; if omitted, returns all drivers

    Returns
    -------
    list[dict]
        Each item: {driver, lap, lap_ms}
    """
    q = (
        db.query(LapTime.driver, LapTime.lap, LapTime.lap_ms)
        .filter(LapTime.race_id == f"{season}-{round}")
    )
    if drivers:
        q = q.filter(LapTime.driver.in_(drivers))

    rows = (
        q.order_by(LapTime.driver, LapTime.lap)
        .all()
    )

    return [
        {"driver": d, "lap": int(l), "lap_ms": float(ms)}
        for d, l, ms in rows
    ]


@router.get("/{season}/{round}/schedule", response_model=RaceWeekendSchedule)
def get_race_schedule(
    season: int,
    round: int,
    db: Session = Depends(get_db),
):
    """
    Return the race weekend schedule with session times and statuses.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2026)
    round : int
        FIA round number within that season

    Returns
    -------
    RaceWeekendSchedule
        Schedule with sessions, times, and statuses
    """
    cache_key = schedule_cache_key(season, round)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Query calendar events for this race
    events = (
        db.query(CalendarEvent)
        .filter_by(season=season, round=round)
        .order_by(CalendarEvent.start_ts)
        .all()
    )

    if not events:
        raise HTTPException(status_code=404, detail=f"No schedule found for {season} round {round}")

    # Determine if sprint weekend
    session_types = {e.session_type.lower() for e in events}
    is_sprint = "sprint" in session_types or "sprint qualifying" in session_types or "ss" in session_types

    sessions = []
    for event in events:
        sessions.append(RaceSession(
            session_type=event.session_type.lower().replace(" ", "_"),
            start_time=event.start_ts.isoformat() if event.start_ts else None,
            end_time=event.end_ts.isoformat() if event.end_ts else None,
            status=event.status or "scheduled",
        ))

    circuit_info = _get_circuit_info(season, round, db)

    result = RaceWeekendSchedule(
        season=season,
        round=round,
        race_name=circuit_info.get("race_name"),
        circuit_id=circuit_info.get("circuit_id"),
        circuit_name=circuit_info.get("circuit_name"),
        circuit_country=circuit_info.get("circuit_country"),
        is_sprint_weekend=is_sprint,
        sessions=sessions,
    )

    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(result.model_dump()))

    return result


@router.get("/{season}/{round}/session/{session_type}/results", response_model=SessionResultsResponse)
def get_session_results(
    season: int,
    round: int,
    session_type: str,
    db: Session = Depends(get_db),
):
    """
    Return results for a specific session (FP1, FP2, FP3, qualifying, sprint, race).

    Parameters
    ----------
    season : int
        Championship year (e.g., 2026)
    round : int
        FIA round number within that season
    session_type : str
        Session type: fp1, fp2, fp3, qualifying, sprint_qualifying, sprint_race, race

    Returns
    -------
    SessionResultsResponse
        Session results with driver positions and times
    """
    normalized_type = session_type.lower().replace(" ", "_")
    cache_key = session_cache_key(season, round, normalized_type)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Query session classifications
    classifications = (
        db.query(SessionClassification)
        .filter_by(season=season, round=round, session_type=normalized_type)
        .order_by(SessionClassification.position)
        .all()
    )

    if not classifications:
        # Check if session exists but hasn't been ingested yet
        event = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=round)
            .filter(CalendarEvent.session_type.ilike(f"%{session_type}%"))
            .first()
        )
        if event and event.status != "ingested":
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "session_not_complete",
                    "message": f"{session_type} has not completed yet",
                    "scheduled_start": event.start_ts.isoformat() if event.start_ts else None,
                }
            )
        raise HTTPException(status_code=404, detail=f"No results found for {session_type}")

    results = []
    for cls in classifications:
        result = SessionResult(
            position=cls.position,
            driver_code=cls.driver_code,
            driver_name=cls.driver_name,
            team=cls.team,
            time=_format_lap_time(cls.time_ms),
            gap=_format_gap(cls.gap_ms),
            laps=cls.laps,
            points=cls.points,
        )
        # Add qualifying-specific fields
        if normalized_type == "qualifying":
            result.q1_time = _format_lap_time(cls.q1_time_ms)
            result.q2_time = _format_lap_time(cls.q2_time_ms)
            result.q3_time = _format_lap_time(cls.q3_time_ms)
            result.eliminated_in = cls.eliminated_in
        results.append(result)

    response = SessionResultsResponse(
        season=season,
        round=round,
        session_type=normalized_type,
        results=results,
    )

    # Cache for 2 hours (completed sessions)
    redis_client.setex(cache_key, 7200, json.dumps(response.model_dump()))

    return response


@router.get("/{season}/{round}/weekend", response_model=WeekendResponse)
def get_race_weekend(
    season: int,
    round: int,
    db: Session = Depends(get_db),
):
    """
    Return aggregated race weekend data: schedule, history, and all session results.
    Single endpoint to reduce API calls from the frontend.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2026)
    round : int
        FIA round number within that season

    Returns
    -------
    WeekendResponse
        Aggregated weekend data with schedule, history, sessions, and metadata
    """
    cache_key = weekend_cache_key(season, round)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    errors = []
    last_updated = dt.datetime.utcnow().isoformat()

    # Get schedule
    schedule = None
    try:
        events = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=round)
            .order_by(CalendarEvent.start_ts)
            .all()
        )
        if events:
            session_types = {e.session_type.lower() for e in events}
            is_sprint = "sprint" in session_types or "sprint qualifying" in session_types
            sessions = [
                RaceSession(
                    session_type=e.session_type.lower().replace(" ", "_"),
                    start_time=e.start_ts.isoformat() if e.start_ts else None,
                    end_time=e.end_ts.isoformat() if e.end_ts else None,
                    status=e.status or "scheduled",
                )
                for e in events
            ]
            circuit_info = _get_circuit_info(season, round, db)
            schedule = RaceWeekendSchedule(
                season=season,
                round=round,
                race_name=circuit_info.get("race_name"),
                circuit_id=circuit_info.get("circuit_id"),
                circuit_name=circuit_info.get("circuit_name"),
                circuit_country=circuit_info.get("circuit_country"),
                is_sprint_weekend=is_sprint,
                sessions=sessions,
            )
    except Exception as e:
        errors.append(f"schedule: {str(e)}")

    # Get history from the circuits endpoint
    circuit_id = schedule.circuit_id if schedule else f"circuit_{season}_{round}"
    history = CircuitHistory(
        circuit_id=circuit_id,
        circuit_name=schedule.circuit_name if schedule else None,
        previous_year=None,
    )

    # Try to fetch actual history data
    try:
        from theundercut.api.v1.circuits import get_circuit_history
        history_data = get_circuit_history(season, circuit_id)
        if history_data and history_data.get("previous_year"):
            history = CircuitHistory(
                circuit_id=history_data.get("circuit_id", circuit_id),
                circuit_name=history_data.get("circuit_name"),
                previous_year=history_data.get("previous_year"),
            )
    except Exception as e:
        errors.append(f"history: {str(e)}")

    # Get all session results
    session_results = {}
    session_types_to_fetch = ["fp1", "fp2", "fp3", "qualifying", "sprint_qualifying", "sprint_race", "race"]

    for stype in session_types_to_fetch:
        try:
            classifications = (
                db.query(SessionClassification)
                .filter_by(season=season, round=round, session_type=stype)
                .order_by(SessionClassification.position)
                .all()
            )
            if classifications:
                results = [
                    SessionResult(
                        position=c.position,
                        driver_code=c.driver_code,
                        driver_name=c.driver_name,
                        team=c.team,
                        time=_format_lap_time(c.time_ms),
                        gap=_format_gap(c.gap_ms),
                        laps=c.laps,
                        points=c.points,
                        q1_time=_format_lap_time(c.q1_time_ms) if stype == "qualifying" else None,
                        q2_time=_format_lap_time(c.q2_time_ms) if stype == "qualifying" else None,
                        q3_time=_format_lap_time(c.q3_time_ms) if stype == "qualifying" else None,
                        eliminated_in=c.eliminated_in if stype == "qualifying" else None,
                    )
                    for c in classifications
                ]
                session_results[stype] = SessionResultsResponse(
                    season=season,
                    round=round,
                    session_type=stype,
                    results=results,
                )
            else:
                session_results[stype] = None
        except Exception as e:
            errors.append(f"{stype}: {str(e)}")
            session_results[stype] = None

    response = WeekendResponse(
        schedule=schedule,
        history=history,
        sessions=session_results,
        meta=WeekendMeta(
            last_updated=last_updated,
            stale=False,
            errors=errors,
        ),
    )

    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(response.model_dump()))

    return response
