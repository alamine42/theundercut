---
date: 2026-03-09
problem_type: integration
component: ingestion
symptoms:
  - "No results found for race" from API
  - Race session status shows "ingested" but results empty
  - Standings work but race results don't display
root_cause: data-source-fallback-missing
severity: high
tags:
  - fastf1
  - openf1
  - ergast
  - race-results
  - ingestion
---

# Race Results Not Stored Despite Successful Ingestion

## Problem

Race results weren't being stored for recent races (e.g., 2026 Australian GP) even though the calendar event was marked as "ingested".

## Symptoms

- `GET /api/v1/race/2026/1/session/race/results` returned `{"detail":"No results found for race"}`
- Calendar event status showed "ingested" for race session
- Standings endpoint worked (using Jolpica API)
- FP1, FP2, FP3, and Qualifying results were stored correctly
- Only race session results were missing

## What Didn't Work

- Checked scheduler logs - scheduler was running correctly
- Verified worker deployment - workers were processing jobs
- Checked Redis connection - REDIS_URL was configured correctly
- Verified CalendarEvent status updates - these were working
- Re-ran mark-ingested admin endpoint - didn't help (data was never stored)

## Solution

Two issues needed fixing:

### 1. FastF1 Returns NaN Positions for Recent Races

FastF1 relies on Ergast API for race classification, but Ergast often lacks data for recent races. When `session.results` returns all-NaN positions, the ingestion silently stored nothing useful.

**Fix in `src/theundercut/services/ingestion.py`:**

```python
# After loading session_results, check if positions are valid
if session_results is not None and not session_results.empty:
    position_col = "Position" if "Position" in session_results.columns else None
    has_valid_positions = False
    if position_col:
        has_valid_positions = session_results[position_col].notna().any()

    if not has_valid_positions:
        logger.info("FastF1 results have no valid positions; trying OpenF1")
        from theundercut.adapters.openf1_loader import OpenF1Provider as OpenF1Loader
        openf1_prov = OpenF1Loader(season, rnd)
        session_results = openf1_prov.load_results(session_type=session_type)
```

### 2. OpenF1 Used Best Lap Time for Race Positions

The OpenF1 loader's `_load_results_from_laps()` was sorting by best lap time to determine positions, which is wrong for race sessions (works for practice, not races).

**Fix in `src/theundercut/adapters/openf1_loader.py`:**

Added `_load_race_results()` method that uses the `/position` endpoint (like qualifying):

```python
def _load_race_results(self, session_key: int, driver_mapping: Dict, session_type: str) -> pd.DataFrame:
    """Load race/sprint results using official position data from OpenF1."""
    r = httpx.get(f"{_API}/position", params={"session_key": session_key}, timeout=_TIMEOUT)
    position_data = r.json()

    # Get final position for each driver (last recorded position)
    final_positions = {}
    for p in position_data:
        driver_num = p.get("driver_number")
        if driver_num is not None:
            final_positions[driver_num] = p.get("position")
    # ... build results DataFrame sorted by position
```

Updated `load_results()` to route race sessions to this new method:

```python
if is_race:
    return self._load_race_results(session_key, driver_mapping, session_type)
```

## Why This Works

1. **FastF1 Fallback**: When Ergast doesn't have classification data (common for races < 24 hours old), the ingestion now falls back to OpenF1 which derives positions from live timing data.

2. **OpenF1 Position Endpoint**: The `/position` endpoint tracks actual race positions throughout the session. The final entry for each driver represents their finishing position, which is the official classification.

## Prevention

1. **Add startup validation for data sources**: Log warnings when external APIs (Ergast) are unreachable or returning incomplete data.

2. **Add integration test**: Test that ingestion handles the case where FastF1 returns empty positions:
   ```python
   def test_ingest_falls_back_when_fastf1_has_no_positions():
       # Mock FastF1 to return NaN positions
       # Verify OpenF1 fallback is used
       # Verify correct positions are stored
   ```

3. **Add monitoring**: Alert when SessionClassification records aren't created after ingestion reports success.

4. **Manual re-ingestion**: Use the new endpoints when automatic ingestion fails:
   - CLI: `theundercut ingest 2026 1 --session Race --force`
   - API: `POST /api/v1/race/2026/1/ingest?session=Race&force=true`

## Related

None
