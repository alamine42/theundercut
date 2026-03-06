# Testing The Undercut Frontend

## Overview
The Undercut is a Next.js 16 F1 analytics dashboard. The frontend lives in `web/` and connects to a FastAPI backend.

## Local Dev Server

```bash
cd web
FASTAPI_URL=https://theundercut-web.onrender.com npm run dev
```

This starts the frontend at `http://localhost:4000` using the production backend API.

## Unit Tests

Tests use Vitest + React Testing Library:

```bash
cd web
npx vitest run                    # run all tests
npx vitest run src/components/race-weekend/__tests__/RaceWeekendWidget.test.tsx  # specific test file
```

## Testing Time-Dependent Widget States

The Race Weekend Widget (`web/src/components/race-weekend/RaceWeekendWidget.tsx`) has 5 states that depend on session times relative to the current time: `off-week`, `pre-weekend`, `race-week`, `during-weekend`, `post-race`.

Since you can't manipulate time in the live app, create a **temporary test page** at `web/src/app/test-widget/page.tsx` that:
1. Imports `RaceWeekendWidget` and the `WeekendResponse` type
2. Creates mock `WeekendResponse` objects with session times relative to `new Date()` (using helpers like `hoursAgo(n)` and `hoursFromNow(n)`)
3. Renders multiple widget instances side-by-side, one per state
4. Navigate to `http://localhost:4000/test-widget` to visually verify

**Important**: Remove the temporary test page after testing - do not commit it.

## Key Files

- `web/src/components/race-weekend/RaceWeekendWidget.tsx` - Main widget with state machine logic
- `web/src/components/race-weekend/RaceHeader.tsx` - Header component (title display)
- `web/src/components/race-weekend/types.ts` - TypeScript interfaces
- `web/src/app/page.tsx` - Homepage that renders the widget (around line 133)

## API Notes

- The backend at `https://theundercut-web.onrender.com` may return `race_name: null` from `/weekend` endpoint early in the season or between races
- When `race_name` is null, the widget title correctly falls back to "Upcoming Race" regardless of state
- To test the GP name title display, you need mock data with a non-null `race_name`

## No Auth Required

No authentication or secrets are needed for local frontend testing. The backend API is publicly accessible.

## No CI Configured

As of March 2026, this repo has no CI checks configured. Rely on local lint (`npm run lint`) and unit tests for verification.
