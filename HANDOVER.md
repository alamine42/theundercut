# Handover – The Undercut (February 13, 2026)

## 1. Infra & Environment
- **Render topology:** Web (`uvicorn theundercut.api.main:app`), worker (`python -m theundercut.worker`), scheduler (`python -m theundercut.scheduler`) + managed Postgres (`theundercut-db`), managed Redis (`theundercut-cache`), shared `/data` disk for FastF1 cache (2 GB).
- **Local `.env`:**
  ```env
  DATABASE_URL=postgresql://theundercut:<PASSWORD>@dpg-d67rmv3h46gs73f1ciag-a.oregon-postgres.render.com/theundercut_40f1
  REDIS_URL=redis://red-d67ropp5pdvs73flou20:6379
  SECRET_KEY=dev-secret-key
  FASTF1_CACHE_DIR=/tmp/fastf1_cache
  ```
- **External access:** Render DB external endpoint resolves on your network but not from this environment. If another agent needs CLI access, ensure Render’s “External Connections” is enabled and share the exact URL (including `?sslmode=require`).

## 2. Recent Code Changes (already merged)
- **Analytics cache helper:** `src/theundercut/services/cache.py` centralizes `analytics_cache_key` + invalidation; API uses it (`src/theundercut/api/v1/analytics.py`).
- **Ingestion hardening:** `_as_iterable` normalization, logging, and `force=True` option to re-run Drive Grades without duplicating lap inserts (`src/theundercut/services/ingestion.py`). Strategy/penalty/overtake persistence now tested.
- **CLI backfill:** `theundercut drive-grade backfill` iterates calendar rounds and calls `ingest_session(..., force=True)` (`src/theundercut/cli.py:143`).
- **Docs/tasks:** `docs/architecture.md` refreshed; `docs/tasks.md` now includes T13–T15 to track the analytics rename + architecture doc + merge plan.
- **Tests:** New suites cover cache helper, ingestion persistence, CLI backfill, analytics payload (see `tests/test_cache_service.py`, `tests/test_ingestion_drive_grade.py`, `tests/test_cli_drive_grade.py`, `tests/test_analytics_service.py`, `tests/test_analytics_api.py`). `pytest tests/test_cache_service.py tests/test_ingestion_drive_grade.py tests/test_cli_drive_grade.py tests/test_analytics_service.py tests/test_analytics_api.py` passes locally.

## 3. Current State
- Alembic migrations were run against the new Render DB by the user; 2025 calendar synced. 2024 calendar + ingestion backfill still pending.
- Render services are up-to-date with `main`; `.env` references prod DB/Redis.
- No Doppler integration yet; secrets managed manually via `.env`/Render dashboard.

## 4. Immediate Next Steps (for next agent)
1. **Sync 2024 calendar:**
   ```bash
   source venv/bin/activate
   export DATABASE_URL=postgresql://theundercut:<PASSWORD>@dpg-d67rmv3h46gs73f1ciag-a.oregon-postgres.render.com/theundercut_40f1?sslmode=require
   theundercut sync-calendar --year 2024
   ```
   *Requires network that can reach OpenF1 + Render DB (this environment cannot resolve those hosts).* 
2. **Run Drive Grade backfill:**
   ```bash
   theundercut drive-grade backfill 2024 --round 1    # repeat for other rounds as needed
   ```
   Confirm `core.driver_metrics` populates and `/api/v1/analytics/2024/1` returns DB-backed `driver_pace_grades`.
3. **Verify prod API/UI:** Hit the Render web URL for `/api/v1/analytics/{season}/{round}` and `/race/{season}/{round}`; ensure Redis cache warm/invalidation works.
4. **Doc updates:** Once steps 1–3 succeed, mark T1/T2 complete in `docs/tasks.md`, note seeded seasons + PITR settings in `docs/architecture.md`, and log any manual bootstrap commands in `docs/ops/` if applicable.
5. **Next roadmap items:**
   - **T7:** Build interactive charts (HTMX now, React later) consuming `/api/v1/analytics`.
   - **T12:** Add monitoring/alerts (Sentry, structured logging, Render health checks).
   - **Drive Grade merge:** Follow `docs/drive_grade_merge_plan.md` to integrate the f1-drive-grade repo fully.

## 5. Open Issues & Risks
- External network access from this environment cannot reach Render DB or OpenF1; future agents may need VPN/tunnel or run commands locally where DNS works.
- Render Postgres currently holds only migrations + 2025 calendar; ingestion jobs need to run ASAP to populate 2024 data.
- Monitoring/alerting still missing; ingestion failures would go unnoticed until T12 completes.

Keep this file updated as ownership changes—record new deployment choices, schemas, or external dependencies so the next agent can continue smoothly.
