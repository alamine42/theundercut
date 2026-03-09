"""
Lightweight OpenF1 fallback if FastF1 is missing a session.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, List, Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

_API = "https://api.openf1.org/v1"
_TIMEOUT = 30


@lru_cache(maxsize=8)
def _fetch_sessions(year: int) -> list[dict]:
    """Fetch and cache all sessions for a year."""
    r = httpx.get(f"{_API}/sessions", params={"year": year}, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


# Map our session types to OpenF1 session names
_SESSION_NAME_MAP = {
    "fp1": "Practice 1",
    "fp2": "Practice 2",
    "fp3": "Practice 3",
    "practice_1": "Practice 1",
    "practice_2": "Practice 2",
    "practice_3": "Practice 3",
    "qualifying": "Qualifying",
    "sprint_qualifying": "Sprint Qualifying",
    "sprint": "Sprint",
    "sprint_race": "Sprint",
    "race": "Race",
    # Also support direct OpenF1 names
    "Practice 1": "Practice 1",
    "Practice 2": "Practice 2",
    "Practice 3": "Practice 3",
    "Qualifying": "Qualifying",
    "Sprint Qualifying": "Sprint Qualifying",
    "Sprint": "Sprint",
    "Race": "Race",
}


def _normalize_session_type(session_type: str) -> str:
    """Convert our session type to OpenF1 session name."""
    return _SESSION_NAME_MAP.get(session_type, session_type)


def _get_session_key(year: int, rnd: int, session_type: str = "Race") -> int | None:
    """
    Map (year, round, session_type) to OpenF1 session_key.

    Note: Our calendar stores rounds with pre-season testing as round 1,
    so actual race rounds start at 2. We use meeting_key ranking to match.
    """
    sessions = _fetch_sessions(year)

    # Normalize session type to OpenF1 naming
    openf1_session_name = _normalize_session_type(session_type)

    # Group by meeting_key to determine round numbers
    meetings: dict[int, list[dict]] = {}
    for s in sessions:
        mk = s.get("meeting_key")
        if mk not in meetings:
            meetings[mk] = []
        meetings[mk].append(s)

    # Sort meeting keys and find the one matching our round
    sorted_keys = sorted(meetings.keys())
    if rnd < 1 or rnd > len(sorted_keys):
        return None

    target_meeting_key = sorted_keys[rnd - 1]

    # Find the session matching the type within this meeting
    for s in meetings[target_meeting_key]:
        if s.get("session_name") == openf1_session_name:
            return s.get("session_key")

    return None


class OpenF1Provider:
    def __init__(self, season: int, rnd: int):
        self.season = season
        self.rnd = rnd
        self._session_cache: dict[str, int | None] = {}

    def _get_session_key(self, session_type: str) -> int | None:
        """Get session_key for the given session type, with caching."""
        if session_type not in self._session_cache:
            self._session_cache[session_type] = _get_session_key(
                self.season, self.rnd, session_type
            )
        return self._session_cache[session_type]

    def load_stints(self, session_type: str = "Race") -> pd.DataFrame:
        """
        Load stint data from OpenF1.

        Returns DataFrame with columns:
        driver_number, stint_number, lap_start, lap_end, compound, tyre_age_at_start
        """
        session_key = self._get_session_key(session_type)
        if session_key is None:
            return pd.DataFrame()

        r = httpx.get(
            f"{_API}/stints",
            params={"session_key": session_key},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    def _get_driver_mapping(self, session_key: int) -> Dict[str, Dict[str, str]]:
        """
        Fetch driver mapping from OpenF1.

        Returns dict: {driver_number: {"abbreviation": "VER", "name": "Max VERSTAPPEN", "team": "Red Bull"}}
        """
        try:
            r = httpx.get(
                f"{_API}/drivers",
                params={"session_key": session_key},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            drivers = {}
            for d in r.json():
                num = str(d.get("driver_number", ""))
                drivers[num] = {
                    "abbreviation": d.get("name_acronym", num),
                    "name": d.get("full_name") or d.get("broadcast_name", ""),
                    "team": d.get("team_name", ""),
                }
            return drivers
        except Exception as e:
            logger.warning("Failed to fetch driver mapping: %s", e)
            return {}

    def load_laps(self, session_type: str = "Race", enrich_stints: bool = True) -> pd.DataFrame:
        """
        Load lap data from OpenF1.

        Returns DataFrame with columns matching FastF1 format:
        Driver, LapNumber, LapTime, Stint, Compound, PitInTime, Team

        Args:
            session_type: Session to load (Race, Qualifying, etc.)
            enrich_stints: If True, fetch stint data and add Stint/Compound columns
        """
        session_key = self._get_session_key(session_type)
        if session_key is None:
            return pd.DataFrame()

        r = httpx.get(
            f"{_API}/laps",
            params={"session_key": session_key},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Get driver mapping (number -> abbreviation, name, team)
        driver_mapping = self._get_driver_mapping(session_key)

        # Keep original driver number for mapping
        df["DriverNumber"] = df["driver_number"].astype(str)

        # Map driver number to abbreviation
        df["Driver"] = df["DriverNumber"].map(
            lambda x: driver_mapping.get(x, {}).get("abbreviation", x)
        )

        # Add team column from driver mapping
        df["Team"] = df["DriverNumber"].map(
            lambda x: driver_mapping.get(x, {}).get("team", "")
        )

        # Rename other columns to FastF1-compatible names
        df = df.rename(columns={
            "lap_number": "LapNumber",
            "lap_duration": "LapTime",
        })

        # Convert lap duration (seconds) to timedelta
        if "LapTime" in df.columns:
            df["LapTime"] = pd.to_timedelta(df["LapTime"], unit="s")

        # Ensure Driver is string for consistency
        df["Driver"] = df["Driver"].astype(str)

        # Enrich with stint data if requested
        if enrich_stints:
            stints_df = self.load_stints(session_type)
            if not stints_df.empty:
                stint_map = self._build_stint_map(stints_df)
                df["Stint"] = df.apply(
                    lambda row: stint_map.get((str(row["Driver"]), row["LapNumber"]), {}).get("stint"),
                    axis=1
                )
                df["Compound"] = df.apply(
                    lambda row: stint_map.get((str(row["Driver"]), row["LapNumber"]), {}).get("compound"),
                    axis=1
                )
            else:
                df["Stint"] = None
                df["Compound"] = None
        else:
            df["Stint"] = None
            df["Compound"] = None

        df["PitInTime"] = pd.NaT  # Mark as not available

        return df

    def load_results(self, session_type: str = "Race") -> pd.DataFrame:
        """
        Load session results from OpenF1.

        For qualifying/race/sprint: Uses official position data from the /position endpoint.
        For practice: Uses lap data with best lap time to determine position.
        Returns DataFrame with columns matching FastF1 format.
        """
        session_key = self._get_session_key(session_type)
        if session_key is None:
            return pd.DataFrame()

        # Get driver mapping
        driver_mapping = self._get_driver_mapping(session_key)

        # For qualifying, race, and sprint sessions, use the official position data
        normalized_type = _normalize_session_type(session_type)
        is_qualifying = "qualifying" in normalized_type.lower()
        is_race = normalized_type.lower() in ("race", "sprint")

        if is_qualifying:
            return self._load_qualifying_results(session_key, driver_mapping)

        if is_race:
            return self._load_race_results(session_key, driver_mapping, session_type)

        # For practice, derive from lap data (best lap time)
        return self._load_results_from_laps(session_key, driver_mapping, session_type)

    def _load_qualifying_results(self, session_key: int, driver_mapping: Dict) -> pd.DataFrame:
        """Load qualifying results using official position data from OpenF1."""
        try:
            r = httpx.get(
                f"{_API}/position",
                params={"session_key": session_key},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            position_data = r.json()
        except Exception as e:
            logger.warning("Failed to fetch position data: %s", e)
            return pd.DataFrame()

        if not position_data:
            return pd.DataFrame()

        # Get the final position for each driver (last recorded position)
        final_positions = {}
        for p in position_data:
            driver_num = p.get("driver_number")
            if driver_num is not None:
                # Keep updating - last entry is the final position
                final_positions[driver_num] = p.get("position")

        # Load lap data for Q1/Q2/Q3 times
        laps_df = self.load_laps("Qualifying", enrich_stints=False)
        lap_times_by_driver = {}
        if not laps_df.empty:
            for driver_num in laps_df["DriverNumber"].unique():
                driver_laps = laps_df[laps_df["DriverNumber"] == driver_num]
                valid_laps = driver_laps[driver_laps["LapTime"].notna()]
                if not valid_laps.empty:
                    best_lap = valid_laps.loc[valid_laps["LapTime"].idxmin()]
                    lap_times_by_driver[driver_num] = best_lap["LapTime"]

        # Build results
        results = []
        for driver_num, position in final_positions.items():
            driver_info = driver_mapping.get(str(driver_num), {})
            results.append({
                "Driver": driver_num,
                "Abbreviation": driver_info.get("abbreviation", str(driver_num)),
                "FirstName": driver_info.get("name", "").split()[0] if driver_info.get("name") else "",
                "LastName": " ".join(driver_info.get("name", "").split()[1:]) if driver_info.get("name") else "",
                "TeamName": driver_info.get("team", ""),
                "Position": position,
                "Time": lap_times_by_driver.get(driver_num),
            })

        results_df = pd.DataFrame(results)
        if not results_df.empty:
            results_df = results_df.sort_values(by="Position", na_position="last")

        return results_df

    def _load_race_results(self, session_key: int, driver_mapping: Dict, session_type: str) -> pd.DataFrame:
        """Load race/sprint results using official position data from OpenF1."""
        try:
            r = httpx.get(
                f"{_API}/position",
                params={"session_key": session_key},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            position_data = r.json()
        except Exception as e:
            logger.warning("Failed to fetch position data for race: %s", e)
            # Fall back to lap-based positions
            return self._load_results_from_laps(session_key, driver_mapping, session_type)

        if not position_data:
            return self._load_results_from_laps(session_key, driver_mapping, session_type)

        # Get the final position for each driver (last recorded position)
        final_positions = {}
        for p in position_data:
            driver_num = p.get("driver_number")
            if driver_num is not None:
                # Keep updating - last entry is the final position
                final_positions[driver_num] = p.get("position")

        # Load lap data for lap counts and best times
        laps_df = self.load_laps(session_type, enrich_stints=False)
        laps_by_driver = {}
        times_by_driver = {}
        if not laps_df.empty:
            for driver_num_str in laps_df["DriverNumber"].unique():
                driver_laps = laps_df[laps_df["DriverNumber"] == driver_num_str]
                # Convert to int for matching with position data
                try:
                    driver_num_int = int(driver_num_str)
                except (ValueError, TypeError):
                    continue
                laps_by_driver[driver_num_int] = len(driver_laps)
                valid_laps = driver_laps[driver_laps["LapTime"].notna()]
                if not valid_laps.empty:
                    best_lap = valid_laps.loc[valid_laps["LapTime"].idxmin()]
                    times_by_driver[driver_num_int] = best_lap["LapTime"]

        # Build results
        results = []
        for driver_num, position in final_positions.items():
            driver_info = driver_mapping.get(str(driver_num), {})
            results.append({
                "Driver": driver_num,
                "Abbreviation": driver_info.get("abbreviation", str(driver_num)),
                "FirstName": driver_info.get("name", "").split()[0] if driver_info.get("name") else "",
                "LastName": " ".join(driver_info.get("name", "").split()[1:]) if driver_info.get("name") else "",
                "TeamName": driver_info.get("team", ""),
                "Position": position,
                "Time": times_by_driver.get(driver_num),
                "LapsCompleted": laps_by_driver.get(driver_num, 0),
            })

        results_df = pd.DataFrame(results)
        if not results_df.empty:
            results_df = results_df.sort_values(by="Position", na_position="last")

        return results_df

    def _load_results_from_laps(self, session_key: int, driver_mapping: Dict, session_type: str) -> pd.DataFrame:
        """Load results by deriving positions from lap times (for practice sessions)."""
        laps_df = self.load_laps(session_type, enrich_stints=False)
        if laps_df.empty:
            return pd.DataFrame()

        # Group by driver and get best lap
        results = []
        for driver_num in laps_df["DriverNumber"].unique():
            driver_laps = laps_df[laps_df["DriverNumber"] == driver_num]
            driver_info = driver_mapping.get(str(driver_num), {})

            # Get best lap time
            valid_laps = driver_laps[driver_laps["LapTime"].notna()]
            if not valid_laps.empty:
                best_lap = valid_laps.loc[valid_laps["LapTime"].idxmin()]
                best_time = best_lap["LapTime"]
            else:
                best_time = None

            results.append({
                "Driver": driver_num,
                "Abbreviation": driver_info.get("abbreviation", str(driver_num)),
                "FirstName": driver_info.get("name", "").split()[0] if driver_info.get("name") else "",
                "LastName": " ".join(driver_info.get("name", "").split()[1:]) if driver_info.get("name") else "",
                "TeamName": driver_info.get("team", ""),
                "Time": best_time,
                "LapsCompleted": len(driver_laps),
            })

        # Sort by best time to determine position
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(
            by="Time",
            na_position="last",
            key=lambda x: x.apply(lambda t: t.total_seconds() if pd.notna(t) else float("inf"))
        )
        results_df["Position"] = range(1, len(results_df) + 1)

        return results_df

    def _build_stint_map(self, stints_df: pd.DataFrame) -> Dict[tuple, dict]:
        """
        Build a lookup map from (driver, lap) -> {stint, compound}.
        """
        stint_map: Dict[tuple, dict] = {}
        for _, row in stints_df.iterrows():
            driver = str(row["driver_number"])
            stint_no = row["stint_number"]
            compound = row.get("compound")
            lap_start = row.get("lap_start", 1)
            lap_end = row.get("lap_end")

            if lap_end is None:
                lap_end = lap_start + 100  # Assume long stint if no end

            for lap in range(int(lap_start), int(lap_end) + 1):
                stint_map[(driver, lap)] = {"stint": stint_no, "compound": compound}

        return stint_map

    def get_stints_for_db(self, session_type: str = "Race") -> List[dict]:
        """
        Get stint data formatted for database insertion.

        Returns list of dicts with: driver, stint_no, compound, laps
        """
        stints_df = self.load_stints(session_type)
        if stints_df.empty:
            return []

        # Get driver mapping (number -> abbreviation)
        session_key = self._get_session_key(session_type)
        if session_key is None:
            return []

        try:
            r = httpx.get(
                f"{_API}/drivers",
                params={"session_key": session_key},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            drivers = {str(d["driver_number"]): d["name_acronym"] for d in r.json()}
        except Exception as e:
            logger.warning("Failed to fetch driver mapping: %s", e)
            drivers = {}

        result = []
        for _, row in stints_df.iterrows():
            driver_num = str(row["driver_number"])
            driver = drivers.get(driver_num, driver_num[:3])
            lap_start = row.get("lap_start", 1)
            lap_end = row.get("lap_end", lap_start)
            laps = int(lap_end) - int(lap_start) + 1 if lap_end else 1

            result.append({
                "driver": driver,
                "stint_no": row["stint_number"],
                "compound": row.get("compound"),
                "laps": laps,
            })

        return result

    def load_telemetry(self):
        """Telemetry not available via OpenF1."""
        return None
