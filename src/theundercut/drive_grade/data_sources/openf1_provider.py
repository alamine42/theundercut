"""Fetch race inputs from the public OpenF1 API."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

try:  # pragma: no cover - optional dependency
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from ..drive_grade import _clamp
from .base import RaceDataProvider, RaceDescriptor

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
}


@dataclass(slots=True)
class OpenF1Config:
    base_url: str = "https://api.openf1.org/v1"
    session_name: str = "Race"
    timeout: float = 30.0


class OpenF1Provider(RaceDataProvider):
    """RaceDataProvider backed by the OpenF1 public API."""

    name = "openf1"

    def __init__(
        self,
        config: OpenF1Config | None = None,
        session: "requests.Session" | None = None,
    ) -> None:
        self.config = config or OpenF1Config()
        self._session = session
        self._schedule_cache: Dict[Tuple[int, int], dict] = {}

    def is_available(self) -> bool:
        return requests is not None

    # Schedule helpers --------------------------------------------------

    def fetch_schedule(self, season: int) -> List[RaceDescriptor]:
        if not self.is_available():
            return []
        sessions = self._get(
            "sessions",
            params={"year": season, "session_name": self.config.session_name},
        )
        descriptors: List[RaceDescriptor] = []
        for entry in sessions:
            round_number = _safe_int(entry.get("round"))
            if round_number is None:
                continue
            race_name = entry.get("meeting_name") or entry.get("event_name") or entry.get("session_name")
            if not race_name:
                continue
            circuit = entry.get("circuit_full_name") or entry.get("location") or race_name
            slug = slugify(race_name)
            descriptors.append(
                RaceDescriptor(
                    season=season,
                    round=round_number,
                    race_name=race_name,
                    circuit=circuit,
                    slug=slug,
                )
            )
            self._schedule_cache[(season, round_number)] = {
                "session_key": entry.get("session_key"),
                "race_name": race_name,
                "circuit": circuit,
                "slug": slug,
                "laps": _safe_int(entry.get("laps")),
            }
        descriptors.sort(key=lambda desc: desc.round)
        return descriptors

    # Race detail -------------------------------------------------------

    def fetch_weekend(self, season: int, round_number: int) -> dict:
        if not self.is_available():
            raise RuntimeError("requests is not available; OpenF1 provider cannot run.")
        session_meta = self._session_cache_entry(season, round_number)
        if not session_meta:
            raise RuntimeError(f"OpenF1 session metadata missing for season={season} round={round_number}")
        session_key = session_meta.get("session_key")
        if session_key is None:
            raise RuntimeError(f"OpenF1 session key missing for season={season} round={round_number}")

        results = self._get("results", params={"session_key": session_key})
        if not results:
            raise RuntimeError(f"No OpenF1 results for session_key={session_key}")

        laps = self._get("laps", params={"session_key": session_key})
        pit_stops = self._get("pit_stops", params={"session_key": session_key})
        overtakes = self._safe_get("overtakes", params={"session_key": session_key})

        driver_lookup = _build_driver_lookup(results)
        lap_map, global_reference = _group_laps(laps, driver_lookup)
        pit_map = _group_pit_stops(pit_stops, driver_lookup)
        total_laps = _resolve_total_laps(session_meta, results, laps)
        driver_entries: List[dict] = []
        for result in results:
            driver_code = _resolve_driver_code(result)
            if not driver_code:
                continue
            lap_times = lap_map.get(driver_code, [])
            lap_deltas = _to_deltas(lap_times, global_reference)
            base_delta = _driver_base_delta(lap_times, global_reference)
            team_name = result.get("team_name") or result.get("team")
            driver_number = _safe_int(result.get("driver_number") or result.get("driver"))
            grid_position = _safe_int(result.get("grid_position") or result.get("grid_place"))
            finish_position = _safe_int(result.get("position"))
            status = result.get("status") or result.get("result")
            consistency, error_rate = _form_metrics(lap_deltas)
            start_precision = _start_precision(grid_position, finish_position, len(results))
            actual_pits = pit_map.get(driver_code, [])
            optimal_pits, degradation_penalty = _estimate_strategy(total_laps, actual_pits)
            penalties = _derive_penalties(result)
            entry = {
                "driver": driver_code,
                "team": team_name or "Unknown",
                "driver_number": driver_number,
                "car_pace": {"base_delta": base_delta, "track_adjustment": 0.0},
                "form": {
                    "consistency": consistency,
                    "error_rate": error_rate,
                    "start_precision": start_precision,
                },
                "lap_deltas": lap_deltas,
                "strategy": {
                    "optimal_pit_laps": optimal_pits,
                    "actual_pit_laps": actual_pits,
                    "degradation_penalty": degradation_penalty,
                },
                "penalties": penalties,
                "overtakes": [],
                "grid_position": grid_position,
                "finish_position": finish_position,
                "classification_status": status,
            }
            driver_entries.append(entry)

        _inject_overtakes(
            overtakes,
            driver_entries,
            total_laps=total_laps,
        )

        return {
            "season": season,
            "round": round_number,
            "race_name": session_meta.get("race_name"),
            "circuit": session_meta.get("circuit"),
            "drivers": driver_entries,
        }

    # Internal helpers --------------------------------------------------

    def _session_cache_entry(self, season: int, round_number: int) -> dict:
        if (season, round_number) not in self._schedule_cache:
            self._hydrate_cache_entry(season, round_number)
        return self._schedule_cache.get((season, round_number), {})

    def _hydrate_cache_entry(self, season: int, round_number: int) -> None:
        sessions = self._get(
            "sessions",
            params={"year": season, "session_name": self.config.session_name},
        )
        for entry in sessions:
            if _safe_int(entry.get("round")) == round_number:
                race_name = entry.get("meeting_name") or entry.get("event_name") or entry.get("session_name")
                slug = slugify(race_name or f"round_{round_number}")
                circuit = entry.get("circuit_full_name") or entry.get("location") or race_name
                self._schedule_cache[(season, round_number)] = {
                    "session_key": entry.get("session_key"),
                    "race_name": race_name,
                    "circuit": circuit,
                    "slug": slug,
                    "laps": _safe_int(entry.get("laps")),
                }
                return

    def _get(self, endpoint: str, params: Dict[str, object]) -> List[dict]:
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        session = self._session or (requests.Session() if requests else None)
        if session is None:
            raise RuntimeError("requests is not available")
        try:
            resp = session.get(url, params=params, timeout=self.config.timeout)
            resp.raise_for_status()
        except Exception as exc:  # pragma: no cover - thin wrapper
            raise RuntimeError(f"OpenF1 request failed ({endpoint}): {exc}") from exc
        data = resp.json()
        if isinstance(data, dict):
            # Some endpoints wrap results inside a key
            data = data.get("data") or data.get("results") or []
        if not isinstance(data, list):
            return []
        return data

    def _safe_get(self, endpoint: str, params: Dict[str, object]) -> List[dict]:
        try:
            return self._get(endpoint, params)
        except Exception:
            return []


# Utility functions ---------------------------------------------------------


def slugify(name: str | None) -> str:
    if not name:
        return "race"
    slug = name.lower()
    for char in [" ", "/", "-", ".", "(", ")", "'"]:
        slug = slug.replace(char, "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def _safe_int(value: object) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_seconds(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        total = 0.0
        parts = text.split(":")
        for part in parts:
            try:
                total = total * 60 + float(part)
            except ValueError:
                return None
        return total
    try:
        return float(text)
    except ValueError:
        return None


def _build_driver_lookup(results: Iterable[dict]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in results:
        code = _resolve_driver_code(row)
        number = row.get("driver_number") or row.get("driver")
        if code and number is not None:
            mapping[str(number)] = code
    return mapping


def _resolve_driver_code(row: dict) -> str | None:
    code = row.get("driver_code") or row.get("driver_id") or row.get("driver")
    if code:
        return str(code).upper()
    number = row.get("driver_number")
    return str(number) if number is not None else None


def _group_laps(
    laps: Iterable[dict],
    lookup: Dict[str, str],
) -> Tuple[Dict[str, List[float]], float]:
    lap_map: Dict[str, List[float]] = {}
    all_times: List[float] = []
    for lap in laps:
        number = lap.get("driver_number") or lap.get("driver")
        if number is None:
            continue
        driver_code = lookup.get(str(number)) or str(number)
        lap_time = _parse_seconds(lap.get("lap_time") or lap.get("lap_duration") or lap.get("duration"))
        if lap_time is None or lap_time <= 0:
            continue
        lap_map.setdefault(driver_code, []).append(lap_time)
        all_times.append(lap_time)
    reference = statistics.median(all_times) if all_times else 0.0
    return lap_map, reference


def _group_pit_stops(pits: Iterable[dict], lookup: Dict[str, str]) -> Dict[str, List[int]]:
    mapping: Dict[str, List[int]] = {}
    for stop in pits:
        number = stop.get("driver_number") or stop.get("driver")
        if number is None:
            continue
        code = lookup.get(str(number)) or str(number)
        lap = _safe_int(stop.get("lap_number") or stop.get("lap"))
        if lap is None:
            continue
        mapping.setdefault(code, []).append(lap)
    for laps in mapping.values():
        laps.sort()
    return mapping


def _resolve_total_laps(meta: dict, results: Iterable[dict], laps: Iterable[dict]) -> int:
    if _safe_int(meta.get("laps")):
        return int(meta["laps"])
    lap_counts = [row.get("laps") for row in results if _safe_int(row.get("laps"))]
    if lap_counts:
        return max(_safe_int(value) or 0 for value in lap_counts)
    lap_numbers = [_safe_int(row.get("lap_number")) for row in laps]
    lap_numbers = [val for val in lap_numbers if val]
    return max(lap_numbers) if lap_numbers else 0


def _to_deltas(times: List[float], reference: float) -> List[float]:
    if not times:
        return []
    return [round(time - reference, 4) for time in times]


def _driver_base_delta(times: List[float], reference: float) -> float:
    if not times:
        return 0.0
    avg = statistics.mean(times)
    return round(avg - reference, 4)


def _form_metrics(lap_deltas: List[float]) -> Tuple[float, float]:
    if not lap_deltas:
        return 0.5, 0.1
    deviations = [abs(delta) for delta in lap_deltas]
    avg_dev = statistics.mean(deviations)
    consistency = _clamp(1 - avg_dev / 1.5)
    threshold = max(statistics.pstdev(lap_deltas), 0.001)
    mistakes = sum(1 for delta in lap_deltas if abs(delta) > threshold * 2)
    error_rate = _clamp(mistakes / max(len(lap_deltas), 1))
    return consistency, error_rate


def _start_precision(grid: int | None, finish: int | None, field_size: int) -> float:
    if grid is None or finish is None or grid <= 0 or finish <= 0:
        return 0.5
    delta = grid - finish
    scale = max(field_size, 20)
    return _clamp(0.5 + delta / scale)


def _estimate_strategy(total_laps: int, actual_pits: List[int]) -> Tuple[List[int], float]:
    if total_laps <= 0 or not actual_pits:
        return [], 0.0
    stint_count = len(actual_pits)
    spacing = total_laps / (stint_count + 1)
    optimal = [max(1, round(spacing * (idx + 1))) for idx in range(stint_count)]
    deviation = sum(abs(act - opt) for act, opt in zip(actual_pits, optimal))
    penalty = _clamp(deviation / max(total_laps, 1))
    return optimal, penalty


def _derive_penalties(result_row: dict) -> List[dict]:
    penalties: List[dict] = []
    total_penalty = _parse_seconds(result_row.get("time_penalty") or result_row.get("penalties"))
    if total_penalty and total_penalty > 0:
        penalties.append({"type": "official", "time_loss": float(total_penalty)})
    return penalties


def _inject_overtakes(
    overtakes: Iterable[dict],
    driver_entries: List[dict],
    *,
    total_laps: int,
) -> None:
    if not overtakes:
        return
    entries_by_driver = {entry["driver"]: entry for entry in driver_entries}
    entries_by_number = {
        int(entry["driver_number"]): entry
        for entry in driver_entries
        if entry.get("driver_number") is not None
    }

    def _entry_for_event(code_value: str | None, number_value: int | None) -> dict | None:
        if code_value and code_value in entries_by_driver:
            return entries_by_driver[code_value]
        if number_value is not None:
            return entries_by_number.get(number_value)
        return None

    for event in overtakes:
        attacker_code = _resolve_driver_code(
            {"driver_code": event.get("overtaking_driver"), "driver_number": event.get("overtaking_driver_number")}
        )
        defender_code = _resolve_driver_code(
            {"driver_code": event.get("overtaken_driver"), "driver_number": event.get("overtaken_driver_number")}
        )
        attacker = _entry_for_event(attacker_code, _safe_int(event.get("overtaking_driver_number")))
        defender = _entry_for_event(defender_code, _safe_int(event.get("overtaken_driver_number")))
        if attacker is None or defender is None:
            continue
        attacker_pace = attacker["car_pace"]["base_delta"]
        defender_pace = defender["car_pace"]["base_delta"]
        lap_number = _safe_int(event.get("lap_number"))
        exposure = event.get("duration") or event.get("elapsed_time") or 2.0
        try:
            exposure_time = float(exposure)
        except (TypeError, ValueError):
            exposure_time = 2.0
        track_difficulty = TRACK_DIFFICULTY_MAP.get(slugify(event.get("location")), 0.5)
        phase = (
            _clamp(lap_number / total_laps, 0.05, 1.0)
            if lap_number and total_laps > 0
            else 0.5
        )
        attacker.setdefault("overtakes", []).append(
            {
                "success": True,
                "exposure_time": exposure_time,
                "penalized": False,
                "lap_number": lap_number,
                "opponent_driver": defender["driver"],
                "opponent_team": defender["team"],
                "event_type": "on_track",
                "event_source": "openf1",
                "context": {
                    "delta_cpi": attacker_pace - defender_pace,
                    "tire_delta": 0,
                    "tire_compound_diff": 0,
                    "ers_delta": 0.0,
                    "track_difficulty": track_difficulty,
                    "race_phase_pressure": phase,
                },
            }
        )


__all__ = ["OpenF1Provider", "OpenF1Config"]
