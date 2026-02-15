"""Utilities for converting raw weekend descriptors into loader tables."""
from __future__ import annotations

from math import nan
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd

from .pipeline import DriverRaceInput, load_weekend_file


def load_driver_inputs_from_json(path: str | Path) -> List[DriverRaceInput]:
    """Parse a JSON weekend file into driver inputs."""

    return load_weekend_file(path)


def build_tables(drivers: Sequence[DriverRaceInput]) -> Dict[str, pd.DataFrame]:
    """Convert DriverRaceInput objects into tabular structures."""

    driver_rows: List[Dict[str, object]] = []
    telemetry_rows: List[Dict[str, object]] = []
    strategy_rows: List[Dict[str, object]] = []
    penalty_rows: List[Dict[str, object]] = []
    overtake_rows: List[Dict[str, object]] = []

    for driver in drivers:
        driver_rows.append(
            {
                "driver": driver.driver,
                "team": driver.team,
                "base_delta": driver.car_pace.base_delta,
                "track_adjustment": driver.car_pace.track_adjustment,
                "form_consistency": driver.form.consistency,
                "form_error_rate": driver.form.error_rate,
                "form_start_precision": driver.form.start_precision,
            }
        )
        for idx, delta in enumerate(driver.lap_deltas, start=1):
            telemetry_rows.append(
                {"driver": driver.driver, "lap_number": idx, "lap_delta": delta}
            )
        strategy_rows.append(
            {
                "driver": driver.driver,
                "optimal_pits": _join_ints(driver.strategy.optimal_pit_laps),
                "actual_pits": _join_ints(driver.strategy.actual_pit_laps),
                "degradation_penalty": driver.strategy.degradation_penalty,
            }
        )
        for penalty in driver.penalties:
            penalty_rows.append(
                {
                    "driver": driver.driver,
                    "type": penalty.type,
                    "time_loss": penalty.time_loss,
                }
            )
        for event in driver.overtakes:
            overtake_rows.append(
                {
                    "driver": driver.driver,
                    "lap_number": event.lap_number if event.lap_number is not None else nan,
                    "opponent_driver": event.opponent if event.opponent is not None else nan,
                    "opponent_team": event.opponent_team if event.opponent_team is not None else nan,
                    "event_type": event.event_type,
                    "event_source": event.event_source,
                    "success": event.success,
                    "exposure_time": event.exposure_time,
                    "penalized": event.penalized,
                    "delta_cpi": event.context.delta_cpi,
                    "tire_delta": event.context.tire_delta,
                    "tire_compound_diff": event.context.tire_compound_diff,
                    "ers_delta": event.context.ers_delta,
                    "track_difficulty": event.context.track_difficulty,
                    "race_phase_pressure": event.context.race_phase_pressure,
                }
            )

    return {
        "driver_baseline": _make_frame(
            driver_rows,
            [
                "driver",
                "team",
                "base_delta",
                "track_adjustment",
                "form_consistency",
                "form_error_rate",
                "form_start_precision",
            ],
        ),
        "telemetry": _make_frame(
            telemetry_rows,
            ["driver", "lap_number", "lap_delta"],
        ),
        "strategy": _make_frame(
            strategy_rows,
            ["driver", "optimal_pits", "actual_pits", "degradation_penalty"],
        ),
        "penalties": _make_frame(
            penalty_rows,
            ["driver", "type", "time_loss"],
        ),
        "overtakes": _make_frame(
            overtake_rows,
            [
                "driver",
                "lap_number",
                "opponent_driver",
                "opponent_team",
                "event_type",
                "event_source",
                "success",
                "exposure_time",
                "penalized",
                "delta_cpi",
                "tire_delta",
                "tire_compound_diff",
                "ers_delta",
                "track_difficulty",
                "race_phase_pressure",
            ],
        ),
    }


def write_tables(
    tables: Dict[str, pd.DataFrame],
    directory: str | Path,
    *,
    file_format: str = "csv",
) -> None:
    """Persist the generated tables to disk."""

    dest = Path(directory)
    dest.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        path = dest / f"{name}.{file_format}"
        if file_format == "parquet":
            frame.to_parquet(path, index=False)
        else:
            frame.to_csv(path, index=False)


def _join_ints(values: Iterable[int]) -> str:
    return "|".join(str(value) for value in values)


def _make_frame(rows: List[Dict[str, object]], columns: List[str]) -> pd.DataFrame:
    if rows:
        return pd.DataFrame(rows)[columns]
    return pd.DataFrame(columns=columns)


__all__ = ["load_driver_inputs_from_json", "build_tables", "write_tables"]
