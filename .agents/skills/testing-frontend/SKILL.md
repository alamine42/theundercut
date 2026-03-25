# Testing The Undercut Frontend

## Overview
The Undercut is a Next.js 16 F1 analytics dashboard. The frontend lives in `web/` and fetches data from a FastAPI backend.

## Local Development Setup

1. Navigate to `web/` directory
2. Install dependencies: `npm install`
3. Create `.env.local` with the backend URL:
   ```
   FASTAPI_URL=https://theundercut-web.onrender.com
   ```
4. For dev mode: `npx next dev -p 3000`
5. For production-like testing (recommended for hydration issues): `npx next build && npx next start -p 3000`

## Devin Secrets Needed
No secrets required. The production API at `https://theundercut-web.onrender.com` is publicly accessible (found in `render.yaml`).

## Running Tests
- Unit tests: `npx vitest run` (from `web/` directory)
- Currently 91 tests across 5 test files

## Common Issues

### React Hydration Errors (#418)
- **Symptom**: `Minified React error #418` in browser console
- **Root cause**: `new Date()` calls during render produce different values at build/ISR time vs client hydration time
- **How to reproduce**: Build with production API data (`FASTAPI_URL=... npx next build`), then `npx next start`. The statically generated HTML has stale date values that mismatch the client's live calculations.
- **Fix pattern**: Use `useEffect` to defer date-dependent calculations to after hydration. For minor text differences (locale formatting), use `suppressHydrationWarning`.
- **Important**: Files using React hooks (`useState`, `useEffect`) MUST have `"use client"` directive at the top for Turbopack compatibility.

### Build Timeouts on /circuits Page
- The circuits page makes multiple API calls during static generation
- If the backend is slow, these can exceed the 60-second build timeout
- Solution: Parallelize API calls with `Promise.all` and add timeouts with fallbacks

### SVG Preload Warnings
- Console shows many warnings about preloaded circuit SVGs not being used
- These are benign warnings, not errors — they come from circuit map images preloaded but not visible in the viewport

## Testing Hydration Fixes
To verify a hydration fix:
1. Build the main branch with production API and confirm error #418 appears (baseline)
2. Build the fix branch with production API and confirm error #418 does NOT appear
3. Hard refresh 2-3 times to rule out intermittent issues
4. Verify countdown widget shows correct non-zero values and ticks down over time

## Key Files
- `web/src/components/race-weekend/RaceWeekendWidget.tsx` — Main widget component
- `web/src/components/race-weekend/RaceCountdown.tsx` — Countdown timer (uses useCountdown hook)
- `web/src/components/race-weekend/SessionCard.tsx` — Session cards with time-dependent text
- `web/src/app/(main)/page.tsx` — Homepage
- `render.yaml` — Contains production API URL

## Production
- Frontend: https://www.theundercut.co/
- Backend API: https://theundercut-web.onrender.com
- Deployed via Render (see render.yaml)
