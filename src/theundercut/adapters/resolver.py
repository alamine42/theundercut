"""
Choose FastF1 first; fall back to OpenF1 if FastF1 fails.
"""

from theundercut.adapters.fastf1_loader import FastF1Provider
from theundercut.adapters.openf1_loader import OpenF1Provider

def get_provider(season: int, rnd: int):
    try:
        prov = FastF1Provider(season, rnd)
        # quick smoke test
        prov.load_laps(session_type="Race").head(1)
        return prov
    except Exception as err:
        print(f"[resolver] FastF1 failed ({err}); trying OpenF1")
        return OpenF1Provider(season, rnd)
