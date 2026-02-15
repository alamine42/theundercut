# The Undercut – Architecture & Implementation Plan

_Last updated: February 13, 2026_

This document orients new contributors by describing the product purpose, runtime components, persistence model, operations flow, MVP scope, and the current task backlog. File paths reference the repository root unless otherwise noted.

## 1. Project Purpose & Stack
- **Audience & value** – Build a Formula 1 analytics destination for data‑obsessed superfans, surfacing interactive lap insights, driver pace grades, and strategy breakdowns with both free and future premium tiers.
- **Core stack** – FastAPI app with HTMX/Tailwind templates (`src/theundercut/api/main.py`, `src/theundercut/web/**`), SQLAlchemy ORM models (`src/theundercut/models.py`), Redis-backed RQ workers (`src/theundercut/worker.py`), Postgres via SQLAlchemy (`src/theundercut/adapters/db.py`), and FastF1/OpenF1 ingestion providers (`src/theundercut/adapters/*.py`).
- **Packaging & deployment** – Dependencies declared in `pyproject.toml` (FastAPI, Redis, SQLAlchemy, FastF1, RQ, Alembic). Containerized via the slim Python 3.11 `Dockerfile` which installs runtime deps then `pip install -e .`. Render deployment (`render.yaml`) provisions three docker-based services (web, worker, scheduler) plus managed Postgres/Redis and a shared `/data` volume for the FastF1 cache.

## 2. Runtime Components
1. **FastAPI surface**
   - Entrypoint includes routers for JSON APIs and web views (`src/theundercut/api/main.py`).
   - `/api/v1/race/{season}/{round}/laps` in `src/theundercut/api/v1/race.py` returns lap rows filtered by optional `drivers` query param.
   - `/api/v1/analytics/{season}/{round}` in `src/theundercut/api/v1/analytics.py` wraps laps, stints, and driver pace grades with Redis caching (key prefix `analytics:v1`).
2. **HTMX/Jinja web pages**
   - `/race/{season}/{round}` route (`src/theundercut/web/routes.py`) renders `src/theundercut/web/templates/race/detail.html` which loads lap JSON via HTMX.
   - `base.html` bundles Tailwind/HTMX CDNs to keep the MVP lean.
3. **Data access**
   - `src/theundercut/adapters/db.py` exposes a pooled SQLAlchemy engine and FastAPI dependency for DB sessions.
   - `src/theundercut/adapters/redis_cache.py` centralizes the Redis client derived from `theundercut/config.py`.

## 3. Background Jobs & Scheduling
- **Provider resolver** – `src/theundercut/adapters/resolver.py` instantiates `FastF1Provider` first, falling back to `OpenF1Provider` if the smoke test fails.
- **Ingestion workflow** – `src/theundercut/services/ingestion.py` loads laps/stints, cleans columns, and bulk inserts with `ON CONFLICT DO NOTHING` on `(race_id, driver, lap)` to prevent duplicates. It also persists driver strategy/penalty/overtake events plus Drive Grade metrics when available, and updates `calendar_events.status`.
- **Scheduler** – `src/theundercut/scheduler.py` runs under a dedicated Render worker. It registers two cron jobs:
  - `daily_calendar_sync` (04:00 UTC) refreshes the season calendar via `adapters/calendar_loader.py`.
  - `enqueue_upcoming` (every 10 min) inspects `CalendarEvent` rows ending within the next two hours, then calls `scheduler.enqueue_at` to schedule `ingest_session`.
- **RQ worker** – `src/theundercut/worker.py` boots an RQ worker on the `default` queue and blocks until jobs finish. Worker and scheduler both rely on `redis_client` connections using `REDIS_URL`.

## 4. Data & Persistence Layer
- **ORM models** – `src/theundercut/models.py` defines ingestion tables (`calendar_events`, `lap_times`, `stints`) and the Drive Grade schema under `core.*` plus validation/calibration tables. `lap_times` holds per-lap telemetry (driver, lap, lap_ms, compound, stint, pit flag); `stints` aggregate laps per stint/compound.
- **Uniqueness & conflict handling** – `_store_laps` enforces unique `(race_id, driver, lap)` inserts via PostgreSQL `ON CONFLICT DO NOTHING` (see `services/ingestion.py:52-91`). `_store_stints` rebuilds aggregated stints on each ingestion run.
- **Reference data** – `_ensure_reference_entries` and `_persist_driver_events` populate `core.seasons`, `core.races`, `core.entries`, `core.strategy_events`, `core.penalty_events`, and `core.overtake_events` so Drive Grade outputs (`core.driver_metrics`) can join back to entries.
- **Migrations** – Alembic configuration lives under `alembic/` with versions tracking schema changes. Run `alembic upgrade head` after provisioning Postgres.

## 5. Tooling & Operations
- **Local bootstrap** – `docker-compose.dev.yml` runs Postgres 16 and Redis 7; developers export `.env.local` with `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `FASTF1_CACHE_DIR`. Run `pip install -e '.[dev]'` and `theundercut sync-calendar` to seed data.
- **CLI utilities** – `src/theundercut/cli.py` exposes Typer commands for `sync-calendar`, Drive Grade runs, and calibration profile management.
- **Render topology** – `render.yaml` declares:
  1. `theundercut-web` (FastAPI via uvicorn) with `/data` disk and env vars wired to managed Postgres/Redis.
  2. `theundercut-worker` (RQ worker) sharing env + disk.
  3. `theundercut-scheduler` (cron loop).
  4. `theundercut-cache` (Redis) and `theundercut-db` (Postgres) managed instances.
- **Secrets** – Until Doppler integration resumes, store per-environment `.env` files and ensure Render dashboard generates `SECRET_KEY`. Settings fall back to safe local defaults inside `src/theundercut/config.py`.

## 6. Public APIs & Contracts
| Endpoint | File | Request | Response Shape |
| --- | --- | --- | --- |
| `GET /api/v1/race/{season}/{round}/laps` | `src/theundercut/api/v1/race.py` | Path params `season`, `round`; optional `drivers` query list. | Array of `{driver:str, lap:int, lap_ms:float}` rows ordered by driver & lap. |
| `GET /api/v1/analytics/{season}/{round}` | `src/theundercut/api/v1/analytics.py` | Path params plus optional `drivers`. | JSON payload: `{ race: {season, round}, last_updated: ISO8601, laps: [...], stints: [...], driver_pace_grades: [...] }`. Grades originate from `core.driver_metrics` when populated; otherwise a lap-time heuristic adds `source:"lap_time_heuristic"`. |
| Web `GET /race/{season}/{round}` | `src/theundercut/web/routes.py` | Server-rendered page w/ HTMX button that hits the laps endpoint. | HTML page referencing `race/detail.html` template. |

**Key ORM types**
- `CalendarEvent` – session metadata with `status` transitions (`scheduled` → `running` → `ingested`).
- `LapTime` – lap pipeline with unique `(race_id, driver, lap)` and tire compound details.
- `Stint` – aggregated stint metrics.
- `DriverMetrics` – Drive Grade outputs per entry: `consistency_score`, `team_strategy_score`, `racecraft_score`, `penalty_score`, `total_grade`, `calibration_profile`, `data_source`.
- `StrategyEvent`, `PenaltyEvent`, `OvertakeEvent` – capture contextual evidence powering Drive Grade components.

## 7. MVP Scope (Free Tier)
Target persona: “data-obsessed superfans” craving interactive tools akin to PFF’s analysis but for F1.

**MVP pillars**
1. **Race Explorer** – Public `/race/{season}/{round}` pages with HTMX components to visualize lap charts, stint summaries, and driver pace grade rankings.
2. **Driver Pace Grade Leaderboard** – Surface `driver_pace_grades` via `/api/v1/analytics` and render cards comparing pace deltas.
3. **Strategy Insights** – Summaries derived from `stints` and `strategy_events` (once ingestion populates them) highlighting tire choices and undercut attempts.
4. **Editorial Modules** – Lightweight CMS or markdown-driven briefs embedded alongside charts to contextualize data (free for MVP).
5. **Interactive Charts** – Use HTMX + small Alpine.js sprinkles initially; plan a React/Vite microfrontend later (T7).

Premium/paywall features (export tools, advanced dashboards, subscriptions) are postponed until after MVP traction.

## 8. Implementation Plan & Tasks
1. **Infra Restoration (T1–T3)** – Recreate Render Postgres/Redis with PITR, wire env vars, verify `/data` mount.
2. **Analytics API Hardening (T5)** – ✅ Completed: caching, pagination, driver pace grade rename.
3. **Ingestion Enhancements (T6)** – In progress: ensure Drive Grade inputs (strategy/penalties/overtakes) are populated and persisted.
4. **Interactive Charts (T7)** – Upcoming: design lap/stint visualizations hitting `/api/v1/analytics`.
5. **Drive Grade Merge** – Documented in `docs/drive_grade_merge_plan.md`; next steps involve schema alignment, shared core package extraction, and orchestrating Drive Grade runs post-ingestion.
6. **Operations & Observability (T11–T12)** – Add calibration seeding automation, health checks, and Sentry/logging before launch.

Refer to `docs/tasks.md` for the authoritative Kanban board (new tasks T13–T15 capture today’s updates).

## 9. Testing & Verification
- **Existing coverage** – `tests/test_analytics_api.py` and `tests/test_analytics_service.py` verify response keys, Redis caching, and Lap query filters. Drive Grade modules have unit tests across `tests/test_drive_grade.py`, `tests/test_pipeline.py`, etc.
- **Recommended additions** – Add ingestion regression tests that simulate provider data and confirm `core.driver_metrics` writes + calendar status transitions. Write HTMX smoke tests once interactive charts land.
- **Test workflow** – Activate `venv`, install dev extras (`pip install -e '.[dev]'`), run `pytest`. For integration tests requiring Postgres/Redis, start `docker compose up db redis` first. Use GitHub Actions (future) to run `pytest` per pull request.

## 10. Known Gaps & Follow-ups
- Render DB/Redis were deleted; reprovision via T1/T2 before redeploying.
- Scheduler resiliency: add monitoring/alerts (T12) so ingestion failures are surfaced quickly.
- Drive Grade outputs currently fallback to the heuristic most of the time; prioritize finishing ingestion enhancements and hooking up the real pipeline.
- Secrets management: once Doppler CLI issues are resolved, migrate `.env` handling to Doppler-managed configs for parity across environments.
- Frontend experience: `/race` page is minimal; interactive charts and editorial modules remain on the backlog (T7/T8).

Maintaining this doc: update the “Last updated” date and sections whenever architecture decisions change so future contributors stay aligned.
