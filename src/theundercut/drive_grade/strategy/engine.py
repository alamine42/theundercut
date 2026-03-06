"""Strategy Score Engine - Main orchestrator for strategy evaluation."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .types import (
    FactorScore,
    LapPositionSnapshot,
    PitStop,
    RaceControlPeriod,
    StrategyFactor,
    StrategyScoreResult,
    WeatherCondition,
)
from .position_delta import PositionDeltaAnalyzer
from .pit_timing import PitTimingScorer, PitTimingConfig
from .tire_selection import TireSelectionScorer, TireSelectionConfig
from .safety_car import SafetyCarScorer, SafetyCarConfig
from .weather import WeatherScorer, WeatherConfig
from .peer_comparison import PeerComparison, PeerComparisonConfig
from .hindsight_simulation import HindsightSimulator, SimulationConfig


@dataclass
class StrategyEngineConfig:
    """Master configuration for strategy scoring."""
    # Factor weights
    pit_timing_weight: float = 0.35
    tire_selection_weight: float = 0.30
    safety_car_weight: float = 0.20
    weather_weight: float = 0.15

    # Sub-configs
    pit_timing: PitTimingConfig = None
    tire_selection: TireSelectionConfig = None
    safety_car: SafetyCarConfig = None
    weather: WeatherConfig = None
    peer_comparison: PeerComparisonConfig = None
    simulation: SimulationConfig = None

    calibration_profile: str = "baseline"
    calibration_version: str = "v1.0"

    def __post_init__(self):
        self.pit_timing = self.pit_timing or PitTimingConfig()
        self.tire_selection = self.tire_selection or TireSelectionConfig()
        self.safety_car = self.safety_car or SafetyCarConfig()
        self.weather = self.weather or WeatherConfig()
        self.peer_comparison = self.peer_comparison or PeerComparisonConfig()
        self.simulation = self.simulation or SimulationConfig()


class StrategyScoreEngine:
    """Main orchestrator for strategy score calculation.

    Coordinates all factor scorers, supporting engines, and
    produces final strategy scores with decision logs.
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
        stint_data: List[Dict],
        race_control: List[RaceControlPeriod],
        weather: List[WeatherCondition],
        lap_times: List[Dict],
        total_laps: int,
        config: Optional[StrategyEngineConfig] = None,
    ):
        """Initialize engine with all race data.

        Args:
            positions: Per-lap position snapshots
            pit_stops: All pit stops
            stint_data: Stint records
            race_control: SC/VSC/Red Flag periods
            weather: Per-lap weather conditions
            lap_times: Lap time records
            total_laps: Total race laps
            config: Engine configuration
        """
        self.positions = positions
        self.pit_stops = pit_stops
        self.stint_data = stint_data
        self.race_control = race_control
        self.weather = weather
        self.lap_times = lap_times
        self.total_laps = total_laps
        self.config = config or StrategyEngineConfig()

        # Initialize factor scorers
        self.pit_timing_scorer = PitTimingScorer(
            positions=positions,
            pit_stops=pit_stops,
            config=self.config.pit_timing,
        )

        self.tire_selection_scorer = TireSelectionScorer(
            pit_stops=pit_stops,
            stint_data=stint_data,
            total_laps=total_laps,
            config=self.config.tire_selection,
        )

        self.safety_car_scorer = SafetyCarScorer(
            positions=positions,
            pit_stops=pit_stops,
            race_control=race_control,
            config=self.config.safety_car,
        )

        self.weather_scorer = WeatherScorer(
            pit_stops=pit_stops,
            weather=weather,
            config=self.config.weather,
        )

        # Supporting engines - initialized lazily when needed
        # These are available for future enhancements but not currently
        # used in the basic scoring flow to avoid unnecessary computation
        self._position_analyzer = None
        self._peer_comparison = None
        self._simulator = None

        # Store data references for lazy initialization
        self._positions = positions
        self._pit_stops = pit_stops
        self._stint_data = stint_data
        self._lap_times = lap_times

        # Get all drivers
        self._drivers = self._extract_drivers()

    def _extract_drivers(self) -> Dict[str, int]:
        """Extract unique drivers with their entry IDs."""
        drivers = {}
        for pos in self.positions:
            if pos.driver_code not in drivers:
                drivers[pos.driver_code] = pos.entry_id
        return drivers

    @property
    def position_analyzer(self) -> PositionDeltaAnalyzer:
        """Lazy-initialized position delta analyzer."""
        if self._position_analyzer is None:
            self._position_analyzer = PositionDeltaAnalyzer(
                positions=self._positions,
                pit_stops=self._pit_stops,
            )
        return self._position_analyzer

    @property
    def peer_comparison(self) -> PeerComparison:
        """Lazy-initialized peer comparison engine."""
        if self._peer_comparison is None:
            self._peer_comparison = PeerComparison(
                positions=self._positions,
                pit_stops=self._pit_stops,
                stint_data=self._stint_data,
                config=self.config.peer_comparison,
            )
        return self._peer_comparison

    @property
    def simulator(self) -> HindsightSimulator:
        """Lazy-initialized hindsight simulator."""
        if self._simulator is None:
            self._simulator = HindsightSimulator(
                positions=self._positions,
                pit_stops=self._pit_stops,
                lap_times=self._lap_times,
                total_laps=self.total_laps,
                config=self.config.simulation,
            )
        return self._simulator

    def score_driver(
        self,
        driver_code: str,
        entry_id: int,
    ) -> StrategyScoreResult:
        """Calculate complete strategy score for a driver.

        Args:
            driver_code: Driver's code (e.g., "VER")
            entry_id: Database entry ID

        Returns:
            StrategyScoreResult with all component scores and decisions.
        """
        # Get individual factor scores
        pit_timing = self.pit_timing_scorer.score_driver(driver_code, entry_id)
        tire_selection = self.tire_selection_scorer.score_driver(driver_code, entry_id)
        safety_car = self.safety_car_scorer.score_driver(driver_code, entry_id)
        weather = self.weather_scorer.score_driver(driver_code, entry_id)

        # Apply configured weights
        pit_timing.weight = self.config.pit_timing_weight
        tire_selection.weight = self.config.tire_selection_weight

        # Adjust SC/weather weights based on whether events occurred
        has_sc = len([p for p in self.race_control if p.event_type in ("safety_car", "vsc")]) > 0
        has_weather = len(self._detect_weather_changes()) > 0

        if has_sc:
            safety_car.weight = self.config.safety_car_weight
        else:
            safety_car.weight = 0.0

        if has_weather:
            weather.weight = self.config.weather_weight
        else:
            weather.weight = 0.0

        # Renormalize weights if SC/weather didn't occur
        self._renormalize_weights(pit_timing, tire_selection, safety_car, weather)

        # Build final result
        return StrategyScoreResult.from_factor_scores(
            driver_code=driver_code,
            entry_id=entry_id,
            pit_timing=pit_timing,
            tire_selection=tire_selection,
            safety_car=safety_car,
            weather=weather,
            calibration_profile=self.config.calibration_profile,
            calibration_version=self.config.calibration_version,
        )

    def score_all_drivers(self) -> List[StrategyScoreResult]:
        """Calculate strategy scores for all drivers in the race.

        Returns:
            List of StrategyScoreResult for each driver.
        """
        results = []
        for driver_code, entry_id in self._drivers.items():
            result = self.score_driver(driver_code, entry_id)
            results.append(result)

        # Sort by total score descending
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results

    def _renormalize_weights(
        self,
        pit_timing: FactorScore,
        tire_selection: FactorScore,
        safety_car: FactorScore,
        weather: FactorScore,
    ) -> None:
        """Renormalize weights when some factors have zero weight."""
        total = (
            pit_timing.weight +
            tire_selection.weight +
            safety_car.weight +
            weather.weight
        )

        if total <= 0:
            # Shouldn't happen, but set defaults
            pit_timing.weight = 0.55
            tire_selection.weight = 0.45
            return

        if total != 1.0:
            # Scale remaining weights to sum to 1.0
            scale = 1.0 / total
            pit_timing.weight *= scale
            tire_selection.weight *= scale
            safety_car.weight *= scale
            weather.weight *= scale

    def _detect_weather_changes(self) -> List[Dict]:
        """Detect weather transitions in the race."""
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
                })
            prev_status = w.track_status

        return transitions

    def get_race_summary(self) -> Dict:
        """Get summary of race conditions for context."""
        return {
            "total_laps": self.total_laps,
            "driver_count": len(self._drivers),
            "pit_stop_count": len(self.pit_stops),
            "sc_periods": len([
                p for p in self.race_control
                if p.event_type == "safety_car"
            ]),
            "vsc_periods": len([
                p for p in self.race_control
                if p.event_type == "vsc"
            ]),
            "weather_changes": len(self._detect_weather_changes()),
            "has_rain": any(
                w.track_status in ("damp", "wet")
                for w in self.weather
            ),
        }
