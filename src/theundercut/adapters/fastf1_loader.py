"""
Very thin wrapper around fastf1 for now.
"""
import fastf1
import pandas as pd

from pathlib import Path

from theundercut.config import get_settings

CACHE_DIR = get_settings().fastf1_cache_dir
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))
except Exception:
    CACHE_DIR = Path("/tmp/fastf1_cache")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

class FastF1Provider:
    def __init__(self, season: int, rnd: int):
        self.season, self.rnd = season, rnd
        fastf1.Cache.enable_cache(str(CACHE_DIR))  # works locally & in Render

    def load_laps(self, session_type: str = "Race") -> pd.DataFrame:
        ses = fastf1.get_session(self.season, self.rnd, session_type)
        ses.load()
        return ses.laps

    # placeholder for future telemetry usage
    def load_telemetry(self):
        return None
