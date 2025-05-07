"""
Lightweight OpenF1 fallback if FastF1 is missing a session.
"""

import httpx, pandas as pd

_API = "https://api.openf1.org/v1"

class OpenF1Provider:
    def __init__(self, season: int, rnd: int):
        self.season, self.rnd = season, rnd

    def _get(self, path: str):
        r = httpx.get(f"{_API}/{path}", params={"year": self.season, "round_number": self.rnd}, timeout=30)
        r.raise_for_status()
        return r.json()

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        data = self._get("laps")
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data).rename(
            columns={"driver_number": "Driver", "lap_number": "LapNumber", "lap_time": "LapTime", "stint_number": "Stint", "compound": "Compound"}
        )
        df["LapTime"] = pd.to_timedelta(df["LapTime"])
        return df

    def load_telemetry(self):
        return None
