# The Undercut

## FastF1 cache path

Both the ingestion jobs and the FastF1 provider expect a writable cache directory at `/data/cache`. In Render this path is backed by the shared disk declared in `render.yaml`; when running locally make sure to either mount a volume to `/data` (e.g., `docker run -v $(pwd)/data:/data …`) or export `FASTF1_CACHE_DIR` and update `theundercut/adapters/fastf1_loader.py` accordingly so the cache can be created.

## API overview

- `GET /api/v1/race/{season}/{round}/laps` – raw lap data (optionally filter by drivers).
- `GET /api/v1/analytics/{season}/{round}` – combined laps, stints, and heuristic driver pace grades returned as JSON with Redis-backed caching (field `driver_pace_grades`).

## Running tests

```bash
source venv/bin/activate
pip install -e '.[dev]'
pytest
```

## CLI commands

- `python -m theundercut.cli sync-calendar --year 2026` – refreshes calendar events from OpenF1/FastF1.
- `python -m theundercut.cli drive-grade run-file data/examples/sample_weekend.json` – runs the Drive Grade pipeline on a JSON weekend or tables directory. Use `--format tables` to force table mode and `--profile baseline` (default) to pick calibration.
- `python -m theundercut.cli drive-grade run-season data/examples --output outputs/demo --profile baseline` – processes every race JSON/directory under the given path (or via `--manifest races.json`) and writes `race_results.csv` plus `season_summary.csv`.
- `python -m theundercut.cli drive-grade calibration import baseline configs/calibration/baseline.json --activate` – seeds the `config.calibration_profiles` table from a JSON file. Use `drive-grade calibration set-active <name>` to flip between stored profiles.

## Calibration profiles

- Default calibration JSON lives under `configs/calibration/`. These files remain the source of truth in Git.
- Store a profile in the database with the CLI command above so API jobs and worker processes pull a consistent configuration.
- When no database row exists (e.g., during local testing), the Drive Grade engine falls back to the JSON files automatically.
