# Design: Live Session Boundary Ingestion

**Epic:** theundercut-phr
**Status:** Draft
**Author:** Claude
**Date:** 2026-02-25

## Overview

Show meaningful status during live F1 sessions instead of stale/empty data. Trigger ingestion at session boundaries (start and end) rather than continuous polling.

## Problem Statement

Currently, session data is only ingested 5 minutes AFTER a session ends. Users who load the page during a live session see no data.

### Current Behavior
1. User loads page 30 minutes into race
2. They see session scheduled (stale) or empty results
3. No indication that session is live

### Desired Behavior
1. User loads page 30 minutes into race
2. They see "Race in Progress" with session start time
3. After race ends, results appear automatically

## Architecture

### State Machine

```
scheduled → live → ingested
```

**State transitions:**
- `scheduled` → `live`: Triggered by scheduler at `start_ts`
- `live` → `ingested`: Triggered by scheduler at `end_ts + 5min`

### Backend Changes

#### 1. Session Start Job

```python
# Scheduled for each session's start_ts

def on_session_start(session_id: int):
    session = CalendarEvent.query.get(session_id)

    # Guard: only transition if still scheduled (idempotent)
    if session.status != 'scheduled':
        logger.info(f"Session {session_id} already {session.status}, skipping")
        return

    session.status = 'live'
    db.session.commit()

    # Invalidate cache so frontend sees "live" status
    cache.delete(f"race_weekend:{session.season}:{session.round}")
```

#### 2. Session End Job (existing, minor change)

```python
# Already scheduled for end_ts + 5 minutes

def on_session_end(session_id: int):
    session = CalendarEvent.query.get(session_id)

    # Guard: only transition if live (handles red flags, delays)
    if session.status != 'live':
        logger.info(f"Session {session_id} is {session.status}, skipping ingestion")
        return

    # Existing ingestion logic...
    results = ingest_session_results(session)
    session.status = 'ingested'
    db.session.commit()
```

#### 3. Handling Session Extensions (Red Flags, Delays)

F1 sessions can run longer than scheduled. The end job runs at `end_ts + 5min` regardless, but:

- If FastF1 returns no results yet → log warning, leave status as `live`
- Existing retry logic will pick it up on next scheduler run
- Manual trigger available if needed: `bd run ingest-session <id>`

### Frontend Changes

#### 1. Live Status Display

When session status is `live`, show:

```tsx
// In SessionCard.tsx
if (session.status === 'live') {
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute h-full w-full rounded-full bg-red-400 opacity-75" />
        <span className="relative rounded-full h-3 w-3 bg-red-500" />
      </span>
      <span className="font-medium text-red-500">In Progress</span>
    </div>
  );
}
```

#### 2. Auto-Refresh on Session End (Optional)

If user has page open when session ends, refresh to show results:

```typescript
// Check if any session transitions from 'live' to 'ingested'
const { data } = useQuery({
  queryKey: ['race-weekend', season, round],
  refetchInterval: hasLiveSession ? 60_000 : false,  // Check every minute if live
});
```

This is optional - users can also just refresh manually.

### API Response

Add `status` to session data:

```typescript
interface RaceSession {
  session_type: string;
  start_time: string;   // ISO 8601 UTC
  end_time: string;     // ISO 8601 UTC
  status: 'scheduled' | 'live' | 'ingested';
}
```

**Status values:**
| Status | Meaning | Frontend Display |
|--------|---------|------------------|
| `scheduled` | Session hasn't started | Countdown timer |
| `live` | Session in progress | "In Progress" indicator |
| `ingested` | Results available | Show results |

**Note:** Status is determined server-side. Frontend should NOT use client clock to determine if session is live.

## Edge Cases

### 1. Red Flags / Session Delays
Session runs longer than `end_ts`. The end job fires but FastF1 has no results yet.
- **Handling:** Leave status as `live`, log warning. Retry on next scheduler cycle.

### 2. Scheduler Restart
Server restarts mid-session, jobs not in memory.
- **Handling:** On startup, query for sessions where `status='live'` and `end_ts < now`. Re-queue end jobs.

### 3. Duplicate Job Execution
Multiple workers or job retry fires the same job twice.
- **Handling:** Idempotent status checks (only transition from expected state).

### 4. Session Cancelled
Session cancelled before it starts (e.g., weather).
- **Handling:** Manual status update to `cancelled`. Job checks status before transitioning.

## What We're NOT Building

- Real-time position updates during race
- Lap-by-lap timing
- Continuous backend polling
- Sub-minute data freshness
- WebSockets or push notifications

These could be added later if there's demand, but the widget's primary value is showing **results after sessions complete**.

## Tasks (Revised)

| ID | Task | Priority | Estimate |
|----|------|----------|----------|
| .1 | Add 'live' status to CalendarEvent | P0 | S |
| .2 | Schedule session start job to set 'live' status | P0 | S |
| .3 | Update frontend to show "In Progress" for live sessions | P1 | S |
| .4 | Optional: Add polling to detect session completion | P2 | S |
| .5 | Unit tests | P2 | S |

## Success Metrics

1. Users see "In Progress" during live sessions (not empty/stale data)
2. Results appear within 10 minutes of session end
3. No additional backend load during sessions

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-25 | Claude | Initial draft with continuous polling |
| 2026-02-25 | Claude | Simplified to session boundary ingestion |
| 2026-02-25 | Claude | Incorporated Codex review feedback (idempotent jobs, edge cases, API contract) |
