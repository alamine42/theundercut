"""Tire Selection Scorer for evaluating compound choice decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .types import (
    FactorScore,
    PitStop,
    StrategyDecisionRecord,
    StrategyDecisionType,
    StrategyFactor,
)


@dataclass
class TireSelectionConfig:
    """Configuration for tire selection scoring."""
    # Expected stint lengths per compound (laps)
    expected_stint_soft: int = 15
    expected_stint_medium: int = 25
    expected_stint_hard: int = 35

    # Scoring parameters
    stint_deviation_penalty: float = 2.0  # Points lost per lap under expected
    compound_mismatch_penalty: float = 10.0  # Penalty for wrong compound
    optimal_sequence_bonus: float = 10.0  # Bonus for optimal strategy
    base_score: float = 50.0


# Compound rankings (higher = harder)
COMPOUND_ORDER = {
    "SOFT": 1,
    "MEDIUM": 2,
    "HARD": 3,
    "INTERMEDIATE": 4,
    "WET": 5,
}


class TireSelectionScorer:
    """Evaluates tire compound selection decisions.

    Analyzes:
    - Compound suitability for track conditions
    - Stint length vs expected compound life
    - Strategy sequence optimization (e.g., M-H vs H-M)
    - Starting tire choice impact
    """

    def __init__(
        self,
        pit_stops: List[PitStop],
        stint_data: List[Dict],  # From stints table
        total_laps: int,
        config: Optional[TireSelectionConfig] = None,
    ):
        """Initialize scorer with race data.

        Args:
            pit_stops: All pit stops with compound info
            stint_data: Stint records with driver, compound, laps
            total_laps: Total race laps
            config: Scoring configuration
        """
        self.pit_stops = pit_stops
        self.stint_data = stint_data
        self.total_laps = total_laps
        self.config = config or TireSelectionConfig()

        # Index stints by driver
        self._driver_stints: Dict[str, List[Dict]] = {}
        for stint in stint_data:
            driver = stint.get("driver")
            if driver:
                if driver not in self._driver_stints:
                    self._driver_stints[driver] = []
                self._driver_stints[driver].append(stint)

        # Sort stints by stint number
        for driver in self._driver_stints:
            self._driver_stints[driver].sort(
                key=lambda s: s.get("stint_no", 0)
            )

        # Index pit stops by driver
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

    def score_driver(
        self,
        driver_code: str,
        entry_id: int,
    ) -> FactorScore:
        """Calculate tire selection score for a driver.

        Args:
            driver_code: Driver's code (e.g., "VER")
            entry_id: Database entry ID

        Returns:
            FactorScore with score and decision records.
        """
        decisions: List[StrategyDecisionRecord] = []
        score = self.config.base_score

        driver_stints = self._driver_stints.get(driver_code, [])

        if not driver_stints:
            return FactorScore(
                factor=StrategyFactor.TIRE_SELECTION,
                score=50.0,
                decisions=[],
                weight=0.30,
            )

        # Evaluate each stint
        for i, stint in enumerate(driver_stints):
            stint_decisions, stint_delta = self._evaluate_stint(
                driver_code, entry_id, stint, i, len(driver_stints)
            )
            decisions.extend(stint_decisions)
            score += stint_delta

        # Evaluate overall strategy sequence
        seq_decisions, seq_delta = self._evaluate_strategy_sequence(
            driver_code, entry_id, driver_stints
        )
        decisions.extend(seq_decisions)
        score += seq_delta

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        return FactorScore(
            factor=StrategyFactor.TIRE_SELECTION,
            score=score,
            decisions=decisions,
            weight=0.30,
        )

    def _evaluate_stint(
        self,
        driver_code: str,
        entry_id: int,
        stint: Dict,
        stint_index: int,
        total_stints: int,
    ) -> tuple[List[StrategyDecisionRecord], float]:
        """Evaluate a single stint's compound choice."""
        decisions = []
        score_delta = 0.0

        compound = stint.get("compound", "").upper()
        laps = stint.get("laps", 0)
        stint_no = stint.get("stint_no", stint_index + 1)

        expected_laps = self._get_expected_stint_length(compound)

        # First stint (starting tire) evaluation
        if stint_index == 0:
            decision, delta = self._evaluate_starting_tire(
                driver_code, compound, total_stints
            )
            if decision:
                decisions.append(decision)
                score_delta += delta

        # Stint length evaluation
        if expected_laps and laps > 0:
            deviation = expected_laps - laps

            if deviation > 5:
                # Pitted too early - didn't maximize tire life
                penalty = min(deviation * self.config.stint_deviation_penalty, 15.0)
                score_delta -= penalty
                decisions.append(StrategyDecisionRecord(
                    lap_number=stint_no,  # Approximate
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=-penalty,
                    explanation=f"Stint {stint_no} on {compound}: {laps} laps vs {expected_laps} expected",
                    comparison_context=f"Underutilized {compound} compound by {deviation} laps",
                ))
            elif laps > expected_laps + 5:
                # Pushed tires too long - potential degradation
                over_laps = laps - expected_laps
                penalty = min(over_laps * 1.5, 10.0)
                score_delta -= penalty
                decisions.append(StrategyDecisionRecord(
                    lap_number=stint_no,
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=-penalty,
                    explanation=f"Stint {stint_no} on {compound}: pushed {over_laps} laps beyond expected life",
                    comparison_context=f"Risk of degradation on {compound}",
                ))
            else:
                # Good stint length
                bonus = 5.0
                score_delta += bonus
                decisions.append(StrategyDecisionRecord(
                    lap_number=stint_no,
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=bonus,
                    explanation=f"Optimal stint length on {compound}",
                ))

        return decisions, score_delta

    def _evaluate_starting_tire(
        self,
        driver_code: str,
        compound: str,
        total_stints: int,
    ) -> tuple[Optional[StrategyDecisionRecord], float]:
        """Evaluate starting tire choice."""
        # For a 2-stop race, starting on MEDIUM is often optimal
        # For a 1-stop race, SOFT start can work

        if total_stints == 2:
            # One-stop race
            if compound == "MEDIUM":
                return StrategyDecisionRecord(
                    lap_number=1,
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=5.0,
                    explanation="Strong starting compound for one-stop strategy",
                ), 5.0
            elif compound == "SOFT":
                return StrategyDecisionRecord(
                    lap_number=1,
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=0.0,
                    explanation="SOFT start acceptable, requires good tire management",
                ), 0.0

        elif total_stints >= 3:
            # Two-stop race
            if compound == "SOFT":
                return StrategyDecisionRecord(
                    lap_number=1,
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=5.0,
                    explanation="Good starting compound for two-stop strategy",
                ), 5.0

        return None, 0.0

    def _evaluate_strategy_sequence(
        self,
        driver_code: str,
        entry_id: int,
        stints: List[Dict],
    ) -> tuple[List[StrategyDecisionRecord], float]:
        """Evaluate overall compound sequence."""
        decisions = []
        score_delta = 0.0

        if len(stints) < 2:
            return decisions, score_delta

        compounds = [s.get("compound", "").upper() for s in stints]
        compounds_used: Set[str] = set(compounds)

        # Check compound variety (using all available compounds is often good)
        dry_compounds = {"SOFT", "MEDIUM", "HARD"}
        used_dry = compounds_used & dry_compounds

        if len(used_dry) >= 2:
            bonus = 5.0
            score_delta += bonus
            decisions.append(StrategyDecisionRecord(
                lap_number=1,
                decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                factor=StrategyFactor.TIRE_SELECTION,
                impact_score=bonus,
                explanation=f"Good compound variety: {', '.join(sorted(used_dry))}",
            ))

        # Check for suboptimal sequences
        # Going HARD -> SOFT at end of race is often bad
        if len(compounds) >= 2:
            last_two = compounds[-2:]
            if last_two == ["HARD", "SOFT"]:
                penalty = 8.0
                score_delta -= penalty
                decisions.append(StrategyDecisionRecord(
                    lap_number=len(stints),
                    decision_type=StrategyDecisionType.COMPOUND_CHOICE,
                    factor=StrategyFactor.TIRE_SELECTION,
                    impact_score=-penalty,
                    explanation="HARD to SOFT transition at end: may lose pace late",
                    comparison_context="Consider SOFT to HARD sequence instead",
                ))

        return decisions, score_delta

    def _get_expected_stint_length(self, compound: str) -> Optional[int]:
        """Get expected stint length for a compound."""
        compound = compound.upper()
        if compound == "SOFT":
            return self.config.expected_stint_soft
        elif compound == "MEDIUM":
            return self.config.expected_stint_medium
        elif compound == "HARD":
            return self.config.expected_stint_hard
        return None
