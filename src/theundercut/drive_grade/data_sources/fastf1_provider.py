"""FastF1 data provider."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Dict, List

try:  # pragma: no cover - optional dependency
    import fastf1
    from fastf1.events import get_event_schedule
except Exception:  # pragma: no cover
    fastf1 = None
    get_event_schedule = None

from ..car_pace import anchor_car_pace_to_team
from ..drive_grade import _clamp
from .base import RaceDataProvider, RaceDescriptor
from .fastf1_overtakes import detect_overtake_events

TRACK_DIFFICULTY_MAP = {
    "monaco_grand_prix": 0.95,
    "são_paulo_grand_prix": 0.55,
    "singapore_grand_prix": 0.85,
    "miami_grand_prix": 0.45,
    "saudi_arabian_grand_prix": 0.4,
    "bahrain_grand_prix": 0.5,
    "australian_grand_prix": 0.55,
    "japanese_grand_prix": 0.65,
    "chinese_grand_prix": 0.5,
    "azerbaijan_grand_prix": 0.6,
    "qatar_grand_prix": 0.5,
    "abu_dhabi_grand_prix": 0.45,
    "italian_grand_prix": 0.35,
    "canadian_grand_prix": 0.55,
    "united_states_grand_prix": 0.5,
    "las_vegas_grand_prix": 0.4,
    "mexico_city_grand_prix": 0.45,
    "spanish_grand_prix": 0.6,
    "hungarian_grand_prix": 0.75,
    "dutch_grand_prix": 0.7,
    "austrian_grand_prix": 0.5,
    "belgian_grand_prix": 0.65,
    "british_grand_prix": 0.55,
    "emilia_romagna_grand_prix": 0.65,
    "monaco": 0.95,
}


@dataclass(slots=True)
class FastF1Config:
    session: str = "R"


class FastF1Provider(RaceDataProvider):
    name = "fastf1"

    def __init__(self, config: FastF1Config | None = None) -> None:
        self.config = config or FastF1Config()

    def is_available(self) -> bool:
        return fastf1 is not None

    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        if fastf1 is None or get_event_schedule is None:
            return []
        schedule = get_event_schedule(season)
        races = schedule[schedule["EventFormat"].notnull()]
        descriptors: List[RaceDescriptor] = []
        for _, row in races.iterrows():
            descriptors.append(
                RaceDescriptor(
                    season=season,
                    round=int(row["RoundNumber"]),
                    race_name=row["EventName"],
                    circuit=row["Location"] or row["EventName"],
                    slug=slugify(row["EventName"]),
                )
            )
        descriptors.sort(key=lambda desc: desc.round)
        return descriptors

    def fetch_weekend(self, season: int, round_number: int) -> dict:
        if fastf1 is None or get_event_schedule is None:
            raise RuntimeError("fastf1 is not installed")
        schedule = get_event_schedule(season)
        row = schedule.loc[schedule["RoundNumber"] == round_number].iloc[0]
        event_name = row["EventName"]
        slug = slugify(event_name)
        session = fastf1.get_session(season, event_name, self.config.session)
        session.load()
        laps = session.laps
        if not session.results.empty and "LapsCompleted" in session.results.columns:
            total_laps = int(session.results["LapsCompleted"].max())
        else:
            total_laps = getattr(session, "total_laps", None) or 0
        if (total_laps is None or total_laps <= 0) and not laps.empty:
            total_laps = int(laps["LapNumber"].max())
        drivers = []
        pit_map: Dict[str, List[int]] = {}
        driver_lookup: Dict[str, dict] = {}
        driver_numbers: Dict[str, str] = {}
        for driver in session.drivers:
            laps_driver = laps.pick_drivers(driver)
            if laps_driver.empty:
                lap_deltas: List[float] = []
                pit_laps: List[int] = []
            else:
                lap_deltas = compute_lap_deltas(laps_driver)
                pit_laps = (
                    laps_driver[laps_driver["PitInTime"].notnull()]["LapNumber"].tolist()
                    if not laps_driver.empty
                    else []
                )
            results_row = session.results.loc[session.results["DriverNumber"] == driver]
            driver_code = results_row["Abbreviation"].iloc[0]
            team_name = results_row["TeamName"].iloc[0]
            grid = int(results_row["GridPosition"].iloc[0]) if not results_row.empty else 0
            position = int(results_row["Position"].iloc[0]) if not results_row.empty else 0
            driver_number = str(results_row["DriverNumber"].iloc[0]) if not results_row.empty else str(driver)
            driver_numbers[driver_code] = driver_number
            pit_map[driver_code] = pit_laps
            finish_position = position if position > 0 else None
            grid_position = grid if grid > 0 else None
            status = results_row["Status"].iloc[0] if "Status" in results_row.columns else None
            entry = {
                "driver": driver_code,
                "team": team_name,
                "car_pace": {"base_delta": _clean_median(lap_deltas), "track_adjustment": 0.0},
                "form": derive_form_metrics(lap_deltas, grid, position),
                "lap_deltas": lap_deltas,
                "grid_position": grid_position,
                "finish_position": finish_position,
                "classification_status": status,
                "pit_laps": pit_laps,
            }
            drivers.append(entry)
            driver_lookup[driver_code] = entry

        # Normalize car pace so each driver reflects their team's average and the field median stays zero
        anchor_car_pace_to_team(drivers)

        pit_targets = derive_pit_targets(pit_map)
        detected_overtakes = detect_overtake_events(session, driver_numbers)
        overtake_map: Dict[str, List[dict]] = {}
        track_difficulty = TRACK_DIFFICULTY_MAP.get(slug, 0.5)
        for detected in detected_overtakes:
            attacker = driver_lookup.get(detected.overtaking_driver)
            defender = driver_lookup.get(detected.overtaken_driver)
            if attacker is None or defender is None:
                continue
            attacker_cpi = attacker["car_pace"]["base_delta"]
            defender_cpi = defender["car_pace"]["base_delta"]
            delta_cpi = attacker_cpi - defender_cpi
            if detected.lap_number and total_laps > 0:
                phase = detected.lap_number / total_laps
            else:
                phase = 0.5
            phase = float(_clamp(phase, 0.05, 1.0))
            overtake_map.setdefault(detected.overtaking_driver, []).append(
                {
                    "lap_number": detected.lap_number,
                    "opponent_driver": defender["driver"],
                    "opponent_team": defender["team"],
                    "event_type": detected.reason,
                    "event_source": "fastf1",
                    "success": True,
                    "exposure_time": 2.0,
                    "penalized": False,
                    "context": {
                        "delta_cpi": delta_cpi,
                        "tire_delta": detected.tire_delta if detected.tire_delta is not None else 0.0,
                        "tire_compound_diff": detected.tire_compound_diff if detected.tire_compound_diff is not None else 0,
                        "ers_delta": detected.ers_delta if detected.ers_delta is not None else 0.0,
                        "track_difficulty": track_difficulty,
                        "race_phase_pressure": phase,
                    },
                }
            )

        enriched_drivers = []
        for entry in drivers:
            pit_laps = entry.pop("pit_laps")
            strategy = build_strategy_entry(pit_laps, pit_targets)
            penalties = derive_penalties(entry["lap_deltas"])
            overtakes = overtake_map.get(entry["driver"], [])
            enriched_drivers.append(
                {
                    **entry,
                    "strategy": strategy,
                    "penalties": penalties,
                    "overtakes": overtakes,
                }
            )
        return {
            "season": season,
            "round": round_number,
            "race_name": event_name,
            "circuit": row["Location"],
            "drivers": enriched_drivers,
        }


def compute_lap_deltas(laps_driver) -> List[float]:
    if laps_driver.empty:
        return []
    lap_times = laps_driver["LapTime"].dt.total_seconds().dropna()
    if lap_times.empty:
        return []
    median_time = lap_times.median()
    return (lap_times - median_time).tolist()


def _clean_median(values: List[float]) -> float:
    if not values:
        return 0.0
    filtered = [value for value in values if abs(value) < 10.0]
    target = filtered if filtered else values
    target.sort()
    mid = len(target) // 2
    if len(target) % 2 == 0:
        return (target[mid - 1] + target[mid]) / 2
    return target[mid]


def derive_form_metrics(deltas: List[float], grid: int, position: int) -> dict:
    if deltas:
        spread = max(deltas) - min(deltas)
        consistency = _clamp(1 - spread / 3)
        error_rate = _clamp(sum(1 for delta in deltas if delta > 1.0) / len(deltas))
    else:
        consistency = 0.5
        error_rate = 0.5
    if grid <= 0 or position <= 0:
        start_precision = 0.5
    else:
        delta = grid - position
        start_precision = _clamp(0.5 + delta / 20)
    return {
        "consistency": consistency,
        "error_rate": error_rate,
        "start_precision": start_precision,
    }


def slugify(value: str) -> str:
    value = value.lower()
    for char in " /().":
        value = value.replace(char, "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def derive_pit_targets(pit_map: Dict[str, List[int]]) -> List[int]:
    max_stops = max((len(stops) for stops in pit_map.values()), default=0)
    targets: List[int] = []
    for idx in range(max_stops):
        laps = [stops[idx] for stops in pit_map.values() if len(stops) > idx]
        if laps:
            targets.append(int(round(median(laps))))
    return targets


def build_strategy_entry(actual: List[int], targets: List[int]) -> dict:
    if not actual:
        return {
            "optimal_pit_laps": [],
            "actual_pit_laps": [],
            "degradation_penalty": 0.0,
        }
    if not targets:
        optimal = actual
    else:
        if len(targets) >= len(actual):
            optimal = targets[: len(actual)]
        else:
            optimal = targets[:] + [targets[-1]] * (len(actual) - len(targets))
    penalty = estimate_degradation_penalty(actual, optimal)
    return {
        "optimal_pit_laps": optimal,
        "actual_pit_laps": actual,
        "degradation_penalty": penalty,
    }


def estimate_degradation_penalty(actual: List[int], optimal: List[int]) -> float:
    if not actual or not optimal:
        return 0.0
    penalty = 0.0
    fallback = optimal[-1]
    for idx, lap in enumerate(actual):
        target = optimal[idx] if idx < len(optimal) else fallback
        diff = lap - target
        if diff > 4:
            penalty += min(diff / 50.0, 0.15)
    return float(_clamp(penalty))


def derive_penalties(lap_deltas: List[float]) -> List[dict]:
    return [
        {"type": "lap_error", "time_loss": float(delta)}
        for delta in lap_deltas
        if delta > 1.5
    ]


__all__ = ["FastF1Provider"]
