# T6 – Ingestion-integrated Drive Grades

_Last updated: February 11, 2026_

## Goal
Compute real Drive Grade metrics automatically after each race ingestion so `/api/v1/analytics` (and future UI) serve DB-backed `core.driver_metrics` rows instead of heuristics.

## Source Data
- `lap_times` and `stints` (already populated). Need tire compounds, pit info, pace baselines.
- New tables from migration (`core.entries`, `core.driver_metrics`, `core.strategy_events`, `core.penalty_events`, `core.overtake_events`). We must populate entries + strategy/penalty/overtake inputs per race.
- Calibration profile: load from `config.calibration_profiles` via `theundercut.drive_grade.calibration_store.fetch_profile_from_db` before running the pipeline.

## Proposed Flow
1. **Expand ingestion step** inside `ingest_session`:
   - After storing laps/stints, fetch raw race context (driver/team, grid, finish, strategy, penalties, overtakes) using Drive Grade providers.
   - Compose `DriverRaceInput` objects using either `FastF1Provider.fetch_weekend` or `OpenF1Provider.fetch_weekend` (already returns drive-grade-friendly JSON).
2. **Persist intermediate tables**
   - Write driver/team/entry metadata into `core.entries` and `core.races`/`core.drivers` (if not yet present).
   - Insert strategy/penalty/overtake events into corresponding tables for transparency + future reuse.
3. **Run Drive Grade pipeline in-process**
   - Convert the provider JSON to `DriverRaceInput` (using existing `load_weekend_file` or by adapting provider output).
   - Instantiate `DriveGradePipeline` with the active calibration profile and compute `DriveGradeBreakdown` per driver.
4. **Persist grades**
   - Map each driver to the `entries.id` row and insert into `core.driver_metrics` (using SQLAlchemy ORM or bulk insert). Include component scores and total grade.
   - Update `CalendarEvent.status` to `ingested` and optionally set `core.driver_metrics.created_at` for tracking.
5. **Cache invalidation / API**
   - After metrics are stored, clear the relevant Redis analytics cache key so `/api/v1/analytics` picks up the new `driver_pace_grades` (which will later read from `core.driver_metrics`).

## Implementation Steps
1. **Provider integration**
   - Add helper in `services/ingestion.py` that calls `FastF1Provider.fetch_weekend` (fallback to `OpenF1Provider`) and returns a normalized dict.
   - Reuse Drive Grade providers via the new `theundercut.core.providers` if possible, or adapt to match the JSON schema expected by `DriveGradePipeline`.
2. **Entry & reference data**
   - Write helper to upsert `core.seasons`, `core.races`, `core.drivers`, `core.teams`, and `core.entries` based on provider metadata.
   - Use race slug `f"{season}-{round}"` for now; update when richer metadata exists.
3. **Strategy/Penalty/Overtake tables**
   - Transliterate provider JSON fields into the normalized tables (actual/optimal pit laps, penalties, overtake contexts). Use race `entry_id` as FK.
4. **Drive Grade execution**
   - Convert provider JSON into `DriverRaceInput` objects via a new helper (similar to `data_loader.load_driver_inputs_from_json`). Run the pipeline and collect `DriveGradeBreakdown`s.
   - Insert into `core.driver_metrics` with calibration profile name and `data_source` (fastf1/openf1).
5. **Testing**
   - Add fixtures to seed `core.*` tables and run ingestion logic in SQLite to ensure the new data surfaces.
   - Add end-to-end test that mocks provider output → ingestion job → driver_metrics row.

## Follow-up
- Later, decouple ingestion-grade pipeline into an RQ job triggered after ingestion (to avoid long-running sync jobs).
- Update `/api/v1/analytics` to read `driver_metrics` instead of computing scores on the fly.
- Expand strategy/penalty extraction by incorporating steward reports and telemetry heuristics.
