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
from theundercut.services.cache import invalidate_analytics_cache


logger = logging.getLogger(__name__)


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

    race_id = f"{season}-{rnd}"
    weekend_payload, grade_source = _try_fetch_drivegrade_weekend(season, rnd)

    with SessionLocal() as db:
        already = db.scalar(
            sa.text("SELECT 1 FROM lap_times WHERE race_id = :rid LIMIT 1"),
            {"rid": f"{season}-{rnd}"},
        )
    existing = bool(already)
    if existing and not force:
        logger.info("%s-%s already ingested; skipping", season, rnd)
        return

    with SessionLocal() as db:
        if not existing:
            _store_laps(db, race_id, laps)
            _store_stints(db, race_id, laps)
        if weekend_payload:
            try:
                _store_driver_grade_outputs(
                    db,
                    season,
                    rnd,
                    weekend_payload,
                    grade_source or provider.__class__.__name__,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to compute grades for %s: %s", race_id, exc)
        else:
            logger.warning("No Drive Grade weekend payload for %s", race_id)
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
    logger.info("%s %s complete: len(laps)=%s", race_id, session_type, len(laps))
