"""
Ingestion service for pre-season testing data.

Uses FastF1 to fetch testing session lap data and stores it in the
testing_events, testing_sessions, testing_laps, and testing_stints tables.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
import fastf1
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from theundercut.adapters.db import SessionLocal
from theundercut.adapters.fastf1_loader import CACHE_DIR
from theundercut.models import (
    TestingEvent,
    TestingSession,
    TestingLap,
    TestingStint,
)

logger = logging.getLogger(__name__)


def _get_testing_schedule(season: int) -> List[Dict]:
    """
    Get list of testing events for a season from FastF1.

    Returns list of dicts with event info:
    - event_name, event_id, circuit, dates, etc.
    """
    try:
        schedule = fastf1.get_event_schedule(season, include_testing=True)
        testing_events = []

        for idx, row in schedule.iterrows():
            # Testing sessions have different naming conventions
            # Look for "Testing" in the event name or check EventFormat
            event_name = str(row.get("EventName", ""))
            event_format = str(row.get("EventFormat", ""))

            if "test" in event_name.lower() or "testing" in event_format.lower():
                # Extract circuit from location
                location = str(row.get("Location", "Unknown"))
                country = str(row.get("Country", ""))

                # Create event_id slug
                event_id = event_name.lower().replace(" ", "_").replace("-", "_")
                event_id = "".join(c for c in event_id if c.isalnum() or c == "_")

                # Get circuit_id from location
                circuit_id = location.lower().replace(" ", "_")
                circuit_id = "".join(c for c in circuit_id if c.isalnum() or c == "_")

                # Get dates
                session_dates = []
                for col in ["Session1Date", "Session2Date", "Session3Date", "Session4Date", "Session5Date"]:
                    if col in row.index and pd.notna(row[col]):
                        session_dates.append(pd.Timestamp(row[col]).date())

                start_date = min(session_dates) if session_dates else None
                end_date = max(session_dates) if session_dates else None
                total_days = len(set(session_dates)) if session_dates else 3

                testing_events.append({
                    "event_name": event_name,
                    "event_id": event_id,
                    "circuit_id": circuit_id,
                    "circuit_name": location,
                    "country": country,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": total_days,
                    "round_number": row.get("RoundNumber"),
                })

        return testing_events
    except Exception as exc:
        logger.warning("Failed to get testing schedule for %d: %s", season, exc)
        return []


def _load_testing_laps(season: int, event_identifier: str | int) -> pd.DataFrame:
    """
    Load testing laps from FastF1.

    Args:
        season: Season year
        event_identifier: Event name/number or round number

    Returns:
        DataFrame with lap data
    """
    try:
        # Get the testing session
        # For testing, we use the event name/number and "Testing" session type
        session = fastf1.get_testing_session(season, event_identifier, 1)
        session.load()
        return session.laps
    except Exception as exc:
        logger.warning("Failed to load testing laps for %s-%s: %s", season, event_identifier, exc)
        # Try alternative approach - get_session with testing event
        try:
            session = fastf1.get_session(season, event_identifier, "Testing")
            session.load()
            return session.laps
        except Exception as exc2:
            logger.warning("Alternative session load failed: %s", exc2)
            return pd.DataFrame()


def _store_testing_laps(
    db: Session,
    session_id: int,
    laps_df: pd.DataFrame,
) -> int:
    """
    Store testing laps in the database.

    Returns number of laps inserted.
    """
    if laps_df.empty:
        return 0

    # Prepare lap records
    records = []
    for _, row in laps_df.iterrows():
        driver_raw = row.get("Driver")
        if pd.isna(driver_raw) or driver_raw is None:
            continue
        driver = str(driver_raw).strip()
        if not driver or driver == "nan" or driver == "None":
            continue

        lap_time = row.get("LapTime")
        lap_time_ms = None
        if pd.notna(lap_time):
            if hasattr(lap_time, "total_seconds"):
                lap_time_ms = lap_time.total_seconds() * 1000
            else:
                lap_time_ms = float(lap_time) if lap_time else None

        # Extract sector times
        s1 = row.get("Sector1Time")
        s2 = row.get("Sector2Time")
        s3 = row.get("Sector3Time")

        sector_1_ms = s1.total_seconds() * 1000 if pd.notna(s1) and hasattr(s1, "total_seconds") else None
        sector_2_ms = s2.total_seconds() * 1000 if pd.notna(s2) and hasattr(s2, "total_seconds") else None
        sector_3_ms = s3.total_seconds() * 1000 if pd.notna(s3) and hasattr(s3, "total_seconds") else None

        # Check validity
        is_valid = row.get("IsAccurate", True)
        if pd.isna(is_valid):
            is_valid = True

        records.append({
            "session_id": session_id,
            "driver": driver,
            "team": str(row.get("Team", "")) if pd.notna(row.get("Team")) else None,
            "lap_number": int(row.get("LapNumber", 0)) if pd.notna(row.get("LapNumber")) else 0,
            "lap_time_ms": lap_time_ms,
            "compound": str(row.get("Compound", "")) if pd.notna(row.get("Compound")) else None,
            "stint_number": int(row.get("Stint", 0)) if pd.notna(row.get("Stint")) else None,
            "sector_1_ms": sector_1_ms,
            "sector_2_ms": sector_2_ms,
            "sector_3_ms": sector_3_ms,
            "is_valid": bool(is_valid),
        })

    if not records:
        return 0

    # Use ON CONFLICT DO NOTHING for idempotent inserts
    stmt = pg_insert(TestingLap).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["session_id", "driver", "lap_number"]
    )
    result = db.execute(stmt)
    return len(records)


def _compute_and_store_stints(
    db: Session,
    session_id: int,
    laps_df: pd.DataFrame,
) -> int:
    """
    Compute stint aggregates from laps and store them.

    Returns number of stints created.
    """
    if laps_df.empty:
        return 0

    # Group laps by driver and stint
    stint_data = (
        laps_df
        .groupby(["Driver", "Stint", "Compound", "Team"])
        .agg(
            start_lap=("LapNumber", "min"),
            end_lap=("LapNumber", "max"),
            lap_count=("LapNumber", "count"),
            avg_pace=("LapTime", "mean"),
        )
        .reset_index()
    )

    records = []
    for _, row in stint_data.iterrows():
        driver = str(row.get("Driver", ""))
        if not driver or driver == "nan":
            continue

        stint_number = row.get("Stint")
        if pd.isna(stint_number):
            continue

        avg_pace = row.get("avg_pace")
        avg_pace_ms = None
        if pd.notna(avg_pace):
            if hasattr(avg_pace, "total_seconds"):
                avg_pace_ms = avg_pace.total_seconds() * 1000

        records.append({
            "session_id": session_id,
            "driver": driver,
            "team": str(row.get("Team", "")) if pd.notna(row.get("Team")) else None,
            "stint_number": int(stint_number),
            "compound": str(row.get("Compound", "")) if pd.notna(row.get("Compound")) else None,
            "start_lap": int(row.get("start_lap", 0)) if pd.notna(row.get("start_lap")) else None,
            "end_lap": int(row.get("end_lap", 0)) if pd.notna(row.get("end_lap")) else None,
            "lap_count": int(row.get("lap_count", 0)) if pd.notna(row.get("lap_count")) else 0,
            "avg_pace_ms": avg_pace_ms,
        })

    if not records:
        return 0

    # Use ON CONFLICT DO NOTHING for idempotent inserts
    stmt = pg_insert(TestingStint).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["session_id", "driver", "stint_number"]
    )
    db.execute(stmt)
    return len(records)


def ingest_testing_event(
    season: int,
    event_id: str,
    force: bool = False,
) -> Dict:
    """
    Ingest all days of a testing event.

    Args:
        season: Season year
        event_id: Event identifier (e.g., "pre_season_testing")
        force: If True, re-ingest even if data exists

    Returns:
        Dict with ingestion results
    """
    results = {
        "season": season,
        "event_id": event_id,
        "days_ingested": 0,
        "total_laps": 0,
        "total_stints": 0,
        "errors": [],
    }

    with SessionLocal() as db:
        # Find or create the testing event
        event = (
            db.query(TestingEvent)
            .filter(TestingEvent.season == season, TestingEvent.event_id == event_id)
            .one_or_none()
        )

        if not event:
            # Try to get event info from schedule
            schedule = _get_testing_schedule(season)
            event_info = next(
                (e for e in schedule if e["event_id"] == event_id),
                None
            )

            if not event_info:
                results["errors"].append(f"Event {event_id} not found in schedule")
                return results

            event = TestingEvent(
                season=season,
                event_id=event_id,
                event_name=event_info.get("event_name", event_id),
                circuit_id=event_info.get("circuit_id", "unknown"),
                total_days=event_info.get("total_days", 3),
                start_date=event_info.get("start_date"),
                end_date=event_info.get("end_date"),
                status="running",
            )
            db.add(event)
            db.flush()

        # Ingest each day
        for day in range(1, event.total_days + 1):
            try:
                day_result = ingest_testing_day(
                    season, event_id, day, force=force, db_session=db
                )
                if day_result.get("laps_count", 0) > 0:
                    results["days_ingested"] += 1
                    results["total_laps"] += day_result.get("laps_count", 0)
                    results["total_stints"] += day_result.get("stints_count", 0)
            except Exception as exc:
                results["errors"].append(f"Day {day}: {str(exc)}")
                logger.exception("Failed to ingest day %d of %s: %s", day, event_id, exc)

        # Update event status
        if results["days_ingested"] > 0:
            event.status = "completed"

        db.commit()

    return results


def ingest_testing_day(
    season: int,
    event_id: str,
    day: int,
    force: bool = False,
    db_session: Optional[Session] = None,
) -> Dict:
    """
    Ingest a single day of testing data.

    Args:
        season: Season year
        event_id: Event identifier
        day: Day number (1, 2, or 3)
        force: If True, re-ingest even if data exists
        db_session: Optional existing database session

    Returns:
        Dict with ingestion results
    """
    results = {
        "season": season,
        "event_id": event_id,
        "day": day,
        "laps_count": 0,
        "stints_count": 0,
        "status": "pending",
    }

    def do_ingest(db: Session):
        # Find the testing event
        event = (
            db.query(TestingEvent)
            .filter(TestingEvent.season == season, TestingEvent.event_id == event_id)
            .one_or_none()
        )

        if not event:
            logger.warning("Event %s not found for season %d", event_id, season)
            results["status"] = "event_not_found"
            return

        # Find or create the session
        session = (
            db.query(TestingSession)
            .filter(TestingSession.event_id == event.id, TestingSession.day == day)
            .one_or_none()
        )

        if session and not force:
            # Check if already has data
            lap_count = db.query(TestingLap).filter(TestingLap.session_id == session.id).count()
            if lap_count > 0:
                logger.info("Day %d of %s already ingested (%d laps)", day, event_id, lap_count)
                results["laps_count"] = lap_count
                results["status"] = "already_ingested"
                return

        if not session:
            session = TestingSession(
                event_id=event.id,
                day=day,
                status="running",
            )
            db.add(session)
            db.flush()

        # Load laps from FastF1
        # Use event name + day as the identifier
        event_identifier = event.event_name
        laps_df = _load_testing_laps_for_day(season, event_identifier, day)

        if laps_df.empty:
            logger.warning("No laps found for day %d of %s", day, event_id)
            results["status"] = "no_data"
            return

        # Store laps
        laps_count = _store_testing_laps(db, session.id, laps_df)
        results["laps_count"] = laps_count

        # Compute and store stints
        stints_count = _compute_and_store_stints(db, session.id, laps_df)
        results["stints_count"] = stints_count

        # Update session status
        session.status = "completed"
        results["status"] = "completed"

        logger.info(
            "Ingested day %d of %s: %d laps, %d stints",
            day, event_id, laps_count, stints_count
        )

    if db_session:
        do_ingest(db_session)
    else:
        with SessionLocal() as db:
            do_ingest(db)
            db.commit()

    return results


def _load_testing_laps_for_day(
    season: int,
    event_name: str,
    day: int,
) -> pd.DataFrame:
    """
    Load laps for a specific day of testing.

    FastF1 testing sessions are typically numbered by day.
    """
    try:
        # FastF1 uses 1-indexed day numbers for testing
        session = fastf1.get_testing_session(season, event_name, day)
        session.load()
        return session.laps
    except Exception as exc:
        logger.warning(
            "Failed to load testing laps for %s day %d: %s",
            event_name, day, exc
        )
        return pd.DataFrame()


def sync_testing_events(season: int) -> List[Dict]:
    """
    Sync testing events from FastF1 schedule to database.

    Returns list of events synced.
    """
    schedule = _get_testing_schedule(season)
    synced = []

    with SessionLocal() as db:
        for event_info in schedule:
            event_id = event_info["event_id"]

            # Check if event exists
            existing = (
                db.query(TestingEvent)
                .filter(TestingEvent.season == season, TestingEvent.event_id == event_id)
                .one_or_none()
            )

            if existing:
                # Update dates if changed
                if event_info.get("start_date"):
                    existing.start_date = event_info["start_date"]
                if event_info.get("end_date"):
                    existing.end_date = event_info["end_date"]
                synced.append({"event_id": event_id, "action": "updated"})
            else:
                # Create new event
                event = TestingEvent(
                    season=season,
                    event_id=event_id,
                    event_name=event_info.get("event_name", event_id),
                    circuit_id=event_info.get("circuit_id", "unknown"),
                    total_days=event_info.get("total_days", 3),
                    start_date=event_info.get("start_date"),
                    end_date=event_info.get("end_date"),
                    status="scheduled",
                )
                db.add(event)
                synced.append({"event_id": event_id, "action": "created"})

        db.commit()

    return synced
