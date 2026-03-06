"""Pit Timing Scorer for evaluating pit stop timing decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .types import (
    FactorScore,
    PitStop,
    StrategyDecisionRecord,
    StrategyDecisionType,
    StrategyFactor,
    LapPositionSnapshot,
)
from .position_delta import PositionDeltaAnalyzer


@dataclass
class PitTimingConfig:
    """Configuration for pit timing scoring."""
    undercut_detection_laps: int = 3  # Laps before peer to count as undercut
    optimal_window_tolerance: int = 2  # Laps deviation allowed from optimal
    traffic_penalty_threshold: float = 3.0  # Seconds lost in traffic
    position_gain_bonus: float = 10.0  # Points per position gained
    position_loss_penalty: float = 8.0  # Points per position lost
    undercut_success_bonus: float = 15.0  # Bonus for successful undercut
    overcut_success_bonus: float = 12.0  # Bonus for successful overcut
    base_score: float = 50.0  # Starting score


class PitTimingScorer:
    """Evaluates pit stop timing decisions.

    Analyzes:
    - Undercut attempts and their success
    - Overcut strategies
    - Pit window optimization (tire degradation)
    - Traffic avoidance
    - Position changes around pit stops
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
        config: Optional[PitTimingConfig] = None,
    ):
        """Initialize scorer with race data.

        Args:
            positions: Per-lap position data for all drivers
            pit_stops: All pit stops in the race
            config: Scoring configuration
        """
        self.positions = positions
        self.pit_stops = pit_stops
        self.config = config or PitTimingConfig()

        # Create position analyzer
        self.position_analyzer = PositionDeltaAnalyzer(positions, pit_stops)

        # Index pit stops by driver
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

        # Sort stops by lap
        for driver in self._driver_stops:
            self._driver_stops[driver].sort(key=lambda s: s.lap)

    def score_driver(
        self,
        driver_code: str,
        entry_id: int,
    ) -> FactorScore:
        """Calculate pit timing score for a driver.

        Args:
            driver_code: Driver's code (e.g., "VER")
            entry_id: Database entry ID

        Returns:
            FactorScore with score and decision records.
        """
        decisions: List[StrategyDecisionRecord] = []
        score = self.config.base_score

        driver_stops = self._driver_stops.get(driver_code, [])

        if not driver_stops:
            # No pit stops - neutral score with no decisions
            return FactorScore(
                factor=StrategyFactor.PIT_TIMING,
                score=50.0,
                decisions=[],
                weight=0.35,
            )

        for stop in driver_stops:
            stop_decisions, stop_score_delta = self._evaluate_pit_stop(
                driver_code, entry_id, stop
            )
            decisions.extend(stop_decisions)
            score += stop_score_delta

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        return FactorScore(
            factor=StrategyFactor.PIT_TIMING,
            score=score,
            decisions=decisions,
            weight=0.35,
        )

    def _evaluate_pit_stop(
        self,
        driver_code: str,
        entry_id: int,
        stop: PitStop,
    ) -> tuple[List[StrategyDecisionRecord], float]:
        """Evaluate a single pit stop.

        Returns:
            Tuple of (decisions, score_delta).
        """
        decisions = []
        score_delta = 0.0

        # Analyze position change
        pos_change = self.position_analyzer.analyze_pit_stop_impact(
            driver_code, stop.lap
        )

        # Check for undercut
        undercut_victims = self.position_analyzer.detect_undercut_victim(
            driver_code, stop.lap
        )

        # Check for overcut
        overcut_victims = self.position_analyzer.detect_overcut_success(
            driver_code, stop.lap
        )

        # Compare to field average
        field_avg_lap = self.position_analyzer.get_field_average_pit_lap(
            exclude_drivers=[driver_code]
        )

        # Evaluate undercut
        if undercut_victims:
            bonus = self.config.undercut_success_bonus * len(undercut_victims)
            score_delta += bonus
            decisions.append(StrategyDecisionRecord(
                lap_number=stop.lap,
                decision_type=StrategyDecisionType.UNDERCUT_ATTEMPT,
                factor=StrategyFactor.PIT_TIMING,
                impact_score=bonus,
                position_delta=pos_change.delta,
                explanation=f"Successful undercut on {', '.join(undercut_victims)}",
                comparison_context=f"Pitted {field_avg_lap - stop.lap:.1f} laps before field average" if field_avg_lap else None,
            ))

        # Evaluate overcut
        elif overcut_victims:
            bonus = self.config.overcut_success_bonus * len(overcut_victims)
            score_delta += bonus
            decisions.append(StrategyDecisionRecord(
                lap_number=stop.lap,
                decision_type=StrategyDecisionType.OVERCUT_ATTEMPT,
                factor=StrategyFactor.PIT_TIMING,
                impact_score=bonus,
                position_delta=pos_change.delta,
                explanation=f"Successful overcut on {', '.join(overcut_victims)}",
                comparison_context=f"Pitted {stop.lap - field_avg_lap:.1f} laps after field average" if field_avg_lap else None,
            ))

        # Standard pit stop evaluation
        else:
            # Position delta impact
            if pos_change.delta > 0:
                bonus = self.config.position_gain_bonus * pos_change.delta
                score_delta += bonus
                decisions.append(StrategyDecisionRecord(
                    lap_number=stop.lap,
                    decision_type=StrategyDecisionType.PIT_STOP,
                    factor=StrategyFactor.PIT_TIMING,
                    impact_score=bonus,
                    position_delta=pos_change.delta,
                    explanation=f"Gained {pos_change.delta} position(s) through pit window",
                    comparison_context=self._get_timing_context(stop.lap, field_avg_lap),
                ))
            elif pos_change.delta < 0:
                penalty = self.config.position_loss_penalty * abs(pos_change.delta)
                score_delta -= penalty
                decisions.append(StrategyDecisionRecord(
                    lap_number=stop.lap,
                    decision_type=StrategyDecisionType.PIT_STOP,
                    factor=StrategyFactor.PIT_TIMING,
                    impact_score=-penalty,
                    position_delta=pos_change.delta,
                    explanation=f"Lost {abs(pos_change.delta)} position(s) through pit window",
                    comparison_context=self._get_timing_context(stop.lap, field_avg_lap),
                ))
            else:
                # Neutral pit stop
                decisions.append(StrategyDecisionRecord(
                    lap_number=stop.lap,
                    decision_type=StrategyDecisionType.PIT_STOP,
                    factor=StrategyFactor.PIT_TIMING,
                    impact_score=0.0,
                    position_delta=0,
                    explanation="Position maintained through pit stop",
                    comparison_context=self._get_timing_context(stop.lap, field_avg_lap),
                ))

        return decisions, score_delta

    def _get_timing_context(
        self,
        pit_lap: int,
        field_avg: Optional[float],
    ) -> Optional[str]:
        """Generate timing comparison context."""
        if field_avg is None:
            return None

        diff = pit_lap - field_avg
        if abs(diff) < 0.5:
            return "Pitted with the field average"
        elif diff < 0:
            return f"Pitted {abs(diff):.1f} laps before field average"
        else:
            return f"Pitted {diff:.1f} laps after field average"
