# Design: Circuit Characteristics

**Epic:** theundercut-cct
**Status:** Planning
**Author:** Mehdi El-Amine
**Date:** 2026-03-10

## Overview

Add comprehensive circuit/track characteristics data to enable comparison and ranking of F1 circuits. This allows fans to understand track profiles and compare circuits across multiple dimensions.

## Problem Statement

Currently, circuit data in the system is minimal (name, country, coordinates). Users cannot:
- Understand what makes each track unique
- Compare track characteristics side-by-side
- See which tracks favor certain driving styles or car setups

## Goals

1. Store rich characteristics data for each circuit
2. Provide API endpoints for accessing, comparing, and ranking circuits
3. Build a frontend UI for circuit comparison and visualization

## Non-Goals

- Real-time telemetry integration
- Predictive modeling based on characteristics

## Deferred for V2

- **Full per-season versioning**: While we add `effective_year` for major layout changes (see below), comprehensive per-lap historical data is out of scope for V1.

## Data Model

### Circuit Characteristics Fields

| Field | Type | Scale | Description |
|-------|------|-------|-------------|
| `full_throttle_pct` | Float | - | Percentage of track at full throttle (e.g., 72.5%) |
| `full_throttle_score` | Integer | 1-10 | Normalized score |
| `average_speed_kph` | Float | - | Circuit average speed in km/h |
| `average_speed_score` | Integer | 1-10 | Normalized score |
| `tire_degradation_score` | Integer | 1-10 | Expected tire wear level |
| `tire_degradation_label` | String | - | Low / Medium / High / Very High |
| `track_abrasion_score` | Integer | 1-10 | Surface roughness |
| `track_abrasion_label` | String | - | Low / Medium / High |
| `corners_slow` | Integer | - | Corners < 100 kph |
| `corners_medium` | Integer | - | Corners 100-180 kph |
| `corners_fast` | Integer | - | Corners > 180 kph |
| `downforce_score` | Integer | 1-10 | Required aero downforce |
| `downforce_label` | String | - | Low / Medium / High |
| `overtaking_difficulty_score` | Integer | 1-10 | 10 = hardest to pass |
| `overtaking_difficulty_label` | String | - | Easy / Medium / Hard |
| `drs_zones` | Integer | - | Count of DRS zones |
| `circuit_type` | String | - | Street / Permanent / Hybrid |
| `effective_year` | Integer | - | Year this configuration became active (for layout changes) |
| `data_completeness` | String | - | complete / partial / unknown |
| `last_updated` | DateTime | - | When characteristics were last modified |

### Schema Design

Create a new `circuit_characteristics` table rather than extending `core.circuits` to support layout versioning:

```sql
CREATE TABLE core.circuit_characteristics (
    id SERIAL PRIMARY KEY,
    circuit_id INTEGER NOT NULL REFERENCES core.circuits(id),
    effective_year INTEGER NOT NULL DEFAULT 2024,

    -- Performance characteristics
    full_throttle_pct FLOAT,
    full_throttle_score INTEGER CHECK (full_throttle_score BETWEEN 1 AND 10),
    average_speed_kph FLOAT,
    average_speed_score INTEGER CHECK (average_speed_score BETWEEN 1 AND 10),

    -- Tire characteristics
    tire_degradation_score INTEGER CHECK (tire_degradation_score BETWEEN 1 AND 10),
    tire_degradation_label VARCHAR(20),
    track_abrasion_score INTEGER CHECK (track_abrasion_score BETWEEN 1 AND 10),
    track_abrasion_label VARCHAR(20),

    -- Corner profile
    corners_slow INTEGER,
    corners_medium INTEGER,
    corners_fast INTEGER,

    -- Aerodynamic requirements
    downforce_score INTEGER CHECK (downforce_score BETWEEN 1 AND 10),
    downforce_label VARCHAR(20),

    -- Racing characteristics
    overtaking_difficulty_score INTEGER CHECK (overtaking_difficulty_score BETWEEN 1 AND 10),
    overtaking_difficulty_label VARCHAR(20),
    drs_zones INTEGER,

    -- Circuit classification
    circuit_type VARCHAR(20) CHECK (circuit_type IN ('Street', 'Permanent', 'Hybrid')),

    -- Metadata
    data_completeness VARCHAR(20) DEFAULT 'unknown' CHECK (data_completeness IN ('complete', 'partial', 'unknown')),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE (circuit_id, effective_year)
);

CREATE INDEX idx_circuit_chars_circuit_year ON core.circuit_characteristics(circuit_id, effective_year DESC);
```

### Migration & Deployment Plan

1. **Migration**: Create Alembic migration for `circuit_characteristics` table
2. **Deploy order**: Run migration → Deploy API → Run seed script
3. **Rollback**: Migration includes `downgrade()` to drop table
4. **Verification**: Automated test confirms ORM matches schema

## API Design

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/circuits` | List all circuits with characteristics |
| GET | `/api/v1/circuits/{id}` | Get single circuit with full details |
| GET | `/api/v1/circuits/{id}/characteristics` | Get just characteristics data |
| GET | `/api/v1/circuits/{id}/characteristics?year=2022` | Get characteristics for specific layout year |
| GET | `/api/v1/circuits/compare?ids=1,5,12` | Compare 2-5 circuits |
| GET | `/api/v1/circuits/rank?by=full_throttle_score&order=desc` | Rank circuits |
| PUT | `/api/v1/circuits/{id}/characteristics` | Update characteristics (admin, authenticated) |

### Authentication

The PUT endpoint requires admin authentication:
- **Mechanism**: API key in `X-Admin-Key` header
- **Provisioning**: Admin key stored in Render environment variable `ADMIN_API_KEY`
- **Audit**: All writes logged with timestamp and source IP
- **Rate limiting**: 10 requests/minute per admin key

### Response Format

```json
{
  "id": 1,
  "name": "Albert Park Circuit",
  "country": "Australia",
  "latitude": -37.8497,
  "longitude": 144.9680,
  "characteristics": {
    "effective_year": 2022,
    "data_completeness": "complete",
    "last_updated": "2026-03-10T12:00:00Z",
    "full_throttle": { "value": 72.5, "score": 7 },
    "average_speed": { "value": 238.5, "score": 8 },
    "tire_degradation": { "score": 6, "label": "Medium-High" },
    "track_abrasion": { "score": 5, "label": "Medium" },
    "corners": { "slow": 4, "medium": 6, "fast": 4, "total": 14 },
    "downforce": { "score": 5, "label": "Medium" },
    "overtaking": { "score": 6, "label": "Medium" },
    "drs_zones": 3,
    "circuit_type": "Permanent"
  }
}
```

### Handling Incomplete Data

When characteristics are partial or missing:

```json
{
  "id": 25,
  "name": "New Circuit",
  "country": "Country",
  "characteristics": {
    "effective_year": 2026,
    "data_completeness": "partial",
    "last_updated": "2026-03-01T00:00:00Z",
    "full_throttle": null,
    "average_speed": { "value": 210.0, "score": 6 },
    "tire_degradation": null,
    "corners": { "slow": null, "medium": null, "fast": null, "total": null },
    ...
  }
}
```

**Client Contract:**
- `null` values indicate missing data (not zero)
- `data_completeness: "partial"` signals incomplete characteristics
- UI must show "Data unavailable" badges for null fields
- Rankings exclude circuits with null values for the ranked field
```

### Comparison Response

```json
{
  "circuits": [
    { "id": 1, "name": "Albert Park", "characteristics": {...} },
    { "id": 5, "name": "Monaco", "characteristics": {...} }
  ],
  "comparison": {
    "highest_full_throttle": { "circuit_id": 1, "value": 72.5 },
    "most_corners": { "circuit_id": 5, "total": 19 }
  }
}
```

### Ranking Response

```json
{
  "ranking": [
    { "rank": 1, "circuit_id": 15, "name": "Monza", "value": 80.1, "score": 10 },
    { "rank": 2, "circuit_id": 12, "name": "Spa", "value": 75.2, "score": 9 }
  ],
  "ranked_by": "full_throttle_score",
  "order": "desc",
  "total": 24
}
```

## Data Sources

Research from:
1. **Official F1 telemetry data** - Full throttle %, average speeds
2. **Pirelli tire performance reports** - Degradation levels, abrasion data
3. **FIA technical bulletins** - DRS zones, circuit specifications
4. **Trusted motorsport sources** - f1-tempo.com, racefans.net, formula1.com

### Data Format

Seed data stored in `data/circuit_characteristics.json`:

```json
{
  "albert_park": {
    "full_throttle_pct": 72.5,
    "average_speed_kph": 238.5,
    "tire_degradation": { "score": 6, "label": "Medium-High" },
    "corners": { "slow": 4, "medium": 6, "fast": 4 },
    "downforce": { "score": 5, "label": "Medium" },
    "overtaking_difficulty": { "score": 6, "label": "Medium" },
    "track_abrasion": { "score": 5, "label": "Medium" },
    "drs_zones": 3,
    "circuit_type": "Permanent"
  }
}
```

## Frontend Design

### Pages

1. **Circuit List** (`/circuits`) - Grid/table with sortable columns
2. **Circuit Detail** (`/circuits/{id}`) - Full characteristics + radar chart
3. **Circuit Comparison** (`/circuits/compare?ids=1,5,12`) - Side-by-side
4. **Circuit Rankings** (`/circuits/rankings`) - Bar chart by characteristic

### Components

```
web/src/components/circuits/
├── CircuitCard.tsx
├── CircuitCharacteristicsDisplay.tsx
├── CircuitRadarChart.tsx
├── CircuitComparisonTable.tsx
├── CircuitRankingChart.tsx
└── index.ts
```

### Visual Design

- **Score indicators**: Color + icon + text label (accessible for color-blind users)
  - Low (1-3): Red background + down arrow + "Low" text
  - Medium (4-6): Yellow background + dash icon + "Medium" text
  - High (7-10): Green background + up arrow + "High" text
- Radar chart for multi-dimensional comparison
- Responsive: stack on mobile, grid on desktop
- Dark mode compatible

### UI States

| State | Circuit List | Circuit Detail | Comparison | Rankings |
|-------|--------------|----------------|------------|----------|
| **Loading** | Skeleton cards | Skeleton sections | Skeleton table | Skeleton bars |
| **Empty** | "No circuits found" message | N/A (404) | "Select circuits to compare" | "No data for this characteristic" |
| **Partial data** | Gray "incomplete" badge | "Data unavailable" for null fields | Cells show "N/A" | Excluded from ranking |
| **Error** | Retry button + error message | Retry button | Per-circuit error indicators | Retry button |

### Mobile Behavior
- **List page**: Single column card layout
- **Detail page**: Stacked sections, radar chart 100% width
- **Comparison**: Horizontal scroll table OR swipeable cards
- **Rankings**: Vertical bar chart, full width

## Caching Strategy

### Cache Keys
- `circuit:{id}:characteristics:{year}` - Single circuit characteristics
- `circuits:list` - Full circuit list with characteristics
- `circuits:compare:{sorted_ids}` - Comparison results
- `circuits:rank:{field}:{order}` - Ranking results

### TTLs
- Single circuit: 24 hours
- List/compare/rank: 1 hour

### Invalidation Triggers
All caches are invalidated via `_bust_circuit_cache(circuit_id)` when:
1. Admin PUT endpoint updates characteristics
2. Seed script runs (CLI command)
3. New `effective_year` record is created

### Implementation
```python
def _bust_circuit_cache(circuit_id: int):
    """Invalidate all caches related to a circuit."""
    redis_client.delete(f"circuit:{circuit_id}:characteristics:*")
    redis_client.delete("circuits:list")
    # Pattern delete for comparisons containing this circuit
    for key in redis_client.scan_iter(f"circuits:compare:*{circuit_id}*"):
        redis_client.delete(key)
    # Delete all rankings (circuit may affect any ranking)
    for key in redis_client.scan_iter("circuits:rank:*"):
        redis_client.delete(key)
```

## Implementation Plan

| Task | Description | Priority | Depends On |
|------|-------------|----------|------------|
| cct.1 | Create CircuitCharacteristics model + Alembic migration | P0 | - |
| cct.2 | Create API endpoints (read + authenticated write) | P1 | cct.1 |
| cct.3 | Create comparison/ranking endpoints | P1 | cct.2 |
| cct.4 | Research & seed circuit data with provenance tracking | P1 | cct.1 |
| cct.5 | Create frontend UI with accessible design | P1 | cct.2, cct.3 |
| cct.6 | Unit tests (API + caching + auth) | P2 | cct.2, cct.3 |
| cct.7 | E2E tests (including empty/error states) | P2 | cct.5 |

### Deployment Sequence
1. **Phase 1 (Backend)**: cct.1 → deploy migration → cct.4 (seed data)
2. **Phase 2 (API)**: cct.2 → cct.3 → deploy API
3. **Phase 3 (Frontend)**: cct.5 → deploy frontend
4. **Phase 4 (Testing)**: cct.6 → cct.7

## Open Questions

1. Should we include track length in characteristics? **→ Yes, add track_length_km**
2. Should scores be auto-computed from raw values or manually curated? **→ Manually curated with clear normalization docs**
3. Do we need an admin UI for editing characteristics, or is API-only sufficient? **→ API-only for V1, admin UI deferred**

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Data accuracy varies by source | Medium | Document provenance in seed JSON, prioritize official F1/FIA sources |
| Score normalization inconsistency | Medium | Create normalization guide doc, review during seeding |
| Track layout changes | High | `effective_year` field supports multiple configurations per circuit |
| Unauthorized data tampering | High | Admin API key authentication + audit logging |
| Stale cached data | Medium | Event-driven cache invalidation on all writes |

## Success Metrics

- All 24 current calendar circuits have complete characteristic data
- Comparison page load time < 500ms
- API response time < 100ms for single circuit
