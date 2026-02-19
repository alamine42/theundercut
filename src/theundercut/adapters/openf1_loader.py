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


def _get_session_key(year: int, rnd: int, session_type: str = "Race") -> int | None:
    """
    Map (year, round, session_type) to OpenF1 session_key.

    Note: Our calendar stores rounds with pre-season testing as round 1,
    so actual race rounds start at 2. We use meeting_key ranking to match.
    """
    sessions = _fetch_sessions(year)

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
        if s.get("session_name") == session_type:
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

    def load_laps(self, session_type: str = "Race", enrich_stints: bool = True) -> pd.DataFrame:
        """
        Load lap data from OpenF1.

        Returns DataFrame with columns matching FastF1 format:
        Driver, LapNumber, LapTime, Stint, Compound, PitInTime

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

        # Map OpenF1 columns to FastF1-compatible names
        df = df.rename(columns={
            "driver_number": "Driver",
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
