# Pre-Season Testing Feature Design

_Last updated: February 22, 2026_

## Overview

Add functionality to capture and display pre-season testing data (lap times, stints, tire compounds) separately from race data. This enables users to analyze testing performance without mixing it with actual race results.

## Requirements

### Data Source
- FastF1/OpenF1 APIs (same as race data)
- Testing sessions are available as separate event types
- FastF1 uses `session.event['EventName']` to identify testing events

### Data Points to Capture
- **Lap Data:** driver, team, lap_number, lap_time, compound, stint_number, sector_times
- **Stint Data:** driver, stint_number, compound, start_lap, end_lap, average_pace
- **Session Data:** season, event_id, event_name, circuit_id, day (1-3), date

### UI/UX
- **Route:** `/testing/[season]` (e.g., `/testing/2025`)
- **Navigation:** Day 1 | Day 2 | Day 3 tabs
- **Views:**
  - Lap times table (driver, best lap, gap, total laps)
  - Stints table (driver, stint #, compound, laps, avg pace)
  - Lap progression chart (line chart, lap times over session)

### Future Considerations
- Data model supports comparison with race performance at same circuit
- No UI for race comparison in this phase

---

## Database Schema

### New Tables (Alembic Migration Required)

```python
# src/theundercut/models.py

class TestingEvent(Base):
    """Pre-season or in-season testing event."""
    __tablename__ = "testing_events"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False, index=True)
    event_id = Column(String(50), nullable=False)  # e.g., "pre_season_2025"
    event_name = Column(String(100), nullable=False)
    circuit_id = Column(String(50), nullable=False)
    total_days = Column(Integer, default=3)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="scheduled")  # scheduled, running, completed

    __table_args__ = (
        UniqueConstraint("season", "event_id", name="uq_testing_event"),
        Index("ix_testing_event_lookup", "season", "event_id"),
    )


class TestingSession(Base):
    """Single day of a testing event."""
    __tablename__ = "testing_sessions"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("testing_events.id"), nullable=False)
    day = Column(Integer, nullable=False)  # 1, 2, or 3
    date = Column(Date)
    status = Column(String(20), default="scheduled")

    event = relationship("TestingEvent", backref="sessions")

    __table_args__ = (
        UniqueConstraint("event_id", "day", name="uq_testing_session"),
    )


class TestingLap(Base):
    """Individual lap from a testing session."""
    __tablename__ = "testing_laps"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("testing_sessions.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    team = Column(String(50))
    lap_number = Column(Integer, nullable=False)
    lap_time_ms = Column(Float)  # milliseconds
    compound = Column(String(20))
    stint_number = Column(Integer)
    sector_1_ms = Column(Float)
    sector_2_ms = Column(Float)
    sector_3_ms = Column(Float)
    is_valid = Column(Boolean, default=True)

    session = relationship("TestingSession", backref="laps")

    __table_args__ = (
        UniqueConstraint("session_id", "driver", "lap_number", name="uq_testing_lap"),
        Index("ix_testing_lap_driver", "session_id", "driver"),
    )


class TestingStint(Base):
    """Aggregated stint from a testing session."""
    __tablename__ = "testing_stints"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("testing_sessions.id"), nullable=False)
    driver = Column(String(3), nullable=False)
    team = Column(String(50))
    stint_number = Column(Integer, nullable=False)
    compound = Column(String(20))
    start_lap = Column(Integer)
    end_lap = Column(Integer)
    lap_count = Column(Integer)
    avg_pace_ms = Column(Float)

    session = relationship("TestingSession", backref="stints")

    __table_args__ = (
        UniqueConstraint("session_id", "driver", "stint_number", name="uq_testing_stint"),
    )
```

### Migration Steps
1. Create Alembic migration: `alembic revision --autogenerate -m "add_testing_tables"`
2. Add indexes for common queries (season lookup, driver filtering)
3. Run `alembic upgrade head` in deployment pipeline

---

## API Design

### Endpoints

```
GET /api/v1/testing/{season}
```
Returns list of testing events for a season.

**Response:**
```json
{
  "season": 2025,
  "events": [
    {
      "event_id": "pre_season_2025",
      "event_name": "Pre-Season Testing",
      "circuit_id": "bahrain",
      "circuit_name": "Bahrain International Circuit",
      "start_date": "2025-02-26",
      "end_date": "2025-02-28",
      "total_days": 3,
      "status": "completed"
    }
  ]
}
```

```
GET /api/v1/testing/{season}/{event_id}/{day}
```
Returns detailed data for a specific testing day.

**Query Parameters:**
- `drivers` (optional): Filter by driver codes (e.g., `?drivers=VER&drivers=HAM`)
- `include_laps` (optional): Include full lap data (default: false for lighter response)

**Response:**
```json
{
  "season": 2025,
  "event_id": "pre_season_2025",
  "event_name": "Pre-Season Testing",
  "circuit_id": "bahrain",
  "day": 1,
  "date": "2025-02-26",
  "status": "completed",
  "results": [
    {
      "position": 1,
      "driver": "VER",
      "team": "Red Bull",
      "best_lap_ms": 90123,
      "best_lap_formatted": "1:30.123",
      "best_lap_compound": "SOFT",
      "gap_ms": null,
      "total_laps": 78,
      "stints": [
        {
          "stint_number": 1,
          "compound": "MEDIUM",
          "lap_count": 15,
          "avg_pace_ms": 92456,
          "avg_pace_formatted": "1:32.456"
        }
      ]
    }
  ],
  "laps": []  // Only populated if include_laps=true
}
```

```
GET /api/v1/testing/{season}/{event_id}/{day}/laps
```
Separate endpoint for full lap data with pagination.

**Query Parameters:**
- `drivers` (optional): Filter by driver codes
- `offset` (optional): Pagination offset (default: 0)
- `limit` (optional): Max laps to return (default: 500, max: 1000)

**Response:**
```json
{
  "total": 1523,
  "offset": 0,
  "limit": 500,
  "laps": [
    {
      "driver": "VER",
      "lap_number": 1,
      "lap_time_ms": 95123,
      "lap_time_formatted": "1:35.123",
      "compound": "MEDIUM",
      "stint": 1,
      "is_valid": true
    }
  ]
}
```

### Caching Strategy
- Redis cache with 24-hour TTL (testing data is static after event)
- Cache key format: `testing:{season}:{event_id}:{day}` (event_id prevents collision)
- Separate cache for laps: `testing_laps:{season}:{event_id}:{day}:{hash(drivers)}`

---

## Ingestion Pipeline

### Testing-Specific Ingestion Service

```python
# src/theundercut/services/testing_ingestion.py

class TestingIngestionService:
    """Handles ingestion of pre-season testing data from FastF1."""

    def ingest_testing_event(self, season: int, event_name: str) -> None:
        """Ingest all days of a testing event."""
        # 1. Fetch event metadata from FastF1
        # 2. Create/update TestingEvent record
        # 3. For each day, call ingest_testing_day()

    def ingest_testing_day(self, season: int, event_id: str, day: int) -> None:
        """Ingest a single testing day."""
        # 1. Fetch session data from FastF1
        # 2. Create/update TestingSession record
        # 3. Store laps with ON CONFLICT DO NOTHING
        # 4. Compute and store stint aggregates
        # 5. Update session status to 'completed'
```

### Scheduler Integration

Add to `src/theundercut/scheduler.py`:

```python
# Pre-season testing ingestion (runs during testing window)
scheduler.cron(
    "0 22 * 2-3 *",  # 22:00 UTC daily during Feb-March
    func=enqueue_testing_ingestion,
    args=[current_season],
    id="testing_ingestion"
)
```

### CLI Commands

Add to `src/theundercut/cli.py`:

```bash
# Manual backfill for testing data
theundercut testing ingest --season 2025 --event "Pre-Season Testing"

# Ingest specific day
theundercut testing ingest-day --season 2025 --event-id pre_season_2025 --day 1
```

---

## Frontend Components

### Pages
- `web/src/app/(main)/testing/[season]/page.tsx` - Main testing page (lists events)
- `web/src/app/(main)/testing/[season]/[eventId]/page.tsx` - Event detail with day tabs

### Components
- `TestingEventCard` - Card for event in list view
- `TestingDayTabs` - Tab navigation for Day 1/2/3
- `TestingLapTimesTable` - Sortable table of best laps
- `TestingStintsTable` - Stint breakdown by driver
- `LapProgressionChart` - Line chart of lap times

### UI States

| State | Behavior |
|-------|----------|
| **Loading** | Skeleton loader matching table structure |
| **Error** | Error banner with retry button; log to Sentry |
| **Empty (season)** | "No testing events scheduled for {season}" with link to previous year |
| **Empty (day)** | Tab visible but grayed; show "Day {n} data not yet available" |
| **Partial data** | Show available data; note "(limited data)" in header |

### Navigation
- Add "Testing" link to nav bar conditionally:
  - Show if current season has testing data OR testing is scheduled within 30 days
  - Use feature flag `SHOW_TESTING_NAV` for manual override

### Responsive Design
- Desktop: Full table with all columns
- Mobile: Card-based layout with expandable stints
- Chart: Horizontally scrollable on small screens

---

## Task Plan (Revised)

| # | Task | Dependencies | Est. |
|---|------|--------------|------|
| 6 | Design testing data models (SQLAlchemy + types) | — | S |
| 13 | Create Alembic migration for testing tables | #6 | S |
| 14 | Implement testing ingestion service | #13 | M |
| 15 | Add scheduler hooks for testing ingestion | #14 | S |
| 16 | Add CLI commands for testing backfill | #14 | S |
| 7 | Add backend API endpoints for testing data | #13 | M |
| 12 | Write API unit tests | #7 | M |
| 17 | Write ingestion integration tests | #14 | M |
| 8 | Create /testing/[season] page with event list | #7 | S |
| 18 | Create /testing/[season]/[eventId] page with day tabs | #8 | M |
| 9 | Build lap times & stints tables | #18 | M |
| 10 | Add lap progression chart | #18 | M |
| 19 | Add loading/error/empty states to all components | #9, #10 | S |
| 20 | Add Testing link to navigation (conditional) | #8 | S |
| 11 | Write e2e tests for testing pages | #18 | M |

**Legend:** S = Small (< 1 day), M = Medium (1-2 days)

### Dependency Graph
```
#6 (models) → #13 (migration) → #14 (ingestion) → #15 (scheduler)
                              ↓                    ↓
                              #7 (API) ←──────── #16 (CLI)
                              ↓
                              #12 (API tests), #17 (ingestion tests)
                              ↓
                              #8 (list page) → #18 (detail page)
                                              ↓
                                    #9 (tables), #10 (chart), #20 (nav)
                                              ↓
                                    #19 (states), #11 (e2e)
```

---

## Edge Cases

1. **No testing data for season** - Show "No testing events scheduled" message
2. **Partial day data** - Show available data, disable tabs for missing days
3. **Driver DNF during testing** - Still show their laps; mark incomplete stints
4. **Multiple testing events** - List view shows all events; URL includes event_id
5. **Very large lap count** - Pagination on laps endpoint; lazy-load in UI
6. **API timeout** - Show error state with retry; graceful degradation
7. **Testing in progress** - Show "Live" badge; data may be incomplete
8. **Cache stale during live session** - Shorter TTL (5 min) when status != completed

---

## Open Questions (Resolved)

1. ~~Should we show testing data in nav before the testing event occurs?~~
   **Answer:** Show nav link if testing scheduled within 30 days, or if data exists.

2. ~~How to handle live testing data during the event itself?~~
   **Answer:** Shorter cache TTL (5 min); "Live" badge in UI; data refresh on tab switch.

3. ~~Should there be driver-specific testing detail pages?~~
   **Answer:** Not in MVP. Filter by driver in existing views is sufficient.

---

## Verification Checklist

- [ ] Alembic migration runs without errors
- [ ] Ingestion pipeline populates all 4 tables correctly
- [ ] API returns data with correct event_id in URL
- [ ] Cache keys include event_id (no collisions)
- [ ] Tables render with loading/error/empty states
- [ ] Chart renders with driver filtering
- [ ] E2E tests pass for all user flows
- [ ] Mobile responsive layout works
