# Testing The Undercut Frontend

## Local Dev Server Setup

1. Create `.env.local` in the `web/` directory:
   ```
   FASTAPI_URL=https://theundercut-web.onrender.com
   ```
2. Start the dev server:
   ```bash
   cd web && NEXT_PUBLIC_SITE_URL=http://localhost:3000 npx next dev -p 3000
   ```
3. If you get a lock file error, remove it:
   ```bash
   rm -f web/.next/dev/lock
   fuser -k 3000/tcp 2>/dev/null
   ```

## Devin Secrets Needed

No secrets are required for frontend testing against production. The production API at `https://theundercut-web.onrender.com` is publicly accessible.

## Key Testing Scenarios

### Countdown Timer
- Navigate to homepage (`/`)
- The countdown widget shows hours, minutes, and seconds (SEC unit)
- Verify the seconds value changes every second by waiting 3-5 seconds
- The countdown should tick live without page refresh

### Hydration Errors (React #418)
- Open browser console before navigating to the page
- Navigate to homepage and check for `React error #418` or hydration mismatch warnings
- Only unrelated warnings (e.g., Agentation session) should appear
- The `hasMounted` pattern in `RaceWeekendWidget.tsx` prevents hydration mismatches from `new Date()` calls
- `RaceCountdown.tsx` defers countdown calculation to client via `useCountdown` hook (returns null on server)

### GP Name Display
- The widget title shows the GP name (e.g., "Japanese Grand Prix") when the backend API returns `race_name` for the round
- If `race_name` is null (backend fix not deployed or Race table not populated), it falls back to "Upcoming Race"
- The backend uses OpenF1 API as fallback when no Race record exists (for upcoming/not-yet-ingested rounds)

### Circuit Characteristics
- Displayed below the countdown when `circuitCharacteristics` prop is non-null
- Requires the backend to return a correct Jolpica-style `circuit_id` (e.g., `suzuka`, not `circuit_2026_3`)
- The frontend maps `circuit_id` → full DB name via `getCircuitNameFromJolpicaId()` in `constants.ts`
- Score badges show Downforce, Tire Deg, Overtaking, and Throttle scores

## Common Issues

- **Lock file error**: If the dev server crashes or is killed, a lock file at `web/.next/dev/lock` may prevent restart. Delete it manually.
- **Backend returning nulls**: The production backend might return null for `race_name`, `circuit_name`, etc. if the OpenF1 fallback isn't deployed yet or the Race table hasn't been populated for that round.
- **OpenF1 circuit_short_name mismatch**: The backend has an `OPENF1_TO_JOLPICA_CIRCUIT` mapping in `src/theundercut/api/v1/race.py` that maps OpenF1 names (e.g., "Melbourne") to Jolpica IDs (e.g., "albert_park"). If a new circuit is added, this mapping may need updating.

## Running Tests

```bash
cd web && npx vitest run
```

All 91 tests should pass. Key test files:
- `RaceCountdown.test.tsx` — countdown display, ticking, accessibility
- `RaceWeekendWidget.test.tsx` — widget states, hydration safety
- `SessionCard.test.tsx` — session card rendering
