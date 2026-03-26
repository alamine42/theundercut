# src/theundercut/api/v1/race.py
import json
import logging
import datetime as dt
from typing import Optional, Tuple, List

import httpx

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
from theundercut.services.standings import fetch_season_standings

logger = logging.getLogger(__name__)

OPENF1_MEETING_CACHE_TTL_SECONDS = 3600  # 1 hour

# Map OpenF1 circuit_short_name to Jolpica-style circuit IDs used by the frontend.
# Only entries where the names diverge need to be listed; circuits whose
# short_name.lower().replace(" ", "_") already matches the Jolpica ID are
# resolved automatically.
OPENF1_TO_JOLPICA_CIRCUIT: dict[str, str] = {
    "Melbourne": "albert_park",
    "Sakhir": "bahrain",
    "Monte Carlo": "monaco",
    "Montreal": "villeneuve",
    "Spielberg": "red_bull_ring",
    "Spa-Francorchamps": "spa",
    "Singapore": "marina_bay",
    "Austin": "americas",
    "Mexico City": "rodriguez",
    "Las Vegas": "vegas",
    "Lusail": "losail",
    "Yas Marina Circuit": "yas_marina",
    "Madrid": "madring",
}

SESSION_RESULTS_TO_FETCH: Tuple[str, ...] = (
    "fp1",
    "fp2",
    "fp3",
    "qualifying",
    "sprint_qualifying",
    "sprint_race",
    "race",
)

SESSION_ALIAS_MAP = {
    "fp1": "fp1",
    "practice_1": "fp1",
    "practice1": "fp1",
    "practice": "fp1",
    "free_practice_1": "fp1",
    "freepractice1": "fp1",
    "fp2": "fp2",
    "practice_2": "fp2",
    "practice2": "fp2",
    "free_practice_2": "fp2",
    "fp3": "fp3",
    "practice_3": "fp3",
    "practice3": "fp3",
    "free_practice_3": "fp3",
    "qualifying": "qualifying",
    "qualifying_session": "qualifying",
    "q": "qualifying",
    "sprint_qualifying": "sprint_qualifying",
    "sprint-qualifying": "sprint_qualifying",
    "sprintqualifying": "sprint_qualifying",
    "sprint_shootout": "sprint_qualifying",
    "sprintshootout": "sprint_qualifying",
    "sq": "sprint_qualifying",
    "ss": "sprint_qualifying",
    "sprint": "sprint_race",
    "sprint_race": "sprint_race",
    "sprintrace": "sprint_race",
    "race": "race",
    "grand_prix": "race",
    "grandprix": "race",
    "gp": "race",
}

SESSION_BACKFILL_GRACE_MINUTES = 2
SESSION_BACKFILL_LOCK_TTL_SECONDS = 300
WEEKEND_CACHE_TTL_SECONDS = 300
HISTORY_CACHE_TTL_SECONDS = 3600


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


class NextRacePreview(BaseModel):
    race_name: Optional[str] = None
    circuit_name: Optional[str] = None
    circuit_country: Optional[str] = None
    fp1_date: Optional[str] = None
    round: Optional[int] = None


class WeekendSummaryResponse(BaseModel):
    season: int
    display_round: Optional[int] = None
    display_weekend: Optional[WeekendResponse] = None
    next_weekend: Optional[WeekendResponse] = None
    next_race_info: Optional[NextRacePreview] = None


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
    if not name:
        return ""
    slug = (
        name.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )
    # collapse duplicate underscores introduced by replacements
    while "__" in slug:
        slug = slug.replace("__", "_")
    return SESSION_ALIAS_MAP.get(slug, slug)


def _derive_session_status(
    status: Optional[str],
    start: Optional[dt.datetime],
    end: Optional[dt.datetime],
    now: Optional[dt.datetime] = None,
) -> str:
    current = now or dt.datetime.now(dt.timezone.utc)
    normalized = (status or "scheduled").lower()
    if normalized == "ingested":
        return "ingested"
    if normalized == "completed":
        return "completed"
    start_ts = _ensure_utc(start)
    end_ts = _ensure_utc(end)
    if end_ts and end_ts <= current:
        return "completed"
    if start_ts and start_ts <= current:
        return "live"
    if normalized in {"running", "live"}:
        return "live"
    return normalized


def _event_to_session(event: CalendarEvent) -> RaceSession:
    start = _ensure_utc(event.start_ts)
    end = _ensure_utc(event.end_ts)
    return RaceSession(
        session_type=_normalize_session_name(event.session_type),
        start_time=start.isoformat() if start else None,
        end_time=end.isoformat() if end else None,
        status=_derive_session_status(event.status, start, end),
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
        status = _derive_session_status(event.status, start, end, now)
        normalized.append(
            {
                "session": _event_to_session(event),
                "start": start,
                "end": end,
                "status": status,
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


def _load_schedule(db: Session, season: int, round_num: int) -> Tuple[List[CalendarEvent], Optional[RaceWeekendSchedule], Optional[WeekendTimeline]]:
    events = (
        db.query(CalendarEvent)
        .filter_by(season=season, round=round_num)
        .order_by(CalendarEvent.start_ts)
        .all()
    )
    if not events:
        return [], None, None

    session_types = {event.session_type.lower() for event in events}
    is_sprint = "sprint" in session_types or "sprint qualifying" in session_types or "ss" in session_types
    sessions = [_event_to_session(event) for event in events]
    circuit_info = _get_circuit_info(season, round_num, db)
    schedule = RaceWeekendSchedule(
        season=season,
        round=round_num,
        race_name=circuit_info.get("race_name"),
        circuit_id=circuit_info.get("circuit_id"),
        circuit_name=circuit_info.get("circuit_name"),
        circuit_country=circuit_info.get("circuit_country"),
        is_sprint_weekend=is_sprint,
        sessions=sessions,
    )
    timeline = _build_timeline(events)
    return events, schedule, timeline


def _maybe_backfill_session_results(
    db: Session,
    season: int,
    round_num: int,
    events: List[CalendarEvent],
) -> List[str]:
    errors: List[str] = []
    if not events:
        return errors

    now = dt.datetime.now(dt.timezone.utc)
    event_lookup = {}
    for event in events:
        normalized = _normalize_session_name(event.session_type)
        if normalized in SESSION_RESULTS_TO_FETCH:
            event_lookup[normalized] = event

    if not event_lookup:
        return errors

    existing_types = {
        row[0]
        for row in (
            db.query(SessionClassification.session_type)
            .filter_by(season=season, round=round_num)
            .distinct()
            .all()
        )
    }

    for normalized, event in event_lookup.items():
        if normalized in existing_types:
            continue
        end_time = _ensure_utc(event.end_ts)
        if not end_time:
            continue
        if end_time + dt.timedelta(minutes=SESSION_BACKFILL_GRACE_MINUTES) > now:
            continue
        lock_key = f"weekend:auto_ingest:{season}:{round_num}:{normalized}"
        if redis_client.get(lock_key):
            continue
        redis_client.setex(lock_key, SESSION_BACKFILL_LOCK_TTL_SECONDS, "1")
        try:
            _trigger_session_ingest(event.season, event.round, event.session_type)
            existing_types.add(normalized)
        except Exception as exc:  # pragma: no cover - defensive logging
            errors.append(f"ingest_failed:{normalized}:{exc}")
            redis_client.delete(lock_key)
        else:
            redis_client.delete(lock_key)

    return errors


def _build_weekend_response(
    db: Session,
    season: int,
    round_num: int,
) -> WeekendResponse:
    last_updated = dt.datetime.utcnow().isoformat()
    errors: List[str] = []
    schedule = None
    timeline = None
    try:
        events, schedule, timeline = _load_schedule(db, season, round_num)
        if not events:
            schedule = None
        else:
            errors.extend(_maybe_backfill_session_results(db, season, round_num, events))
    except Exception as exc:
        errors.append(f"schedule: {str(exc)}")
    history = _load_circuit_history(db, season, round_num, schedule, errors)

    session_results: dict[str, Optional[SessionResultsResponse]] = {}
    for stype in SESSION_RESULTS_TO_FETCH:
        try:
            classifications = (
                db.query(SessionClassification)
                .filter_by(season=season, round=round_num, session_type=stype)
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
                    round=round_num,
                    session_type=stype,
                    results=results,
                )
            else:
                session_results[stype] = None
        except Exception as exc:
            errors.append(f"{stype}: {str(exc)}")
            session_results[stype] = None

    return WeekendResponse(
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


def _get_weekend_with_cache(db: Session, season: int, round_num: Optional[int]) -> Optional[WeekendResponse]:
    if not round_num or round_num <= 0:
        return None
    cache_key = weekend_cache_key(season, round_num)
    cached = redis_client.get(cache_key)
    if cached:
        try:
            payload = json.loads(cached)
            return WeekendResponse(**payload)
        except Exception:
            redis_client.delete(cache_key)

    payload = _build_weekend_response(db, season, round_num)
    redis_client.setex(cache_key, WEEKEND_CACHE_TTL_SECONDS, json.dumps(payload.model_dump()))
    return payload


def _build_next_race_preview(weekend: Optional[WeekendResponse]) -> Optional[NextRacePreview]:
    if not weekend or not weekend.schedule:
        return None
    first_session = next((s for s in weekend.schedule.sessions if s.start_time), None)
    return NextRacePreview(
        race_name=weekend.schedule.race_name,
        circuit_name=weekend.schedule.circuit_name,
        circuit_country=weekend.schedule.circuit_country,
        fp1_date=first_session.start_time if first_session else None,
        round=weekend.schedule.round,
    )


def _fetch_openf1_meeting(meeting_key: int) -> Optional[dict]:
    """Fetch meeting metadata from OpenF1, with Redis caching."""
    cache_key = f"openf1:meeting:{meeting_key}"
    cached = redis_client.get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            redis_client.delete(cache_key)

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.openf1.org/v1/meetings",
                params={"meeting_key": meeting_key},
            )
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                meeting = data[0]
                redis_client.setex(cache_key, OPENF1_MEETING_CACHE_TTL_SECONDS, json.dumps(meeting))
                return meeting
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("Failed to fetch OpenF1 meeting %s: %s", meeting_key, exc)
    return None


def _get_circuit_info(season: int, rnd: int, db: Session) -> dict:
    """Get circuit info from Race and Circuit tables, falling back to OpenF1."""
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

    # Fallback: use OpenF1 meeting data via calendar event meeting_key
    event = (
        db.query(CalendarEvent)
        .filter_by(season=season, round=rnd)
        .first()
    )
    if event and event.meeting_key:
        meeting = _fetch_openf1_meeting(event.meeting_key)
        if meeting:
            circuit_short = meeting.get("circuit_short_name") or ""
            # Use explicit mapping first, then fall back to normalised short name
            circuit_id = OPENF1_TO_JOLPICA_CIRCUIT.get(
                circuit_short,
                circuit_short.lower().replace(" ", "_").replace("-", "_") if circuit_short else f"circuit_{season}_{rnd}",
            )
            return {
                "circuit_id": circuit_id,
                "circuit_name": circuit_short or None,
                "circuit_country": meeting.get("country_name") or None,
                "race_name": meeting.get("meeting_name") or None,
            }

    if event:
        return {
            "circuit_id": f"circuit_{season}_{rnd}",
            "circuit_name": None,
            "circuit_country": None,
            "race_name": None,
        }
    return {"circuit_id": None, "circuit_name": None, "circuit_country": None, "race_name": None}


def _load_circuit_history(
    db: Session,
    season: int,
    rnd: int,
    schedule: Optional[RaceWeekendSchedule],
    errors: List[str],
) -> CircuitHistory:
    circuit_id = schedule.circuit_id if schedule else f"circuit_{season}_{rnd}"
    base_history = CircuitHistory(
        circuit_id=circuit_id,
        circuit_name=schedule.circuit_name if schedule else None,
        previous_year=None,
    )
    cache_key = history_cache_key(season, circuit_id)
    cached = redis_client.get(cache_key)
    if cached:
        try:
            payload = json.loads(cached)
            return CircuitHistory(**payload)
        except Exception:
            redis_client.delete(cache_key)

    try:
        from theundercut.api.v1.circuits import get_circuit_history

        history_data = get_circuit_history(season, circuit_id)
        if history_data and history_data.get("previous_year"):
            redis_client.setex(cache_key, HISTORY_CACHE_TTL_SECONDS, json.dumps(history_data))
            return CircuitHistory(
                circuit_id=history_data.get("circuit_id", circuit_id),
                circuit_name=history_data.get("circuit_name"),
                previous_year=history_data.get("previous_year"),
            )
    except Exception as exc:
        errors.append(f"history: {str(exc)}")
    return base_history

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

    events, schedule, _ = _load_schedule(db, season, round)
    if not events or schedule is None:
        raise HTTPException(status_code=404, detail=f"No schedule found for {season} round {round}")

    redis_client.setex(cache_key, 300, json.dumps(schedule.model_dump()))
    return schedule


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
    """
    payload = _get_weekend_with_cache(db, season, round)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"No weekend found for {season}-{round}")
    return payload


@router.get("/{season}/weekend/summary", response_model=WeekendSummaryResponse)
def get_weekend_summary(
    season: int,
    db: Session = Depends(get_db),
):
    standings = fetch_season_standings(db, season)
    races_completed = int(standings.get("races_completed", 0)) if standings else 0
    last_round = races_completed or None
    next_round = races_completed + 1 if races_completed else 1

    last_weekend = _get_weekend_with_cache(db, season, last_round) if last_round else None
    next_weekend = _get_weekend_with_cache(db, season, next_round)

    if last_weekend and not last_weekend.schedule:
        last_weekend = None
    if next_weekend and not next_weekend.schedule:
        next_weekend = None

    display_weekend = None
    display_round = None
    if last_weekend and last_weekend.timeline and last_weekend.timeline.state != "off-week":
        display_weekend = last_weekend
        display_round = last_round
    elif next_weekend:
        display_weekend = next_weekend
        display_round = next_round
    else:
        display_weekend = last_weekend
        display_round = last_round

    preview_source = next_weekend or display_weekend
    next_race_info = _build_next_race_preview(preview_source)

    include_next = (
        next_weekend if next_weekend and (display_round is None or display_round != next_round) else None
    )

    return WeekendSummaryResponse(
        season=season,
        display_round=display_round,
        display_weekend=display_weekend,
        next_weekend=include_next,
        next_race_info=next_race_info,
    )


def _trigger_session_ingest(season: int, round_num: int, session_label: str) -> None:
    from theundercut.services.ingestion import ingest_session

    ingest_session(season, round_num, session_label)


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
