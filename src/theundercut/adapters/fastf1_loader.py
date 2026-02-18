"""
Very thin wrapper around fastf1 for now.
"""
import logging
from pathlib import Path

import fastf1
import pandas as pd

from theundercut.config import get_settings
from theundercut.utils.timeout import run_with_timeout, TimeoutError, FASTF1_TIMEOUT

logger = logging.getLogger(__name__)

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
        def _load() -> pd.DataFrame:
            ses = fastf1.get_session(self.season, self.rnd, session_type)
            ses.load()
            return ses.laps

        try:
            return run_with_timeout(
                _load,
                timeout=FASTF1_TIMEOUT,
                description=f"FastF1 load_laps({self.season}, {self.rnd}, {session_type})",
            )
        except TimeoutError:
            logger.warning(
                "FastF1 timed out loading laps for %d round %d",
                self.season,
                self.rnd,
            )
            raise

    # placeholder for future telemetry usage
    def load_telemetry(self):
        return None
