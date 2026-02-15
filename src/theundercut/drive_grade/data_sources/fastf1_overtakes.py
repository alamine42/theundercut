"""Utilities for extracting overtake events from FastF1 timing data."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass(slots=True)
class DetectedOvertake:
    lap_number: int
    overtaking_driver: str
    overtaken_driver: str
    reason: str  # "on_track" or "pit_cycle"
    tire_delta: float | None
    tire_compound_diff: int | None
    ers_delta: float | None


def detect_overtake_events(session, driver_numbers: Dict[str, str]) -> List[DetectedOvertake]:
    """Detect overtakes using lap classification deltas and enrich with telemetry."""

    laps = session.laps[
        [
            "Driver",
            "DriverNumber",
            "LapNumber",
            "Position",
            "PitInTime",
            "PitOutTime",
            "LapTime",
            "LapStartTime",
            "Time",
            "TyreLife",
            "Compound",
        ]
    ].copy()
    laps = laps.dropna(subset=["Driver", "LapNumber", "Position"])
    if laps.empty:
        return []
    laps.sort_values(["Driver", "LapNumber", "Time"], inplace=True)
    laps = laps.drop_duplicates(subset=["Driver", "LapNumber"], keep="last")

    classification, pit_flags, tyre_life_map, compound_map, lap_mid_times = _build_classification(laps)
    throttle_lookup = _build_throttle_lookup(session, driver_numbers)

    events: List[DetectedOvertake] = []
    sorted_laps = sorted(classification.keys())

    for idx in range(1, len(sorted_laps)):
        prev_lap = sorted_laps[idx - 1]
        lap = sorted_laps[idx]
        prev_positions = classification.get(prev_lap)
        curr_positions = classification.get(lap)
        if not prev_positions or not curr_positions:
            continue
        prev_order = [driver for driver, _ in sorted(prev_positions.items(), key=lambda item: item[1])]
        curr_order = [driver for driver, _ in sorted(curr_positions.items(), key=lambda item: item[1])]
        for driver, before in prev_positions.items():
            after = curr_positions.get(driver)
            if after is None or after >= before:
                continue
            prev_idx = prev_order.index(driver)
            curr_idx = curr_order.index(driver)
            prev_ahead = prev_order[:prev_idx]
            curr_ahead = curr_order[:curr_idx]
            overtaken = [code for code in prev_ahead if code not in curr_ahead]
            if not overtaken:
                continue
            driver_pitted = pit_flags.get((driver, prev_lap), False) or pit_flags.get((driver, lap), False)
            for target in overtaken:
                target_pitted = pit_flags.get((target, prev_lap), False) or pit_flags.get((target, lap), False)
                reason = "pit_cycle" if driver_pitted or target_pitted else "on_track"
                tire_delta = _compute_tire_delta(driver, target, lap, tyre_life_map)
                compound_diff = _compute_compound_diff(driver, target, lap, compound_map)
                ers_delta = _compute_throttle_delta(driver, target, lap, lap_mid_times, throttle_lookup)
                events.append(
                    DetectedOvertake(
                        lap_number=lap,
                        overtaking_driver=driver,
                        overtaken_driver=target,
                        reason=reason,
                        tire_delta=tire_delta,
                        tire_compound_diff=compound_diff,
                        ers_delta=ers_delta,
                    )
                )
    return events


def _build_classification(
    laps: pd.DataFrame,
) -> Tuple[
    Dict[int, Dict[str, int]],
    Dict[Tuple[str, int], bool],
    Dict[Tuple[str, int], float],
    Dict[Tuple[str, int], str],
    Dict[Tuple[str, int], float],
]:
    classification: Dict[int, Dict[str, int]] = defaultdict(dict)
    pit_flags: Dict[Tuple[str, int], bool] = {}
    tyre_life: Dict[Tuple[str, int], float] = {}
    compounds: Dict[Tuple[str, int], str] = {}
    lap_mid_times: Dict[Tuple[str, int], float] = {}

    for row in laps.itertuples():
        lap = int(row.LapNumber)
        driver = row.Driver
        position = int(row.Position)
        classification[lap][driver] = position
        pit_flag = False
        if pd.notna(row.PitInTime):
            pit_flag = True
        if pd.notna(row.PitOutTime):
            pit_flag = True
        if pit_flag:
            pit_flags[(driver, lap)] = True
            pit_flags[(driver, max(0, lap - 1))] = True
        if pd.notna(row.TyreLife):
            tyre_life[(driver, lap)] = float(row.TyreLife)
        if isinstance(row.Compound, str):
            compounds[(driver, lap)] = row.Compound.upper()
        mid_time = None
        if pd.notna(row.LapStartTime) and pd.notna(row.LapTime):
            mid_delta = row.LapStartTime + 0.5 * row.LapTime
            mid_time = mid_delta.total_seconds()
        elif pd.notna(row.Time):
            mid_time = row.Time.total_seconds()
        if mid_time is not None:
            lap_mid_times[(driver, lap)] = float(mid_time)

    return classification, pit_flags, tyre_life, compounds, lap_mid_times


def _compute_tire_delta(driver: str, opponent: str, lap: int, tyre_life: Dict[Tuple[str, int], float]) -> float | None:
    life_attacker = tyre_life.get((driver, lap))
    life_defender = tyre_life.get((opponent, lap))
    if life_attacker is None or life_defender is None:
        return None
    return life_defender - life_attacker


COMPOUND_ORDER = {
    "HARD": 1,
    "C1": 1,
    "MEDIUM": 2,
    "C2": 2,
    "SOFT": 3,
    "C3": 3,
    "C4": 3,
    "C5": 3,
    "INTERMEDIATE": 2,
    "WET": 1,
}


def _compute_compound_diff(driver: str, opponent: str, lap: int, compounds: Dict[Tuple[str, int], str]) -> int | None:
    attacker = compounds.get((driver, lap))
    defender = compounds.get((opponent, lap))
    if attacker is None or defender is None:
        return None
    att_rank = COMPOUND_ORDER.get(attacker.upper(), 0)
    def_rank = COMPOUND_ORDER.get(defender.upper(), 0)
    return att_rank - def_rank


def _build_throttle_lookup(session, driver_numbers: Dict[str, str]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    lookup: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for code, number in driver_numbers.items():
        try:
            telemetry = session.car_data[number]
        except Exception:
            continue
        if telemetry is None or telemetry.empty or "SessionTime" not in telemetry:
            continue
        if "Throttle" not in telemetry:
            continue
        times = telemetry["SessionTime"].dt.total_seconds().to_numpy()
        values = telemetry["Throttle"].to_numpy()
        if len(times) == 0:
            continue
        lookup[code] = (times, values)
    return lookup


def _compute_throttle_delta(
    driver: str,
    opponent: str,
    lap: int,
    lap_mid_times: Dict[Tuple[str, int], float],
    throttle_lookup: Dict[str, Tuple[np.ndarray, np.ndarray]],
) -> float | None:
    mid_time = lap_mid_times.get((driver, lap))
    if mid_time is None:
        return None
    driver_throttle = _lookup_value(throttle_lookup.get(driver), mid_time)
    opponent_throttle = _lookup_value(throttle_lookup.get(opponent), mid_time)
    if driver_throttle is None or opponent_throttle is None:
        return None
    return driver_throttle - opponent_throttle


def _lookup_value(data: Tuple[np.ndarray, np.ndarray] | None, target: float) -> float | None:
    if data is None:
        return None
    times, values = data
    if len(times) == 0:
        return None
    idx = np.searchsorted(times, target)
    if idx <= 0:
        return float(values[0])
    if idx >= len(times):
        return float(values[-1])
    before = (target - times[idx - 1], values[idx - 1])
    after = (times[idx] - target, values[idx])
    return float(before[1] if before[0] <= after[0] else after[1])


__all__ = ["DetectedOvertake", "detect_overtake_events"]
