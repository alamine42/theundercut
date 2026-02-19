"""
Homepage data service.

Provides data for the homepage dashboard: current season, latest race info,
podium finishers, and standings summary.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_current_season(db: Session) -> int:
    """
    Determine the current/latest season with data.

    Returns the most recent season that has lap_times data,
    defaulting to 2024 if no data found.
    """
    # Use SUBSTR for SQLite compatibility (works in PostgreSQL too)
    result = db.execute(text("""
        SELECT DISTINCT CAST(SUBSTR(race_id, 1, 4) AS INTEGER) as season
        FROM lap_times
        ORDER BY season DESC
        LIMIT 1
    """))
    row = result.fetchone()
    return row[0] if row else 2024


def get_latest_race(db: Session, season: int) -> Optional[Dict[str, Any]]:
    """
    Get the most recent completed race for a season.

    Returns:
        {
            "race_id": "2025-12",
            "round": 12,
            "name": "British Grand Prix",
            "date": "2025-07-06"
        }
    """
    # Find the highest round with lap_times data
    # Use SUBSTR for portability: extract round number after the dash
    result = db.execute(text("""
        SELECT
            lt.race_id,
            CAST(SUBSTR(lt.race_id, 6) AS INTEGER) as round,
            ce.meeting_key
        FROM lap_times lt
        LEFT JOIN calendar_events ce
            ON ce.season = :season
            AND ce.round = CAST(SUBSTR(lt.race_id, 6) AS INTEGER)
            AND ce.session_type = 'Race'
        WHERE lt.race_id LIKE :pattern
        GROUP BY lt.race_id, ce.meeting_key
        ORDER BY round DESC
        LIMIT 1
    """), {"season": season, "pattern": f"{season}-%"})

    row = result.fetchone()
    if not row:
        return None

    race_id = row[0]
    round_num = row[1]

    # Get race name from OpenF1 meeting data or use fallback
    race_name = _get_race_name(db, season, round_num)

    return {
        "race_id": race_id,
        "round": round_num,
        "name": race_name,
        "season": season,
    }


def _get_race_name(db: Session, season: int, round_num: int) -> str:
    """Get human-readable race name for a round."""
    # Map of known race names by meeting_key or round
    # This is a simplified approach - could be enhanced with a proper mapping table
    race_names = {
        # 2024 season
        (2024, 1): "Bahrain Grand Prix",
        (2024, 2): "Saudi Arabian Grand Prix",
        (2024, 3): "Australian Grand Prix",
        (2024, 4): "Japanese Grand Prix",
        (2024, 5): "Chinese Grand Prix",
        (2024, 6): "Miami Grand Prix",
        (2024, 7): "Emilia Romagna Grand Prix",
        (2024, 8): "Monaco Grand Prix",
        (2024, 9): "Canadian Grand Prix",
        (2024, 10): "Spanish Grand Prix",
        (2024, 11): "Austrian Grand Prix",
        (2024, 12): "British Grand Prix",
        (2024, 13): "Hungarian Grand Prix",
        (2024, 14): "Belgian Grand Prix",
        (2024, 15): "Dutch Grand Prix",
        (2024, 16): "Italian Grand Prix",
        (2024, 17): "Azerbaijan Grand Prix",
        (2024, 18): "Singapore Grand Prix",
        (2024, 19): "United States Grand Prix",
        (2024, 20): "Mexico City Grand Prix",
        (2024, 21): "São Paulo Grand Prix",
        (2024, 22): "Las Vegas Grand Prix",
        (2024, 23): "Qatar Grand Prix",
        (2024, 24): "Abu Dhabi Grand Prix",
        # 2025 season
        (2025, 1): "Australian Grand Prix",
        (2025, 2): "Chinese Grand Prix",
        (2025, 3): "Japanese Grand Prix",
        (2025, 4): "Bahrain Grand Prix",
        (2025, 5): "Saudi Arabian Grand Prix",
        (2025, 6): "Miami Grand Prix",
        (2025, 7): "Emilia Romagna Grand Prix",
        (2025, 8): "Monaco Grand Prix",
        (2025, 9): "Spanish Grand Prix",
        (2025, 10): "Canadian Grand Prix",
        (2025, 11): "Austrian Grand Prix",
        (2025, 12): "British Grand Prix",
        (2025, 13): "Belgian Grand Prix",
        (2025, 14): "Hungarian Grand Prix",
        (2025, 15): "Dutch Grand Prix",
        (2025, 16): "Italian Grand Prix",
        (2025, 17): "Azerbaijan Grand Prix",
        (2025, 18): "Singapore Grand Prix",
        (2025, 19): "United States Grand Prix",
        (2025, 20): "Mexico City Grand Prix",
        (2025, 21): "São Paulo Grand Prix",
        (2025, 22): "Las Vegas Grand Prix",
        (2025, 23): "Qatar Grand Prix",
        (2025, 24): "Abu Dhabi Grand Prix",
    }
    return race_names.get((season, round_num), f"Round {round_num}")


def get_podium(db: Session, race_id: str) -> List[Dict[str, Any]]:
    """
    Get podium finishers (P1, P2, P3) for a race.

    Uses lap count to determine finishing positions (most laps = higher position,
    ties broken by total race time approximation via lap times).

    Returns:
        [
            {"position": 1, "driver": "VER", "team": "Red Bull"},
            {"position": 2, "driver": "NOR", "team": "McLaren"},
            {"position": 3, "driver": "LEC", "team": "Ferrari"},
        ]
    """
    # Get finishing order by counting laps completed and total time
    result = db.execute(text("""
        WITH driver_stats AS (
            SELECT
                driver,
                COUNT(*) as laps_completed,
                SUM(lap_ms) as total_time_ms
            FROM lap_times
            WHERE race_id = :race_id AND lap_ms IS NOT NULL
            GROUP BY driver
        )
        SELECT
            driver,
            laps_completed,
            total_time_ms
        FROM driver_stats
        ORDER BY laps_completed DESC, total_time_ms ASC
        LIMIT 3
    """), {"race_id": race_id})

    rows = result.fetchall()

    podium = []
    for i, row in enumerate(rows):
        driver_code = row[0]
        team = _get_team_for_driver(driver_code, race_id)
        podium.append({
            "position": i + 1,
            "driver": driver_code,
            "team": team,
        })

    return podium


def _get_team_for_driver(driver_code: str, race_id: str) -> str:
    """Map driver code to team name."""
    # Extract season from race_id
    season = int(race_id.split("-")[0])

    # Team mappings by season
    teams_2024 = {
        "VER": "Red Bull", "PER": "Red Bull",
        "HAM": "Mercedes", "RUS": "Mercedes",
        "LEC": "Ferrari", "SAI": "Ferrari", "BEA": "Ferrari",
        "NOR": "McLaren", "PIA": "McLaren",
        "ALO": "Aston Martin", "STR": "Aston Martin",
        "OCO": "Alpine", "GAS": "Alpine",
        "TSU": "RB", "RIC": "RB", "LAW": "RB",
        "BOT": "Sauber", "ZHO": "Sauber",
        "MAG": "Haas", "HUL": "Haas",
        "ALB": "Williams", "SAR": "Williams", "COL": "Williams",
    }

    teams_2025 = {
        "VER": "Red Bull", "LAW": "Red Bull",
        "RUS": "Mercedes", "ANT": "Mercedes",
        "LEC": "Ferrari", "HAM": "Ferrari",
        "NOR": "McLaren", "PIA": "McLaren",
        "ALO": "Aston Martin", "STR": "Aston Martin",
        "GAS": "Alpine", "DOO": "Alpine",
        "TSU": "RB", "HAD": "RB",
        "BOR": "Sauber", "HUL": "Sauber",
        "BEA": "Haas", "OCO": "Haas",
        "ALB": "Williams", "SAI": "Williams", "COL": "Williams",
    }

    if season >= 2025:
        return teams_2025.get(driver_code, "Unknown")
    return teams_2024.get(driver_code, "Unknown")


def get_homepage_data(db: Session) -> Dict[str, Any]:
    """
    Fetch all data needed for the homepage in a single call.

    Returns:
        {
            "season": 2025,
            "latest_race": {...},
            "podium": [...],
        }
    """
    season = get_current_season(db)
    latest_race = get_latest_race(db, season)

    podium = []
    if latest_race:
        podium = get_podium(db, latest_race["race_id"])

    return {
        "season": season,
        "latest_race": latest_race,
        "podium": podium,
    }
