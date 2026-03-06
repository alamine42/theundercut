"""Safety Car Response Scorer for evaluating SC/VSC strategy decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .types import (
    FactorScore,
    PitStop,
    RaceControlPeriod,
    StrategyDecisionRecord,
    StrategyDecisionType,
    StrategyFactor,
    LapPositionSnapshot,
)
from .position_delta import PositionDeltaAnalyzer


@dataclass
class SafetyCarConfig:
    """Configuration for safety car scoring."""
    sc_pit_bonus: float = 15.0  # Bonus for pitting under SC
    sc_pit_position_gain: float = 8.0  # Per position gained
    sc_miss_penalty: float = 10.0  # Penalty for missing SC opportunity
    vsc_pit_bonus: float = 10.0  # VSC pit bonus (smaller window)
    reaction_bonus_threshold: int = 2  # Laps to react for bonus
    queue_penalty_laps: int = 5  # Laps stuck in queue
    base_score: float = 50.0


class SafetyCarScorer:
    """Evaluates Safety Car and VSC response decisions.

    Analyzes:
    - Opportunistic pitting during SC/VSC windows
    - Reaction time to SC deployment
    - Position changes from SC strategy
    - Stay-out vs pit decisions
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
        race_control: List[RaceControlPeriod],
        config: Optional[SafetyCarConfig] = None,
    ):
        """Initialize scorer with race data.

        Args:
            positions: Per-lap position data
            pit_stops: All pit stops
            race_control: SC/VSC/Red Flag periods
            config: Scoring configuration
        """
        self.positions = positions
        self.pit_stops = pit_stops
        self.race_control = race_control
        self.config = config or SafetyCarConfig()

        self.position_analyzer = PositionDeltaAnalyzer(positions, pit_stops)

        # Index pit stops by driver
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

        # Filter for SC and VSC periods
        self.sc_periods = [
            p for p in race_control
            if p.event_type in ("safety_car", "vsc")
        ]

    def score_driver(
        self,
        driver_code: str,
        entry_id: int,
    ) -> FactorScore:
        """Calculate safety car response score for a driver.

        Args:
            driver_code: Driver's code
            entry_id: Database entry ID

        Returns:
            FactorScore with score and decision records.
        """
        decisions: List[StrategyDecisionRecord] = []
        score = self.config.base_score

        # If no SC periods, return neutral score
        if not self.sc_periods:
            return FactorScore(
                factor=StrategyFactor.SAFETY_CAR,
                score=50.0,
                decisions=[],
                weight=0.0,  # No weight when no SC
            )

        driver_stops = self._driver_stops.get(driver_code, [])

        for period in self.sc_periods:
            period_decisions, delta = self._evaluate_sc_period(
                driver_code, entry_id, period, driver_stops
            )
            decisions.extend(period_decisions)
            score += delta

        # Clamp score
        score = max(0.0, min(100.0, score))

        return FactorScore(
            factor=StrategyFactor.SAFETY_CAR,
            score=score,
            decisions=decisions,
            weight=0.20,
        )

    def _evaluate_sc_period(
        self,
        driver_code: str,
        entry_id: int,
        period: RaceControlPeriod,
        driver_stops: List[PitStop],
    ) -> tuple[List[StrategyDecisionRecord], float]:
        """Evaluate driver's response to a SC/VSC period."""
        decisions = []
        score_delta = 0.0

        is_vsc = period.event_type == "vsc"
        sc_start = period.start_lap
        sc_end = period.end_lap or sc_start + 3

        # Check if driver pitted during SC
        pitted_during_sc = False
        pit_lap = None
        for stop in driver_stops:
            if sc_start <= stop.lap <= sc_end:
                pitted_during_sc = True
                pit_lap = stop.lap
                break

        # Position before and after SC
        pos_before = self.position_analyzer.get_position(driver_code, sc_start - 1)
        pos_after = self.position_analyzer.get_position(driver_code, sc_end + 1)

        if pos_before and pos_after:
            pos_delta = pos_before - pos_after

            if pitted_during_sc:
                # Evaluate the pit decision
                bonus = self.config.vsc_pit_bonus if is_vsc else self.config.sc_pit_bonus

                # Add position gain bonus
                if pos_delta > 0:
                    bonus += self.config.sc_pit_position_gain * pos_delta

                score_delta += bonus

                reaction_laps = pit_lap - sc_start if pit_lap else 0
                reaction_context = None
                if reaction_laps <= self.config.reaction_bonus_threshold:
                    reaction_context = f"Quick reaction - pitted on lap {pit_lap}"
                    score_delta += 5.0
                else:
                    reaction_context = f"Pitted on lap {pit_lap}, {reaction_laps} laps into SC"

                decisions.append(StrategyDecisionRecord(
                    lap_number=pit_lap or sc_start,
                    decision_type=StrategyDecisionType.SC_PIT,
                    factor=StrategyFactor.SAFETY_CAR,
                    impact_score=bonus,
                    position_delta=pos_delta,
                    explanation=f"Pitted during {'VSC' if is_vsc else 'SC'} for 'free' stop",
                    comparison_context=reaction_context,
                ))

            else:
                # Stayed out - evaluate if this was the right call
                if pos_delta > 0:
                    # Gained positions by staying out
                    bonus = 8.0
                    score_delta += bonus
                    decisions.append(StrategyDecisionRecord(
                        lap_number=sc_start,
                        decision_type=StrategyDecisionType.SC_STAY_OUT,
                        factor=StrategyFactor.SAFETY_CAR,
                        impact_score=bonus,
                        position_delta=pos_delta,
                        explanation=f"Stayed out during {'VSC' if is_vsc else 'SC'}, gained track position",
                        comparison_context=f"Others pitted, jumped {pos_delta} position(s)",
                    ))
                elif pos_delta < 0:
                    # Lost positions - missed opportunity
                    penalty = self.config.sc_miss_penalty
                    score_delta -= penalty
                    decisions.append(StrategyDecisionRecord(
                        lap_number=sc_start,
                        decision_type=StrategyDecisionType.SC_STAY_OUT,
                        factor=StrategyFactor.SAFETY_CAR,
                        impact_score=-penalty,
                        position_delta=pos_delta,
                        explanation=f"Stayed out during {'VSC' if is_vsc else 'SC'}, lost positions",
                        comparison_context=f"Missed 'free' pit stop opportunity",
                    ))
                else:
                    # Neutral - no change
                    decisions.append(StrategyDecisionRecord(
                        lap_number=sc_start,
                        decision_type=StrategyDecisionType.SC_STAY_OUT,
                        factor=StrategyFactor.SAFETY_CAR,
                        impact_score=0.0,
                        position_delta=0,
                        explanation=f"Stayed out during {'VSC' if is_vsc else 'SC'}, maintained position",
                    ))

        return decisions, score_delta

    def _count_field_pits_during_sc(
        self,
        period: RaceControlPeriod,
    ) -> int:
        """Count how many drivers pitted during SC."""
        count = 0
        sc_start = period.start_lap
        sc_end = period.end_lap or sc_start + 3

        for stop in self.pit_stops:
            if sc_start <= stop.lap <= sc_end:
                count += 1

        return count
