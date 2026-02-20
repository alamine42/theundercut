"""
Season standings service.

Fetches driver and constructor championship standings, computing derived
metrics like positions gained, projected points, and last-5-race performance.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"


def _fetch_driver_standings(season: int) -> List[Dict[str, Any]]:
    """Fetch driver standings from Jolpica API."""
    url = f"{JOLPICA_BASE}/{season}/driverStandings.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        standings_lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
        if not standings_lists:
            return []

        return standings_lists[0].get("DriverStandings", [])
    except Exception:
        return []


def _fetch_constructor_standings(season: int) -> List[Dict[str, Any]]:
    """Fetch constructor standings from Jolpica API."""
    url = f"{JOLPICA_BASE}/{season}/constructorStandings.json"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        standings_lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
        if not standings_lists:
            return []

        return standings_lists[0].get("ConstructorStandings", [])
    except Exception:
        return []


def _fetch_race_results(season: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch race results with pagination (API caps at 100 per request)."""
    all_races: Dict[str, Dict] = {}  # round -> race data
    offset = 0
    page_limit = 100  # API maximum per request

    try:
        with httpx.Client(timeout=15) as client:
            while True:
                url = f"{JOLPICA_BASE}/{season}/results.json?limit={page_limit}&offset={offset}"
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()

                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if not races:
                    break

                # Merge races (API may return partial race data across pages)
                for race in races:
                    round_num = race.get("round")
                    if round_num in all_races:
                        # Append results to existing race
                        all_races[round_num]["Results"].extend(race.get("Results", []))
                    else:
                        all_races[round_num] = race

                # Check if we've fetched all results
                total = int(data.get("MRData", {}).get("total", 0))
                offset += page_limit
                if offset >= total:
                    break

        # Return races sorted by round
        return [all_races[r] for r in sorted(all_races.keys(), key=int)]
    except Exception:
        return []


def _compute_last_n_points(races: List[Dict], driver_code: str, n: int = 5) -> int:
    """Compute points earned in last N races for a driver."""
    points = 0
    race_count = 0

    # Races are ordered by round, get last N
    for race in reversed(races):
        if race_count >= n:
            break
        for result in race.get("Results", []):
            if result.get("Driver", {}).get("code") == driver_code:
                points += float(result.get("points", 0))
                race_count += 1
                break

    return int(points)


def _compute_constructor_last_n_points(races: List[Dict], constructor_id: str, n: int = 5) -> int:
    """Compute points earned in last N races for a constructor."""
    points = 0
    races_counted = set()

    for race in reversed(races):
        if len(races_counted) >= n:
            break
        race_round = race.get("round")
        for result in race.get("Results", []):
            constructors = result.get("Constructor", {})
            if constructors.get("constructorId") == constructor_id:
                if race_round not in races_counted:
                    races_counted.add(race_round)
                points += float(result.get("points", 0))

    return int(points)


def _compute_driver_metrics(races: List[Dict], driver_code: str) -> Dict[str, Any]:
    """Compute per-driver metrics from race history."""
    total_races = 0
    poles = 0
    total_start = 0
    total_finish = 0
    positions_gained = 0

    for race in races:
        for result in race.get("Results", []):
            if result.get("Driver", {}).get("code") == driver_code:
                total_races += 1
                grid = int(result.get("grid", 0))
                position = int(result.get("position", 0)) if result.get("position", "").isdigit() else 20

                if grid == 1:
                    poles += 1
                if grid > 0:
                    total_start += grid
                if position > 0:
                    total_finish += position
                    positions_gained += (grid - position) if grid > 0 else 0
                break

    return {
        "total_races": total_races,
        "poles": poles,
        "avg_start_pos": round(total_start / total_races, 1) if total_races else 0,
        "avg_finish_pos": round(total_finish / total_races, 1) if total_races else 0,
        "positions_gained": positions_gained,
        "positions_gained_per_race": round(positions_gained / total_races, 2) if total_races else 0,
    }


def fetch_season_standings(db: Session, season: int) -> Dict[str, Any]:
    """
    Fetch complete season standings with computed metrics.

    Returns:
        {
            "season": int,
            "last_updated": str,
            "races_completed": int,
            "races_remaining": int,
            "drivers": [...],
            "constructors": [...]
        }
    """
    # Fetch raw standings
    driver_standings = _fetch_driver_standings(season)
    constructor_standings = _fetch_constructor_standings(season)
    races = _fetch_race_results(season, limit=24)  # Full season

    # Count races from calendar
    races_completed = 0
    races_remaining = 0
    try:
        result = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE session_type = 'Race' AND start_ts < NOW()) as completed,
                COUNT(*) FILTER (WHERE session_type = 'Race' AND start_ts >= NOW()) as remaining
            FROM calendar_events
            WHERE season = :season
        """), {"season": season})
        row = result.fetchone()
        if row:
            races_completed = row[0] or 0
            races_remaining = row[1] or 0
    except Exception:
        races_completed = len(races)
        races_remaining = 24 - races_completed  # Estimate

    # Transform driver standings
    drivers = []
    for d in driver_standings:
        driver_code = d.get("Driver", {}).get("code", "???")
        points = float(d.get("points", 0))
        wins = int(d.get("wins", 0))

        # Get constructor name
        constructors = d.get("Constructors", [])
        constructor_name = constructors[0].get("name", "Unknown") if constructors else "Unknown"

        # Compute metrics
        pts_last_5 = _compute_last_n_points(races, driver_code, 5)
        metrics = _compute_driver_metrics(races, driver_code)

        # Use races_completed for points_per_race (more reliable than counting from results API)
        driver_races = metrics["total_races"] if metrics["total_races"] > 0 else races_completed
        drivers.append({
            "driver_code": driver_code,
            "driver_name": f"{d.get('Driver', {}).get('givenName', '')} {d.get('Driver', {}).get('familyName', '')}".strip(),
            "constructor_name": constructor_name,
            "points": int(points),
            "wins": wins,
            "pts_last_5": pts_last_5,
            "points_per_race": round(points / driver_races, 1) if driver_races else 0,
            "points_won_lost": 0,  # TODO: compute from expected vs actual
            "alt_points": 0,  # TODO: compute alternate scoring
            **metrics,
        })

    # Transform constructor standings
    constructors = []
    for c in constructor_standings:
        constructor_id = c.get("Constructor", {}).get("constructorId", "")
        constructor_name = c.get("Constructor", {}).get("name", "Unknown")
        points = float(c.get("points", 0))

        pts_last_5 = _compute_constructor_last_n_points(races, constructor_id, 5)

        constructors.append({
            "constructor_id": constructor_id,
            "constructor_name": constructor_name,
            "points": int(points),
            "wins": int(c.get("wins", 0)),
            "pts_last_5": pts_last_5,
            "positions_gained": 0,  # TODO: aggregate from drivers
            "points_won_lost": 0,
            "alt_points": 0,
        })

    return {
        "season": season,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "races_completed": races_completed,
        "races_remaining": races_remaining,
        "drivers": drivers,
        "constructors": constructors,
    }
