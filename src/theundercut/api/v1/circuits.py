"""Circuit analytics API endpoints."""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_TTL_SECONDS = 600  # 10 minutes

# Circuit shortnames for display
CIRCUIT_SHORTNAMES: Dict[str, str] = {
    "albert_park": "Albert Park",
    "americas": "COTA",
    "bahrain": "Bahrain",
    "baku": "Baku",
    "catalunya": "Barcelona",
    "hungaroring": "Hungary",
    "imola": "Imola",
    "interlagos": "Interlagos",
    "jeddah": "Jeddah",
    "losail": "Qatar",
    "marina_bay": "Singapore",
    "miami": "Miami",
    "monaco": "Monaco",
    "monza": "Monza",
    "red_bull_ring": "Austria",
    "rodriguez": "Mexico City",
    "shanghai": "China",
    "silverstone": "Silverstone",
    "spa": "Spa",
    "suzuka": "Suzuka",
    "vegas": "Vegas",
    "villeneuve": "Montreal",
    "yas_marina": "Abu Dhabi",
    "zandvoort": "Zandvoort",
}


def get_circuit_shortname(circuit_id: str) -> str:
    """Get the shortname for a circuit."""
    return CIRCUIT_SHORTNAMES.get(circuit_id, circuit_id)

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


def _fetch_circuit_info(circuit_id: str) -> Optional[Dict[str, Any]]:
    """Fetch circuit details from Jolpica API."""
    url = f"{JOLPICA_BASE}/circuits/{circuit_id}.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        circuits = data.get("MRData", {}).get("CircuitTable", {}).get("Circuits", [])
        return circuits[0] if circuits else None
    except Exception:
        return None


def _fetch_circuit_results(circuit_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch historical race results for a circuit with pagination."""
    all_races: List[Dict] = []
    offset = 0
    page_limit = 100

    try:
        with httpx.Client(timeout=15) as client:
            while len(all_races) < limit:
                url = f"{JOLPICA_BASE}/circuits/{circuit_id}/results.json?limit={page_limit}&offset={offset}"
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()

                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if not races:
                    break

                all_races.extend(races)
                total = int(data.get("MRData", {}).get("total", 0))
                offset += page_limit
                if offset >= total:
                    break

        return all_races[:limit]
    except Exception:
        return []


def _parse_lap_time_to_ms(time_str: str) -> Optional[int]:
    """Parse lap time string (e.g., '1:23.456') to milliseconds."""
    if not time_str:
        return None
    try:
        # Handle format "1:23.456" or "23.456"
        if ":" in time_str:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
            return int((minutes * 60 + seconds) * 1000)
        else:
            return int(float(time_str) * 1000)
    except (ValueError, IndexError):
        return None


def _fetch_circuit_qualifying_history(circuit_id: str) -> List[Dict[str, Any]]:
    """Fetch historical qualifying results for a circuit."""
    all_races: List[Dict] = []
    offset = 0
    page_limit = 100

    try:
        with httpx.Client(timeout=15) as client:
            while True:
                url = f"{JOLPICA_BASE}/circuits/{circuit_id}/qualifying.json?limit={page_limit}&offset={offset}"
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()

                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if not races:
                    break

                all_races.extend(races)
                total = int(data.get("MRData", {}).get("total", 0))
                offset += page_limit
                if offset >= total:
                    break

        return all_races
    except Exception:
        return []


@router.get("/trends/{circuit_id}")
def get_circuit_trends(circuit_id: str) -> Dict[str, Any]:
    """
    Get lap time evolution across seasons for a circuit.

    Returns pole times, fastest race laps, and winner info per season.
    """
    cache_key = f"circuit_trends:v1:{circuit_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch historical race results
    race_results = _fetch_circuit_results(circuit_id, limit=50)

    # Fetch historical qualifying
    qualifying_results = _fetch_circuit_qualifying_history(circuit_id)

    # Build qualifying lookup by season
    qual_by_season: Dict[str, Dict] = {}
    for qual in qualifying_results:
        season = qual.get("season")
        qual_results = qual.get("QualifyingResults", [])
        if qual_results:
            pole = qual_results[0]
            # Get best qualifying time (Q3 > Q2 > Q1)
            pole_time = pole.get("Q3") or pole.get("Q2") or pole.get("Q1")
            qual_by_season[season] = {
                "pole_driver": pole.get("Driver", {}).get("code"),
                "pole_time": pole_time,
                "pole_time_ms": _parse_lap_time_to_ms(pole_time),
            }

    # Build trends from race results
    trends = []
    for race in race_results:
        season = race.get("season")
        if not season:
            continue

        results = race.get("Results", [])
        if not results:
            continue

        winner = results[0]

        # Find fastest lap
        fastest_lap_time = None
        fastest_lap_ms = None
        fastest_lap_driver = None
        for result in results:
            fl = result.get("FastestLap", {})
            if fl.get("rank") == "1":
                fastest_lap_time = fl.get("Time", {}).get("time")
                fastest_lap_ms = _parse_lap_time_to_ms(fastest_lap_time)
                fastest_lap_driver = result.get("Driver", {}).get("code")
                break

        # Get pole info
        qual_info = qual_by_season.get(season, {})

        # Parse winner time (total race time)
        winner_time = winner.get("Time", {}).get("time")
        winner_time_ms = None
        if winner_time:
            # Race time format varies - could be "1:23:45.678" or "+1 Lap" etc.
            try:
                if ":" in winner_time and "Lap" not in winner_time:
                    parts = winner_time.split(":")
                    if len(parts) == 3:
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds = float(parts[2])
                        winner_time_ms = int((hours * 3600 + minutes * 60 + seconds) * 1000)
                    elif len(parts) == 2:
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        winner_time_ms = int((minutes * 60 + seconds) * 1000)
            except (ValueError, IndexError):
                pass

        trends.append({
            "year": int(season),
            "pole_driver": qual_info.get("pole_driver"),
            "pole_time": qual_info.get("pole_time"),
            "pole_time_ms": qual_info.get("pole_time_ms"),
            "fastest_lap_driver": fastest_lap_driver,
            "fastest_lap_time": fastest_lap_time,
            "fastest_lap_ms": fastest_lap_ms,
            "winner": winner.get("Driver", {}).get("code"),
            "winner_team": winner.get("Constructor", {}).get("name"),
            "winner_time_ms": winner_time_ms,
        })

    # Sort by year descending
    trends.sort(key=lambda t: t["year"], reverse=True)

    payload = {
        "circuit_id": circuit_id,
        "trends": trends,
    }

    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload


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
            "shortname": get_circuit_shortname(circuit_id),
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


def _fetch_circuit_qualifying(circuit_id: str, season: int) -> Optional[Dict[str, Any]]:
    """Fetch qualifying results for a specific race."""
    url = f"{JOLPICA_BASE}/{season}/circuits/{circuit_id}/qualifying.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        return races[0] if races else None
    except Exception:
        return None


def _get_strategy_patterns(db: Session, circuit_id: str, season: int) -> List[Dict[str, Any]]:
    """Get pit stop strategy patterns from local stint data."""
    # Map circuit_id to race_id pattern (we need to find the round)
    # For now, return empty - will be populated when we have the mapping
    try:
        # Get races for this circuit from schedule
        races = _fetch_race_schedule(season)
        round_num = None
        for race in races:
            if race.get("Circuit", {}).get("circuitId") == circuit_id:
                round_num = int(race.get("round", 0))
                break

        if not round_num:
            return []

        race_id = f"{season}-{round_num}"

        # Query stint data
        result = db.execute(text("""
            SELECT driver, COUNT(DISTINCT stint_no) as stops,
                   STRING_AGG(DISTINCT compound, ',' ORDER BY compound) as compounds
            FROM stints
            WHERE race_id = :race_id
            GROUP BY driver
        """), {"race_id": race_id})

        rows = result.fetchall()
        if not rows:
            return []

        # Calculate most common stops
        stop_counts = defaultdict(int)
        compounds_used = set()
        for driver, stops, compounds in rows:
            stop_counts[stops] += 1
            if compounds:
                compounds_used.update(compounds.split(","))

        most_common_stops = max(stop_counts.keys(), key=lambda k: stop_counts[k]) if stop_counts else 0

        return [{
            "year": season,
            "most_common_stops": most_common_stops,
            "compounds_used": sorted(list(compounds_used)),
        }]
    except Exception:
        return []


@router.get("/{season}/{circuit_id}")
def get_circuit_detail(
    season: int,
    circuit_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get comprehensive analytics for a specific circuit.

    Returns circuit info, race results, lap records, driver/team stats.
    """
    cache_key = f"circuit_detail:v1:{season}:{circuit_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch circuit info
    circuit_info = _fetch_circuit_info(circuit_id)
    if not circuit_info:
        return {"error": "Circuit not found"}

    # Fetch historical results for this circuit
    historical_races = _fetch_circuit_results(circuit_id, limit=30)

    # Get current season race info
    current_race = None
    for race in historical_races:
        if race.get("season") == str(season):
            current_race = race
            break

    # Build race info
    race_info = None
    if current_race:
        results = current_race.get("Results", [])
        winner = results[0] if results else {}
        fastest_lap_holder = None
        fastest_lap_time = None

        for r in results:
            fl = r.get("FastestLap", {})
            if fl.get("rank") == "1":
                fastest_lap_holder = r.get("Driver", {}).get("code")
                fastest_lap_time = fl.get("Time", {}).get("time")
                break

        # Get pole position from qualifying
        qual = _fetch_circuit_qualifying(circuit_id, season)
        pole_sitter = None
        if qual:
            qual_results = qual.get("QualifyingResults", [])
            if qual_results:
                pole_sitter = qual_results[0].get("Driver", {}).get("code")

        race_info = {
            "round": int(current_race.get("round", 0)),
            "date": current_race.get("date", ""),
            "race_name": current_race.get("raceName", ""),
            "winner": winner.get("Driver", {}).get("code"),
            "winner_team": winner.get("Constructor", {}).get("name"),
            "pole": pole_sitter,
            "fastest_lap": fastest_lap_holder,
            "fastest_lap_time": fastest_lap_time,
        }

    # Build lap records (all-time fastest from historical data)
    all_time_fastest = None
    season_fastest = None
    for race in historical_races:
        for result in race.get("Results", []):
            fl = result.get("FastestLap", {})
            if fl.get("rank") == "1":
                time_str = fl.get("Time", {}).get("time", "")
                if time_str:
                    record = {
                        "driver": result.get("Driver", {}).get("code"),
                        "time": time_str,
                        "year": int(race.get("season", 0)),
                    }
                    if race.get("season") == str(season):
                        season_fastest = record
                    # Track all-time (simplified - just use most recent for now)
                    if not all_time_fastest:
                        all_time_fastest = record

    # Build historical winners
    historical_winners = []
    for race in sorted(historical_races, key=lambda r: r.get("season", ""), reverse=True):
        results = race.get("Results", [])
        if results:
            winner = results[0]
            historical_winners.append({
                "year": int(race.get("season", 0)),
                "driver": winner.get("Driver", {}).get("code"),
                "driver_name": f"{winner.get('Driver', {}).get('givenName', '')} {winner.get('Driver', {}).get('familyName', '')}".strip(),
                "team": winner.get("Constructor", {}).get("name"),
            })

    # Build driver stats at this circuit
    driver_stats: Dict[str, Dict] = defaultdict(lambda: {
        "races": 0, "wins": 0, "podiums": 0, "points": 0, "finishes": []
    })
    for race in historical_races:
        for result in race.get("Results", []):
            driver_code = result.get("Driver", {}).get("code")
            if not driver_code:
                continue
            position = result.get("position", "")
            if position.isdigit():
                pos = int(position)
                driver_stats[driver_code]["races"] += 1
                driver_stats[driver_code]["finishes"].append(pos)
                driver_stats[driver_code]["points"] += float(result.get("points", 0))
                if pos == 1:
                    driver_stats[driver_code]["wins"] += 1
                if pos <= 3:
                    driver_stats[driver_code]["podiums"] += 1

    driver_stats_list = []
    for driver, stats in driver_stats.items():
        if stats["races"] > 0:
            driver_stats_list.append({
                "driver": driver,
                "races": stats["races"],
                "wins": stats["wins"],
                "podiums": stats["podiums"],
                "points": int(stats["points"]),
                "avg_finish": round(sum(stats["finishes"]) / len(stats["finishes"]), 1) if stats["finishes"] else 0,
            })
    driver_stats_list.sort(key=lambda d: (-d["wins"], -d["podiums"], d["avg_finish"]))

    # Build team stats
    team_stats: Dict[str, Dict] = defaultdict(lambda: {"races": 0, "wins": 0, "podiums": 0, "points": 0})
    for race in historical_races:
        teams_in_race = set()
        for result in race.get("Results", []):
            team = result.get("Constructor", {}).get("name")
            if not team:
                continue
            position = result.get("position", "")
            if position.isdigit():
                pos = int(position)
                if team not in teams_in_race:
                    team_stats[team]["races"] += 1
                    teams_in_race.add(team)
                team_stats[team]["points"] += float(result.get("points", 0))
                if pos == 1:
                    team_stats[team]["wins"] += 1
                if pos <= 3:
                    team_stats[team]["podiums"] += 1

    team_stats_list = []
    for team, stats in team_stats.items():
        team_stats_list.append({
            "team": team,
            "races": stats["races"],
            "wins": stats["wins"],
            "podiums": stats["podiums"],
            "points": int(stats["points"]),
        })
    team_stats_list.sort(key=lambda t: (-t["wins"], -t["podiums"]))

    # Get strategy patterns from local data
    strategy_patterns = _get_strategy_patterns(db, circuit_id, season)

    payload = {
        "circuit": {
            "id": circuit_id,
            "name": circuit_info.get("circuitName", ""),
            "shortname": get_circuit_shortname(circuit_id),
            "country": circuit_info.get("Location", {}).get("country", ""),
            "city": circuit_info.get("Location", {}).get("locality", ""),
            "lat": circuit_info.get("Location", {}).get("lat"),
            "lng": circuit_info.get("Location", {}).get("long"),
            "url": circuit_info.get("url", ""),
        },
        "season": season,
        "race_info": race_info,
        "lap_records": {
            "all_time_fastest": all_time_fastest,
            "season_fastest": season_fastest,
        },
        "historical_winners": historical_winners[:15],  # Last 15 years
        "driver_stats": driver_stats_list[:20],  # Top 20 drivers
        "team_stats": team_stats_list[:15],  # Top 15 teams
        "strategy_patterns": strategy_patterns,
    }

    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    return payload
