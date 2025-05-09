"""
Very thin wrapper around fastf1 for now.
"""
from pathlib import Path
import fastf1
import pandas as pd

CACHE_DIR = Path("/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)   # ensure directory
fastf1.Cache.enable_cache(str(CACHE_DIR))

class FastF1Provider:
    def __init__(self, season: int, rnd: int):
        self.season, self.rnd = season, rnd
        fastf1.Cache.enable_cache("/data/cache")  # works locally & in Render

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        ses = fastf1.get_session(self.season, self.rnd, session_type)
        ses.load()
        return ses.laps

    # placeholder for future telemetry usage
    def load_telemetry(self):
        return None
