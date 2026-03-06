"""Core types for strategy scoring."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class StrategyDecisionType(str, Enum):
    """Types of strategic decisions."""
    PIT_STOP = "pit_stop"
    STAY_OUT = "stay_out"
    UNDERCUT_ATTEMPT = "undercut_attempt"
    OVERCUT_ATTEMPT = "overcut_attempt"
    COMPOUND_CHOICE = "compound_choice"
    TIRE_CHANGE = "tire_change"
    SC_PIT = "sc_pit"
    SC_STAY_OUT = "sc_stay_out"
    WEATHER_SWITCH = "weather_switch"
    WEATHER_GAMBLE = "weather_gamble"


class StrategyFactor(str, Enum):
    """Strategy scoring factors."""
    PIT_TIMING = "pit_timing"
    TIRE_SELECTION = "tire_selection"
    SAFETY_CAR = "safety_car"
    WEATHER = "weather"


@dataclass
class StrategyDecisionRecord:
    """Record of a single strategic decision with impact assessment."""
    lap_number: int
    decision_type: StrategyDecisionType
    factor: StrategyFactor
    impact_score: float  # Positive = good, negative = bad
    explanation: str
    position_delta: Optional[int] = None
    time_delta_ms: Optional[int] = None
    comparison_context: Optional[str] = None


@dataclass
class FactorScore:
    """Score for a single strategy factor."""
    factor: StrategyFactor
    score: float  # 0-100
    decisions: List[StrategyDecisionRecord] = field(default_factory=list)
    weight: float = 0.25  # Default equal weight


@dataclass
class StrategyScoreResult:
    """Complete strategy score result for a driver."""
    driver_code: str
    entry_id: int
    total_score: float  # 0-100
    pit_timing_score: float
    tire_selection_score: float
    safety_car_score: float
    weather_score: float
    decisions: List[StrategyDecisionRecord] = field(default_factory=list)
    calibration_profile: str = "baseline"
    calibration_version: str = "v1.0"

    @classmethod
    def from_factor_scores(
        cls,
        driver_code: str,
        entry_id: int,
        pit_timing: FactorScore,
        tire_selection: FactorScore,
        safety_car: FactorScore,
        weather: FactorScore,
        calibration_profile: str = "baseline",
        calibration_version: str = "v1.0",
    ) -> "StrategyScoreResult":
        """Create result from individual factor scores with weighted average."""
        # Normalize weights
        total_weight = (
            pit_timing.weight + tire_selection.weight +
            safety_car.weight + weather.weight
        )

        if total_weight == 0:
            total_score = 50.0
        else:
            total_score = (
                pit_timing.score * pit_timing.weight +
                tire_selection.score * tire_selection.weight +
                safety_car.score * safety_car.weight +
                weather.score * weather.weight
            ) / total_weight

        # Combine all decisions
        all_decisions = (
            pit_timing.decisions +
            tire_selection.decisions +
            safety_car.decisions +
            weather.decisions
        )
        all_decisions.sort(key=lambda d: d.lap_number)

        return cls(
            driver_code=driver_code,
            entry_id=entry_id,
            total_score=total_score,
            pit_timing_score=pit_timing.score,
            tire_selection_score=tire_selection.score,
            safety_car_score=safety_car.score,
            weather_score=weather.score,
            decisions=all_decisions,
            calibration_profile=calibration_profile,
            calibration_version=calibration_version,
        )


@dataclass
class PitStop:
    """Represents a pit stop event."""
    lap: int
    driver_code: str
    entry_id: int
    compound_in: Optional[str] = None  # Tire coming off
    compound_out: Optional[str] = None  # Tire going on
    pit_duration_ms: Optional[int] = None
    position_before: Optional[int] = None
    position_after: Optional[int] = None


@dataclass
class RaceControlPeriod:
    """Represents a SC/VSC/Red Flag period."""
    event_type: str  # safety_car, vsc, red_flag
    start_lap: int
    end_lap: Optional[int]
    cause: Optional[str] = None


@dataclass
class WeatherCondition:
    """Weather condition for a lap."""
    lap_number: int
    track_status: str  # dry, damp, wet
    air_temp_c: Optional[float] = None
    track_temp_c: Optional[float] = None
    rain_intensity: Optional[str] = None  # none, light, moderate, heavy


@dataclass
class LapPositionSnapshot:
    """Position snapshot for a lap."""
    lap_number: int
    driver_code: str
    entry_id: int
    position: int
    gap_to_leader_ms: Optional[int] = None
    gap_to_ahead_ms: Optional[int] = None
