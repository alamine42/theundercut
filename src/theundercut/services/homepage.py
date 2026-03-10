"""
Homepage data service.

Provides data for the homepage dashboard: current season, latest race info,
podium finishers, and standings summary.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from theundercut.models import Race, Season, Entry, Driver, Team


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
    """Get human-readable race name for a round from the database."""
    race = (
        db.query(Race)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season, Race.round_number == round_num)
        .first()
    )
    if race and race.slug:
        return race.slug.replace("-", " ").title()
    return f"Round {round_num}"


def _parse_race_id(race_id: str) -> Tuple[int, int]:
    season_str, round_str = race_id.split("-", maxsplit=1)
    return int(season_str), int(round_str)


def _get_driver_team_map(db: Session, race_id: str) -> Dict[str, str]:
    """Return mapping of driver codes to team names for a given race."""
    try:
        season_value, round_value = _parse_race_id(race_id)
    except ValueError:
        return {}

    race = (
        db.query(Race)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season_value, Race.round_number == round_value)
        .first()
    )
    if not race:
        return {}

    rows = (
        db.query(Driver.code, Team.name)
        .join(Entry, Entry.driver_id == Driver.id)
        .join(Team, Entry.team_id == Team.id)
        .filter(Entry.race_id == race.id)
        .all()
    )
    return {code: team or "Unknown" for code, team in rows}


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
    team_map = _get_driver_team_map(db, race_id)
    podium = []
    for i, row in enumerate(rows):
        driver_code = row[0]
        team = team_map.get(driver_code, "Unknown")
        podium.append({
            "position": i + 1,
            "driver": driver_code,
            "team": team,
        })

    return podium


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
