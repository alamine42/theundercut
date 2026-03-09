# src/theundercut/api/v1/race.py
import json
import datetime as dt
from typing import Optional, Tuple, List

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


class WeekendTimeline(BaseModel):
    state: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    is_active: bool
    next_session: Optional[RaceSession] = None
    next_session_in_seconds: Optional[int] = None
    current_session: Optional[RaceSession] = None


class WeekendResponse(BaseModel):
    schedule: Optional[RaceWeekendSchedule] = None
    history: Optional[CircuitHistory] = None
    sessions: dict[str, Optional[SessionResultsResponse]]
    meta: WeekendMeta
    timeline: Optional[WeekendTimeline] = None


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


def _normalize_session_name(name: str) -> str:
    return name.lower().replace(" ", "_")


def _event_to_session(event: CalendarEvent) -> RaceSession:
    start = _ensure_utc(event.start_ts)
    end = _ensure_utc(event.end_ts)
    return RaceSession(
        session_type=_normalize_session_name(event.session_type),
        start_time=start.isoformat() if start else None,
        end_time=end.isoformat() if end else None,
        status=(event.status or "scheduled").lower(),
    )


def _ensure_utc(value: Optional[dt.datetime]) -> Optional[dt.datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _build_timeline(events: List[CalendarEvent]) -> Optional[WeekendTimeline]:
    if not events:
        return None

    now = dt.datetime.now(dt.timezone.utc)
    normalized = []

    for event in events:
        start = _ensure_utc(event.start_ts)
        default_end = start + dt.timedelta(hours=2) if start else None
        end = _ensure_utc(event.end_ts) if event.end_ts else _ensure_utc(default_end)
        normalized.append(
            {
                "session": _event_to_session(event),
                "start": start,
                "end": end,
                "status": (event.status or "scheduled").lower(),
            }
        )

    starts = [entry["start"] for entry in normalized if entry["start"] is not None]
    first_start = min(starts) if starts else None
    race_entry = next(
        (entry for entry in normalized if entry["session"].session_type == "race"),
        None,
    )
    fallback_end = max(
        (
            entry["end"]
            for entry in normalized
            if entry["end"] is not None
        ),
        default=None,
    )

    race_end = fallback_end
    if race_entry and race_entry["end"]:
        race_end = race_entry["end"]

    window_start = first_start
    window_end = race_end + dt.timedelta(hours=24) if race_end else None

    def _is_completed(entry: dict) -> bool:
        return entry["status"] in {"completed", "ingested"}

    def _has_started(entry: dict) -> bool:
        start = entry["start"]
        return (
            entry["status"] in {"live", "running"} or
            (_is_completed(entry)) or
            (start is not None and start <= now)
        )

    race_completed = race_entry is not None and _is_completed(race_entry)
    any_started = any(_has_started(entry) for entry in normalized)

    if race_completed:
        if window_end and now <= window_end:
            state = "post-race"
        else:
            state = "off-week"
    elif any_started:
        state = "during-weekend"
    else:
        if first_start is None:
            state = "off-week"
        else:
            days_until = (first_start - now).total_seconds() / 86400
            if days_until <= 3:
                state = "race-week"
            elif days_until <= 7:
                state = "pre-weekend"
            else:
                state = "off-week"

    is_active = (
        window_start is not None
        and window_end is not None
        and window_start <= now <= window_end
    )

    next_session_entry = None
    future_entries = [
        entry
        for entry in normalized
        if entry["session"].start_time
        and entry["start"]
        and entry["start"] > now
        and not _is_completed(entry)
    ]
    if future_entries:
        next_session_entry = min(future_entries, key=lambda entry: entry["start"])

    current_session_entry = next(
        (
            entry
            for entry in normalized
            if entry["start"]
            and entry["end"]
            and entry["start"] <= now <= entry["end"]
        ),
        None,
    )
    if current_session_entry is None:
        current_session_entry = next(
            (
                entry
                for entry in normalized
                if entry["status"] in {"live", "running"}
            ),
            None,
        )

    next_seconds = None
    if next_session_entry and next_session_entry["start"]:
        next_seconds = int((next_session_entry["start"] - now).total_seconds())

    return WeekendTimeline(
        state=state,
        window_start=window_start.isoformat() if window_start else None,
        window_end=window_end.isoformat() if window_end else None,
        is_active=is_active,
        next_session=next_session_entry["session"] if next_session_entry else None,
        next_session_in_seconds=next_seconds,
        current_session=current_session_entry["session"] if current_session_entry else None,
    )


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
    timeline = None
    try:
        events = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=round)
            .order_by(CalendarEvent.start_ts)
            .all()
        )
        if events:
            timeline = _build_timeline(events)
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
        timeline=timeline,
    )

    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(response.model_dump()))

    return response


# --- Admin endpoints ---

@router.post("/{season}/{round}/mark-ingested")
def mark_sessions_ingested(
    season: int,
    round: int,
    session: Optional[str] = Query(None, description="Specific session to mark, or all if omitted"),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to mark calendar event(s) as ingested.

    Use this when data was ingested but status wasn't updated properly.
    """
    from theundercut.services.cache import invalidate_race_weekend_cache

    query = db.query(CalendarEvent).filter_by(season=season, round=round)
    if session:
        query = query.filter(CalendarEvent.session_type.ilike(session))

    events = query.all()
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No calendar events found for {season}-{round}" + (f" {session}" if session else "")
        )

    updated = []
    for ev in events:
        old_status = ev.status
        ev.status = "ingested"
        updated.append({"session": ev.session_type, "old_status": old_status})

    db.commit()

    # Clear cache
    try:
        invalidate_race_weekend_cache(season, round)
    except Exception:
        pass

    return {"updated": updated, "count": len(updated)}


@router.post("/{season}/{round}/ingest")
def trigger_session_ingest(
    season: int,
    round: int,
    session: str = Query("Race", description="Session type to ingest (Race, Qualifying, FP1, etc.)"),
    force: bool = Query(False, description="Force re-ingestion even if already marked as ingested"),
):
    """
    Admin endpoint to manually trigger session ingestion.

    Use this to re-ingest a session after code fixes or when automatic
    ingestion failed to store data properly.
    """
    from theundercut.services.ingestion import ingest_session

    try:
        ingest_session(season, round, session_type=session, force=force)
        return {
            "status": "success",
            "message": f"Ingested {season}-{round} {session}",
            "force": force,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(exc)}"
        )
