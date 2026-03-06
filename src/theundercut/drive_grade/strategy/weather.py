"""Weather Response Scorer for evaluating weather-related strategy decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .types import (
    FactorScore,
    PitStop,
    WeatherCondition,
    StrategyDecisionRecord,
    StrategyDecisionType,
    StrategyFactor,
)


@dataclass
class WeatherConfig:
    """Configuration for weather scoring."""
    early_switch_bonus: float = 15.0  # First to switch correctly
    late_switch_penalty: float = 10.0  # Late to switch
    wrong_compound_penalty: float = 20.0  # Wrong compound choice
    gamble_success_bonus: float = 25.0  # Successful weather gamble
    gamble_fail_penalty: float = 15.0  # Failed weather gamble
    base_score: float = 50.0


# Compound categories
WET_COMPOUNDS = {"INTERMEDIATE", "WET"}
DRY_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}


class WeatherScorer:
    """Evaluates weather-related strategy decisions.

    Analyzes:
    - Timing of wet/dry transitions
    - Compound selection for conditions
    - Weather gambling decisions
    - Comparison to field timing
    """

    def __init__(
        self,
        pit_stops: List[PitStop],
        weather: List[WeatherCondition],
        config: Optional[WeatherConfig] = None,
    ):
        """Initialize scorer with race data.

        Args:
            pit_stops: All pit stops with compound info
            weather: Per-lap weather conditions
            config: Scoring configuration
        """
        self.pit_stops = pit_stops
        self.weather = weather
        self.config = config or WeatherConfig()

        # Index pit stops by driver
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

        # Sort stops
        for driver in self._driver_stops:
            self._driver_stops[driver].sort(key=lambda s: s.lap)

        # Index weather by lap
        self._lap_weather: Dict[int, WeatherCondition] = {
            w.lap_number: w for w in weather
        }

        # Detect weather transitions
        self.transitions = self._detect_transitions()

    def score_driver(
        self,
        driver_code: str,
        entry_id: int,
    ) -> FactorScore:
        """Calculate weather response score for a driver.

        Args:
            driver_code: Driver's code
            entry_id: Database entry ID

        Returns:
            FactorScore with score and decision records.
        """
        decisions: List[StrategyDecisionRecord] = []
        score = self.config.base_score

        # If no weather changes, return neutral score
        if not self.transitions:
            return FactorScore(
                factor=StrategyFactor.WEATHER,
                score=50.0,
                decisions=[],
                weight=0.0,  # No weight when no weather changes
            )

        driver_stops = self._driver_stops.get(driver_code, [])

        for transition in self.transitions:
            trans_decisions, delta = self._evaluate_transition(
                driver_code, entry_id, transition, driver_stops
            )
            decisions.extend(trans_decisions)
            score += delta

        # Clamp score
        score = max(0.0, min(100.0, score))

        return FactorScore(
            factor=StrategyFactor.WEATHER,
            score=score,
            decisions=decisions,
            weight=0.15,
        )

    def _detect_transitions(self) -> List[Dict]:
        """Detect weather transition points."""
        transitions = []

        if not self.weather:
            return transitions

        sorted_weather = sorted(self.weather, key=lambda w: w.lap_number)
        prev_status = None

        for w in sorted_weather:
            if prev_status and w.track_status != prev_status:
                transitions.append({
                    "lap": w.lap_number,
                    "from": prev_status,
                    "to": w.track_status,
                    "rain_intensity": w.rain_intensity,
                })
            prev_status = w.track_status

        return transitions

    def _evaluate_transition(
        self,
        driver_code: str,
        entry_id: int,
        transition: Dict,
        driver_stops: List[PitStop],
    ) -> tuple[List[StrategyDecisionRecord], float]:
        """Evaluate driver's response to a weather transition."""
        decisions = []
        score_delta = 0.0

        trans_lap = transition["lap"]
        from_status = transition["from"]
        to_status = transition["to"]

        # Determine required compound
        going_wet = to_status in ("damp", "wet")
        going_dry = to_status == "dry" and from_status in ("damp", "wet")

        # Find when driver switched compounds
        switch_lap = None
        correct_switch = False

        for stop in driver_stops:
            if stop.lap >= trans_lap - 2:  # Look for switches around transition
                compound_out = (stop.compound_out or "").upper()
                if going_wet and compound_out in WET_COMPOUNDS:
                    switch_lap = stop.lap
                    correct_switch = True
                    break
                elif going_dry and compound_out in DRY_COMPOUNDS:
                    switch_lap = stop.lap
                    correct_switch = True
                    break

        # Calculate field average switch lap
        field_switch_lap = self._get_field_switch_lap(trans_lap, going_wet)

        if switch_lap:
            reaction_time = switch_lap - trans_lap

            if correct_switch:
                if field_switch_lap and switch_lap < field_switch_lap:
                    # Switched before field average
                    bonus = self.config.early_switch_bonus
                    score_delta += bonus
                    decisions.append(StrategyDecisionRecord(
                        lap_number=switch_lap,
                        decision_type=StrategyDecisionType.WEATHER_SWITCH,
                        factor=StrategyFactor.WEATHER,
                        impact_score=bonus,
                        explanation=f"Early switch to {'wets' if going_wet else 'slicks'} at lap {switch_lap}",
                        comparison_context=f"Switched {field_switch_lap - switch_lap:.1f} laps before field average" if field_switch_lap else None,
                    ))
                elif field_switch_lap and switch_lap > field_switch_lap + 2:
                    # Switched late
                    penalty = self.config.late_switch_penalty
                    score_delta -= penalty
                    decisions.append(StrategyDecisionRecord(
                        lap_number=switch_lap,
                        decision_type=StrategyDecisionType.WEATHER_SWITCH,
                        factor=StrategyFactor.WEATHER,
                        impact_score=-penalty,
                        explanation=f"Late switch to {'wets' if going_wet else 'slicks'} at lap {switch_lap}",
                        comparison_context=f"Switched {switch_lap - field_switch_lap:.1f} laps after field average",
                    ))
                else:
                    # Switched with field
                    decisions.append(StrategyDecisionRecord(
                        lap_number=switch_lap,
                        decision_type=StrategyDecisionType.WEATHER_SWITCH,
                        factor=StrategyFactor.WEATHER,
                        impact_score=5.0,
                        explanation=f"Switched to {'wets' if going_wet else 'slicks'} with the field",
                    ))
                    score_delta += 5.0
        else:
            # Didn't switch - evaluate if this was a gamble
            gamble_paid_off = self._check_gamble_result(trans_lap, going_wet)

            if gamble_paid_off:
                bonus = self.config.gamble_success_bonus
                score_delta += bonus
                decisions.append(StrategyDecisionRecord(
                    lap_number=trans_lap,
                    decision_type=StrategyDecisionType.WEATHER_GAMBLE,
                    factor=StrategyFactor.WEATHER,
                    impact_score=bonus,
                    explanation="Stayed out during weather change - gamble paid off",
                    comparison_context="Track dried/weather improved",
                ))
            elif gamble_paid_off is False:
                penalty = self.config.gamble_fail_penalty
                score_delta -= penalty
                decisions.append(StrategyDecisionRecord(
                    lap_number=trans_lap,
                    decision_type=StrategyDecisionType.WEATHER_GAMBLE,
                    factor=StrategyFactor.WEATHER,
                    impact_score=-penalty,
                    explanation="Stayed out during weather change - lost time",
                    comparison_context="Wrong compound for conditions",
                ))

        return decisions, score_delta

    def _get_field_switch_lap(
        self,
        transition_lap: int,
        going_wet: bool,
    ) -> Optional[float]:
        """Calculate when the field switched compounds."""
        switch_laps = []

        for driver, stops in self._driver_stops.items():
            for stop in stops:
                if stop.lap < transition_lap - 2:
                    continue
                if stop.lap > transition_lap + 10:
                    break

                compound_out = (stop.compound_out or "").upper()
                if going_wet and compound_out in WET_COMPOUNDS:
                    switch_laps.append(stop.lap)
                    break
                elif not going_wet and compound_out in DRY_COMPOUNDS:
                    switch_laps.append(stop.lap)
                    break

        if switch_laps:
            return sum(switch_laps) / len(switch_laps)
        return None

    def _check_gamble_result(
        self,
        transition_lap: int,
        went_wet: bool,
    ) -> Optional[bool]:
        """Check if staying out on wrong compound was the right call.

        Returns:
            True if gamble paid off, False if it didn't, None if unclear.
        """
        # Look at weather a few laps later
        for offset in range(3, 8):
            later_weather = self._lap_weather.get(transition_lap + offset)
            if later_weather:
                if went_wet and later_weather.track_status == "dry":
                    # It dried up - staying out paid off
                    return True
                elif not went_wet and later_weather.track_status in ("damp", "wet"):
                    # It stayed wet - staying on slicks was bad
                    return False

        return None
