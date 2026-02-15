# Drive Grade Merge Plan

_Last updated: February 11, 2026_

## Objectives
- Combine the data-rich scoring engine from `~/Development/f1-drive-grade` with The Undercut's ingestion, API, and deployment stack.
- Preserve Drive Grade's calibration assets, validation tooling, and documentation while avoiding duplicated provider/ingestion code.
- Deliver race-day driver pace grades through The Undercut's `/api/v1/analytics` surface and future dashboards.

## Current State Summary
- **The Undercut** already handles FastF1/OpenF1 ingestion, stores laps/stints in Postgres, schedules jobs, and serves basic web/API endpoints.
- **F1 Drive Grade** contains the scoring pipeline (`src/f1_drive_grade`), calibration configs, CLI scripts, and documentation for computing 0–100 driver/team grades.
- Both repos reference similar schemas; Drive Grade's `docs/integration_architecture.md` defines the desired shared model (`core.*` tables, calibration profiles, validation metrics).

## Proposed Merge Approach

### 1. Create a Shared Core Package
- Move the existing `undercut_core` package (currently inside `f1-drive-grade`) into The Undercut repo under `src/theundercut/core`.
- Expose provider abstractions (FastF1/OpenF1 loaders), schema constants, and shared utilities from this core module.
- Update both ingestion jobs and the Drive Grade engine (once migrated) to import from the shared package.

### 2. Align Database Schema
- Extend The Undercut's Alembic migrations to add the Drive Grade tables described in `docs/database_schema.md`: `core.driver_metrics`, `core.strategy_events`, `core.penalty_events`, `core.overtake_events`, plus optional reference tables (`core.seasons`, `core.races`, `core.entries`).
- Add a `config.calibration_profiles` table and `validation.*` tables for expert comparisons.
- Backfill existing lap/stint data to populate `core.entries` and related reference rows by joining Calendar events + driver metadata.

### 3. Import the Drive Grade Engine
- Copy `src/f1_drive_grade` (and required configs/scripts) into The Undercut at `src/theundercut/drive_grade`.
- Preserve CLI entrypoints by wiring Typer commands inside `theundercut.cli` (e.g., `drive-grade run-race`, `drive-grade calibrate`).
- Keep calibration JSON/profiles under `configs/calibration/` inside the repo and load them via the new DB-backed table going forward.

### 4. Orchestrate the Combined Pipeline
- Extend `scheduler.py` to enqueue a `compute_drive_grade` RQ job once `ingest_session` completes for a race (status `ingested`).
- Implement the job to:
  1. Load the race's normalized data from Postgres (or parquet dumps) using the Drive Grade engine.
  2. Run the scoring modules (consistency, racecraft, penalties, strategy).
  3. Persist results into `core.driver_metrics` and export CSV summaries under `outputs/<season>/<round>/` for analysts.
  4. Emit validation metrics by comparing against finishing positions/external ranks when available.

### 5. Update APIs/Web Experience
- Expand `/api/v1/analytics` (or add `/api/v1/grades`) to serve the computed driver pace/grade components directly from `core.driver_metrics` instead of the current heuristic.
- Build HTMX/React components that visualize the grade breakdowns using the same endpoint.
- Document data contracts so future clients can trust the schema.

### 6. Decommission Standalone Repo
- Once the Drive Grade engine, configs, and docs are merged, archive the `f1-drive-grade` repo or keep it as a mirror pointing to The Undercut.
- Move remaining docs (`drive_grade_model.md`, `pipeline_usage.md`, `expert_rankings.md`) into The Undercut's `docs/` directory.

## Workstream Breakdown

| Workstream | Key Tasks |
| --- | --- |
| **Schema** | Author Alembic migration for new tables, seed reference data, add ORM models. |
| **Core Package** | Relocate `undercut_core`, adjust imports, publish as local package. |
| **Engine Migration** | Copy scoring modules, calibration configs, tests; integrate with Typer CLI. |
| **Pipeline Orchestration** | Add RQ job + scheduler hook, implement grade writer + validation logging. |
| **API/UI Integration** | Serve real grade data via API, update frontend components. |
| **Docs & Ops** | Consolidate docs, update README/architecture diagrams, plan CI coverage.

## Dependencies & Risks
- Requires Postgres schema migration and possible data backfill; plan for downtime or run migrations off-hours.
- Drive Grade engine expects various input tables (strategy, penalties, overtakes) that The Undercut does not currently populate; prioritize ingestion enhancements before flipping to the new engine.
- Calibration profiles live in JSON files today; ensure they are versioned and auditable once stored in DB.
- Validation data (expert rankings) may contain PII or paid sources; respect licensing when importing.

## Immediate Next Steps
1. Add this plan to the repo (done) and align the team on phases. ✅
2. Spike on the schema migration (design Alembic scripts, update ORM models). ✅ (migration drafted as `5b1ed8f6a828`)
3. Decide whether to keep Drive Grade as a submodule or fully absorb its source; update tasks accordingly. ➡️ _Decision: absorb source; initial copy placed under `src/theundercut/drive_grade` (dependencies/calibration wiring still pending)._
4. Begin extracting `undercut_core` into The Undercut so both repos share provider logic until the full merge is complete. ✅ (core providers added under `src/theundercut/core`)

### Follow-up Tasks After Initial Import
- [x] Wire Typer/CLI commands in `theundercut.cli` to call the Drive Grade pipeline (`pipeline.py`, `scripts/run_*` equivalents).
- [x] Sync calibration profiles + configs from `f1-drive-grade/configs` into a DB-backed store (`config.calibration_profiles`) and expose import/activation commands.
- [ ] Port Drive Grade tests (within `tests/`) and ensure they run under The Undercut's pytest suite.
- [ ] Decide how to package notebooks/docs; likely move `docs/drive_grade_model.md`, `docs/pipeline_usage.md`, etc., into this repo and remove duplicates from the original project.
