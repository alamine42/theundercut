"""Hindsight Simulation Engine for 'what-if' strategy analysis."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .types import LapPositionSnapshot, PitStop


@dataclass
class SimulationResult:
    """Result of a strategy simulation."""
    scenario: str
    projected_position: int
    position_delta: int  # vs actual result
    time_delta_ms: int  # vs actual result
    confidence: float  # 0-1


@dataclass
class SimulationConfig:
    """Configuration for simulation."""
    pit_stop_loss_ms: int = 22000  # Average pit stop time loss
    tire_delta_per_lap_ms: int = 100  # Fresh vs old tire advantage
    traffic_penalty_per_car_ms: int = 500  # Time lost per car in traffic


class HindsightSimulator:
    """Simulates alternative strategy choices.

    Provides 'what-if' baselines by modeling what would have
    happened with different pit timing, compound choices, etc.
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
        lap_times: List[Dict],  # From lap_times table
        total_laps: int,
        config: Optional[SimulationConfig] = None,
    ):
        """Initialize simulator.

        Args:
            positions: Per-lap position data
            pit_stops: Actual pit stops
            lap_times: Lap time data
            total_laps: Total race laps
            config: Simulation configuration
        """
        self.positions = positions
        self.pit_stops = pit_stops
        self.lap_times = lap_times
        self.total_laps = total_laps
        self.config = config or SimulationConfig()

        # Index positions
        self._position_index: Dict[Tuple[str, int], LapPositionSnapshot] = {}
        for pos in positions:
            self._position_index[(pos.driver_code, pos.lap_number)] = pos

        # Index lap times
        self._lap_time_index: Dict[Tuple[str, int], int] = {}
        for lap in lap_times:
            driver = lap.get("driver")
            lap_num = lap.get("lap")
            lap_ms = lap.get("lap_ms")
            if driver and lap_num and lap_ms:
                self._lap_time_index[(driver, lap_num)] = lap_ms

        # Index pit stops by driver
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

    def simulate_alternate_pit_lap(
        self,
        driver_code: str,
        actual_pit_lap: int,
        alternate_pit_lap: int,
    ) -> Optional[SimulationResult]:
        """Simulate what would have happened with different pit timing.

        Args:
            driver_code: Driver to simulate
            actual_pit_lap: When they actually pitted
            alternate_pit_lap: When we're simulating they pit

        Returns:
            SimulationResult or None if insufficient data.
        """
        if alternate_pit_lap == actual_pit_lap:
            return None

        actual_pos = self._position_index.get((driver_code, self.total_laps))
        if not actual_pos:
            return None

        # Simple model: earlier pit = tire advantage, later pit = track position
        lap_delta = alternate_pit_lap - actual_pit_lap

        if lap_delta < 0:
            # Earlier pit - gain tire advantage, lose track position initially
            tire_advantage_laps = abs(lap_delta)
            time_gained = tire_advantage_laps * self.config.tire_delta_per_lap_ms

            # Estimate position impact
            # Each ~500ms is roughly a position
            position_change = time_gained // 500
        else:
            # Later pit - maintain track position longer, older tires at end
            tire_disadvantage_laps = lap_delta
            time_lost = tire_disadvantage_laps * self.config.tire_delta_per_lap_ms

            position_change = -(time_lost // 500)

        projected_position = max(1, actual_pos.position - position_change)

        return SimulationResult(
            scenario=f"Pit on lap {alternate_pit_lap} instead of {actual_pit_lap}",
            projected_position=projected_position,
            position_delta=actual_pos.position - projected_position,
            time_delta_ms=position_change * 500,
            confidence=0.6,  # Simple model has moderate confidence
        )

    def simulate_no_pit_stop(
        self,
        driver_code: str,
        pit_lap: int,
    ) -> Optional[SimulationResult]:
        """Simulate what if driver hadn't pitted.

        Useful for evaluating SC pit decisions.
        """
        actual_pos = self._position_index.get((driver_code, self.total_laps))
        if not actual_pos:
            return None

        laps_remaining = self.total_laps - pit_lap

        # No pit = save pit stop time but have older tires
        time_saved = self.config.pit_stop_loss_ms
        tire_penalty = laps_remaining * self.config.tire_delta_per_lap_ms * 2

        net_time = time_saved - tire_penalty
        position_change = net_time // 500

        projected_position = max(1, actual_pos.position - position_change)

        return SimulationResult(
            scenario=f"No pit stop at lap {pit_lap}",
            projected_position=projected_position,
            position_delta=actual_pos.position - projected_position,
            time_delta_ms=net_time,
            confidence=0.5,
        )

    def simulate_extra_pit_stop(
        self,
        driver_code: str,
        proposed_lap: int,
    ) -> Optional[SimulationResult]:
        """Simulate adding an extra pit stop."""
        actual_pos = self._position_index.get((driver_code, self.total_laps))
        if not actual_pos:
            return None

        laps_remaining = self.total_laps - proposed_lap

        # Extra pit = lose pit time but fresher tires
        time_lost = self.config.pit_stop_loss_ms
        tire_benefit = laps_remaining * self.config.tire_delta_per_lap_ms

        net_time = tire_benefit - time_lost
        position_change = net_time // 500

        projected_position = max(1, min(20, actual_pos.position - position_change))

        return SimulationResult(
            scenario=f"Additional pit stop at lap {proposed_lap}",
            projected_position=projected_position,
            position_delta=actual_pos.position - projected_position,
            time_delta_ms=net_time,
            confidence=0.5,
        )

    def get_optimal_pit_windows(
        self,
        driver_code: str,
        num_stops: int = 1,
    ) -> List[Tuple[int, int]]:
        """Calculate optimal pit windows based on tire degradation.

        Returns:
            List of (start_lap, end_lap) tuples for optimal pit windows.
        """
        # Simple heuristic: divide race evenly
        if num_stops == 0:
            return []

        stint_length = self.total_laps // (num_stops + 1)
        windows = []

        for i in range(1, num_stops + 1):
            optimal_lap = stint_length * i
            window_start = max(1, optimal_lap - 3)
            window_end = min(self.total_laps - 5, optimal_lap + 3)
            windows.append((window_start, window_end))

        return windows

    def evaluate_pit_timing(
        self,
        driver_code: str,
    ) -> Dict[str, any]:
        """Evaluate driver's pit timing vs optimal.

        Returns:
            Dict with timing evaluation.
        """
        driver_stops = self._driver_stops.get(driver_code, [])
        num_stops = len(driver_stops)

        optimal_windows = self.get_optimal_pit_windows(driver_code, num_stops)

        result = {
            "num_stops": num_stops,
            "stops_in_window": 0,
            "stops_early": 0,
            "stops_late": 0,
            "details": [],
        }

        for i, stop in enumerate(driver_stops):
            if i >= len(optimal_windows):
                break

            window_start, window_end = optimal_windows[i]

            if window_start <= stop.lap <= window_end:
                result["stops_in_window"] += 1
                result["details"].append({
                    "stop": i + 1,
                    "lap": stop.lap,
                    "status": "optimal",
                    "window": (window_start, window_end),
                })
            elif stop.lap < window_start:
                result["stops_early"] += 1
                result["details"].append({
                    "stop": i + 1,
                    "lap": stop.lap,
                    "status": "early",
                    "delta": window_start - stop.lap,
                })
            else:
                result["stops_late"] += 1
                result["details"].append({
                    "stop": i + 1,
                    "lap": stop.lap,
                    "status": "late",
                    "delta": stop.lap - window_end,
                })

        return result
