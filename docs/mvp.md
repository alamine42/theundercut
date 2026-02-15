# MVP Scope – Data-Obsessed F1 Superfans
_Last updated: February 11, 2026_

## Core User & Struggling Moment
- **User:** Telemetry-heavy F1 fans who already watch every race and want objective breakdowns, not just commentary.
- **Struggle:** Existing sources (TV broadcasts, social media, official apps) deliver raw data or generic recaps but lack trustworthy, interactive tools that combine lap times, tire strategy, and driver grading in a single destination.

## MVP Promise
“Get interactive race analytics (lap charts, driver grades, strategy tools) within minutes of lights-out, plus downloadable data for your own tinkering — completely free.”

## Functional Scope
1. **Race Analytics Hub**
   - Landing page per race with:
     - Interactive lap chart (compare up to 3 drivers).
     - Tire stint timeline.
     - Driver grade cards (overall + sector insights).
   - Powered by REST endpoints and Redis caching for fast reloads.
2. **Data Download Portal**
   - Authenticated superfans can export CSVs (laps, stints, derived metrics) for a selected race.
3. **CMS-lite Workflow**
   - Internal staff can trigger ingestion and mark a race “ready” via CLI or admin endpoint.

## Out-of-Scope for MVP
- Real-time streaming telemetry.
- Full CMS/editor UI (manual Markdown or simple admin is enough initially).
- Mobile apps (responsive web only).
- Advanced personalization or recommendation algorithms.

## Key Success Metrics
- Time from race ingestion to published analytics < 30 minutes.
- 50%+ of logged-in superfans interact with at least one chart per visit.
- Conversion rate from free to paid ≥ 8% in first cohort.

## Implementation Milestones
1. **Backend foundation (Week 1-2)**
   - Central config (done), consistent env management.
   - Extend API with `/analytics/{season}/{round}` returning laps, stints, driver grades JSON.
   - Implement Redis caching and query filters.
2. **Ingestion & Metrics (Week 2-3)**
   - Enhance ingestion job to compute driver grades (e.g., percentile vs teammate).
   - Store derived metrics in `analytics_driver_scores` table.
3. **Interactive UI (Week 3-5)**
   - Build a React/Vite front-end mounted under `/premium` consuming the API.
   - Lap chart: multi-driver selection, tooltips, zoom.
   - Stint timeline + driver grade cards.
4. **Downloads & Admin (Week 5-6)**
   - CSV export endpoint with signed URLs.
   - “Mark race ready” admin endpoint/CLI.

## Dependencies & Risks
- Need consistent FastF1/OpenF1 data quality; set up alerts for ingestion failures.
- Chart performance may require pre-aggregating data (e.g., downsampling long races).
- Subscription flow depends on Stripe configuration; ensure test keys available before coding.
