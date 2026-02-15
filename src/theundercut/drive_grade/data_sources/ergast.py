"""Integration helpers for fetching F1 data from the Ergast API."""
from __future__ import annotations

from statistics import mean, median, pstdev
from typing import Dict, List, Mapping, Sequence

import requests

from ..car_pace import anchor_car_pace_to_team
from ..drive_grade import _clamp
from .base import RaceDataProvider, RaceDescriptor

BASE_URL = "https://ergast.com/api/f1"
RESULT_LIMIT = 300
LAP_LIMIT = 6000
PIT_LIMIT = 2000


class ErgastClient:
    """Thin HTTP client for the Ergast API."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def fetch_season_schedule(self, season: int | str) -> List[RaceDescriptor]:
        payload = self._get_json(f"{season}.json")
        races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        descriptors: List[RaceDescriptor] = []
        for race in races:
            descriptors.append(
                RaceDescriptor(
                    season=int(race.get("season", season)),
                    round=int(race.get("round", 0)),
                    race_name=race.get("raceName", ""),
                    circuit=race.get("Circuit", {}).get("circuitName", ""),
                    slug=slugify_race(race.get("raceName", "race")),
                )
            )
        return descriptors

    def fetch_weekend(self, season: int | str, round_number: int | str) -> dict:
        results = self._get_json(f"{season}/{round_number}/results.json", params={"limit": RESULT_LIMIT})
        laps = self._get_json(f"{season}/{round_number}/laps.json", params={"limit": LAP_LIMIT})
        pit_stops = self._get_json(f"{season}/{round_number}/pitstops.json", params={"limit": PIT_LIMIT})
        return build_weekend_descriptor(results, laps, pit_stops)

    def _get_json(self, path: str, params: Mapping[str, str | int] | None = None) -> dict:
        url = f"{BASE_URL}/{path}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


def build_weekend_descriptor(results_payload: dict, laps_payload: dict, pit_payload: dict) -> dict:
    race = _extract_race(results_payload)
    lap_deltas = extract_lap_deltas(laps_payload)
    pit_map = extract_pit_laps(pit_payload)
    drivers_payload = race.get("Results", [])
    drivers: List[dict] = []
    for result in drivers_payload:
        driver_entry = build_driver_entry(result, lap_deltas, pit_map)
        drivers.append(driver_entry)
    anchor_car_pace_to_team(drivers)
    return {
        "season": race.get("season"),
        "round": race.get("round"),
        "race_name": race.get("raceName"),
        "circuit": race.get("Circuit", {}).get("circuitName"),
        "drivers": drivers,
    }


def build_driver_entry(result: dict, lap_deltas: Mapping[str, List[float]], pit_map: Mapping[str, List[int]]) -> dict:
    driver_info = result.get("Driver", {})
    constructor = result.get("Constructor", {})
    driver_id = driver_info.get("driverId")
    given = driver_info.get("givenName", "")
    family = driver_info.get("familyName", "")
    name = driver_info.get("code") or f"{given[:1]}. {family}".strip()
    team = constructor.get("name", "Unknown")
    deltas = lap_deltas.get(driver_id, [])
    base_delta = mean(deltas) if deltas else 0.0
    form = derive_form_metrics(
        deltas,
        grid=int(result.get("grid", "0") or 0),
        position=int(result.get("position", "0") or 0),
    )
    actual_pits = pit_map.get(driver_id, [])
    return {
        "driver": name,
        "team": team,
        "car_pace": {"base_delta": base_delta, "track_adjustment": 0.0},
        "form": form,
        "lap_deltas": deltas,
        "grid_position": int(result.get("grid", "0") or 0) or None,
        "finish_position": int(result.get("position", "0") or 0) or None,
        "classification_status": result.get("status"),
        "strategy": {
            "optimal_pit_laps": actual_pits,
            "actual_pit_laps": actual_pits,
            "degradation_penalty": 0.0,
        },
        "penalties": [],
        "overtakes": [],
    }


def derive_form_metrics(deltas: Sequence[float], grid: int, position: int) -> dict:
    if deltas:
        spread = pstdev(deltas) if len(deltas) > 1 else 0.0
        consistency = _clamp(1 - spread / 0.8)
        error_rate = _clamp(sum(1 for delta in deltas if delta > 0.6) / len(deltas))
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


def extract_lap_deltas(payload: dict) -> Dict[str, List[float]]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return {}
    lap_entries = races[0].get("Laps", [])
    lap_map: Dict[str, List[float]] = {}
    for lap in lap_entries:
        timings = lap.get("Timings", [])
        if not timings:
            continue
        lap_times = [lap_time_to_seconds(timing.get("time", "0:00.000")) for timing in timings]
        lap_median = median(lap_times)
        for timing, lap_time in zip(timings, lap_times):
            driver_id = timing.get("driverId")
            lap_map.setdefault(driver_id, []).append(lap_time - lap_median)
    return lap_map


def extract_pit_laps(payload: dict) -> Dict[str, List[int]]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return {}
    pit_entries = races[0].get("PitStops", [])
    pit_map: Dict[str, List[int]] = {}
    for stop in pit_entries:
        driver_id = stop.get("driverId")
        lap = int(stop.get("lap", "0") or 0)
        pit_map.setdefault(driver_id, []).append(lap)
    for laps in pit_map.values():
        laps.sort()
    return pit_map


def lap_time_to_seconds(time_str: str) -> float:
    minutes, rest = time_str.split(":")
    seconds = float(rest)
    return int(minutes) * 60 + seconds


def _extract_race(payload: dict) -> dict:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    return races[0] if races else {}


def slugify_race(name: str) -> str:
    slug = name.lower().replace("'", "")
    for char in [" ", "/", "-", ".", "(", ")"]:
        slug = slug.replace(char, "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "race"

class ErgastProvider(RaceDataProvider):
    name = "ergast"

    def __init__(self, client: ErgastClient | None = None) -> None:
        self.client = client or ErgastClient()

    def is_available(self) -> bool:
        return True

    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        return self.client.fetch_season_schedule(season)

    def fetch_weekend(self, season: int, round_number: int) -> dict:
        return self.client.fetch_weekend(season, round_number)


__all__ = [
    "ErgastClient",
    "ErgastProvider",
    "build_weekend_descriptor",
    "build_driver_entry",
    "extract_lap_deltas",
    "extract_pit_laps",
    "lap_time_to_seconds",
    "slugify_race",
]
