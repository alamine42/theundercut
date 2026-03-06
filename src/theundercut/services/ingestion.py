"""
RQ job: ingest an F1 session into Postgres.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Iterable as IterableType

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from theundercut.adapters.resolver import get_provider
from theundercut.adapters.db import SessionLocal
from theundercut.models import (
    LapTime,
    Stint,
    CalendarEvent,
    Race,
    Season,
    Entry,
    Driver,
    Team,
    DriverMetrics,
    StrategyEvent as StrategyEventRecord,
    PenaltyEvent as PenaltyEventRecord,
    OvertakeEvent as OvertakeEventRecord,
    Circuit,
    SessionClassification,
    LapPosition,
    RaceControlEvent,
    RaceWeather,
    StrategyScore,
    StrategyDecision,
)
from theundercut.drive_grade.pipeline import (
    DriveGradePipeline,
    DriverRaceInput,
    StrategyPlan,
    PenaltyEvent as GradePenaltyEvent,
)
from theundercut.drive_grade.drive_grade import (
    CarPaceIndex,
    DriverFormModifier,
    OvertakeContext,
    OvertakeEvent as GradeOvertakeEvent,
)
from theundercut.drive_grade.data_sources.fastf1_provider import FastF1Provider
from theundercut.drive_grade.data_sources.openf1_provider import OpenF1Provider, slugify
from theundercut.drive_grade.calibration import (
    get_active_calibration,
    load_calibration_profile,
    set_active_calibration,
)
from theundercut.services.cache import (
    invalidate_analytics_cache,
    invalidate_session_cache,
    invalidate_strategy_cache,
)
from theundercut.drive_grade.strategy import (
    StrategyScoreEngine,
    StrategyEngineConfig,
    StrategyScoreResult,
)
from theundercut.drive_grade.strategy.types import (
    PitStop as StrategyPitStop,
    RaceControlPeriod,
    WeatherCondition,
    LapPositionSnapshot,
)


logger = logging.getLogger(__name__)


# Session type mapping from FastF1 identifiers to our normalized types
SESSION_TYPE_MAP = {
    "FP1": "fp1",
    "FP2": "fp2",
    "FP3": "fp3",
    "Practice 1": "fp1",
    "Practice 2": "fp2",
    "Practice 3": "fp3",
    "Qualifying": "qualifying",
    "Q": "qualifying",
    "Sprint": "sprint_race",
    "Sprint Qualifying": "sprint_qualifying",
    "Sprint Shootout": "sprint_qualifying",
    "SS": "sprint_qualifying",
    "SQ": "sprint_qualifying",
    "Race": "race",
    "R": "race",
}


def _store_laps(db: Session, race_id: str, df: pd.DataFrame) -> None:
    """
    Clean, normalise and bulk-insert lap records.
    If the unique index (race_id, driver, lap) already has a row,
    ON CONFLICT DO NOTHING prevents duplicates.
    """
    cleaned = (
        df.rename(
            columns={
                "Driver": "driver",
                "LapNumber": "lap",
                "Compound": "compound",
                "Stint": "stint_no",
            }
        )
        .assign(
            lap_ms=lambda d: (
                d.LapTime.dt.total_seconds() * 1000
            ).round().astype("Int64"),
            lap=lambda d: d.lap.astype("Int64"),
            stint_no=lambda d: d.stint_no.astype("Int64"),
            pit=lambda d: d.PitInTime.notna(),
            race_id=race_id,
        )
        .fillna({"lap_ms": -1, "lap": -1, "stint_no": -1})
    )

    stmt = pg_insert(LapTime).values(
        cleaned[
            ["race_id", "driver", "lap", "lap_ms", "compound", "stint_no", "pit"]
        ].to_dict("records")
    )

    # If a row with same (race_id, driver, lap) exists, skip it.
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["race_id", "driver", "lap"]
    )

    db.execute(stmt)



def _store_session_classifications(
    db: Session,
    season: int,
    rnd: int,
    session_type: str,
    laps: pd.DataFrame,
    provider,
    session_results: pd.DataFrame = None,
) -> None:
    """
    Store session classification results (positions, times, gaps).
    Uses ON CONFLICT DO UPDATE to handle post-race penalties/amendments.

    For race/sprint sessions, uses actual classification from session_results.
    For practice sessions, derives from best lap times.
    """
    normalized_type = SESSION_TYPE_MAP.get(session_type, session_type.lower())
    is_race_or_sprint = normalized_type in ("race", "sprint_race")
    is_qualifying = "qualifying" in normalized_type

    # Prefer session results for race/sprint/qualifying if available
    if session_results is not None and not session_results.empty:
        timestamp = dt.datetime.utcnow()

        for _, row in session_results.iterrows():
            driver_code = row.get("Abbreviation") or row.get("Driver")
            if not driver_code or pd.isna(driver_code):
                continue

            driver_code = str(driver_code).strip().upper()

            # Get driver name from results
            first_name = row.get("FirstName", "")
            last_name = row.get("LastName", "")
            driver_name = f"{first_name} {last_name}".strip() if first_name or last_name else None

            # Get position - use ClassifiedPosition or Position
            position = row.get("ClassifiedPosition") or row.get("Position")
            if pd.isna(position):
                position = None
            else:
                try:
                    position = int(position)
                except (ValueError, TypeError):
                    position = None

            # Get team
            team = row.get("TeamName") or row.get("Team")
            if pd.isna(team):
                team = None

            # Get time and gap
            time_ms = None
            gap_ms = None

            if "Time" in row and not pd.isna(row["Time"]):
                try:
                    time_val = row["Time"]
                    if hasattr(time_val, "total_seconds"):
                        time_ms = time_val.total_seconds() * 1000
                    else:
                        time_ms = float(time_val) * 1000 if time_val else None
                except (ValueError, TypeError):
                    pass

            # Get laps completed
            laps_completed = row.get("LapsCompleted")
            if pd.isna(laps_completed):
                laps_completed = None
            else:
                try:
                    laps_completed = int(laps_completed)
                except (ValueError, TypeError):
                    laps_completed = None

            # Get points for race/sprint
            points = None
            if is_race_or_sprint and "Points" in row:
                try:
                    points = int(row["Points"]) if not pd.isna(row["Points"]) else None
                except (ValueError, TypeError):
                    pass

            # Get qualifying times if available
            q1_time_ms = None
            q2_time_ms = None
            q3_time_ms = None
            eliminated_in = None

            if is_qualifying:
                for q_col, q_attr in [("Q1", "q1_time_ms"), ("Q2", "q2_time_ms"), ("Q3", "q3_time_ms")]:
                    if q_col in row and not pd.isna(row[q_col]):
                        try:
                            q_val = row[q_col]
                            if hasattr(q_val, "total_seconds"):
                                q_ms = q_val.total_seconds() * 1000
                            else:
                                q_ms = float(q_val) * 1000 if q_val else None
                            if q_attr == "q1_time_ms":
                                q1_time_ms = q_ms
                            elif q_attr == "q2_time_ms":
                                q2_time_ms = q_ms
                            elif q_attr == "q3_time_ms":
                                q3_time_ms = q_ms
                        except (ValueError, TypeError):
                            pass

                # Determine elimination phase
                if q3_time_ms is None and q2_time_ms is not None:
                    eliminated_in = "Q2"
                elif q2_time_ms is None and q1_time_ms is not None:
                    eliminated_in = "Q1"

            # Check for amendments
            existing = (
                db.query(SessionClassification)
                .filter_by(season=season, round=rnd, session_type=normalized_type, driver_code=driver_code)
                .one_or_none()
            )
            amended = existing and existing.position != position

            stmt = pg_insert(SessionClassification).values(
                season=season,
                round=rnd,
                session_type=normalized_type,
                driver_code=driver_code,
                driver_name=driver_name,
                team=team,
                position=position,
                time_ms=time_ms,
                gap_ms=gap_ms,
                laps=laps_completed,
                points=points,
                q1_time_ms=q1_time_ms,
                q2_time_ms=q2_time_ms,
                q3_time_ms=q3_time_ms,
                eliminated_in=eliminated_in,
                ingested_at=timestamp,
                amended=amended,
            )

            stmt = stmt.on_conflict_do_update(
                constraint="uq_session_classification",
                set_={
                    "driver_name": stmt.excluded.driver_name,
                    "position": stmt.excluded.position,
                    "time_ms": stmt.excluded.time_ms,
                    "gap_ms": stmt.excluded.gap_ms,
                    "laps": stmt.excluded.laps,
                    "team": stmt.excluded.team,
                    "points": stmt.excluded.points,
                    "q1_time_ms": stmt.excluded.q1_time_ms,
                    "q2_time_ms": stmt.excluded.q2_time_ms,
                    "q3_time_ms": stmt.excluded.q3_time_ms,
                    "eliminated_in": stmt.excluded.eliminated_in,
                    "ingested_at": stmt.excluded.ingested_at,
                    "amended": amended,
                }
            )

            db.execute(stmt)

        logger.info("Stored %d session classifications from results for %s-%s %s",
                    len(session_results), season, rnd, normalized_type)
        return

    # Fallback: derive from lap data (for practice sessions or if results unavailable)
    if laps.empty:
        logger.warning("No laps to extract classifications from for %s-%s %s", season, rnd, session_type)
        return

    # Group by driver and compute best lap, total laps
    driver_stats = (
        laps.groupby("Driver")
        .agg(
            best_lap_ms=("LapTime", lambda x: x.dropna().dt.total_seconds().min() * 1000 if not x.dropna().empty else None),
            total_laps=("LapNumber", "max"),
            team=("Team", "first") if "Team" in laps.columns else ("Driver", lambda x: "Unknown"),
        )
        .reset_index()
    )

    # Sort by best lap to get positions
    driver_stats = driver_stats.sort_values("best_lap_ms", na_position="last")
    driver_stats["position"] = range(1, len(driver_stats) + 1)

    # Compute gap to leader
    leader_time = driver_stats["best_lap_ms"].iloc[0] if not driver_stats.empty else None
    driver_stats["gap_ms"] = driver_stats["best_lap_ms"] - leader_time if leader_time else None

    timestamp = dt.datetime.utcnow()

    for _, row in driver_stats.iterrows():
        driver_code = row["Driver"]
        if not driver_code or pd.isna(driver_code):
            continue

        # Check if record exists (for amended tracking)
        existing = (
            db.query(SessionClassification)
            .filter_by(season=season, round=rnd, session_type=normalized_type, driver_code=driver_code)
            .one_or_none()
        )

        amended = False
        if existing and existing.position != row["position"]:
            amended = True

        stmt = pg_insert(SessionClassification).values(
            season=season,
            round=rnd,
            session_type=normalized_type,
            driver_code=driver_code,
            driver_name=None,  # Not available from laps
            team=row.get("team") if row.get("team") != "Unknown" else None,
            position=int(row["position"]) if pd.notna(row["position"]) else None,
            time_ms=row["best_lap_ms"] if pd.notna(row["best_lap_ms"]) else None,
            gap_ms=row["gap_ms"] if pd.notna(row["gap_ms"]) and row["position"] != 1 else None,
            laps=int(row["total_laps"]) if pd.notna(row["total_laps"]) else None,
            ingested_at=timestamp,
            amended=amended,
        )

        # On conflict, update the record (for post-race penalties)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_session_classification",
            set_={
                "position": stmt.excluded.position,
                "time_ms": stmt.excluded.time_ms,
                "gap_ms": stmt.excluded.gap_ms,
                "laps": stmt.excluded.laps,
                "team": stmt.excluded.team,
                "ingested_at": stmt.excluded.ingested_at,
                "amended": amended,
            }
        )

        db.execute(stmt)

    logger.info("Stored %d session classifications from laps for %s-%s %s", len(driver_stats), season, rnd, normalized_type)


def _store_stints(db: Session, race_id: str, df: pd.DataFrame) -> None:
    df = (
        df.groupby(["Driver", "Stint", "Compound"])
        .agg(laps=("LapNumber", "count"), avg=("LapTime", "mean"))
        .reset_index()
        .rename(
            columns={
                "Driver": "driver",
                "Stint": "stint_no",
                "Compound": "compound",
            }
        )
        .assign(
            race_id=race_id,
            avg_lap_ms=lambda d: d.avg.dt.total_seconds() * 1000,
        )
    )
    db.bulk_insert_mappings(
        Stint,
        df[["race_id", "driver", "stint_no", "compound", "laps", "avg_lap_ms"]].to_dict(
            "records"
        ),
    )


def _store_lap_positions(
    db: Session,
    race_row: Race,
    entry_map: dict[str, Entry],
    laps: pd.DataFrame,
) -> None:
    """
    Store per-lap position data for position delta analysis.
    Extracts position from laps DataFrame if available, or derives from lap times.
    """
    if laps.empty:
        logger.warning("No laps for position extraction")
        return

    # Check if Position column exists
    has_position = "Position" in laps.columns

    records = []
    for lap_num in laps["LapNumber"].dropna().unique():
        lap_data = laps[laps["LapNumber"] == lap_num].copy()

        if has_position:
            # Use existing position data
            lap_data = lap_data.dropna(subset=["Position"])
            lap_data = lap_data.sort_values("Position")
        else:
            # Derive position from cumulative time (sum of lap times up to this lap)
            # This is approximate but better than nothing
            lap_data = lap_data.dropna(subset=["LapTime"])
            lap_data = lap_data.sort_values("LapTime")
            lap_data["Position"] = range(1, len(lap_data) + 1)

        leader_time = None
        prev_time = None

        for idx, row in lap_data.iterrows():
            driver_code = row.get("Driver")
            if not driver_code or pd.isna(driver_code):
                continue

            driver_code = str(driver_code).strip().upper()
            if driver_code not in entry_map:
                continue

            entry = entry_map[driver_code]
            position = int(row["Position"]) if pd.notna(row["Position"]) else None

            # Calculate gaps - prefer FastF1's actual gap columns when available
            gap_to_leader_ms = None
            gap_to_ahead_ms = None

            # Try to get gaps from FastF1's actual timing data
            if "GapToLeader" in row.index and pd.notna(row.get("GapToLeader")):
                try:
                    gap_val = row["GapToLeader"]
                    if hasattr(gap_val, "total_seconds"):
                        gap_to_leader_ms = int(gap_val.total_seconds() * 1000)
                    elif isinstance(gap_val, (int, float)):
                        gap_to_leader_ms = int(gap_val * 1000) if gap_val < 1000 else int(gap_val)
                except (AttributeError, TypeError, ValueError):
                    pass

            if "Gap" in row.index and pd.notna(row.get("Gap")):
                try:
                    gap_val = row["Gap"]
                    if hasattr(gap_val, "total_seconds"):
                        gap_to_ahead_ms = int(gap_val.total_seconds() * 1000)
                    elif isinstance(gap_val, (int, float)):
                        gap_to_ahead_ms = int(gap_val * 1000) if gap_val < 1000 else int(gap_val)
                except (AttributeError, TypeError, ValueError):
                    pass

            # Fallback: derive from cumulative time if gap data not available
            if gap_to_leader_ms is None and "Time" in row.index and pd.notna(row.get("Time")):
                try:
                    current_time = row["Time"].total_seconds() * 1000 if hasattr(row["Time"], "total_seconds") else float(row["Time"]) * 1000
                    if leader_time is None:
                        leader_time = current_time
                    else:
                        gap_to_leader_ms = int(current_time - leader_time)
                    if prev_time is not None and gap_to_ahead_ms is None:
                        gap_to_ahead_ms = int(current_time - prev_time)
                    prev_time = current_time
                except (AttributeError, TypeError, ValueError):
                    pass

            records.append({
                "race_id": race_row.id,
                "entry_id": entry.id,
                "lap_number": int(lap_num),
                "position": position,
                "gap_to_leader_ms": gap_to_leader_ms,
                "gap_to_ahead_ms": gap_to_ahead_ms,
            })

    if records:
        # Use ON CONFLICT DO UPDATE to support re-ingestion with corrected data
        for record in records:
            stmt = pg_insert(LapPosition).values(**record)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_lap_position",
                set_={
                    "position": stmt.excluded.position,
                    "gap_to_leader_ms": stmt.excluded.gap_to_leader_ms,
                    "gap_to_ahead_ms": stmt.excluded.gap_to_ahead_ms,
                },
            )
            db.execute(stmt)

        logger.info("Stored %d lap positions for race %s", len(records), race_row.id)


def _store_race_control_events(
    db: Session,
    race_row: Race,
    race_control: pd.DataFrame,
) -> None:
    """
    Store Safety Car, VSC, and Red Flag events from race control messages.
    Extracts SC/VSC periods and persists to race_control_events table.
    """
    if race_control is None or race_control.empty:
        logger.info("No race control data available for race %s", race_row.id)
        return

    # Filter for SC, VSC, and Red Flag events
    sc_events = []
    current_event = None

    for _, row in race_control.iterrows():
        category = row.get("Category", "")
        flag = row.get("Flag", "")
        message = str(row.get("Message", "")).upper()
        lap = row.get("Lap")
        time = row.get("Time")

        # Detect Safety Car events (non-virtual)
        if "SAFETY CAR" in message and "VIRTUAL" not in message:
            # SC end: "IN THIS LAP" or "ENDING" indicate SC is ending
            if "IN THIS LAP" in message or "ENDING" in message:
                if current_event and current_event["event_type"] == "safety_car":
                    current_event["end_lap"] = int(lap) if pd.notna(lap) else None
                    current_event["end_time"] = time if pd.notna(time) else None
                    sc_events.append(current_event)
                    current_event = None
            # SC start: only "DEPLOYED" indicates actual start
            elif "DEPLOYED" in message:
                if current_event is None:
                    current_event = {
                        "event_type": "safety_car",
                        "start_lap": int(lap) if pd.notna(lap) else None,
                        "start_time": time if pd.notna(time) else None,
                        "cause": row.get("Message"),
                    }

        # Detect Virtual Safety Car events
        elif "VIRTUAL SAFETY CAR" in message or "VSC" in message:
            # VSC end
            if "ENDING" in message:
                if current_event and current_event["event_type"] == "vsc":
                    current_event["end_lap"] = int(lap) if pd.notna(lap) else None
                    current_event["end_time"] = time if pd.notna(time) else None
                    sc_events.append(current_event)
                    current_event = None
            # VSC start
            elif "DEPLOYED" in message:
                if current_event is None:
                    current_event = {
                        "event_type": "vsc",
                        "start_lap": int(lap) if pd.notna(lap) else None,
                        "start_time": time if pd.notna(time) else None,
                        "cause": row.get("Message"),
                    }

        # Detect Red Flag events
        elif "RED FLAG" in message:
            # Red Flag end
            if "GREEN" in message or "RESTART" in message:
                if current_event and current_event["event_type"] == "red_flag":
                    current_event["end_lap"] = int(lap) if pd.notna(lap) else None
                    current_event["end_time"] = time if pd.notna(time) else None
                    sc_events.append(current_event)
                    current_event = None
            # Red Flag start
            elif current_event is None:
                current_event = {
                    "event_type": "red_flag",
                    "start_lap": int(lap) if pd.notna(lap) else None,
                    "start_time": time if pd.notna(time) else None,
                    "cause": row.get("Message"),
                }

    # Handle event that didn't end (race finished under SC)
    if current_event:
        sc_events.append(current_event)

    # Store events with ON CONFLICT DO UPDATE for re-ingestion support
    for event in sc_events:
        if event.get("start_lap") is None:
            continue

        stmt = pg_insert(RaceControlEvent).values(
            race_id=race_row.id,
            event_type=event["event_type"],
            start_lap=event["start_lap"],
            end_lap=event.get("end_lap"),
            start_time=event.get("start_time"),
            end_time=event.get("end_time"),
            cause=event.get("cause"),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_race_control_event",
            set_={
                "end_lap": stmt.excluded.end_lap,
                "end_time": stmt.excluded.end_time,
                "cause": stmt.excluded.cause,
            },
        )
        db.execute(stmt)

    logger.info("Stored %d race control events for race %s", len(sc_events), race_row.id)


def _store_race_weather(
    db: Session,
    race_row: Race,
    weather: pd.DataFrame,
    laps: pd.DataFrame,
) -> None:
    """
    Store per-lap weather conditions for weather strategy analysis.
    Maps weather data to lap numbers.
    """
    if weather is None or weather.empty:
        logger.info("No weather data available for race %s", race_row.id)
        return

    if laps.empty:
        logger.warning("No laps to map weather data to")
        return

    # Get unique lap numbers from laps
    lap_numbers = sorted(laps["LapNumber"].dropna().unique())

    # Weather data has timestamps, need to map to laps
    # Get lap start times if available
    lap_times = {}
    if "LapStartTime" in laps.columns:
        for lap_num in lap_numbers:
            lap_data = laps[laps["LapNumber"] == lap_num]
            if not lap_data.empty:
                first_start = lap_data["LapStartTime"].min()
                if pd.notna(first_start):
                    lap_times[lap_num] = first_start

    # Pre-sort weather data once for efficient lookup (avoid O(n²) copies)
    weather_sorted = None
    weather_times = None
    if "Time" in weather.columns:
        weather_sorted = weather.sort_values("Time").reset_index(drop=True)
        weather_times = weather_sorted["Time"].tolist()

    records = []
    for lap_num in lap_numbers:
        # Find closest weather reading for this lap
        weather_row = None

        if lap_times and lap_num in lap_times and weather_sorted is not None:
            lap_start = lap_times[lap_num]
            # Binary search for closest weather reading (O(log n) instead of O(n))
            import bisect
            idx = bisect.bisect_left(weather_times, lap_start)
            # Check neighbors to find closest
            if idx == 0:
                weather_row = weather_sorted.iloc[0]
            elif idx >= len(weather_times):
                weather_row = weather_sorted.iloc[-1]
            else:
                before = weather_times[idx - 1]
                after = weather_times[idx]
                if abs(lap_start - before) <= abs(after - lap_start):
                    weather_row = weather_sorted.iloc[idx - 1]
                else:
                    weather_row = weather_sorted.iloc[idx]
        elif weather_sorted is not None:
            # Fallback: use proportional position in weather data
            idx = int((lap_num - 1) / max(len(lap_numbers) - 1, 1) * (len(weather_sorted) - 1))
            idx = min(idx, len(weather_sorted) - 1)
            weather_row = weather_sorted.iloc[idx]
        else:
            # No time column, use proportional index on original
            idx = int((lap_num - 1) / max(len(lap_numbers) - 1, 1) * (len(weather) - 1))
            idx = min(idx, len(weather) - 1)
            weather_row = weather.iloc[idx]

        if weather_row is None:
            continue

        # Determine track status
        track_status = "dry"
        rainfall = weather_row.get("Rainfall")
        if pd.notna(rainfall) and rainfall > 0:
            track_status = "wet" if rainfall > 0.5 else "damp"

        # Also check TrackStatus if available
        track_status_raw = weather_row.get("TrackStatus")
        if pd.notna(track_status_raw):
            status_str = str(track_status_raw).lower()
            if "wet" in status_str:
                track_status = "wet"
            elif "damp" in status_str:
                track_status = "damp"

        # Determine rain intensity
        rain_intensity = "none"
        if pd.notna(rainfall):
            if rainfall > 2.0:
                rain_intensity = "heavy"
            elif rainfall > 0.5:
                rain_intensity = "moderate"
            elif rainfall > 0:
                rain_intensity = "light"

        records.append({
            "race_id": race_row.id,
            "lap_number": int(lap_num),
            "track_status": track_status,
            "air_temp_c": float(weather_row.get("AirTemp")) if pd.notna(weather_row.get("AirTemp")) else None,
            "track_temp_c": float(weather_row.get("TrackTemp")) if pd.notna(weather_row.get("TrackTemp")) else None,
            "humidity_pct": float(weather_row.get("Humidity")) if pd.notna(weather_row.get("Humidity")) else None,
            "rain_intensity": rain_intensity,
        })

    # Store weather records with ON CONFLICT DO UPDATE for re-ingestion support
    for record in records:
        stmt = pg_insert(RaceWeather).values(**record)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_race_weather",
            set_={
                "track_status": stmt.excluded.track_status,
                "air_temp_c": stmt.excluded.air_temp_c,
                "track_temp_c": stmt.excluded.track_temp_c,
                "humidity_pct": stmt.excluded.humidity_pct,
                "rain_intensity": stmt.excluded.rain_intensity,
            },
        )
        db.execute(stmt)

    logger.info("Stored %d weather records for race %s", len(records), race_row.id)


def _build_minimal_weekend_from_laps(laps: pd.DataFrame, season: int, rnd: int) -> dict | None:
    """
    Build minimal weekend payload from laps data when DriveGrade payload is unavailable.
    This allows strategy scoring to work even without full DriveGrade data.
    """
    if laps.empty:
        return None

    drivers = []
    for driver_code in laps["Driver"].dropna().unique():
        driver_code = str(driver_code).strip().upper()
        if not driver_code:
            continue

        # Get team if available
        driver_laps = laps[laps["Driver"] == driver_code]
        team = "Unknown"
        if "Team" in driver_laps.columns and not driver_laps["Team"].dropna().empty:
            team = str(driver_laps["Team"].dropna().iloc[0])

        drivers.append({
            "driver": driver_code,
            "team": team,
        })

    if not drivers:
        return None

    return {
        "season": season,
        "round": rnd,
        "race_name": f"Round {rnd}",
        "slug": f"{season}-{rnd}",
        "drivers": drivers,
    }


def _compute_and_store_strategy_scores(
    db: Session,
    race_row: Race,
    entry_map: dict[str, Entry],
    laps: pd.DataFrame,
    season: int,
    rnd: int,
) -> None:
    """
    Compute enhanced strategy scores for all drivers in the race.
    Uses the StrategyScoreEngine with all available race data.
    """
    if laps.empty:
        logger.warning("No laps for strategy scoring")
        return

    # Get total laps
    total_laps = int(laps["LapNumber"].max()) if not laps.empty else 0
    if total_laps == 0:
        logger.warning("Cannot compute strategy scores without lap data")
        return

    # Load lap positions from DB
    db_positions = db.query(LapPosition).filter(
        LapPosition.race_id == race_row.id
    ).all()

    positions = []
    for pos in db_positions:
        # Look up driver code from entry
        driver_code = None
        for code, entry in entry_map.items():
            if entry.id == pos.entry_id:
                driver_code = code
                break
        if driver_code:
            positions.append(LapPositionSnapshot(
                lap_number=pos.lap_number,
                driver_code=driver_code,
                entry_id=pos.entry_id,
                position=pos.position,
                gap_to_leader_ms=pos.gap_to_leader_ms,
                gap_to_ahead_ms=pos.gap_to_ahead_ms,
            ))

    if not positions:
        logger.warning("No position data available for strategy scoring")
        return

    # Extract pit stops from laps data
    pit_stops = []
    pit_laps = laps[laps["PitInTime"].notna()]
    for _, row in pit_laps.iterrows():
        driver_code = str(row.get("Driver", "")).strip().upper()
        if not driver_code or driver_code not in entry_map:
            continue

        entry = entry_map[driver_code]
        lap_num = int(row["LapNumber"]) if pd.notna(row["LapNumber"]) else 0

        # Get compound info
        compound_in = row.get("Compound")
        if pd.isna(compound_in):
            compound_in = None

        # Try to find the compound going on from next lap
        next_lap = laps[
            (laps["Driver"] == row["Driver"]) &
            (laps["LapNumber"] == lap_num + 1)
        ]
        compound_out = None
        if not next_lap.empty and pd.notna(next_lap.iloc[0].get("Compound")):
            compound_out = next_lap.iloc[0]["Compound"]

        pit_stops.append(StrategyPitStop(
            lap=lap_num,
            driver_code=driver_code,
            entry_id=entry.id,
            compound_in=str(compound_in) if compound_in else None,
            compound_out=str(compound_out) if compound_out else None,
        ))

    # Load stint data - stints use string race_id like "2024-5"
    stint_race_id = f"{season}-{rnd}"
    stints = db.query(Stint).filter(Stint.race_id == stint_race_id).all()
    stint_data = []
    for stint in stints:
        stint_data.append({
            "driver": stint.driver,
            "stint_no": stint.stint_no,
            "compound": stint.compound,
            "laps": stint.laps,
            "avg_lap_ms": stint.avg_lap_ms,
        })

    # Load race control events
    db_race_control = db.query(RaceControlEvent).filter(
        RaceControlEvent.race_id == race_row.id
    ).all()

    race_control = []
    for event in db_race_control:
        race_control.append(RaceControlPeriod(
            event_type=event.event_type,
            start_lap=event.start_lap,
            end_lap=event.end_lap,
            cause=event.cause,
        ))

    # Load weather data
    db_weather = db.query(RaceWeather).filter(
        RaceWeather.race_id == race_row.id
    ).all()

    weather = []
    for w in db_weather:
        weather.append(WeatherCondition(
            lap_number=w.lap_number,
            track_status=w.track_status,
            air_temp_c=w.air_temp_c,
            track_temp_c=w.track_temp_c,
            rain_intensity=w.rain_intensity,
        ))

    # Build lap times list
    lap_times = []
    for _, row in laps.iterrows():
        driver = row.get("Driver")
        lap_num = row.get("LapNumber")
        lap_time = row.get("LapTime")
        if pd.notna(driver) and pd.notna(lap_num) and pd.notna(lap_time):
            try:
                lap_ms = int(lap_time.total_seconds() * 1000)
                lap_times.append({
                    "driver": str(driver).upper(),
                    "lap": int(lap_num),
                    "lap_ms": lap_ms,
                })
            except (AttributeError, TypeError):
                pass

    # Initialize and run the strategy engine
    engine = StrategyScoreEngine(
        positions=positions,
        pit_stops=pit_stops,
        stint_data=stint_data,
        race_control=race_control,
        weather=weather,
        lap_times=lap_times,
        total_laps=total_laps,
    )

    # Score all drivers
    results = engine.score_all_drivers()
    timestamp = dt.datetime.utcnow()

    # Store results
    for result in results:
        entry = entry_map.get(result.driver_code)
        if not entry:
            continue

        # Upsert strategy score
        stmt = pg_insert(StrategyScore).values(
            entry_id=entry.id,
            total_score=result.total_score,
            pit_timing_score=result.pit_timing_score,
            tire_selection_score=result.tire_selection_score,
            safety_car_score=result.safety_car_score,
            weather_score=result.weather_score,
            calibration_profile=result.calibration_profile,
            calibration_version=result.calibration_version,
            computed_at=timestamp,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entry_id"],
            set_={
                "total_score": stmt.excluded.total_score,
                "pit_timing_score": stmt.excluded.pit_timing_score,
                "tire_selection_score": stmt.excluded.tire_selection_score,
                "safety_car_score": stmt.excluded.safety_car_score,
                "weather_score": stmt.excluded.weather_score,
                "calibration_profile": stmt.excluded.calibration_profile,
                "calibration_version": stmt.excluded.calibration_version,
                "computed_at": stmt.excluded.computed_at,
            },
        )
        db.execute(stmt)
        db.flush()

        # Get the strategy score ID
        strategy_score = db.query(StrategyScore).filter(
            StrategyScore.entry_id == entry.id
        ).one()

        # Delete old decisions and insert new ones
        db.query(StrategyDecision).filter(
            StrategyDecision.strategy_score_id == strategy_score.id
        ).delete()

        for decision in result.decisions:
            db.add(StrategyDecision(
                strategy_score_id=strategy_score.id,
                lap_number=decision.lap_number,
                decision_type=decision.decision_type.value,
                factor=decision.factor.value,
                impact_score=decision.impact_score,
                position_delta=decision.position_delta,
                time_delta_ms=decision.time_delta_ms,
                explanation=decision.explanation,
                comparison_context=decision.comparison_context,
            ))

    db.flush()
    logger.info("Computed and stored strategy scores for %d drivers in race %s",
                len(results), race_row.id)


def _int_or_none(value) -> int | None:
    try:
        if value in (None, "", "nan"):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_default(value, default: float | None = 0.0) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_iterable(values) -> list:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        return [values]
    if isinstance(values, IterableType):
        return list(values)
    return [values]


def _int_list(values) -> list[int]:
    result: list[int] = []
    for value in _as_iterable(values):
        parsed = _int_or_none(value)
        if parsed is not None:
            result.append(parsed)
    return result


def _normalize_driver_code(code: object) -> str | None:
    if code is None:
        return None
    normalized = str(code).strip().upper()
    return normalized or None


def _get_or_create(db: Session, model, filters: dict, defaults: dict | None = None):
    instance = db.query(model).filter_by(**filters).one_or_none()
    if instance:
        if defaults:
            for key, value in defaults.items():
                existing = getattr(instance, key, None)
                if existing in (None, "", 0):
                    setattr(instance, key, value)
        return instance
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance


def _try_fetch_drivegrade_weekend(season: int, rnd: int) -> tuple[dict | None, str | None]:
    providers: list[tuple[str, object]] = []
    try:
        fast = FastF1Provider()
        if fast.is_available():
            providers.append(("fastf1", fast))
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("FastF1 provider unavailable: %s", exc)
    providers.append(("openf1", OpenF1Provider()))
    for name, provider in providers:
        try:
            weekend = provider.fetch_weekend(season, rnd)
            if not weekend:
                continue
            weekend.setdefault("season", season)
            weekend.setdefault("round", rnd)
            if not weekend.get("race_name"):
                weekend["race_name"] = f"Round {rnd}"
            weekend.setdefault(
                "slug",
                slugify(weekend.get("race_name")) if weekend.get("race_name") else f"{season}-{rnd}",
            )
            return weekend, name
        except Exception as exc:
            logger.warning("%s provider fetch failed for %s-%s: %s", name, season, rnd, exc)
            continue
    return None, None


def _driver_inputs_from_weekend(weekend: dict) -> list[DriverRaceInput]:
    inputs: list[DriverRaceInput] = []
    for entry in weekend.get("drivers", []):
        driver_code = _normalize_driver_code(entry.get("driver"))
        if not driver_code:
            continue
        team = entry.get("team") or "Unknown"
        car_pace_info = entry.get("car_pace") or {}
        car_pace = CarPaceIndex(
            driver=driver_code,
            team=team,
            base_delta=_float_or_default(car_pace_info.get("base_delta"), 0.0) or 0.0,
            track_adjustment=_float_or_default(car_pace_info.get("track_adjustment"), 0.0) or 0.0,
        )
        form_info = entry.get("form") or {}
        form = DriverFormModifier(
            consistency=_float_or_default(form_info.get("consistency"), 0.5) or 0.5,
            error_rate=_float_or_default(form_info.get("error_rate"), 0.0) or 0.0,
            start_precision=_float_or_default(form_info.get("start_precision"), 0.5) or 0.5,
        )
        lap_deltas = [
            _float_or_default(delta, 0.0) or 0.0
            for delta in _as_iterable(entry.get("lap_deltas"))
            if delta is not None
        ]
        strategy_info = entry.get("strategy") or {}
        strategy = StrategyPlan(
            optimal_pit_laps=_int_list(strategy_info.get("optimal_pit_laps")),
            actual_pit_laps=_int_list(strategy_info.get("actual_pit_laps")),
            degradation_penalty=_float_or_default(strategy_info.get("degradation_penalty"), 0.0) or 0.0,
        )
        penalty_inputs: list[GradePenaltyEvent] = []
        for penalty in _as_iterable(entry.get("penalties")):
            penalty_inputs.append(
                GradePenaltyEvent(
                    type=str(penalty.get("type", "penalty")),
                    time_loss=_float_or_default(penalty.get("time_loss"), 0.0) or 0.0,
                )
            )
        overtake_inputs: list[GradeOvertakeEvent] = []
        for event in _as_iterable(entry.get("overtakes")):
            context = event.get("context") or {}
            overtake_inputs.append(
                GradeOvertakeEvent(
                    context=OvertakeContext(
                        delta_cpi=_float_or_default(context.get("delta_cpi"), 0.0) or 0.0,
                        tire_delta=int(_float_or_default(context.get("tire_delta"), 0.0) or 0.0),
                        tire_compound_diff=int(_float_or_default(context.get("tire_compound_diff"), 0.0) or 0.0),
                        ers_delta=_float_or_default(context.get("ers_delta"), 0.0) or 0.0,
                        track_difficulty=_float_or_default(context.get("track_difficulty"), 0.5) or 0.5,
                        race_phase_pressure=_float_or_default(context.get("race_phase_pressure"), 0.5) or 0.5,
                    ),
                    success=bool(event.get("success", True)),
                    exposure_time=_float_or_default(event.get("exposure_time"), 0.0) or 0.0,
                    penalized=bool(event.get("penalized", False)),
                    lap_number=_int_or_none(event.get("lap_number")),
                    opponent=_normalize_driver_code(event.get("opponent_driver")),
                    opponent_team=event.get("opponent_team"),
                    event_type=str(event.get("event_type", "on_track")),
                    event_source=str(event.get("event_source", "provider")),
                )
            )
        inputs.append(
            DriverRaceInput(
                driver=driver_code,
                team=team,
                car_pace=car_pace,
                form=form,
                lap_deltas=lap_deltas,
                strategy=strategy,
                penalties=penalty_inputs,
                overtakes=overtake_inputs,
            )
        )
    return inputs


def _store_driver_grade_outputs(
    db: Session,
    season: int,
    rnd: int,
    weekend: dict,
    data_source: str,
) -> None:
    race_row, entry_map = _ensure_reference_entries(db, season, rnd, weekend)
    _persist_driver_events(db, entry_map, weekend.get("drivers", []))
    driver_inputs = _driver_inputs_from_weekend(weekend)
    if not driver_inputs:
        logger.warning("No driver inputs for %s-%s; skipping Drive Grade", season, rnd)
        return
    set_active_calibration(load_calibration_profile())
    calibration = get_active_calibration()
    pipeline = DriveGradePipeline(calibration=calibration)
    results = {driver.driver: pipeline.score_driver(driver) for driver in driver_inputs}
    timestamp = dt.datetime.utcnow()
    for code, entry in entry_map.items():
        breakdown = results.get(code)
        if not breakdown:
            continue
        metrics = (
            db.query(DriverMetrics)
            .filter(DriverMetrics.entry_id == entry.id)
            .one_or_none()
        )
        if not metrics:
            metrics = DriverMetrics(entry_id=entry.id)
            db.add(metrics)
        metrics.calibration_profile = calibration.name
        metrics.data_source = data_source
        metrics.consistency_raw = breakdown.consistency_score
        metrics.consistency_score = breakdown.consistency_score
        metrics.team_strategy_raw = breakdown.team_strategy_score
        metrics.team_strategy_score = breakdown.team_strategy_score
        metrics.racecraft_raw = breakdown.racecraft_score
        metrics.racecraft_score = breakdown.racecraft_score
        metrics.penalties_raw = breakdown.penalty_score
        metrics.penalty_score = breakdown.penalty_score
        metrics.total_grade = breakdown.total_grade
        metrics.created_at = timestamp
    db.flush()


def _ensure_reference_entries(
    db: Session,
    season_value: int,
    round_value: int,
    weekend: dict,
) -> tuple[Race, dict[str, Entry]]:
    season_row = _get_or_create(db, Season, {"year": season_value}, {"status": "active"})
    circuit_name = weekend.get("circuit") or weekend.get("race_name") or f"Round {round_value}"
    circuit_row = _get_or_create(db, Circuit, {"name": circuit_name})
    race_slug = weekend.get("slug") or slugify(weekend.get("race_name")) or f"{season_value}-{round_value}"
    race_row = _get_or_create(
        db,
        Race,
        {"slug": race_slug},
        {
            "season_id": season_row.id,
            "round_number": round_value,
            "circuit_id": circuit_row.id,
            "session_type": "R",
        },
    )
    entry_map: dict[str, Entry] = {}
    for entry in weekend.get("drivers", []):
        driver_code = _normalize_driver_code(entry.get("driver"))
        if not driver_code:
            continue
        driver_row = _get_or_create(db, Driver, {"code": driver_code})
        team_name = entry.get("team") or "Unknown"
        team_row = _get_or_create(db, Team, {"name": team_name})
        entry_row = _get_or_create(
            db,
            Entry,
            {"race_id": race_row.id, "driver_id": driver_row.id},
            {"team_id": team_row.id},
        )
        entry_row.car_number = _int_or_none(entry.get("driver_number"))
        entry_row.grid_position = _int_or_none(entry.get("grid_position"))
        entry_row.finish_position = _int_or_none(entry.get("finish_position"))
        entry_row.status = entry.get("classification_status")
        entry_map[driver_code] = entry_row
    db.flush()
    return race_row, entry_map


def _persist_driver_events(
    db: Session,
    entry_map: dict[str, Entry],
    drivers: list[dict],
) -> None:
    for entry in drivers:
        driver_code = _normalize_driver_code(entry.get("driver"))
        if not driver_code or driver_code not in entry_map:
            continue
        entry_row = entry_map[driver_code]
        strategy = entry.get("strategy") or {}
        penalties = entry.get("penalties", [])
        overtakes = entry.get("overtakes", [])
        db.query(StrategyEventRecord).filter(StrategyEventRecord.entry_id == entry_row.id).delete()
        db.query(PenaltyEventRecord).filter(PenaltyEventRecord.entry_id == entry_row.id).delete()
        db.query(OvertakeEventRecord).filter(OvertakeEventRecord.entry_id == entry_row.id).delete()
        _insert_strategy_events(db, entry_row.id, strategy)
        _insert_penalty_events(db, entry_row.id, penalties)
        _insert_overtake_events(db, entry_map, entry_row.id, overtakes)


def _insert_strategy_events(db: Session, entry_id: int, strategy: dict) -> None:
    optimal = _int_list(strategy.get("optimal_pit_laps"))
    actual = _int_list(strategy.get("actual_pit_laps"))
    penalty = _float_or_default(strategy.get("degradation_penalty"), 0.0) or 0.0
    fallback = optimal[-1] if optimal else None
    if not actual and not optimal:
        if penalty:
            db.add(
                StrategyEventRecord(
                    entry_id=entry_id,
                    degradation_penalty=penalty,
                )
            )
        return
    for idx, executed in enumerate(actual or optimal):
        planned = optimal[idx] if idx < len(optimal) else fallback
        db.add(
            StrategyEventRecord(
                entry_id=entry_id,
                planned_lap=planned,
                executed_lap=executed,
                degradation_penalty=penalty if idx == 0 else 0.0,
            )
        )


def _insert_penalty_events(db: Session, entry_id: int, penalties: list[dict]) -> None:
    for penalty in penalties:
        db.add(
            PenaltyEventRecord(
                entry_id=entry_id,
                penalty_type=penalty.get("type"),
                time_loss_seconds=_float_or_default(penalty.get("time_loss"), 0.0),
                source=penalty.get("source") or "provider",
                lap_number=_int_or_none(penalty.get("lap_number")),
                notes=penalty.get("notes"),
            )
        )


def _insert_overtake_events(
    db: Session,
    entry_map: dict[str, Entry],
    entry_id: int,
    overtakes: list[dict],
) -> None:
    for event in overtakes:
        context = event.get("context") or {}
        opponent_code = _normalize_driver_code(event.get("opponent_driver"))
        opponent_entry_id = entry_map.get(opponent_code).id if opponent_code and opponent_code in entry_map else None
        db.add(
            OvertakeEventRecord(
                entry_id=entry_id,
                opponent_entry_id=opponent_entry_id,
                lap_number=_int_or_none(event.get("lap_number")),
                success=bool(event.get("success", True)),
                penalized=bool(event.get("penalized", False)),
                exposure_time=_float_or_default(event.get("exposure_time"), 0.0),
                delta_cpi=_float_or_default(context.get("delta_cpi")),
                tire_delta=_float_or_default(context.get("tire_delta")),
                tire_compound_diff=_float_or_default(context.get("tire_compound_diff")),
                ers_delta=_float_or_default(context.get("ers_delta")),
                track_difficulty=_float_or_default(context.get("track_difficulty")),
                race_phase_pressure=_float_or_default(context.get("race_phase_pressure")),
                event_type=event.get("event_type"),
                event_source=event.get("event_source"),
            )
        )


def ingest_session(season: int, rnd: int, session_type: str = "Race", force: bool = False) -> None:
    """Main RQ job entry-point."""
    provider = get_provider(season, rnd)
    laps = provider.load_laps(session_type=session_type)
    if laps.empty:
        logger.warning("No laps for %s-%s %s", season, rnd, session_type)
        return

    # Try to get session results (for race/qualifying classification)
    session_results = None
    try:
        session_results = provider.load_results(session_type=session_type)
    except AttributeError:
        # Provider doesn't support load_results, will derive from laps
        pass
    except Exception as exc:
        logger.warning("Failed to load session results for %s-%s %s: %s", season, rnd, session_type, exc)

    # Load race control and weather data (for Race sessions only)
    race_control = None
    weather_data = None
    is_race = session_type.lower() in ("race", "r")

    if is_race:
        try:
            race_control = provider.load_race_control(session_type=session_type)
        except AttributeError:
            logger.debug("Provider doesn't support load_race_control")
        except Exception as exc:
            logger.warning("Failed to load race control for %s-%s: %s", season, rnd, exc)

        try:
            weather_data = provider.load_weather(session_type=session_type)
        except AttributeError:
            logger.debug("Provider doesn't support load_weather")
        except Exception as exc:
            logger.warning("Failed to load weather for %s-%s: %s", season, rnd, exc)

    race_id = f"{season}-{rnd}"
    normalized_session = SESSION_TYPE_MAP.get(session_type, session_type.lower())
    weekend_payload, grade_source = _try_fetch_drivegrade_weekend(season, rnd)

    # Check if this specific session has already been ingested (by CalendarEvent status)
    with SessionLocal() as db:
        event = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=rnd)
            .filter(CalendarEvent.session_type.ilike(f"%{session_type}%"))
            .one_or_none()
        )
        session_already_ingested = event and event.status == "ingested"

        # Also check if lap_times exist for this race (for race-specific data)
        lap_data_exists = db.scalar(
            sa.text("SELECT 1 FROM lap_times WHERE race_id = :rid LIMIT 1"),
            {"rid": f"{season}-{rnd}"},
        )

    if session_already_ingested and not force:
        logger.info("%s-%s %s already ingested; skipping", season, rnd, session_type)
        return

    with SessionLocal() as db:
        # Store laps/stints only if this is race session and no lap data exists yet
        # (Practice sessions don't need separate lap storage - we derive classifications from provider data)
        is_race_session = normalized_session in ("race", "sprint_race")
        if is_race_session and not lap_data_exists:
            _store_laps(db, race_id, laps)
            _store_stints(db, race_id, laps)
        # Always store session classifications (supports amendments)
        try:
            _store_session_classifications(db, season, rnd, session_type, laps, provider, session_results)
        except Exception as exc:
            logger.exception("Failed to store session classifications for %s-%s %s: %s", season, rnd, session_type, exc)

        # Variables to hold race context for strategy data
        race_row = None
        entry_map = None

        if weekend_payload:
            # First ensure we have race/entry reference data (independent of DriveGrade)
            try:
                race_row, entry_map = _ensure_reference_entries(db, season, rnd, weekend_payload)
            except Exception as exc:
                logger.exception("Failed to create reference entries for %s: %s", race_id, exc)

            # Then compute DriveGrade scores (can fail without blocking strategy scoring)
            try:
                _store_driver_grade_outputs(
                    db,
                    season,
                    rnd,
                    weekend_payload,
                    grade_source or provider.__class__.__name__,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to compute DriveGrade for %s: %s", race_id, exc)
        else:
            logger.warning("No Drive Grade weekend payload for %s", race_id)
            # Fallback: Try to build minimal race/entry data from laps for strategy scoring
            if is_race and not laps.empty:
                try:
                    fallback_payload = _build_minimal_weekend_from_laps(laps, season, rnd)
                    if fallback_payload:
                        race_row, entry_map = _ensure_reference_entries(db, season, rnd, fallback_payload)
                        logger.info("Created fallback race context from laps for %s", race_id)
                except Exception as exc:
                    logger.warning("Failed to create fallback race context for %s: %s", race_id, exc)

        # Store strategy-related data (only for Race sessions with valid race context)
        if is_race and race_row and entry_map:
            # Store lap positions
            try:
                _store_lap_positions(db, race_row, entry_map, laps)
            except Exception as exc:
                logger.warning("Failed to store lap positions for %s: %s", race_id, exc)

            # Store race control events (SC, VSC, red flags)
            if race_control is not None:
                try:
                    _store_race_control_events(db, race_row, race_control)
                except Exception as exc:
                    logger.warning("Failed to store race control events for %s: %s", race_id, exc)

            # Store weather data
            if weather_data is not None:
                try:
                    _store_race_weather(db, race_row, weather_data, laps)
                except Exception as exc:
                    logger.warning("Failed to store weather data for %s: %s", race_id, exc)

            # Compute and store enhanced strategy scores
            try:
                _compute_and_store_strategy_scores(db, race_row, entry_map, laps, season, rnd)
            except Exception as exc:
                logger.warning("Failed to compute strategy scores for %s: %s", race_id, exc)

        # mark calendar row
        ev = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=rnd, session_type=session_type)
            .one_or_none()
        )
        if ev:
            ev.status = "ingested"
        db.commit()
    try:
        invalidate_analytics_cache(season, rnd)
    except Exception as exc:  # pragma: no cover - cache should not block ingestion
        logger.warning("Failed to invalidate analytics cache for %s-%s: %s", season, rnd, exc)
    try:
        invalidate_session_cache(season, rnd, session_type)
    except Exception as exc:  # pragma: no cover - cache should not block ingestion
        logger.warning("Failed to invalidate session cache for %s-%s %s: %s", season, rnd, session_type, exc)
    try:
        invalidate_strategy_cache(season, rnd)
    except Exception as exc:  # pragma: no cover - cache should not block ingestion
        logger.warning("Failed to invalidate strategy cache for %s-%s: %s", season, rnd, exc)
    logger.info("%s %s complete: len(laps)=%s", race_id, session_type, len(laps))
