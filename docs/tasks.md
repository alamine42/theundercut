# Task Tracker

Legend: ☐ = not started, ◐ = in progress, ☑ = done

| ID | Status | Title | Owner | Notes |
| -- | ------ | ----- | ----- | ----- |
| T1 | ☑ | Provision Render Postgres + enable PITR | Infra | Postgres 18 provisioned (basic plan - PITR not available) |
| T2 | ☑ | Provision Render Redis cache + /data disk | Infra | Redis 8.1.4 + 2GB /data disk provisioned |
| T3 | ☑ | Update Render web service to use theundercut repo | Platform | Switched from Flask app to FastAPI; Docker + uvicorn |
| T4 | ☑ | Implement centralized config module (env parsing, secrets) | Backend | Unlocks consistent settings usage |
| T5 | ☑ | Build public analytics API (laps, stints, driver grades) with caching | Backend | Live at /api/v1/analytics/{season}/{round} |
| T6 | ☑ | Enhance ingestion to compute driver grades/derived metrics | Data | OpenF1 adapter fixed; 2024+2025 seasons ingested (52K laps) |
| T7 | ☐ | Build React interactive charts (lap/stint/grades) | Web | Depends on T5 |
| T8 | ☐ | Implement CSV export & admin ready toggle | Backend/Web | Depends on T5/T6 |
| T9 | ☑ | Schema alignment for Drive Grade tables (core.driver_metrics, strategy, penalties, overtakes) | Data/Infra | Migration applied; schema in production |
| T10| ☑ | Extract shared `undercut_core` package and import Drive Grade engine | Backend | Core package + engine source + CLI + tests merged |
| T11| ☐ | Calibration storage & seeding (DB + CLIs) | Backend | Profiles imported, needs production rollout checklist |
| T12| ☐ | Monitoring & alerting setup (Sentry, logs) | Platform | Post-MVP |
| T13| ☑ | Rename analytics output to "driver pace grade" (API/tests/docs) | Backend | Ensures `/api/v1/analytics` matches terminology agreed with product |
| T14| ☑ | Refresh architecture + MVP implementation plan | Product | Updated `docs/architecture.md` with stack overview, MVP scope, testing strategy |
| T15| ☑ | Document Drive Grade merge approach | Backend | See `docs/drive_grade_merge_plan.md` for phased migration |
| T16| ☐ | Fix calendar loader to exclude pre-season testing | Data | Round 1 currently maps to testing; actual races start at round 2 |
| T17| ☐ | Investigate FastF1 hanging issue | Data | FastF1 hangs on session.load(); using OpenF1 as workaround |
| T18| ☐ | Add stint data to OpenF1 ingestion | Data | OpenF1 laps endpoint doesn't include stint/compound info |

Active sprint picks: **T7** (interactive charts), **T11** (calibration), **T12** (monitoring).
