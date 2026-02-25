# Race Weekend Widget Design

_Last updated: February 24, 2026_
_Design review: Codex (1 critical, 3 warnings addressed)_

## Overview

Replace the static "Last Race Results" section on the homepage with a dynamic Race Weekend Widget that shows upcoming race information and progressively reveals session results as the weekend unfolds.

## Requirements

### Core Functionality
- Show countdown to next race (even during off-weeks)
- Display historical data: previous year's winner and podium
- Progressive reveal: compact view (top 3) expands to full grid on click
- Sessions appear as separate cards as they complete (FP1, FP2, FP3, Quali, Sprint*, Race)
- Sprint weekends: sprint qualifying and sprint race shown as regular sessions
- No live timing (results only after session completes)
- ISR revalidation (5 min) for data freshness

### Widget States

| State | Trigger | Display |
|-------|---------|---------|
| **Pre-weekend** | >3 days before FP1 | Next race info, countdown, historical data |
| **Race week** | Within 3 days of FP1 | Race info, session schedule, historical data |
| **During weekend** | FP1 started | Completed sessions + next session countdown |
| **Post-race** | Race completed | All session results, race as primary |
| **Off-week** | >7 days to next race | Next race countdown, last race summary |

---

## Wireframes

### Pre-Weekend / Off-Week State

```
┌─────────────────────────────────────────────────────────────────┐
│  NEXT RACE                                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🏁 Australian Grand Prix          Round 3 of 24               │
│     Albert Park Circuit, Melbourne                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          RACE STARTS IN                                  │   │
│  │     4 days  12 hours  35 min                            │   │
│  │          Sun, Mar 16 · 06:00 UTC                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ LAST YEAR ─────────────────────────────────────────────┐   │
│  │  🥇 VER  Red Bull       │  Pole: VER                    │   │
│  │  🥈 PER  Red Bull       │  Fastest: VER 1:20.235        │   │
│  │  🥉 ALO  Aston Martin   │                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### During Weekend - Compact View

```
┌─────────────────────────────────────────────────────────────────┐
│  AUSTRALIAN GRAND PRIX                              Round 3     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ FP1         │ │ FP2         │ │ FP3         │               │
│  │ ✓ Completed │ │ ✓ Completed │ │ ○ 2h 15m    │               │
│  │             │ │             │ │             │               │
│  │ 1. VER      │ │ 1. NOR      │ │             │               │
│  │ 2. NOR      │ │ 2. VER      │ │             │               │
│  │ 3. LEC      │ │ 3. HAM      │ │             │               │
│  │             │ │             │ │             │               │
│  │ [Expand ↓]  │ │ [Expand ↓]  │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ QUALIFYING  │ │ RACE        │ │             │               │
│  │ ○ Tomorrow  │ │ ○ Sunday    │ │             │               │
│  │   14:00 UTC │ │   06:00 UTC │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Session Card - Expanded View

```
┌─────────────────────────────────────────────────────────────────┐
│  FP2                                              ✓ Completed   │
├─────────────────────────────────────────────────────────────────┤
│  Pos  Driver        Team              Time        Gap           │
│  ─────────────────────────────────────────────────────────────  │
│   1   NOR  Norris   McLaren          1:18.245      -           │
│   2   VER  Verstap  Red Bull         1:18.367    +0.122        │
│   3   HAM  Hamilto  Ferrari          1:18.412    +0.167        │
│   4   LEC  Leclerc  Ferrari          1:18.456    +0.211        │
│   5   PIA  Piastri  McLaren          1:18.489    +0.244        │
│   6   RUS  Russell  Mercedes         1:18.523    +0.278        │
│   7   SAI  Sainz    Williams         1:18.567    +0.322        │
│   8   ALO  Alonso   Aston Martin     1:18.601    +0.356        │
│   9   STR  Stroll   Aston Martin     1:18.645    +0.400        │
│  10   OCO  Ocon     Haas             1:18.689    +0.444        │
│  ... (11-20)                                                    │
│                                                                 │
│                                            [Collapse ↑]         │
└─────────────────────────────────────────────────────────────────┘
```

### Qualifying Card - Expanded

```
┌─────────────────────────────────────────────────────────────────┐
│  QUALIFYING                                       ✓ Completed   │
├─────────────────────────────────────────────────────────────────┤
│  Pos  Driver        Q1          Q2          Q3          Gap     │
│  ─────────────────────────────────────────────────────────────  │
│   1   VER  Verstap  1:17.823    1:17.456    1:16.915     -      │
│   2   NOR  Norris   1:17.912    1:17.512    1:17.023   +0.108   │
│   3   LEC  Leclerc  1:17.956    1:17.534    1:17.089   +0.174   │
│  ...                                                            │
│  16   ALB  Albon    1:18.456    1:18.234       -       Q2       │
│  ...                                                            │
│  20   SAR  Sargeant 1:19.123       -           -       Q1       │
│                                                                 │
│                                            [Collapse ↑]         │
└─────────────────────────────────────────────────────────────────┘
```

### Sprint Weekend Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  CHINESE GRAND PRIX (Sprint)                        Round 5     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────┐ ┌───────────┐ ┌─────────────┐ ┌───────┐ ┌─────────┐ │
│  │ FP1   │ │ SPRINT Q  │ │ SPRINT RACE │ │ QUALI │ │ RACE    │ │
│  │ ✓     │ │ ✓         │ │ ✓           │ │ ✓     │ │ ○ 2h    │ │
│  └───────┘ └───────────┘ └─────────────┘ └───────┘ └─────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout

```
┌───────────────────────────┐
│  AUSTRALIAN GP    Rd 3    │
├───────────────────────────┤
│                           │
│  Race in 4d 12h 35m       │
│  Sun, Mar 16 · 06:00 UTC  │
│                           │
├───────────────────────────┤
│  Last Year                │
│  ──────────────────────── │
│  🥇 VER  Red Bull         │
│  🥈 PER  Red Bull         │
│  🥉 ALO  Aston Martin     │
│                           │
│  Pole: VER                │
│  Fastest: VER 1:20.235    │
├───────────────────────────┤
│  Sessions                 │
│  ──────────────────────── │
│  ┌───────────────────┐    │
│  │ FP1    ✓ Complete │    │
│  │ 1. VER  2. NOR    │    │
│  │ 3. LEC  [More]    │    │
│  └───────────────────┘    │
│  ┌───────────────────┐    │
│  │ FP2    ✓ Complete │    │
│  │ 1. NOR  2. VER    │    │
│  │ 3. HAM  [More]    │    │
│  └───────────────────┘    │
│         ...               │
└───────────────────────────┘
```

---

## Component Hierarchy

```
web/src/components/race-weekend/
├── RaceWeekendWidget.tsx       # Main container, handles state logic
├── RaceHeader.tsx              # Race name, round, circuit info
├── RaceCountdown.tsx           # Countdown timer display
├── HistoricalData.tsx          # Previous year's results
├── SessionGrid.tsx             # Grid layout for session cards
├── SessionCard.tsx             # Individual session card
│   ├── SessionCardCompact.tsx  # Top 3 view
│   └── SessionCardExpanded.tsx # Full results view
├── QualifyingCard.tsx          # Special layout for Q1/Q2/Q3
├── types.ts                    # Component-specific types
└── index.ts                    # Exports
```

### Component Props

```typescript
// RaceWeekendWidget.tsx
interface RaceWeekendWidgetProps {
  schedule: RaceWeekendSchedule;
  sessionResults: Map<string, SessionResults>;
  history: CircuitHistory | null;
}

// SessionCard.tsx
interface SessionCardProps {
  session: RaceSession;
  results?: SessionResults;
  isExpanded: boolean;
  onToggle: () => void;
}

// HistoricalData.tsx
interface HistoricalDataProps {
  history: CircuitHistory;
  circuitName: string;
}
```

---

## API Design

### New Endpoints

#### 1. Race Weekend Schedule

```
GET /api/v1/race/{season}/{round}/schedule
```

**Response:**
```json
{
  "season": 2026,
  "round": 3,
  "race_name": "Australian Grand Prix",
  "circuit_id": "albert_park",
  "circuit_name": "Albert Park Circuit",
  "circuit_country": "Australia",
  "is_sprint_weekend": false,
  "sessions": [
    {
      "session_type": "fp1",
      "start_time": "2026-03-14T01:30:00Z",
      "end_time": "2026-03-14T02:30:00Z",
      "status": "completed"
    },
    {
      "session_type": "fp2",
      "start_time": "2026-03-14T05:00:00Z",
      "end_time": "2026-03-14T06:00:00Z",
      "status": "completed"
    },
    {
      "session_type": "fp3",
      "start_time": "2026-03-15T01:30:00Z",
      "end_time": "2026-03-15T02:30:00Z",
      "status": "scheduled"
    },
    {
      "session_type": "qualifying",
      "start_time": "2026-03-15T05:00:00Z",
      "end_time": "2026-03-15T06:00:00Z",
      "status": "scheduled"
    },
    {
      "session_type": "race",
      "start_time": "2026-03-16T06:00:00Z",
      "end_time": "2026-03-16T08:00:00Z",
      "status": "scheduled"
    }
  ]
}
```

**Implementation:**
- Query `CalendarEvent` table by season + round
- Join with circuit metadata
- Determine `is_sprint_weekend` from session types present

#### 2. Session Results

```
GET /api/v1/race/{season}/{round}/session/{session_type}/results
```

**Path Parameters:**
- `session_type`: `fp1`, `fp2`, `fp3`, `qualifying`, `sprint_qualifying`, `sprint_race`, `race`

**Response (Practice/Sprint):**
```json
{
  "season": 2026,
  "round": 3,
  "session_type": "fp2",
  "results": [
    {
      "position": 1,
      "driver_code": "NOR",
      "driver_name": "Lando Norris",
      "team": "McLaren",
      "time": "1:18.245",
      "gap": null,
      "laps": 28
    },
    {
      "position": 2,
      "driver_code": "VER",
      "driver_name": "Max Verstappen",
      "team": "Red Bull",
      "time": "1:18.367",
      "gap": "+0.122",
      "laps": 31
    }
  ]
}
```

**Response (Qualifying):**
```json
{
  "season": 2026,
  "round": 3,
  "session_type": "qualifying",
  "results": [
    {
      "position": 1,
      "driver_code": "VER",
      "driver_name": "Max Verstappen",
      "team": "Red Bull",
      "q1_time": "1:17.823",
      "q2_time": "1:17.456",
      "q3_time": "1:16.915",
      "gap": null,
      "eliminated_in": null
    },
    {
      "position": 16,
      "driver_code": "ALB",
      "driver_name": "Alex Albon",
      "team": "Williams",
      "q1_time": "1:18.456",
      "q2_time": "1:18.234",
      "q3_time": null,
      "gap": null,
      "eliminated_in": "Q2"
    }
  ]
}
```

**Error Response (Session not complete):**
```json
{
  "error": "session_not_complete",
  "message": "FP3 has not started yet",
  "scheduled_start": "2026-03-15T01:30:00Z"
}
```

#### 3. Circuit History

```
GET /api/v1/circuits/{season}/{circuit_id}/history
```

**Response:**
```json
{
  "circuit_id": "albert_park",
  "circuit_name": "Albert Park Circuit",
  "previous_year": {
    "season": 2025,
    "winner": {
      "driver_code": "VER",
      "driver_name": "Max Verstappen",
      "team": "Red Bull"
    },
    "second": {
      "driver_code": "PER",
      "driver_name": "Sergio Perez",
      "team": "Red Bull"
    },
    "third": {
      "driver_code": "ALO",
      "driver_name": "Fernando Alonso",
      "team": "Aston Martin"
    },
    "pole": {
      "driver_code": "VER",
      "driver_name": "Max Verstappen",
      "team": "Red Bull"
    },
    "fastest_lap": {
      "driver_code": "VER",
      "driver_name": "Max Verstappen",
      "time": "1:20.235"
    }
  }
}
```

**Response (New circuit, no history):**
```json
{
  "circuit_id": "las_vegas",
  "circuit_name": "Las Vegas Strip Circuit",
  "previous_year": null
}
```

### Caching Strategy

**Event-driven invalidation** (addresses Codex WARNING: Stale Data From TTL Mismatch):

| Endpoint | Cache TTL | Cache Key | Invalidation Trigger |
|----------|-----------|-----------|----------------------|
| `/schedule` | 5 min | `schedule:{season}:{round}` | `CalendarEvent.status` change |
| `/session/*/results` | 2 hours | `session:{season}:{round}:{type}` | Ingestion completion, penalty update |
| `/history` | 7 days | `history:{season}:{circuit_id}` | None (immutable) |

**Cache invalidation hooks:**
- When ingestion marks `CalendarEvent.status = 'ingested'`, bust `session:*` cache for that round
- When penalty/classification updates occur, re-ingest and bust cache
- Frontend shows "Last updated: X min ago" with stale indicator if >30 min old

---

## Data Flow

**Single aggregated endpoint** (addresses Codex WARNING: High-Latency Fan-Out Fetch Pattern):

Instead of multiple API calls, introduce a single aggregator endpoint:

```
GET /api/v1/race/{season}/{round}/weekend
```

**Response:**
```json
{
  "schedule": { ... },
  "history": { ... },
  "sessions": {
    "fp1": { "status": "completed", "results": [...] },
    "fp2": { "status": "completed", "results": [...] },
    "qualifying": { "status": "scheduled", "results": null }
  },
  "meta": {
    "last_updated": "2026-03-14T06:15:00Z",
    "stale": false
  }
}
```

This collapses 3-8 API calls into 1, with Redis caching at the aggregated level.

**Fallback strategy:**
- Primary: Read from persisted `session_classifications` table
- Fallback: Fetch from FastF1/OpenF1 only if session not yet ingested
- Error: Return partial data with per-section error metadata

```
┌─────────────────────────────────────────────────────────────────┐
│                        Homepage (RSC)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Single API call: /api/v1/race/{season}/{round}/weekend      │
│     - Returns schedule, history, all session results            │
│     - Cached in Redis with event-driven invalidation            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Render RaceWeekendWidget with aggregated data               │
│     - Graceful degradation per section on partial failures      │
│     - Shows stale indicator if data >30 min old                 │
└─────────────────────────────────────────────────────────────────┘
```

### Original Data Flow (Deprecated)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Homepage (RSC)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Determine current/next race round                           │
│     - Query /api/v1/circuits/{season} for race dates            │
│     - Find round where date >= today OR most recent             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Fetch race weekend data (parallel)                          │
│     ┌──────────────────────┐  ┌──────────────────────────┐     │
│     │ /race/{s}/{r}/       │  │ /circuits/{s}/{c}/       │     │
│     │ schedule             │  │ history                  │     │
│     └──────────────────────┘  └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. For each completed session, fetch results (parallel)        │
│     ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│     │ /session/  │ │ /session/  │ │ /session/  │               │
│     │ fp1/results│ │ fp2/results│ │ quali/...  │               │
│     └────────────┘ └────────────┘ └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Render RaceWeekendWidget with data                          │
│     - Pass schedule, results map, history                       │
│     - Component handles display logic                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Considerations

**Single source of truth** (addresses Codex CRITICAL: Dual Source of Truth):

### New Table Required

Session classifications MUST be persisted to avoid dual data sources. The existing ingestion pipeline already populates `lap_times` and `stints`; we extend it to also store condensed session results.

```python
# src/theundercut/models.py - NEW TABLE (Alembic migration required)
class SessionClassification(Base):
    """Condensed session results for all session types."""
    __tablename__ = "session_classifications"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    session_type = Column(String(20), nullable=False)  # fp1, fp2, fp3, qualifying, sprint_qualifying, sprint_race, race
    driver_code = Column(String(3), nullable=False)
    driver_name = Column(String(100))
    team = Column(String(50))
    position = Column(Integer)
    time_ms = Column(Float)  # Best lap time (practice) or classified time (race)
    gap_ms = Column(Float)   # Gap to leader
    laps = Column(Integer)
    points = Column(Integer) # For race/sprint
    # Qualifying-specific
    q1_time_ms = Column(Float)
    q2_time_ms = Column(Float)
    q3_time_ms = Column(Float)
    eliminated_in = Column(String(5))  # Q1, Q2, or null
    # Metadata
    ingested_at = Column(DateTime, default=func.now())
    amended = Column(Boolean, default=False)  # True if post-race penalty changed classification

    __table_args__ = (
        UniqueConstraint("season", "round", "session_type", "driver_code", name="uq_session_classification"),
        Index("ix_session_classification_lookup", "season", "round", "session_type"),
    )
```

### Data Flow

1. **Ingestion pipeline** (existing `services/ingestion.py`) extended to:
   - Fetch session classifications from FastF1 after session completes
   - Persist to `session_classifications` table with `ON CONFLICT DO UPDATE` (for penalty amendments)
   - Bust Redis cache on successful ingestion

2. **Widget API** reads from `session_classifications`:
   - Primary: Query Postgres (fast, consistent with rest of product)
   - Fallback: If session not yet ingested AND within 2 hours of end time, fetch live from FastF1
   - Never: Fetch from external API for sessions ingested >2 hours ago

3. **Cache invalidation** tied to ingestion lifecycle:
   - `CalendarEvent.status` transitions trigger cache bust
   - Penalty amendments trigger re-ingestion and cache bust

### Existing Tables Used

- `CalendarEvent` - Session times and status (already populated)
- `lap_times` - Detailed lap data (existing)
- `stints` - Stint aggregates (existing)
- Circuit data from Jolpica API (no local table needed)

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| **New circuit (no history)** | Hide "Last Year" section, show only race info |
| **Circuit renamed** | Map old circuit_id to new (e.g., Turkey → Istanbul Park) |
| **Session cancelled** | Show "Cancelled" badge, skip in results |
| **Red-flagged session** | Show available results, note "Session red-flagged" |
| **Sprint weekend** | Detect via session types, show 6 session cards |
| **Double-header weekends** | Each race is separate round, widget shows current |
| **Season not started** | Show Round 1 countdown with pre-season testing link |
| **Season ended** | Show final race results, "See you in {next_year}" |
| **API timeout** | Show error state with retry, fall back to cached data |
| **Partial results** | Show available data, indicate "Results updating..." |
| **Post-race penalty** | Re-ingest classification, bust cache, show "Updated" badge |
| **Provider outage** | Serve from Postgres; if not ingested yet, show "Data unavailable" |
| **Ingestion lag** | Show "Awaiting official results" for 2h window post-session |
| **Stale cache** | Show "Last updated X min ago" indicator if >30 min old |

---

## Task Plan

**Revised task plan** (addresses Codex WARNING: Task Plan Ignores Data Acquisition & Resiliency Work):

| ID | Task | Priority | Dependencies | Type |
|----|------|----------|--------------|------|
| `.0a` | Create SessionClassification model + Alembic migration | P0 | - | Backend/DB |
| `.0b` | Extend ingestion to persist session classifications | P0 | .0a | Backend |
| `.0c` | Add cache invalidation hooks tied to ingestion | P0 | .0b | Backend |
| `.1` | Create race weekend schedule API endpoint | P1 | .0c | Backend/API |
| `.2` | Create session results API endpoints | P1 | .0c | Backend/API |
| `.2b` | Create aggregated `/weekend` endpoint | P1 | .1, .2 | Backend/API |
| `.3` | Create historical race data API endpoint | P2 | - | Backend/API |
| `.4` | Add TypeScript types for race weekend data | P1 | .2b, .3 | Frontend |
| `.5` | Create RaceWeekendWidget component | P1 | .4 | Frontend |
| `.6` | Replace Last Race Results with RaceWeekendWidget | P1 | .5 | Frontend |
| `.7` | Unit tests for race weekend API endpoints | P2 | .1, .2, .2b | Testing |
| `.8` | Unit tests for RaceWeekendWidget components | P2 | .5 | Testing |
| `.9` | E2E tests for race weekend widget | P2 | .6 | Testing |

### New Infrastructure Tasks (P0)

These MUST complete before API work begins:

1. **`.0a` - Database schema**: Create `SessionClassification` model, generate Alembic migration, run on dev/staging
2. **`.0b` - Ingestion extension**: Modify `services/ingestion.py` to fetch and persist session classifications after each session ingests
3. **`.0c` - Cache hooks**: Add Redis cache invalidation when `CalendarEvent.status` changes or classifications are amended

### Dependency Graph

```
.0a (schema) ─► .0b (ingestion) ─► .0c (cache hooks)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
            .1 (schedule API)                       .2 (results API)
                    │                                       │
                    └──────────────► .2b (aggregator) ◄─────┘
                                          │
                    .3 (history) ─────────┤
                                          ▼
                                    .4 (types)
                                          │
                                          ▼
                                    .5 (component)
                                          │
                                          ▼
                                    .6 (integrate)
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
            .8 (component tests)                          .9 (e2e)

.1, .2, .2b ─────────────────────► .7 (API tests)
```

---

## Verification Checklist

### Infrastructure (P0)
- [ ] Alembic migration creates `session_classifications` table
- [ ] Ingestion persists classifications after session completion
- [ ] Cache invalidation triggers on `CalendarEvent.status` change
- [ ] Penalty amendments re-ingest and bust cache

### API
- [ ] Schedule endpoint returns all sessions with correct times
- [ ] Session results endpoint handles all session types
- [ ] Aggregated `/weekend` endpoint returns all data in single call
- [ ] Historical data shows previous year's podium
- [ ] API serves from Postgres, not live provider calls (except fallback)

### Frontend
- [ ] Countdown timer displays correctly
- [ ] Progressive reveal expands/collapses smoothly
- [ ] Sprint weekends show all 6 sessions
- [ ] Mobile layout is usable
- [ ] ISR revalidation works (5 min freshness)
- [ ] Error states display gracefully per section
- [ ] Stale indicator shows when data >30 min old
- [ ] New circuits handle missing history

### Testing
- [ ] Unit tests cover API endpoints
- [ ] Unit tests cover ingestion extension
- [ ] E2E tests pass for all user flows

---

## Open Questions

1. ~~Should we show all upcoming sessions in the schedule?~~
   **Answer:** Yes, show all sessions with status (upcoming/completed).

2. ~~How to handle timezone display?~~
   **Answer:** Show UTC times with local time conversion on client.

3. ~~Should countdown be client-side JavaScript?~~
   **Answer:** No, use server-rendered "X days, Y hours" format. Updates on ISR refresh.
