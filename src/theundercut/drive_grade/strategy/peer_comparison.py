"""Peer Comparison logic for relative strategy evaluation."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .types import LapPositionSnapshot, PitStop


@dataclass
class PeerGroup:
    """Group of drivers with similar pace."""
    drivers: Set[str]
    avg_lap_time_ms: float
    pace_delta_threshold: float = 500.0  # ms


@dataclass
class PeerComparisonConfig:
    """Configuration for peer comparison."""
    pace_delta_threshold: float = 500.0  # ms - drivers within this are peers
    min_peer_group_size: int = 3
    percentile_bins: int = 4  # Quartiles


class PeerComparison:
    """Provides relative context for strategy scoring.

    Groups cars by similar pace and compares strategic choices
    to peers rather than the entire field.
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
        stint_data: List[Dict],
        config: Optional[PeerComparisonConfig] = None,
    ):
        """Initialize with race data.

        Args:
            positions: Per-lap position data
            pit_stops: All pit stops
            stint_data: Stint records with avg pace
            config: Configuration
        """
        self.positions = positions
        self.pit_stops = pit_stops
        self.stint_data = stint_data
        self.config = config or PeerComparisonConfig()

        # Calculate average pace per driver
        self._driver_pace: Dict[str, float] = {}
        for stint in stint_data:
            driver = stint.get("driver")
            avg_pace = stint.get("avg_lap_ms")
            if driver and avg_pace:
                if driver not in self._driver_pace:
                    self._driver_pace[driver] = []
                self._driver_pace[driver].append(avg_pace)

        # Convert to averages
        for driver, paces in list(self._driver_pace.items()):
            if isinstance(paces, list):
                self._driver_pace[driver] = sum(paces) / len(paces)

        # Build peer groups
        self.peer_groups = self._build_peer_groups()

        # Index pit stops
        self._driver_stops: Dict[str, List[PitStop]] = {}
        for stop in pit_stops:
            if stop.driver_code not in self._driver_stops:
                self._driver_stops[stop.driver_code] = []
            self._driver_stops[stop.driver_code].append(stop)

    def _build_peer_groups(self) -> List[PeerGroup]:
        """Build peer groups based on similar pace."""
        if not self._driver_pace:
            return []

        # Sort drivers by pace
        sorted_drivers = sorted(
            self._driver_pace.items(),
            key=lambda x: x[1]
        )

        groups = []
        current_group: Set[str] = set()
        current_pace = None

        for driver, pace in sorted_drivers:
            if current_pace is None:
                current_pace = pace
                current_group.add(driver)
            elif abs(pace - current_pace) <= self.config.pace_delta_threshold:
                current_group.add(driver)
            else:
                if len(current_group) >= self.config.min_peer_group_size:
                    avg_pace = sum(
                        self._driver_pace[d] for d in current_group
                    ) / len(current_group)
                    groups.append(PeerGroup(
                        drivers=current_group.copy(),
                        avg_lap_time_ms=avg_pace,
                    ))
                current_group = {driver}
                current_pace = pace

        # Don't forget the last group
        if len(current_group) >= self.config.min_peer_group_size:
            avg_pace = sum(
                self._driver_pace[d] for d in current_group
            ) / len(current_group)
            groups.append(PeerGroup(
                drivers=current_group,
                avg_lap_time_ms=avg_pace,
            ))

        return groups

    def get_peer_group(self, driver_code: str) -> Optional[PeerGroup]:
        """Get the peer group for a driver."""
        for group in self.peer_groups:
            if driver_code in group.drivers:
                return group
        return None

    def get_peer_average_pit_lap(
        self,
        driver_code: str,
        stop_number: int = 1,
    ) -> Optional[float]:
        """Get average pit lap for a driver's peers.

        Args:
            driver_code: Driver to find peers for
            stop_number: Which pit stop (1, 2, etc.)

        Returns:
            Average pit lap for peers, or None.
        """
        group = self.get_peer_group(driver_code)
        if not group:
            return None

        pit_laps = []
        for peer in group.drivers:
            if peer == driver_code:
                continue
            stops = self._driver_stops.get(peer, [])
            if len(stops) >= stop_number:
                pit_laps.append(stops[stop_number - 1].lap)

        if not pit_laps:
            return None

        return sum(pit_laps) / len(pit_laps)

    def get_percentile_rank(
        self,
        driver_code: str,
        metric: str,
        value: float,
    ) -> float:
        """Calculate percentile rank for a metric value.

        Args:
            driver_code: Driver to compare
            metric: Metric name (for logging)
            value: Value to rank

        Returns:
            Percentile (0-100) where higher is better.
        """
        group = self.get_peer_group(driver_code)
        if not group or len(group.drivers) < 2:
            return 50.0

        # Get all values for this metric from peers
        peer_values = []
        for peer in group.drivers:
            # This would need to be passed in or calculated
            # For now, return neutral
            pass

        return 50.0

    def compare_pit_timing_to_peers(
        self,
        driver_code: str,
    ) -> Dict[str, float]:
        """Compare driver's pit timing to their peers.

        Returns:
            Dict with comparison metrics.
        """
        result = {
            "peer_avg_stop1": None,
            "peer_avg_stop2": None,
            "driver_stop1": None,
            "driver_stop2": None,
            "delta_stop1": None,
            "delta_stop2": None,
        }

        driver_stops = self._driver_stops.get(driver_code, [])

        if driver_stops:
            result["driver_stop1"] = driver_stops[0].lap
            if len(driver_stops) > 1:
                result["driver_stop2"] = driver_stops[1].lap

        peer_avg1 = self.get_peer_average_pit_lap(driver_code, 1)
        if peer_avg1:
            result["peer_avg_stop1"] = peer_avg1
            if result["driver_stop1"]:
                result["delta_stop1"] = result["driver_stop1"] - peer_avg1

        peer_avg2 = self.get_peer_average_pit_lap(driver_code, 2)
        if peer_avg2:
            result["peer_avg_stop2"] = peer_avg2
            if result["driver_stop2"]:
                result["delta_stop2"] = result["driver_stop2"] - peer_avg2

        return result

    def get_compound_usage_comparison(
        self,
        driver_code: str,
    ) -> Dict[str, int]:
        """Compare compound usage to peers.

        Returns:
            Dict mapping compound to count of peers using it.
        """
        group = self.get_peer_group(driver_code)
        if not group:
            return {}

        compound_counts: Dict[str, int] = {}

        for peer in group.drivers:
            if peer == driver_code:
                continue

            for stint in self.stint_data:
                if stint.get("driver") == peer:
                    compound = stint.get("compound", "").upper()
                    if compound:
                        compound_counts[compound] = compound_counts.get(compound, 0) + 1

        return compound_counts
