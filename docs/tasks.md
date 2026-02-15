# Task Tracker

Legend: ☐ = not started, ◐ = in progress, ☑ = done

| ID | Status | Title | Owner | Notes |
| -- | ------ | ----- | ----- | ----- |
| T1 | ☐ | Provision Render Postgres + enable PITR | Infra | Needed before prod redeploy |
| T2 | ☐ | Provision Render Redis cache + /data disk | Infra | Share connection strings w/ app |
| T3 | ☐ | Update `render.yaml` with CMS/analytics env vars | Platform | No paywall secrets needed |
| T4 | ☑ | Implement centralized config module (env parsing, secrets) | Backend | Unlocks consistent settings usage |
| T5 | ☑ | Build public analytics API (laps, stints, driver grades) with caching | Backend | Depends on T1/T2 |
| T6 | ☐ | Enhance ingestion to compute driver grades/derived metrics | Data | Depends on T5 schema |
| T7 | ☐ | Build React interactive charts (lap/stint/grades) | Web | Depends on T5 |
| T8 | ☐ | Implement CSV export & admin ready toggle | Backend/Web | Depends on T5/T6 |
| T9 | ◐ | Schema alignment for Drive Grade tables (core.driver_metrics, strategy, penalties, overtakes) | Data/Infra | Migration drafted; needs review + seed plan |
| T10| ◐ | Extract shared `undercut_core` package and import Drive Grade engine | Backend | Core package + engine source + CLI + tests merged; docs pending |
| T11| ☐ | Calibration storage & seeding (DB + CLIs) | Backend | Profiles imported, needs production rollout checklist |
| T12| ☐ | Monitoring & alerting setup (Sentry, logs) | Platform | Post-MVP |
| T13| ☑ | Rename analytics output to “driver pace grade” (API/tests/docs) | Backend | Ensures `/api/v1/analytics` matches terminology agreed with product |
| T14| ☑ | Refresh architecture + MVP implementation plan | Product | Updated `docs/architecture.md` with stack overview, MVP scope, testing strategy |
| T15| ☑ | Document Drive Grade merge approach | Backend | See `docs/drive_grade_merge_plan.md` for phased migration |

Active sprint picks: **T5**, **T6**, **T7** (backend + analytics).
