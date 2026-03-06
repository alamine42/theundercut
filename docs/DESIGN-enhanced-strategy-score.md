# Enhanced Strategy Score - Design Document

_Created: March 5, 2026_

## 1. Overview

Enhance the existing `team_strategy_score` field in `DriveGradeBreakdown` with a comprehensive model that evaluates team strategy decisions and their impact on race outcomes. The score evaluates pit timing, tire compound selection, safety car response, and weather calls.

### Goals
- **Explainable**: Component sub-scores + decision log showing each strategic decision and its impact
- **Testable**: Deterministic calculations from race data, validated against historical race outcomes
- **Simple metric**: Final 0-100 score that's easy to understand and compare

### Non-Goals
- Real-time scoring during live sessions (post-race only)
- Driver skill evaluation (that's what Drive Grade racecraft/consistency handles)
- Financial/commercial strategy decisions

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     StrategyScoreEngine                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│
│  │ PitTiming    │  │ TireSelect   │  │ SafetyCar    │  │ Weather  ││
│  │ Scorer       │  │ Scorer       │  │ Scorer       │  │ Scorer   ││
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘│
│         │                 │                 │                │      │
│         └─────────────────┴────────┬────────┴────────────────┘      │
│                                    │                                │
│  ┌────────────────┐  ┌─────────────┴───────┐  ┌────────────────┐   │
│  │ Hindsight      │  │ Position Delta      │  │ Peer           │   │
│  │ Simulator      │  │ Analyzer            │  │ Comparison     │   │
│  └────────────────┘  └─────────────────────┘  └────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  StrategyScore (0-100) + StrategyDecision[] (decision log)         │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **Ingestion completes** → Race data available in `lap_times`, `stints`, `calendar_events`
2. **StrategyScoreEngine triggered** → Loads race data from DB
3. **Factor scorers run** → Each produces sub-score + decisions
4. **Supporting engines provide context** → Simulation, position delta, peer comparison
5. **Scores combined** → Weighted average of factor scores
6. **Results persisted** → `StrategyScore` and `StrategyDecision` tables

## 3. Database Schema

### 3.1 New Tables

```sql
-- Core strategy score per driver per race (linked to Entry for referential integrity)
CREATE TABLE strategy_scores (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES core.entries(id) ON DELETE CASCADE,

    -- Component scores (0-100)
    total_score FLOAT NOT NULL,
    pit_timing_score FLOAT NOT NULL,
    tire_selection_score FLOAT NOT NULL,
    safety_car_score FLOAT NOT NULL,
    weather_score FLOAT NOT NULL,

    -- Metadata for recomputation
    calibration_profile VARCHAR(50) NOT NULL,
    calibration_version VARCHAR(20) NOT NULL,  -- Track which version was used
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(entry_id)  -- One score per entry, enables idempotent upserts
);

-- Decision log for explainability
CREATE TABLE strategy_decisions (
    id SERIAL PRIMARY KEY,
    strategy_score_id INTEGER NOT NULL REFERENCES strategy_scores(id) ON DELETE CASCADE,

    -- Decision context
    lap_number INTEGER NOT NULL,
    decision_type VARCHAR(50) NOT NULL,  -- 'pit_stop', 'stay_out', 'tire_change', 'compound_choice', etc.
    factor VARCHAR(20) NOT NULL,         -- 'pit_timing', 'tire_selection', 'safety_car', 'weather'

    -- Impact assessment
    impact_score FLOAT NOT NULL,         -- Positive = good decision, negative = bad
    position_delta INTEGER,              -- Positions gained/lost (nullable)
    time_delta_ms INTEGER,               -- Time gained/lost in milliseconds (nullable)

    -- Explainability
    explanation TEXT NOT NULL,           -- Human-readable explanation
    comparison_context TEXT,             -- What peers did, simulation alternative, etc.

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Safety Car/VSC periods (required for SafetyCar scorer)
CREATE TABLE race_control_events (
    id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES core.races(id),

    event_type VARCHAR(20) NOT NULL,     -- 'safety_car', 'vsc', 'red_flag'
    start_lap INTEGER NOT NULL,
    end_lap INTEGER,                      -- NULL if race ends under SC
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    cause TEXT,                           -- Incident description if available

    UNIQUE(race_id, event_type, start_lap)
);

-- Weather conditions during race (required for Weather scorer)
CREATE TABLE race_weather (
    id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES core.races(id),
    lap_number INTEGER NOT NULL,

    track_status VARCHAR(20) NOT NULL,   -- 'dry', 'damp', 'wet'
    air_temp_c FLOAT,
    track_temp_c FLOAT,
    humidity_pct FLOAT,
    rain_intensity VARCHAR(20),          -- 'none', 'light', 'moderate', 'heavy'

    UNIQUE(race_id, lap_number)
);

-- Per-lap position snapshots (required for position delta analysis)
CREATE TABLE lap_positions (
    id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES core.races(id),
    entry_id INTEGER NOT NULL REFERENCES core.entries(id),
    lap_number INTEGER NOT NULL,

    position INTEGER NOT NULL,           -- Race position at end of lap
    gap_to_leader_ms INTEGER,            -- Gap to P1 in milliseconds
    gap_to_ahead_ms INTEGER,             -- Gap to car ahead

    UNIQUE(race_id, entry_id, lap_number)
);

CREATE INDEX idx_strategy_scores_entry ON strategy_scores(entry_id);
CREATE INDEX idx_strategy_decisions_score ON strategy_decisions(strategy_score_id);
CREATE INDEX idx_race_control_events_race ON race_control_events(race_id);
CREATE INDEX idx_race_weather_race ON race_weather(race_id);
CREATE INDEX idx_lap_positions_race ON lap_positions(race_id, lap_number);
```

### 3.2 Integration with Existing Schema

- `strategy_scores.entry_id` → References `core.entries` for proper FK integrity
- Driver/team info derived via `entries` → `drivers`/`teams` joins
- `race_control_events` and `race_weather` provide SC/weather data for scorers
- `lap_positions` provides position delta data for analysis
- Enables idempotent upserts: `ON CONFLICT (entry_id) DO UPDATE`

## 4. Factor Scorers

### 4.1 Pit Timing Scorer

**Inputs:**
- Actual pit stop laps from `stints`
- Lap times surrounding pit windows
- Position data before/after stops

**Evaluates:**
- **Undercut detection**: Did pitting early gain positions on competitors?
- **Overcut detection**: Did staying out on better tires gain advantage?
- **Pit window optimization**: Was the stop in the optimal degradation window?
- **Reaction to traffic**: Did pit timing avoid rejoining in traffic?

**Output:** Score 0-100 + list of `PitDecision` events

### 4.2 Tire Compound Selection Scorer

**Inputs:**
- Compounds used per stint from `stints`
- Track temperature data (if available)
- Compound performance data from session

**Evaluates:**
- **Compound suitability**: Did chosen compound match track conditions?
- **Stint length achievement**: Did stint match expected compound life?
- **Strategy sequence**: Was the compound order optimal (e.g., M-H vs H-M)?
- **Starting tire choice**: Was qualifying tire strategy sound?

**Output:** Score 0-100 + list of `TireDecision` events

### 4.3 Safety Car Response Scorer

**Inputs:**
- Safety Car and VSC periods from session data
- Pit stops relative to SC windows
- Position changes during SC periods

**Evaluates:**
- **Opportunistic pitting**: Did team capitalize on "free" pit stops?
- **Queue timing**: How quickly did they react (vs being stuck in queue)?
- **Stay-out decisions**: Was staying out the right call?
- **Track position trade-offs**: Did SC strategy gain or lose net positions?

**Output:** Score 0-100 + list of `SCDecision` events

**Edge case:** Races with no safety car periods → Return neutral score (50)

### 4.4 Weather Response Scorer

**Inputs:**
- Weather transitions from session data
- Tire compound changes (slicks ↔ inters ↔ wets)
- Timing of compound switches relative to field

**Evaluates:**
- **Transition timing**: First to switch vs. field average
- **Correct compound choice**: Inters vs wets vs staying on slicks
- **Risk/reward assessment**: Gambling on weather changes

**Output:** Score 0-100 + list of `WeatherDecision` events

**Edge case:** Dry races → Return neutral score (50) with no decisions

## 5. Supporting Engines

### 5.1 Hindsight Simulation Engine

Simulates alternative strategy choices to provide "what-if" baselines:

- Given actual race data, model what would have happened with different pit timing
- Account for traffic, tire degradation curves, and track position
- Output: Projected position for alternative strategies

**Example:** "If Hamilton pitted on lap 20 instead of lap 25, simulation projects P3 finish instead of P4"

### 5.2 Position Delta Analyzer

Tracks position changes and attributes them to strategic decisions:

- Monitor position changes around each pit stop
- Identify undercut victims and overcut successes
- Calculate net position gain/loss per decision
- Separate strategy-driven changes from pace-driven changes

### 5.3 Peer Comparison Logic

Provides relative context for scoring:

- Group cars by similar pace (within X seconds per lap)
- Compare strategic choices to peer group
- Calculate percentile ranking for each factor
- Adjusts absolute scores based on relative performance

## 6. Score Calculation

### 6.1 Component Weights

```python
FACTOR_WEIGHTS = {
    'pit_timing': 0.35,       # Biggest impact factor
    'tire_selection': 0.30,   # Compound choice matters
    'safety_car': 0.20,       # Opportunistic gains
    'weather': 0.15,          # Less common but high impact
}
```

### 6.2 Final Score Formula

```python
total_score = (
    pit_timing_score * 0.35 +
    tire_selection_score * 0.30 +
    safety_car_score * 0.20 +
    weather_score * 0.15
)
```

For races without SC or weather changes, weights are renormalized:
- No SC: pit_timing=0.45, tire=0.40, weather=0.15
- No weather: pit_timing=0.40, tire=0.35, safety_car=0.25
- Neither: pit_timing=0.55, tire=0.45

### 6.3 Score Interpretation

| Score Range | Interpretation |
|-------------|----------------|
| 90-100 | Exceptional strategy, maximized opportunities |
| 75-89 | Strong strategy, few missed opportunities |
| 60-74 | Solid strategy, some suboptimal decisions |
| 45-59 | Average strategy, clear room for improvement |
| 30-44 | Poor strategy, significant positions lost |
| 0-29 | Strategy disaster, major errors |

## 7. API Endpoints

### 7.1 Race Strategy Scores

```
GET /api/v1/strategy/{season}/{round}/scores
```

Returns all driver strategy scores for a race:

```json
{
  "race": {"season": 2026, "round": 3, "name": "Australian GP"},
  "scores": [
    {
      "driver": "VER",
      "team": "Red Bull",
      "total_score": 87,
      "components": {
        "pit_timing": 92,
        "tire_selection": 85,
        "safety_car": 78,
        "weather": 50
      },
      "decision_count": 5
    }
  ]
}
```

### 7.2 Driver Strategy Detail

```
GET /api/v1/strategy/{season}/{round}/driver/{driver}
```

Returns detailed breakdown + decision log:

```json
{
  "driver": "VER",
  "team": "Red Bull",
  "total_score": 87,
  "components": {...},
  "decisions": [
    {
      "lap": 18,
      "type": "pit_stop",
      "factor": "pit_timing",
      "impact": +12,
      "position_delta": +2,
      "explanation": "Undercut on Norris successful, gained 2 positions",
      "comparison": "Pitted 3 laps before peer average"
    }
  ]
}
```

## 8. Calibration

### 8.1 Calibration Parameters

```json
{
  "strategy_score": {
    "factor_weights": {
      "pit_timing": 0.35,
      "tire_selection": 0.30,
      "safety_car": 0.20,
      "weather": 0.15
    },
    "pit_timing": {
      "undercut_detection_laps": 3,
      "optimal_window_tolerance": 2,
      "traffic_penalty_threshold": 3.0
    },
    "tire_selection": {
      "stint_deviation_penalty": 0.1,
      "compound_mismatch_penalty": 0.2
    },
    "safety_car": {
      "reaction_bonus_threshold": 2,
      "queue_penalty_laps": 5
    },
    "peer_comparison": {
      "pace_delta_threshold": 0.5,
      "min_peer_group_size": 3
    }
  }
}
```

### 8.2 Integration with CalibrationProfile

Extend existing `CalibrationProfile` dataclass with strategy scoring parameters. JSON files under `configs/calibration/` remain source of truth.

## 9. Integration Points

### 9.1 Ingestion Hook

After `ingest_session()` completes for a race:

1. Check if race has ended (`session_type == 'race'`, `status == 'ingested'`)
2. Ingest supporting data (SC/VSC periods, weather, lap positions) if not already present
3. Enqueue `compute_strategy_score` job
4. Job loads race data, runs engine, persists results with **idempotent upsert**
5. Invalidate relevant caches

### 9.2 Idempotent Upsert Strategy

All score writes use `ON CONFLICT DO UPDATE` to handle re-ingestion and calibration changes:

```python
# Idempotent upsert for strategy scores
INSERT INTO strategy_scores (entry_id, total_score, ..., calibration_profile, calibration_version)
VALUES (...)
ON CONFLICT (entry_id) DO UPDATE SET
    total_score = EXCLUDED.total_score,
    ...,
    calibration_profile = EXCLUDED.calibration_profile,
    calibration_version = EXCLUDED.calibration_version,
    computed_at = NOW();

# Clear old decisions and insert new ones
DELETE FROM strategy_decisions WHERE strategy_score_id = ?;
INSERT INTO strategy_decisions ...;
```

### 9.3 Recompute & Backfill CLI

CLI commands for retroactive score computation:

```bash
# Recompute all scores for a season with current calibration
python -m theundercut.cli strategy-score recompute --season 2026

# Recompute specific race
python -m theundercut.cli strategy-score recompute --season 2026 --round 5

# Backfill historical seasons
python -m theundercut.cli strategy-score backfill --seasons 2024,2025
```

### 9.4 Drive Grade Integration

Update `DriveGradeBreakdown.team_strategy_score` to use the new detailed score:

```python
# In pipeline.py
def score_driver(self, driver_input: DriverRaceInput) -> DriveGradeBreakdown:
    # ... existing code ...

    # Use enhanced strategy score if available
    if enhanced_strategy_score := self.strategy_engine.score(driver_input):
        strategy = enhanced_strategy_score.total_score / 100  # Normalize to 0-1
    else:
        strategy = compute_strategy_score(driver_input.strategy, calibration=self.calibration)
```

## 10. Testing Strategy

### 10.1 Unit Tests

- Each factor scorer tested independently with mock race data
- Edge cases: no SC, no weather, DNF, red flag, etc.
- Score calculation with various weight combinations

### 10.2 Integration Tests

- Full engine flow with real FastF1 data from past races
- Verify decision log accuracy against known race events
- Database persistence and retrieval

### 10.3 Validation

- Compare scores against expert analysis (published strategy reviews)
- Correlation with race results (good strategy → better finish delta)
- Season aggregates match team reputation (e.g., Ferrari strategy memes)

## 11. Data Source Investigation

### 11.1 Safety Car / VSC Data

**FastF1 availability**: FastF1 provides race control messages via `session.race_control_messages` which includes SC, VSC, and red flag events with timestamps. This is the primary source.

**Fallback**: OpenF1 API provides `/race_control` endpoint with similar data.

**Implementation**: Parse race control messages during ingestion, extract SC/VSC periods, persist to `race_control_events` table.

### 11.2 Weather Data

**FastF1 availability**: FastF1 provides weather data via `session.weather_data` with air/track temps, humidity, rainfall, and track status per lap.

**Implementation**: Extract weather data during ingestion, persist lap-by-lap to `race_weather` table.

### 11.3 Lap Position Data

**FastF1 availability**: FastF1 provides position data via `session.results` and can be derived from lap times + pit stops.

**Implementation**: Compute position per lap during ingestion, persist to `lap_positions` table.

## 12. Open Questions (Resolved)

1. ~~**Data availability**: Does FastF1 provide reliable SC/VSC period data?~~ → **Yes**, via `race_control_messages`
2. ~~**Weather data**: What's the best source for track weather during sessions?~~ → **FastF1** `weather_data`
3. **Simulation complexity**: Start with simple "what-if" pit timing simulation; iterate based on accuracy validation
4. **Historical backfill**: Yes, add CLI command for backfill (see §9.3)

## 13. Implementation Phases (Revised)

### Phase 0: Data Prerequisites (NEW - Tasks .16, .17, .18)
**Must complete before scorer implementation**
- Ingest SC/VSC periods from FastF1 race control messages
- Ingest weather data from FastF1 weather_data
- Ingest/derive per-lap position data
- Update schema with new tables

### Phase 1: Foundation (Tasks .1, .2, .3)
- Database models and migration (updated schema with entry_id FK)
- Pit timing scorer (highest impact)
- Tire selection scorer

### Phase 2: Context Engines (Tasks .6, .7, .8)
- Position delta analyzer
- Peer comparison logic
- Basic hindsight simulation

### Phase 3: SC/Weather (Tasks .4, .5)
- Safety car response scorer (depends on Phase 0 SC data)
- Weather response scorer (depends on Phase 0 weather data)

### Phase 4: Integration (Tasks .9, .10, .11, .15, .19)
- StrategyScoreEngine orchestrator
- Ingestion pipeline integration (with idempotent upserts)
- API endpoints
- Calibration extension
- Recompute/backfill CLI commands

### Phase 5: Testing (Tasks .12, .13, .14)
- Unit tests
- Integration tests
- E2E tests
