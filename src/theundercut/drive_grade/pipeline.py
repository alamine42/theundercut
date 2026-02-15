"""Data ingestion and pipeline orchestration for Drive Grade."""
from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .calibration import CalibrationProfile, get_active_calibration
from .drive_grade import (
    CarPaceIndex,
    DriveGradeBreakdown,
    DriveGradeCalculator,
    DriverFormModifier,
    OvertakeContext,
    OvertakeEvent,
    _clamp,
)


@dataclass(slots=True)
class StrategyPlan:
    """Representation of the intended and executed pit strategy."""

    optimal_pit_laps: List[int]
    actual_pit_laps: List[int]
    degradation_penalty: float = 0.0


@dataclass(slots=True)
class PenaltyEvent:
    """Simple record of time lost to errors or sanctions."""

    type: str
    time_loss: float


@dataclass(slots=True)
class DriverRaceInput:
    """All intermediate values required to build a Drive Grade."""

    driver: str
    team: str
    car_pace: CarPaceIndex
    form: DriverFormModifier
    lap_deltas: List[float]
    strategy: StrategyPlan
    penalties: List[PenaltyEvent]
    overtakes: List[OvertakeEvent]


class DriveGradePipeline:
    """Coordinates ingestion, intermediate metric creation, and final scoring."""

    def __init__(
        self,
        calculator: DriveGradeCalculator | None = None,
        calibration: CalibrationProfile | None = None,
    ) -> None:
        self.calculator = calculator or DriveGradeCalculator()
        self.calibration = calibration or get_active_calibration()

    def score_driver(self, driver_input: DriverRaceInput) -> DriveGradeBreakdown:
        expected_delta = (
            driver_input.car_pace.expected_delta + driver_input.form.adjustment()
        )
        consistency = compute_consistency_score(
            driver_input.lap_deltas,
            expected_delta,
            driver_input.strategy.actual_pit_laps,
            calibration=self.calibration,
        )
        strategy = compute_strategy_score(driver_input.strategy, calibration=self.calibration)
        penalties = compute_penalty_score(driver_input.penalties, calibration=self.calibration)
        on_track_events = sum(1 for event in driver_input.overtakes if getattr(event, "event_type", "on_track") == "on_track")
        pit_cycle_events = sum(1 for event in driver_input.overtakes if getattr(event, "event_type", "on_track") != "on_track")
        return self.calculator.build_breakdown(
            consistency=consistency,
            strategy=strategy,
            penalties=penalties,
            events=driver_input.overtakes,
            on_track_events=on_track_events,
            pit_cycle_events=pit_cycle_events,
        )

    def run_from_json(self, path: str | Path) -> Dict[str, DriveGradeBreakdown]:
        drivers = load_weekend_file(path)
        return {driver.driver: self.score_driver(driver) for driver in drivers}


def compute_consistency_score(
    lap_deltas: Sequence[float],
    expected_delta: float,
    actual_pit_laps: Sequence[int],
    *,
    calibration: CalibrationProfile | None = None,
) -> float:
    """Higher when actual lap deltas stay near expectation, with pace/stint bonuses."""

    cal = calibration or get_active_calibration()
    if not lap_deltas:
        return 0.5
    deviations = [abs(delta - expected_delta) for delta in lap_deltas]
    average_offset = sum(deviations) / len(deviations)
    base_score = _clamp(1 - average_offset / cal.consistency_tolerance)

    pace_advantage = max(-expected_delta - cal.pace_min_advantage, 0.0)
    pace_boost = min(pace_advantage / cal.pace_advantage_scale, cal.pace_boost_cap)
    pace_factor = 1.0 + pace_boost

    avg_stint = _average_stint_length(len(lap_deltas), actual_pit_laps)
    if avg_stint > cal.stint_target_laps > 0:
        stint_boost = min((avg_stint - cal.stint_target_laps) / cal.stint_target_laps, cal.stint_boost_cap)
        stint_factor = 1.0 + stint_boost
    else:
        stint_factor = 1.0

    return _clamp(base_score * pace_factor * stint_factor)


def _average_stint_length(total_laps: int, pit_laps: Sequence[int]) -> float:
    if total_laps <= 0:
        return 0.0
    if not pit_laps:
        return float(total_laps)
    sorted_pits = sorted(int(lap) for lap in pit_laps if int(lap) > 0)
    stints: List[int] = []
    prev = 1
    for pit in sorted_pits:
        if pit <= prev:
            continue
        stints.append(max(pit - prev, 0))
        prev = pit
    if prev <= total_laps:
        stints.append(max(total_laps - prev + 1, 0))
    if not stints:
        return float(total_laps)
    return sum(stints) / len(stints)


def compute_strategy_score(plan: StrategyPlan, *, calibration: CalibrationProfile | None = None) -> float:
    """Reward pit timing that tracks the optimal plan while avoiding degradation."""

    cal = calibration or get_active_calibration()
    if not plan.optimal_pit_laps or not plan.actual_pit_laps:
        base_score = 0.5
    else:
        diffs = []
        default_opt = plan.optimal_pit_laps[-1]
        default_act = plan.actual_pit_laps[-1]
        for opt, act in zip_longest(plan.optimal_pit_laps, plan.actual_pit_laps):
            opt_val = default_opt if opt is None else opt
            act_val = default_act if act is None else act
            diffs.append(abs(opt_val - act_val))
        avg_diff = sum(diffs) / len(diffs)
        base_score = _clamp(1 - avg_diff / cal.strategy_lap_tolerance)
    degradation_hit = _clamp(plan.degradation_penalty)
    return _clamp(base_score - 0.5 * degradation_hit)


def compute_penalty_score(
    penalties: Sequence[PenaltyEvent],
    *,
    calibration: CalibrationProfile | None = None,
) -> float:
    """Map cumulative time loss onto the 0–1 penalty component."""

    cal = calibration or get_active_calibration()
    if not penalties:
        return 0.0
    total_loss = sum(max(event.time_loss, 0.0) for event in penalties)
    return _clamp(total_loss / cal.penalty_normalizer)


def load_weekend_file(path: str | Path) -> List[DriverRaceInput]:
    """Parse a JSON description of a race weekend into pipeline inputs."""

    raw = json.loads(Path(path).read_text())
    drivers = []
    for entry in raw.get("drivers", []):
        drivers.append(parse_driver_entry(entry))
    return drivers


def parse_driver_entry(entry: Dict) -> DriverRaceInput:
    car_pace = CarPaceIndex(
        driver=entry["driver"],
        team=entry["team"],
        base_delta=float(entry["car_pace"]["base_delta"]),
        track_adjustment=float(entry["car_pace"].get("track_adjustment", 0.0)),
    )
    form = DriverFormModifier(
        consistency=float(entry["form"]["consistency"]),
        error_rate=float(entry["form"]["error_rate"]),
        start_precision=float(entry["form"]["start_precision"]),
    )
    strategy_data = entry.get("strategy", {})
    strategy = StrategyPlan(
        optimal_pit_laps=[int(lap) for lap in strategy_data.get("optimal_pit_laps", [])],
        actual_pit_laps=[int(lap) for lap in strategy_data.get("actual_pit_laps", [])],
        degradation_penalty=float(strategy_data.get("degradation_penalty", 0.0)),
    )
    penalties = [
        PenaltyEvent(type=pen["type"], time_loss=float(pen["time_loss"]))
        for pen in entry.get("penalties", [])
    ]
    overtakes = [build_event(raw_event) for raw_event in entry.get("overtakes", [])]
    return DriverRaceInput(
        driver=entry["driver"],
        team=entry["team"],
        car_pace=car_pace,
        form=form,
        lap_deltas=[float(delta) for delta in entry.get("lap_deltas", [])],
        strategy=strategy,
        penalties=penalties,
        overtakes=overtakes,
    )


def build_event(raw_event: Dict) -> OvertakeEvent:
    context = raw_event.get("context", {})
    overtake_context = OvertakeContext(
        delta_cpi=float(context.get("delta_cpi", 0.0)),
        tire_delta=int(context.get("tire_delta", 0)),
        tire_compound_diff=int(context.get("tire_compound_diff", 0)),
        ers_delta=float(context.get("ers_delta", 0.0)),
        track_difficulty=float(context.get("track_difficulty", 0.5)),
        race_phase_pressure=float(context.get("race_phase_pressure", 0.5)),
    )
    return OvertakeEvent(
        context=overtake_context,
        success=bool(raw_event.get("success", True)),
        exposure_time=float(raw_event.get("exposure_time", 5.0)),
        penalized=bool(raw_event.get("penalized", False)),
        lap_number=int(raw_event["lap_number"]) if "lap_number" in raw_event and raw_event["lap_number"] not in (None, "") else None,
        opponent=raw_event.get("opponent_driver") or raw_event.get("opponent"),
        opponent_team=raw_event.get("opponent_team"),
        event_type=raw_event.get("event_type", "on_track"),
        event_source=raw_event.get("event_source", "unknown"),
    )


__all__ = [
    "DriveGradePipeline",
    "DriverRaceInput",
    "StrategyPlan",
    "PenaltyEvent",
    "compute_consistency_score",
    "compute_strategy_score",
    "compute_penalty_score",
    "load_weekend_file",
]
