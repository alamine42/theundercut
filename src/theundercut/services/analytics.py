"""Helper functions to assemble race analytics payloads."""

from __future__ import annotations

import datetime as dt
from statistics import mean
from typing import Iterable, List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from theundercut.models import (
    LapTime,
    Stint,
    DriverMetrics,
    Entry,
    Race,
    Season,
    Driver,
)


def _race_id(season: int, rnd: int) -> str:
    return f"{season}-{rnd}"


def _normalise_laps(rows: Iterable) -> List[Dict[str, Any]]:
    laps: List[Dict[str, Any]] = []
    for driver, lap, lap_ms, compound, stint_no, pit in rows:
        laps.append(
            {
                "driver": driver,
                "lap": int(lap) if lap is not None else None,
                "lap_ms": int(lap_ms) if lap_ms is not None else None,
                "compound": compound,
                "stint_no": int(stint_no) if stint_no is not None else None,
                "pit": bool(pit) if pit is not None else False,
            }
        )
    return laps


def _normalise_stints(rows: Iterable) -> List[Dict[str, Any]]:
    stints: List[Dict[str, Any]] = []
    for driver, stint_no, compound, laps, avg_lap_ms in rows:
        stints.append(
            {
                "driver": driver,
                "stint_no": int(stint_no) if stint_no is not None else None,
                "compound": compound,
                "laps": int(laps) if laps is not None else None,
                "avg_lap_ms": float(avg_lap_ms) if avg_lap_ms is not None else None,
            }
        )
    return stints


def _compute_driver_pace_grade_table(laps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Temporary heuristic until T6 precomputes richer metrics."""
    # Group lap_ms per driver ignoring invalid values
    per_driver: Dict[str, List[int]] = {}
    for lap in laps:
        lap_ms = lap["lap_ms"]
        driver = lap["driver"]
        if lap_ms is None or lap_ms <= 0:
            continue
        per_driver.setdefault(driver, []).append(lap_ms)

    if not per_driver:
        return []

    averages = {drv: mean(vals) for drv, vals in per_driver.items() if vals}
    if not averages:
        return []

    best = min(averages.values())
    worst = max(averages.values())
    spread = max(worst - best, 1)

    grades: List[Dict[str, Any]] = []
    for driver, avg in averages.items():
        pace_delta = avg - best
        # Simple 0-100 score where best driver ~95-100, slowest >=65
        score = max(60.0, 100.0 - (pace_delta / spread) * 35.0)
        grades.append(
            {
                "driver": driver,
                "pace_ms": avg,
                "pace_delta_ms": pace_delta,
                "score": round(score, 1),
            }
        )
    # Sort descending by score
    grades.sort(key=lambda item: item["score"], reverse=True)
    return grades


def _fetch_driver_metric_grades(
    db: Session,
    season: int,
    rnd: int,
) -> list[dict]:
    rows = (
        db.query(
            Driver.code,
            DriverMetrics.total_grade,
            DriverMetrics.consistency_score,
            DriverMetrics.team_strategy_score,
            DriverMetrics.racecraft_score,
            DriverMetrics.penalty_score,
        )
        .join(Entry, DriverMetrics.entry_id == Entry.id)
        .join(Driver, Entry.driver_id == Driver.id)
        .join(Race, Entry.race_id == Race.id)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season, Race.round_number == rnd)
        .order_by(Driver.code)
        .all()
    )
    return [
        {
            "driver": code,
            "total_grade": float(total or 0.0),
            "consistency": float(consistency or 0.0),
            "team_strategy": float(strategy or 0.0),
            "racecraft": float(racecraft or 0.0),
            "penalties": float(penalties or 0.0),
            "source": "drive_grade_db",
        }
        for code, total, consistency, strategy, racecraft, penalties in rows
    ]


def fetch_race_analytics(
    db: Session,
    season: int,
    rnd: int,
    drivers: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    race_id = _race_id(season, rnd)

    lap_stmt = (
        select(
            LapTime.driver,
            LapTime.lap,
            LapTime.lap_ms,
            LapTime.compound,
            LapTime.stint_no,
            LapTime.pit,
        )
        .where(LapTime.race_id == race_id)
        .order_by(LapTime.driver, LapTime.lap)
    )
    if drivers:
        lap_stmt = lap_stmt.where(LapTime.driver.in_(list(drivers)))

    lap_rows = db.execute(lap_stmt).all()
    laps = _normalise_laps(lap_rows)

    stint_stmt = (
        select(
            Stint.driver,
            Stint.stint_no,
            Stint.compound,
            Stint.laps,
            Stint.avg_lap_ms,
        )
        .where(Stint.race_id == race_id)
        .order_by(Stint.driver, Stint.stint_no)
    )
    if drivers:
        stint_stmt = stint_stmt.where(Stint.driver.in_(list(drivers)))

    stint_rows = db.execute(stint_stmt).all()
    stints = _normalise_stints(stint_rows)

    driver_metric_grades = _fetch_driver_metric_grades(db, season, rnd)
    if driver_metric_grades:
        driver_pace_grades = driver_metric_grades
    else:
        driver_pace_grades = [
            {**grade, "source": "lap_time_heuristic"}
            for grade in _compute_driver_pace_grade_table(laps)
        ]

    response = {
        "race": {"season": season, "round": rnd},
        "last_updated": dt.datetime.utcnow().isoformat() + "Z",
        "laps": laps,
        "stints": stints,
        "driver_pace_grades": driver_pace_grades,
    }
    return response


__all__ = ["fetch_race_analytics"]
