"""Position Delta Analyzer for tracking position changes around strategic decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .types import LapPositionSnapshot, PitStop


@dataclass
class PositionChange:
    """Represents a position change event."""
    lap: int
    driver_code: str
    position_before: int
    position_after: int
    delta: int  # Positive = gained positions, negative = lost
    cause: str  # pit_stop, on_track, sc_restart, etc.


class PositionDeltaAnalyzer:
    """Analyzes position changes and attributes them to strategic decisions.

    Tracks position changes around pit stops, safety car periods, and
    other strategic moments to determine the impact of team decisions.
    """

    def __init__(
        self,
        positions: List[LapPositionSnapshot],
        pit_stops: List[PitStop],
    ):
        """Initialize with position and pit stop data.

        Args:
            positions: Per-lap position snapshots for all drivers
            pit_stops: List of pit stop events
        """
        self.positions = positions
        self.pit_stops = pit_stops

        # Index positions by (driver, lap)
        self._position_index: Dict[Tuple[str, int], LapPositionSnapshot] = {}
        for pos in positions:
            self._position_index[(pos.driver_code, pos.lap_number)] = pos

        # Index positions by lap for field comparison
        self._lap_positions: Dict[int, List[LapPositionSnapshot]] = {}
        for pos in positions:
            if pos.lap_number not in self._lap_positions:
                self._lap_positions[pos.lap_number] = []
            self._lap_positions[pos.lap_number].append(pos)

        # Sort positions within each lap
        for lap in self._lap_positions:
            self._lap_positions[lap].sort(key=lambda p: p.position)

    def get_position(self, driver_code: str, lap: int) -> Optional[int]:
        """Get driver's position at end of a specific lap."""
        snapshot = self._position_index.get((driver_code, lap))
        return snapshot.position if snapshot else None

    def get_position_delta(
        self,
        driver_code: str,
        lap_before: int,
        lap_after: int,
    ) -> Optional[int]:
        """Calculate position change between two laps.

        Returns:
            Positive if positions gained, negative if lost, None if data missing.
        """
        pos_before = self.get_position(driver_code, lap_before)
        pos_after = self.get_position(driver_code, lap_after)

        if pos_before is None or pos_after is None:
            return None

        # Lower position number = better, so delta is reversed
        return pos_before - pos_after

    def analyze_pit_stop_impact(
        self,
        driver_code: str,
        pit_lap: int,
        window: int = 2,
    ) -> PositionChange:
        """Analyze position change around a pit stop.

        Args:
            driver_code: Driver code
            pit_lap: Lap of the pit stop
            window: Laps before/after to consider

        Returns:
            PositionChange with the impact analysis.
        """
        pos_before = self.get_position(driver_code, pit_lap - 1)
        pos_after = self.get_position(driver_code, pit_lap + window)

        # Fallback to pit lap positions if window data not available
        if pos_before is None:
            pos_before = self.get_position(driver_code, pit_lap)
        if pos_after is None:
            pos_after = self.get_position(driver_code, pit_lap + 1)
            if pos_after is None:
                pos_after = self.get_position(driver_code, pit_lap)

        # Default to same position if no data
        pos_before = pos_before or 0
        pos_after = pos_after or pos_before

        delta = pos_before - pos_after

        return PositionChange(
            lap=pit_lap,
            driver_code=driver_code,
            position_before=pos_before,
            position_after=pos_after,
            delta=delta,
            cause="pit_stop",
        )

    def detect_undercut_victim(
        self,
        attacker_code: str,
        pit_lap: int,
    ) -> List[str]:
        """Detect drivers who were undercut by the attacker.

        An undercut victim is someone who:
        - Was ahead of attacker before the pit stop
        - Pitted later than attacker
        - Ended up behind attacker after both pitted

        Returns:
            List of driver codes who were undercut.
        """
        victims = []

        attacker_pos_before = self.get_position(attacker_code, pit_lap - 1)
        if attacker_pos_before is None:
            return victims

        # Find attacker's position a few laps after pit
        attacker_pos_after = None
        for offset in range(1, 5):
            pos = self.get_position(attacker_code, pit_lap + offset)
            if pos is not None:
                attacker_pos_after = pos
                break

        if attacker_pos_after is None:
            return victims

        # Check each driver who was ahead before
        for pos in self._lap_positions.get(pit_lap - 1, []):
            if pos.driver_code == attacker_code:
                continue
            if pos.position >= attacker_pos_before:
                continue  # Was behind attacker

            # Check if this driver pitted later
            driver_pit = self._find_pit_stop(pos.driver_code, pit_lap, pit_lap + 5)
            if driver_pit is None:
                continue  # Didn't pit in window

            if driver_pit <= pit_lap:
                continue  # Pitted same lap or earlier

            # Check if attacker is now ahead
            victim_pos_after = self.get_position(pos.driver_code, pit_lap + 4)
            if victim_pos_after and victim_pos_after > attacker_pos_after:
                victims.append(pos.driver_code)

        return victims

    def detect_overcut_success(
        self,
        driver_code: str,
        pit_lap: int,
    ) -> List[str]:
        """Detect drivers who were overcut by staying out.

        An overcut success is when:
        - Driver stays out while others pit
        - Driver gains track position by building gap on fresh tires
        - Driver maintains position after their own stop

        Returns:
            List of driver codes who were overtaken via overcut.
        """
        overtaken = []

        driver_pos_before = self.get_position(driver_code, pit_lap - 3)
        if driver_pos_before is None:
            return overtaken

        # Find drivers who pitted before us and we ended up ahead
        for stop in self.pit_stops:
            if stop.driver_code == driver_code:
                continue
            if stop.lap >= pit_lap:
                continue  # Pitted same or later
            if stop.lap < pit_lap - 5:
                continue  # Pitted too early

            # Check if we were behind before their pit
            their_pos_before = self.get_position(stop.driver_code, stop.lap - 1)
            if their_pos_before is None or their_pos_before >= driver_pos_before:
                continue  # They were behind us

            # Check if we're now ahead after our pit
            our_pos_after = self.get_position(driver_code, pit_lap + 2)
            their_pos_after = self.get_position(stop.driver_code, pit_lap + 2)

            if our_pos_after and their_pos_after and our_pos_after < their_pos_after:
                overtaken.append(stop.driver_code)

        return overtaken

    def get_field_average_pit_lap(
        self,
        exclude_drivers: Optional[List[str]] = None,
        window_start: int = 1,
        window_end: int = 100,
    ) -> Optional[float]:
        """Calculate average pit lap for the field.

        Args:
            exclude_drivers: Drivers to exclude from calculation
            window_start: First lap to consider
            window_end: Last lap to consider

        Returns:
            Average pit lap or None if no data.
        """
        exclude = set(exclude_drivers or [])
        pit_laps = []

        for stop in self.pit_stops:
            if stop.driver_code in exclude:
                continue
            if window_start <= stop.lap <= window_end:
                pit_laps.append(stop.lap)

        if not pit_laps:
            return None

        return sum(pit_laps) / len(pit_laps)

    def _find_pit_stop(
        self,
        driver_code: str,
        lap_start: int,
        lap_end: int,
    ) -> Optional[int]:
        """Find a driver's pit stop lap within a window."""
        for stop in self.pit_stops:
            if stop.driver_code == driver_code:
                if lap_start <= stop.lap <= lap_end:
                    return stop.lap
        return None

    def get_gap_to_ahead(
        self,
        driver_code: str,
        lap: int,
    ) -> Optional[int]:
        """Get gap to car ahead in milliseconds."""
        snapshot = self._position_index.get((driver_code, lap))
        return snapshot.gap_to_ahead_ms if snapshot else None

    def calculate_position_trajectory(
        self,
        driver_code: str,
        start_lap: int,
        end_lap: int,
    ) -> List[Tuple[int, int]]:
        """Get position trajectory for a driver over lap range.

        Returns:
            List of (lap, position) tuples.
        """
        trajectory = []
        for lap in range(start_lap, end_lap + 1):
            pos = self.get_position(driver_code, lap)
            if pos is not None:
                trajectory.append((lap, pos))
        return trajectory
