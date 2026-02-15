"""Utilities for ingesting tabular telemetry/strategy data into pipeline inputs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set

import pandas as pd

from .drive_grade import (
    CarPaceIndex,
    DriverFormModifier,
    OvertakeContext,
    OvertakeEvent,
)
from .pipeline import (
    DriverRaceInput,
    PenaltyEvent,
    StrategyPlan,
)


REQUIRED_COLUMNS: Dict[str, Set[str]] = {
    "driver_baseline": {
        "driver",
        "team",
        "base_delta",
        "track_adjustment",
        "form_consistency",
        "form_error_rate",
        "form_start_precision",
    },
    "telemetry": {"driver", "lap_number", "lap_delta"},
    "strategy": {"driver", "optimal_pits", "actual_pits", "degradation_penalty"},
    "penalties": {"driver", "type", "time_loss"},
    "overtakes": {
        "driver",
        "success",
        "exposure_time",
        "penalized",
        "delta_cpi",
        "tire_delta",
        "tire_compound_diff",
        "ers_delta",
        "track_difficulty",
        "race_phase_pressure",
    },
}


class TableValidationError(ValueError):
    """Raised when table schemas or values are invalid."""


@dataclass(slots=True)
class WeekendTables:
    """Typed collection of weekend data sourced from tabular files."""

    driver_baseline: pd.DataFrame
    telemetry: pd.DataFrame
    strategy: pd.DataFrame
    penalties: pd.DataFrame
    overtakes: pd.DataFrame


class WeekendTableLoader:
    """Loads driver context, telemetry, and race events from CSV/Parquet tables."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        if not self.directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

    def load_tables(self) -> WeekendTables:
        return WeekendTables(
            driver_baseline=self._read_table("driver_baseline"),
            telemetry=self._read_table("telemetry"),
            strategy=self._read_table("strategy"),
            penalties=self._read_table("penalties"),
            overtakes=self._read_table("overtakes"),
        )

    def build_driver_inputs(self) -> List[DriverRaceInput]:
        tables = self.load_tables()

        lap_map = (
            tables.telemetry.sort_values("lap_number")
            .groupby("driver")["lap_delta"]
            .apply(list)
            .to_dict()
        )
        strategy_map = {}
        for row in tables.strategy.itertuples():
            optimal = _parse_int_list(row.optimal_pits, field_name="optimal_pits", driver=row.driver)
            actual = _parse_int_list(row.actual_pits, field_name="actual_pits", driver=row.driver)
            _validate_strategy_lists(row.driver, optimal, actual)
            strategy_map[row.driver] = StrategyPlan(
                optimal_pit_laps=optimal,
                actual_pit_laps=actual,
                degradation_penalty=float(row.degradation_penalty or 0.0),
            )
        penalty_map: Dict[str, List[PenaltyEvent]] = {}
        for row in tables.penalties.itertuples():
            penalty_map.setdefault(row.driver, []).append(
                PenaltyEvent(type=row.type, time_loss=float(row.time_loss))
            )

        overtake_map: Dict[str, List[OvertakeEvent]] = {}
        for row in tables.overtakes.itertuples():
            context = OvertakeContext(
                delta_cpi=float(row.delta_cpi),
                tire_delta=int(row.tire_delta),
                tire_compound_diff=int(row.tire_compound_diff),
                ers_delta=float(row.ers_delta),
                track_difficulty=float(row.track_difficulty),
                race_phase_pressure=float(row.race_phase_pressure),
            )
            lap_value = getattr(row, "lap_number", None)
            if lap_value == lap_value and lap_value is not None:
                lap_value = int(lap_value)
            else:
                lap_value = None
            opponent_driver = getattr(row, "opponent_driver", None)
            if opponent_driver == opponent_driver:
                opponent_driver = opponent_driver or None
            else:
                opponent_driver = None
            opponent_team = getattr(row, "opponent_team", None)
            if opponent_team == opponent_team:
                opponent_team = opponent_team or None
            else:
                opponent_team = None
            event_type = getattr(row, "event_type", "on_track") or "on_track"
            event_source = getattr(row, "event_source", "unknown") or "unknown"
            overtake_map.setdefault(row.driver, []).append(
                OvertakeEvent(
                    context=context,
                    success=_parse_bool(row.success),
                    exposure_time=float(row.exposure_time),
                    penalized=_parse_bool(row.penalized),
                    lap_number=lap_value,
                    opponent=opponent_driver,
                    opponent_team=opponent_team,
                    event_type=str(event_type),
                    event_source=str(event_source),
                )
            )

        inputs: List[DriverRaceInput] = []
        for row in tables.driver_baseline.itertuples():
            driver_name = row.driver
            car_pace = CarPaceIndex(
                driver=driver_name,
                team=row.team,
                base_delta=float(row.base_delta),
                track_adjustment=float(row.track_adjustment or 0.0),
            )
            form = DriverFormModifier(
                consistency=float(row.form_consistency),
                error_rate=float(row.form_error_rate),
                start_precision=float(row.form_start_precision),
            )
            inputs.append(
                DriverRaceInput(
                    driver=driver_name,
                    team=row.team,
                    car_pace=car_pace,
                    form=form,
                    lap_deltas=lap_map.get(driver_name, []),
                    strategy=strategy_map.get(driver_name, StrategyPlan([], [])),
                    penalties=penalty_map.get(driver_name, []),
                    overtakes=overtake_map.get(driver_name, []),
                )
            )
        return inputs

    def _read_table(self, stem: str) -> pd.DataFrame:
        for ext in (".parquet", ".csv"):
            path = self.directory / f"{stem}{ext}"
            if path.exists():
                if path.suffix == ".parquet":
                    df = pd.read_parquet(path)
                else:
                    df = pd.read_csv(path)
                _validate_columns(stem, df)
                return df
        raise FileNotFoundError(f"Missing {stem}.csv or {stem}.parquet in {self.directory}")


def _validate_columns(stem: str, frame: pd.DataFrame) -> None:
    required = REQUIRED_COLUMNS.get(stem)
    if not required:
        return
    missing = required - set(frame.columns)
    if missing:
        raise TableValidationError(f"{stem} missing columns: {sorted(missing)}")


def _parse_int_list(value: object, *, field_name: str, driver: object) -> List[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    parts = str(value).split("|")
    entries: List[int] = []
    for part in parts:
        text = part.strip()
        if not text:
            continue
        try:
            entries.append(int(text))
        except ValueError as exc:
            raise TableValidationError(
                f"Could not parse integer in {field_name} for driver '{driver}': {text}"
            ) from exc
    return entries


def _validate_strategy_lists(driver: str, optimal: List[int], actual: List[int]) -> None:
    if not optimal and not actual:
        return
    if len(optimal) != len(actual):
        raise TableValidationError(
            f"Strategy plan mismatch for driver '{driver}': "
            f"{len(optimal)} optimal vs {len(actual)} actual pit entries."
        )


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


__all__ = ["WeekendTableLoader", "WeekendTables", "TableValidationError"]
