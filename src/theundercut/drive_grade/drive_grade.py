"""Core abstractions for the Formula One Drive Grade model."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Iterable, List


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Keep values within inclusive bounds."""

    return max(lower, min(upper, value))


@dataclass(slots=True)
class CarPaceIndex:
    """Represents expected lap delta versus the median car."""

    driver: str
    team: str
    base_delta: float  # negative = faster than median
    track_adjustment: float = 0.0

    @property
    def expected_delta(self) -> float:
        return self.base_delta + self.track_adjustment


@dataclass(slots=True)
class DriverFormModifier:
    """Encapsulates recent execution form for a driver."""

    consistency: float  # 0–1 score
    error_rate: float  # fraction of laps with notable mistakes
    start_precision: float  # 0–1, higher is better launches

    def adjustment(self) -> float:
        """Return modifier to CarPaceIndex in seconds."""

        consistency_bonus = (self.consistency - 0.5) * 0.2
        error_penalty = self.error_rate * 0.15
        start_bonus = (self.start_precision - 0.5) * 0.05
        return consistency_bonus + start_bonus - error_penalty


@dataclass(slots=True)
class OvertakeContext:
    """Contextual data associated with an overtake attempt."""

    delta_cpi: float  # attacker CPI minus defender CPI (negative = attacker faster)
    tire_delta: int  # attacker tire age advantage in laps (positive = fresher)
    tire_compound_diff: int  # -1 same, 0 harder vs softer indicator, 1 softer, etc.
    ers_delta: float  # attacker deploy minus defender deploy in percentage points
    track_difficulty: float  # 0 easy, 1 impossible
    race_phase_pressure: float  # 0–1 (1=last lap)


@dataclass(slots=True)
class OvertakeEvent:
    """Results of a single wheel-to-wheel interaction."""

    context: OvertakeContext
    success: bool
    exposure_time: float  # seconds spent side-by-side or defending
    penalized: bool = False
    lap_number: int | None = None
    opponent: str | None = None
    opponent_team: str | None = None
    event_type: str = "on_track"
    event_source: str = "unknown"

    def difficulty(self) -> float:
        ctx = self.context
        base = (
            -ctx.delta_cpi * 1.2
            + ctx.tire_delta * -0.05
            + ctx.tire_compound_diff * -0.15
            - ctx.ers_delta * 0.01
            + ctx.track_difficulty * 1.5
        )
        # High pressure makes things harder
        base += ctx.race_phase_pressure * 0.5
        return _clamp(1 / (1 + exp(-base)), 0.05, 0.95)

    def value(self) -> float:
        difficulty = self.difficulty()
        exposure_multiplier = 1 - exp(-self.exposure_time / 5)
        magnitude = difficulty * exposure_multiplier
        if self.penalized:
            magnitude *= 0.2
        return magnitude if self.success else -0.5 * magnitude


CONSISTENCY_WEIGHT = 0.55
RACECRAFT_WEIGHT = 0.45
PENALTY_WEIGHT = 0.10


@dataclass(slots=True)
class DriveGradeBreakdown:
    """Summary of the high-level scoring components."""

    consistency_score: float
    team_strategy_score: float
    racecraft_score: float
    penalty_score: float
    on_track_events: int
    pit_cycle_events: int
    total_grade: float = field(init=False)

    def __post_init__(self) -> None:
        self.total_grade = (
            CONSISTENCY_WEIGHT * self.consistency_score
            + RACECRAFT_WEIGHT * self.racecraft_score
            - PENALTY_WEIGHT * self.penalty_score
        )


class DriveGradeCalculator:
    """Helper responsible for deriving scores from intermediate metrics."""

    @staticmethod
    def normalize_component(value: float, mean: float = 0.5, std: float = 0.15) -> float:
        """Simple z-score based normalization onto 0–1 band."""

        if std <= 0:
            return _clamp(value)
        return _clamp(0.5 + (value - mean) / (4 * std))

    @staticmethod
    def racecraft_score(events: Iterable[OvertakeEvent]) -> float:
        total = sum(event.value() for event in events if event.event_type == "on_track")
        capped = _clamp(total)
        return capped

    def build_breakdown(
        self,
        consistency: float,
        strategy: float,
        penalties: float,
        events: Iterable[OvertakeEvent],
        on_track_events: int,
        pit_cycle_events: int,
    ) -> DriveGradeBreakdown:
        racecraft = self.racecraft_score(events)
        return DriveGradeBreakdown(
            consistency_score=self.normalize_component(consistency),
            team_strategy_score=self.normalize_component(strategy),
            racecraft_score=self.normalize_component(racecraft),
            penalty_score=self.normalize_component(penalties),
            on_track_events=on_track_events,
            pit_cycle_events=pit_cycle_events,
        )


__all__ = [
    "CarPaceIndex",
    "DriverFormModifier",
    "OvertakeContext",
    "OvertakeEvent",
    "DriveGradeBreakdown",
    "DriveGradeCalculator",
]
