"""
Very thin wrapper around fastf1 for now.
"""

import fastf1
import pandas as pd

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
