"""
Lightweight OpenF1 fallback if FastF1 is missing a session.
"""

from __future__ import annotations

import httpx
import pandas as pd
from functools import lru_cache

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

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        """
        Load lap data from OpenF1.

        Returns DataFrame with columns matching FastF1 format:
        Driver, LapNumber, LapTime, Stint, Compound, PitInTime
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

        # OpenF1 doesn't provide stint/compound in laps endpoint
        # These would need to come from stints endpoint if needed
        df["Stint"] = None
        df["Compound"] = None
        df["PitInTime"] = pd.NaT  # Mark as not available

        # Ensure Driver is string for consistency
        df["Driver"] = df["Driver"].astype(str)

        return df

    def load_telemetry(self):
        """Telemetry not available via OpenF1."""
        return None
