"""Circuit analytics API endpoints."""

from __future__ import annotations

import json
from typing import List, Dict, Any

from fastapi import APIRouter
import httpx

from theundercut.adapters.redis_cache import redis_client

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_TTL_SECONDS = 600  # 10 minutes

router = APIRouter(
    prefix="/api/v1/circuits",
    tags=["circuits"],
)


def _fetch_circuits(season: int) -> List[Dict[str, Any]]:
    """Fetch all circuits for a season from Jolpica API."""
    url = f"{JOLPICA_BASE}/{season}/circuits.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        return data.get("MRData", {}).get("CircuitTable", {}).get("Circuits", [])
    except Exception:
        return []


def _fetch_race_schedule(season: int) -> List[Dict[str, Any]]:
    """Fetch race schedule to get round numbers and dates for each circuit."""
    url = f"{JOLPICA_BASE}/{season}.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        return data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    except Exception:
        return []


@router.get("/{season}")
def get_circuits(season: int) -> Dict[str, Any]:
    """
    Get all circuits for a season with race information.

    Returns circuit list with round numbers, race names, and dates.
    """
    cache_key = f"circuits:v1:{season}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch circuits and race schedule
    circuits_raw = _fetch_circuits(season)
    races = _fetch_race_schedule(season)

    # Build circuit_id -> race info mapping
    race_by_circuit: Dict[str, Dict] = {}
    for race in races:
        circuit_id = race.get("Circuit", {}).get("circuitId")
        if circuit_id:
            race_by_circuit[circuit_id] = {
                "round": int(race.get("round", 0)),
                "race_name": race.get("raceName", ""),
                "date": race.get("date", ""),
            }

    # Build response
    circuits = []
    for circuit in circuits_raw:
        circuit_id = circuit.get("circuitId", "")
        race_info = race_by_circuit.get(circuit_id, {})

        circuits.append({
            "circuit_id": circuit_id,
            "name": circuit.get("circuitName", ""),
            "country": circuit.get("Location", {}).get("country", ""),
            "city": circuit.get("Location", {}).get("locality", ""),
            "round": race_info.get("round"),
            "race_name": race_info.get("race_name", ""),
            "date": race_info.get("date", ""),
        })

    # Sort by round number
    circuits.sort(key=lambda c: c.get("round") or 999)

    payload = {
        "season": season,
        "circuits": circuits,
    }

    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload
