"""Helpers for deriving car pace baselines that are anchored at the team level."""
from __future__ import annotations

from statistics import median
from typing import MutableMapping, Sequence


DriverEntry = MutableMapping[str, object]


def anchor_car_pace_to_team(drivers: Sequence[DriverEntry]) -> None:
    """Assign each driver the team-average base_delta and recenter the field median."""
    team_samples: dict[str, list[float]] = {}
    for entry in drivers:
        team = entry.get("team")
        car_pace = entry.get("car_pace")
        if not isinstance(team, str) or not isinstance(car_pace, MutableMapping):
            continue
        base_delta = float(car_pace.get("base_delta", 0.0))
        team_samples.setdefault(team, []).append(base_delta)

    anchors: dict[str, float] = {}
    for team, values in team_samples.items():
        anchors[team] = sum(values) / len(values) if values else 0.0

    field_median = median(anchors.values()) if anchors else 0.0
    for entry in drivers:
        team = entry.get("team")
        car_pace = entry.get("car_pace")
        if not isinstance(team, str) or not isinstance(car_pace, MutableMapping):
            continue
        car_pace["base_delta"] = float(anchors.get(team, 0.0) - field_median)


__all__ = ["anchor_car_pace_to_team"]
