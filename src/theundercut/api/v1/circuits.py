"""Circuit analytics API endpoints."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
import httpx

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.config import get_settings
from theundercut.models import Circuit, CircuitCharacteristics

logger = logging.getLogger(__name__)

# Rate limiting: 1 request per second to avoid 429 errors
_last_request_time = 0.0
_request_interval = 1.0  # 1 second between requests

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_TTL_SECONDS = 600  # 10 minutes
HISTORICAL_CACHE_TTL_SECONDS = 86400  # 24 hours for historical data


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

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
    except Exception as e:
        logger.warning(f"Failed to fetch circuits for season {season}: {e}")
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
    except Exception as e:
        logger.warning(f"Failed to fetch race schedule for season {season}: {e}")
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
    except Exception as e:
        logger.warning(f"Failed to fetch circuit info for {circuit_id}: {e}")
        return None


def _rate_limited_request(client: httpx.Client, url: str, max_retries: int = 5) -> httpx.Response:
    """Make a rate-limited HTTP request with retry logic for 429 errors."""
    global _last_request_time

    for attempt in range(max_retries):
        # Rate limiting: ensure minimum interval between requests
        elapsed = time.time() - _last_request_time
        if elapsed < _request_interval:
            time.sleep(_request_interval - elapsed)

        _last_request_time = time.time()

        try:
            resp = client.get(url)
            if resp.status_code == 429:
                # Rate limited - wait and retry with exponential backoff
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s, 16s, 32s
                logger.debug(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2
                time.sleep(wait_time)
                continue
            raise

    # If we get here, all retries failed
    raise httpx.HTTPStatusError(f"Max retries exceeded for {url}", request=None, response=None)


def _fetch_circuit_results(circuit_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch historical race results for a circuit with pagination and caching.

    Fetches the MOST RECENT races by starting from the end of the dataset.
    """
    # Check cache first (historical data changes rarely)
    cache_key = f"circuit_results:{circuit_id}:{limit}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error for circuit results {circuit_id}: {e}")
        # Continue without cache

    all_races: List[Dict] = []
    page_limit = 100  # ~5 races per 100 results

    try:
        with httpx.Client(timeout=30) as client:
            # First, get the total count to calculate where to start
            url = f"{JOLPICA_BASE}/circuits/{circuit_id}/results.json?limit=1&offset=0"
            resp = _rate_limited_request(client, url)
            data = resp.json()
            total = _safe_int(data.get("MRData", {}).get("total", 0))

            if total == 0:
                return []

            # Calculate starting offset to get the most recent races
            # Each race has ~20 results, so limit races * 20 results per race
            results_needed = limit * 20
            start_offset = max(0, total - results_needed)

            offset = start_offset
            while len(all_races) < limit and offset < total:
                url = f"{JOLPICA_BASE}/circuits/{circuit_id}/results.json?limit={page_limit}&offset={offset}"
                resp = _rate_limited_request(client, url)
                data = resp.json()

                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if not races:
                    break

                all_races.extend(races)
                offset += page_limit

        # Sort by season descending to get most recent first
        all_races.sort(key=lambda r: _safe_int(r.get("season", 0)), reverse=True)
        result = all_races[:limit]

        # Only cache if we got data (avoid caching transient failures)
        if result:
            try:
                redis_client.setex(cache_key, HISTORICAL_CACHE_TTL_SECONDS, json.dumps(result))
            except Exception as e:
                logger.warning(f"Redis write error for circuit results {circuit_id}: {e}")
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch circuit results for {circuit_id}: {e}")
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
                total = _safe_int(data.get("MRData", {}).get("total", 0))
                offset += page_limit
                if offset >= total:
                    break

        return all_races
    except Exception as e:
        logger.warning(f"Failed to fetch qualifying history for {circuit_id}: {e}")
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
            "year": _safe_int(season),
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


def _compute_preview_stats_from_races(races: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute preview stats from pre-fetched race data."""
    if not races:
        return {
            "last_winner": None,
            "last_winner_team": None,
            "dominant_driver": None,
            "dominant_driver_wins": 0,
            "dominant_team": None,
            "dominant_team_wins": 0,
        }

    # Sort races by season descending to get the most recent
    sorted_races = sorted(races, key=lambda r: _safe_int(r.get("season", 0)), reverse=True)

    # Get last winner
    last_winner = None
    last_winner_team = None
    if sorted_races:
        results = sorted_races[0].get("Results", [])
        if results:
            winner = results[0]
            last_winner = winner.get("Driver", {}).get("code")
            last_winner_team = winner.get("Constructor", {}).get("name")

    # Count wins per driver and team
    driver_wins: Dict[str, int] = defaultdict(int)
    team_wins: Dict[str, int] = defaultdict(int)

    for race in races:
        results = race.get("Results", [])
        if results:
            winner = results[0]
            driver_code = winner.get("Driver", {}).get("code")
            team_name = winner.get("Constructor", {}).get("name")
            if driver_code:
                driver_wins[driver_code] += 1
            if team_name:
                team_wins[team_name] += 1

    # Find dominant driver and team
    dominant_driver = None
    dominant_driver_wins = 0
    if driver_wins:
        dominant_driver = max(driver_wins.keys(), key=lambda k: driver_wins[k])
        dominant_driver_wins = driver_wins[dominant_driver]

    dominant_team = None
    dominant_team_wins = 0
    if team_wins:
        dominant_team = max(team_wins.keys(), key=lambda k: team_wins[k])
        dominant_team_wins = team_wins[dominant_team]

    return {
        "last_winner": last_winner,
        "last_winner_team": last_winner_team,
        "dominant_driver": dominant_driver,
        "dominant_driver_wins": dominant_driver_wins,
        "dominant_team": dominant_team,
        "dominant_team_wins": dominant_team_wins,
    }


def _fetch_all_circuit_results_parallel(circuit_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch historical results for multiple circuits sequentially with rate limiting.

    Uses sequential fetching to properly enforce rate limits and avoid 429 errors.
    Results are cached for 24 hours, so subsequent requests will be fast.
    """
    results: Dict[str, List[Dict[str, Any]]] = {}

    # Fetch sequentially to properly enforce rate limiting
    # The Jolpica API has strict rate limits (~1 req/sec)
    # Only fetch 15 races per circuit - enough for preview stats
    for circuit_id in circuit_ids:
        try:
            results[circuit_id] = _fetch_circuit_results(circuit_id, 15)
        except Exception as e:
            logger.warning(f"Failed to fetch results for circuit {circuit_id}: {e}")
            results[circuit_id] = []

    return results

# Pydantic models for circuit characteristics

class CharacteristicsUpdate(BaseModel):
    """Request model for updating circuit characteristics."""
    effective_year: Optional[int] = None
    full_throttle_pct: Optional[float] = None
    full_throttle_score: Optional[int] = Field(None, ge=1, le=10)
    average_speed_kph: Optional[float] = None
    average_speed_score: Optional[int] = Field(None, ge=1, le=10)
    track_length_km: Optional[float] = None
    tire_degradation_score: Optional[int] = Field(None, ge=1, le=10)
    tire_degradation_label: Optional[str] = None
    track_abrasion_score: Optional[int] = Field(None, ge=1, le=10)
    track_abrasion_label: Optional[str] = None
    corners_slow: Optional[int] = None
    corners_medium: Optional[int] = None
    corners_fast: Optional[int] = None
    downforce_score: Optional[int] = Field(None, ge=1, le=10)
    downforce_label: Optional[str] = None
    overtaking_difficulty_score: Optional[int] = Field(None, ge=1, le=10)
    overtaking_difficulty_label: Optional[str] = None
    drs_zones: Optional[int] = None
    circuit_type: Optional[str] = None
    data_completeness: Optional[str] = None

    @validator('tire_degradation_label', 'track_abrasion_label', 'downforce_label', 'overtaking_difficulty_label')
    def validate_labels(cls, v):
        if v is not None:
            valid = ['Low', 'Medium', 'High', 'Very High', 'Medium-High', 'Medium-Low']
            if v not in valid:
                raise ValueError(f'Label must be one of: {valid}')
        return v

    @validator('circuit_type')
    def validate_circuit_type(cls, v):
        if v is not None and v not in ['Street', 'Permanent', 'Hybrid']:
            raise ValueError('circuit_type must be Street, Permanent, or Hybrid')
        return v

    @validator('data_completeness')
    def validate_completeness(cls, v):
        if v is not None and v not in ['complete', 'partial', 'unknown']:
            raise ValueError('data_completeness must be complete, partial, or unknown')
        return v


def _format_characteristics(char: CircuitCharacteristics) -> Dict[str, Any]:
    """Format characteristics for API response."""
    corners_total = None
    if char.corners_slow is not None or char.corners_medium is not None or char.corners_fast is not None:
        corners_total = (char.corners_slow or 0) + (char.corners_medium or 0) + (char.corners_fast or 0)

    return {
        "effective_year": char.effective_year,
        "data_completeness": char.data_completeness,
        "last_updated": char.last_updated.isoformat() if char.last_updated else None,
        "full_throttle": {
            "value": char.full_throttle_pct,
            "score": char.full_throttle_score
        } if char.full_throttle_pct is not None or char.full_throttle_score is not None else None,
        "average_speed": {
            "value": char.average_speed_kph,
            "score": char.average_speed_score
        } if char.average_speed_kph is not None or char.average_speed_score is not None else None,
        "track_length_km": char.track_length_km,
        "tire_degradation": {
            "score": char.tire_degradation_score,
            "label": char.tire_degradation_label
        } if char.tire_degradation_score is not None else None,
        "track_abrasion": {
            "score": char.track_abrasion_score,
            "label": char.track_abrasion_label
        } if char.track_abrasion_score is not None else None,
        "corners": {
            "slow": char.corners_slow,
            "medium": char.corners_medium,
            "fast": char.corners_fast,
            "total": corners_total
        },
        "downforce": {
            "score": char.downforce_score,
            "label": char.downforce_label
        } if char.downforce_score is not None else None,
        "overtaking": {
            "score": char.overtaking_difficulty_score,
            "label": char.overtaking_difficulty_label
        } if char.overtaking_difficulty_score is not None else None,
        "drs_zones": char.drs_zones,
        "circuit_type": char.circuit_type
    }


def _format_circuit_with_characteristics(circuit: Circuit, char: Optional[CircuitCharacteristics]) -> Dict[str, Any]:
    """Format circuit with characteristics for API response."""
    return {
        "id": circuit.id,
        "name": circuit.name,
        "country": circuit.country,
        "latitude": circuit.latitude,
        "longitude": circuit.longitude,
        "characteristics": _format_characteristics(char) if char else None
    }


def _bust_circuit_cache(circuit_id: int):
    """Invalidate all caches related to a circuit."""
    try:
        # Delete specific circuit caches
        for key in redis_client.scan_iter(f"circuit_chars:{circuit_id}:*"):
            redis_client.delete(key)
        # Delete list cache
        redis_client.delete("circuits_chars:list")
        # Delete comparison caches that might include this circuit
        for key in redis_client.scan_iter("circuits_chars:compare:*"):
            redis_client.delete(key)
        # Delete all ranking caches
        for key in redis_client.scan_iter("circuits_chars:rank:*"):
            redis_client.delete(key)
        logger.info(f"Busted circuit cache for circuit_id={circuit_id}")
    except Exception as e:
        logger.warning(f"Failed to bust circuit cache: {e}")


def _verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> str:
    """Verify admin API key from header."""
    settings = get_settings()
    if not settings.admin_api_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    if not x_admin_key:
        raise HTTPException(status_code=401, detail="X-Admin-Key header required")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return x_admin_key


@router.get("/characteristics")
def list_circuits_with_characteristics(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    List all circuits with their characteristics.

    Returns all circuits from the database with their current characteristics.
    """
    cache_key = "circuits_chars:list"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error for circuits characteristics list: {e}")

    # Query all circuits with their latest characteristics
    circuits = db.query(Circuit).all()

    result = []
    for circuit in circuits:
        # Get the most recent characteristics for this circuit
        char = db.query(CircuitCharacteristics).filter(
            CircuitCharacteristics.circuit_id == circuit.id
        ).order_by(desc(CircuitCharacteristics.effective_year)).first()

        result.append(_format_circuit_with_characteristics(circuit, char))

    payload = {
        "circuits": result,
        "total": len(result)
    }

    try:
        redis_client.setex(cache_key, 3600, json.dumps(payload))  # 1 hour TTL
    except Exception as e:
        logger.warning(f"Redis write error: {e}")

    return payload


@router.get("/characteristics/compare")
def compare_circuits(
    ids: str = Query(..., description="Comma-separated circuit IDs (2-5)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compare characteristics of 2-5 circuits side-by-side.
    """
    circuit_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]

    if len(circuit_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 circuit IDs required")
    if len(circuit_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 circuits for comparison")

    # Sort IDs for consistent cache key
    sorted_ids = sorted(circuit_ids)
    cache_key = f"circuits_chars:compare:{','.join(map(str, sorted_ids))}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error: {e}")

    circuits_data = []
    for cid in circuit_ids:
        circuit = db.query(Circuit).filter(Circuit.id == cid).first()
        if not circuit:
            raise HTTPException(status_code=404, detail=f"Circuit {cid} not found")

        char = db.query(CircuitCharacteristics).filter(
            CircuitCharacteristics.circuit_id == cid
        ).order_by(desc(CircuitCharacteristics.effective_year)).first()

        circuits_data.append({
            "circuit": circuit,
            "characteristics": char
        })

    # Build comparison highlights
    comparison = {}

    # Find highest full throttle
    full_throttle_scores = [(c["circuit"].id, c["characteristics"].full_throttle_score)
                            for c in circuits_data
                            if c["characteristics"] and c["characteristics"].full_throttle_score]
    if full_throttle_scores:
        best = max(full_throttle_scores, key=lambda x: x[1])
        comparison["highest_full_throttle"] = {"circuit_id": best[0], "score": best[1]}

    # Find easiest overtaking
    overtaking_scores = [(c["circuit"].id, c["characteristics"].overtaking_difficulty_score)
                         for c in circuits_data
                         if c["characteristics"] and c["characteristics"].overtaking_difficulty_score]
    if overtaking_scores:
        easiest = min(overtaking_scores, key=lambda x: x[1])
        comparison["easiest_overtaking"] = {"circuit_id": easiest[0], "score": easiest[1]}

    # Find most corners
    corner_totals = []
    for c in circuits_data:
        if c["characteristics"]:
            char = c["characteristics"]
            if char.corners_slow is not None or char.corners_medium is not None or char.corners_fast is not None:
                total = (char.corners_slow or 0) + (char.corners_medium or 0) + (char.corners_fast or 0)
                corner_totals.append((c["circuit"].id, total))
    if corner_totals:
        most = max(corner_totals, key=lambda x: x[1])
        comparison["most_corners"] = {"circuit_id": most[0], "total": most[1]}

    # Find highest downforce
    downforce_scores = [(c["circuit"].id, c["characteristics"].downforce_score)
                        for c in circuits_data
                        if c["characteristics"] and c["characteristics"].downforce_score]
    if downforce_scores:
        highest = max(downforce_scores, key=lambda x: x[1])
        comparison["highest_downforce"] = {"circuit_id": highest[0], "score": highest[1]}

    payload = {
        "circuits": [_format_circuit_with_characteristics(c["circuit"], c["characteristics"])
                    for c in circuits_data],
        "comparison": comparison
    }

    try:
        redis_client.setex(cache_key, 3600, json.dumps(payload))  # 1 hour TTL
    except Exception as e:
        logger.warning(f"Redis write error: {e}")

    return payload




@router.get("/characteristics/rank")
def rank_circuits(
    by: str = Query(..., description="Field to rank by (e.g., full_throttle_score, downforce_score)"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(24, ge=1, le=50, description="Number of results to return"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Rank circuits by a specific characteristic.

    Circuits with null values for the ranked field are excluded.
    """
    valid_fields = [
        "full_throttle_score", "average_speed_score", "tire_degradation_score",
        "track_abrasion_score", "downforce_score", "overtaking_difficulty_score",
        "drs_zones", "track_length_km"
    ]
    if by not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ranking field. Must be one of: {valid_fields}"
        )

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Order must be 'asc' or 'desc'")

    cache_key = f"circuits_chars:rank:{by}:{order}:{limit}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error: {e}")

    # Get the column to rank by
    rank_column = getattr(CircuitCharacteristics, by)

    # Query characteristics with non-null values for the ranked field
    query = db.query(CircuitCharacteristics, Circuit).join(
        Circuit, CircuitCharacteristics.circuit_id == Circuit.id
    ).filter(rank_column.isnot(None))

    # Apply ordering
    if order == "desc":
        query = query.order_by(desc(rank_column))
    else:
        query = query.order_by(rank_column)

    results = query.limit(limit).all()

    ranking = []
    for i, (char, circuit) in enumerate(results, 1):
        value = getattr(char, by)
        ranking.append({
            "rank": i,
            "circuit_id": circuit.id,
            "name": circuit.name,
            "country": circuit.country,
            "value": value,
            "effective_year": char.effective_year
        })

    payload = {
        "ranking": ranking,
        "ranked_by": by,
        "order": order,
        "total": len(ranking)
    }

    try:
        redis_client.setex(cache_key, 3600, json.dumps(payload))  # 1 hour TTL
    except Exception as e:
        logger.warning(f"Redis write error: {e}")

    return payload




@router.get("/characteristics/{circuit_id}")
def get_circuit_characteristics(
    circuit_id: int,
    year: Optional[int] = Query(None, description="Get characteristics for specific layout year"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get characteristics for a specific circuit.

    Optionally specify a year to get historical layout characteristics.
    """
    cache_key = f"circuit_chars:{circuit_id}:{year or 'latest'}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error: {e}")

    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Get characteristics for specified year or most recent
    query = db.query(CircuitCharacteristics).filter(
        CircuitCharacteristics.circuit_id == circuit_id
    )
    if year:
        query = query.filter(CircuitCharacteristics.effective_year == year)
    else:
        query = query.order_by(desc(CircuitCharacteristics.effective_year))

    char = query.first()

    payload = _format_circuit_with_characteristics(circuit, char)

    try:
        redis_client.setex(cache_key, 86400, json.dumps(payload))  # 24 hour TTL
    except Exception as e:
        logger.warning(f"Redis write error: {e}")

    return payload


@router.put("/characteristics/{circuit_id}")
def update_circuit_characteristics(
    circuit_id: int,
    update: CharacteristicsUpdate,
    db: Session = Depends(get_db),
    admin_key: str = Depends(_verify_admin_key),
) -> Dict[str, Any]:
    """
    Update characteristics for a circuit (admin only).

    Requires X-Admin-Key header with valid admin API key.
    """
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    effective_year = update.effective_year or datetime.now(timezone.utc).year

    # Find existing characteristics for this circuit and year
    char = db.query(CircuitCharacteristics).filter(
        CircuitCharacteristics.circuit_id == circuit_id,
        CircuitCharacteristics.effective_year == effective_year
    ).first()

    if not char:
        # Create new record
        char = CircuitCharacteristics(
            circuit_id=circuit_id,
            effective_year=effective_year
        )
        db.add(char)

    # Update fields from request
    update_data = update.dict(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        if field != 'effective_year':  # Don't update effective_year as it's part of the key
            setattr(char, field, value)

    char.last_updated = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(char)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update circuit characteristics: {e}")
        raise HTTPException(status_code=500, detail="Failed to update characteristics")

    # Log the update for audit
    logger.info(f"Circuit {circuit_id} characteristics updated by admin for year {effective_year}")

    # Bust cache
    _bust_circuit_cache(circuit_id)

    return _format_circuit_with_characteristics(circuit, char)





@router.get("/{season}")
def get_circuits(season: int) -> Dict[str, Any]:
    """
    Get all circuits for a season with race information.

    Returns circuit list with round numbers, race names, dates, and preview stats.
    """
    cache_key = f"circuits:v2:{season}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis error for circuits {season}: {e}")

    # Fetch circuits and race schedule
    circuits_raw = _fetch_circuits(season)
    races = _fetch_race_schedule(season)

    # Build circuit_id -> race info mapping
    race_by_circuit: Dict[str, Dict] = {}
    for race in races:
        circuit_id = race.get("Circuit", {}).get("circuitId")
        if circuit_id:
            race_by_circuit[circuit_id] = {
                "round": _safe_int(race.get("round", 0)),
                "race_name": race.get("raceName", ""),
                "date": race.get("date", ""),
            }

    # Get all circuit IDs for parallel fetch
    circuit_ids = [c.get("circuitId", "") for c in circuits_raw if c.get("circuitId")]

    # Fetch all circuit historical results in parallel (cached individually)
    all_circuit_results = _fetch_all_circuit_results_parallel(circuit_ids)

    # Build response with preview stats
    circuits = []
    for circuit in circuits_raw:
        circuit_id = circuit.get("circuitId", "")
        race_info = race_by_circuit.get(circuit_id, {})

        # Compute preview stats from pre-fetched data
        circuit_races = all_circuit_results.get(circuit_id, [])
        preview = _compute_preview_stats_from_races(circuit_races)

        circuits.append({
            "circuit_id": circuit_id,
            "name": circuit.get("circuitName", ""),
            "shortname": get_circuit_shortname(circuit_id),
            "country": circuit.get("Location", {}).get("country", ""),
            "city": circuit.get("Location", {}).get("locality", ""),
            "round": race_info.get("round"),
            "race_name": race_info.get("race_name", ""),
            "date": race_info.get("date", ""),
            "preview": preview,
        })

    # Sort by round number
    circuits.sort(key=lambda c: c.get("round") or 999)

    payload = {
        "season": season,
        "circuits": circuits,
    }

    try:
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception as e:
        logger.warning(f"Redis write error for circuits {season}: {e}")
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
    except Exception as e:
        logger.warning(f"Failed to fetch qualifying for {circuit_id} season {season}: {e}")
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
                round_num = _safe_int(race.get("round", 0))
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
    except Exception as e:
        logger.warning(f"Failed to get strategy patterns for {circuit_id} season {season}: {e}")
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
            "round": _safe_int(current_race.get("round", 0)),
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
                        "year": _safe_int(race.get("season", 0)),
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
                "year": _safe_int(race.get("season", 0)),
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


@router.get("/{season}/{circuit_id}/history")
def get_circuit_history(
    season: int,
    circuit_id: str,
) -> Dict[str, Any]:
    """
    Get previous year's race results for a circuit (for Race Weekend Widget).

    Returns podium, pole position, and fastest lap from the previous season.
    """
    cache_key = f"circuit_history:v1:{season}:{circuit_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    previous_season = season - 1

    # Fetch historical results for this circuit
    historical_races = _fetch_circuit_results(circuit_id, limit=10)

    # Find the previous season's race
    previous_race = None
    for race in historical_races:
        if race.get("season") == str(previous_season):
            previous_race = race
            break

    if not previous_race:
        # Circuit is new or wasn't on calendar last year
        payload = {
            "circuit_id": circuit_id,
            "circuit_name": get_circuit_shortname(circuit_id),
            "previous_year": None,
        }
        # Cache for 7 days (historical data doesn't change)
        redis_client.setex(cache_key, 604800, json.dumps(payload))
        return payload

    results = previous_race.get("Results", [])

    # Get podium
    winner = None
    second = None
    third = None
    if len(results) >= 1:
        w = results[0]
        winner = {
            "driver_code": w.get("Driver", {}).get("code"),
            "driver_name": f"{w.get('Driver', {}).get('givenName', '')} {w.get('Driver', {}).get('familyName', '')}".strip(),
            "team": w.get("Constructor", {}).get("name"),
        }
    if len(results) >= 2:
        s = results[1]
        second = {
            "driver_code": s.get("Driver", {}).get("code"),
            "driver_name": f"{s.get('Driver', {}).get('givenName', '')} {s.get('Driver', {}).get('familyName', '')}".strip(),
            "team": s.get("Constructor", {}).get("name"),
        }
    if len(results) >= 3:
        t = results[2]
        third = {
            "driver_code": t.get("Driver", {}).get("code"),
            "driver_name": f"{t.get('Driver', {}).get('givenName', '')} {t.get('Driver', {}).get('familyName', '')}".strip(),
            "team": t.get("Constructor", {}).get("name"),
        }

    # Get pole position from qualifying
    qual = _fetch_circuit_qualifying(circuit_id, previous_season)
    pole = None
    if qual:
        qual_results = qual.get("QualifyingResults", [])
        if qual_results:
            p = qual_results[0]
            pole = {
                "driver_code": p.get("Driver", {}).get("code"),
                "driver_name": f"{p.get('Driver', {}).get('givenName', '')} {p.get('Driver', {}).get('familyName', '')}".strip(),
                "team": p.get("Constructor", {}).get("name"),
            }

    # Get fastest lap
    fastest_lap = None
    for r in results:
        fl = r.get("FastestLap", {})
        if fl.get("rank") == "1":
            fastest_lap = {
                "driver_code": r.get("Driver", {}).get("code"),
                "driver_name": f"{r.get('Driver', {}).get('givenName', '')} {r.get('Driver', {}).get('familyName', '')}".strip(),
                "time": fl.get("Time", {}).get("time"),
            }
            break

    payload = {
        "circuit_id": circuit_id,
        "circuit_name": get_circuit_shortname(circuit_id),
        "previous_year": {
            "season": previous_season,
            "winner": winner,
            "second": second,
            "third": third,
            "pole": pole,
            "fastest_lap": fastest_lap,
        },
    }

    # Cache for 7 days (historical data doesn't change)
    redis_client.setex(cache_key, 604800, json.dumps(payload))
    return payload


# --- Circuit Characteristics Endpoints -------------------------------------------
