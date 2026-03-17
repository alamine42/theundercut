import { API_CONFIG } from "./constants";
import type {
  AnalyticsResponse,
  StandingsResponse,
  SimpleLapData,
  HomepageResponse,
  CircuitsResponse,
  CircuitDetailResponse,
  CircuitTrendsResponse,
  TestingEventsResponse,
  TestingDayResponse,
  TestingLapsResponse,
  RaceWeekendSchedule,
  SessionResultsResponse,
  CircuitHistoryResponse,
  WeekendResponse,
  WeekendSummaryResponse,
  CircuitsCharacteristicsResponse,
  CircuitWithCharacteristics,
  CircuitsRankingResponse,
  CircuitsCompareResponse,
} from "@/types/api";

const BASE_URL = API_CONFIG.baseUrl;

// =============================================================================
// Fetch Options with ISR
// =============================================================================

function fetchOptions(revalidate?: number): RequestInit {
  return {
    next: { revalidate: revalidate ?? API_CONFIG.revalidateSeconds },
  };
}

type QueryParam = string | number | boolean | Array<string | number | boolean> | null | undefined;

async function apiFetch<T>(
  path: string,
  options?: { query?: Record<string, QueryParam>; revalidate?: number }
): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`, getBaseUrl());
  const params = options?.query ?? {};
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((val) => {
        if (val !== undefined && val !== null) {
          url.searchParams.append(key, String(val));
        }
      });
    } else if (value !== undefined && value !== null) {
      url.searchParams.append(key, String(value));
    }
  });

  const res = await fetch(url.toString(), fetchOptions(options?.revalidate));
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status}`);
  }
  return res.json();
}

// =============================================================================
// Analytics API
// =============================================================================

export async function fetchAnalytics(
  season: number,
  round: number,
  drivers?: string[]
): Promise<AnalyticsResponse> {
  return apiFetch<AnalyticsResponse>(`/analytics/${season}/${round}`, {
    query: drivers && drivers.length > 0 ? { drivers } : undefined,
  });
}

// =============================================================================
// Standings API
// =============================================================================

export async function fetchStandings(
  season: number
): Promise<StandingsResponse> {
  return apiFetch<StandingsResponse>(`/standings/${season}`);
}

// =============================================================================
// Race Laps API
// =============================================================================

export async function fetchLaps(
  season: number,
  round: number,
  drivers?: string[]
): Promise<SimpleLapData[]> {
  return apiFetch<SimpleLapData[]>(`/race/${season}/${round}/laps`, {
    query: drivers && drivers.length > 0 ? { drivers } : undefined,
  });
}

// =============================================================================
// Homepage API
// =============================================================================

export async function fetchHomepage(): Promise<HomepageResponse> {
  return apiFetch<HomepageResponse>(`/homepage`);
}

// =============================================================================
// Circuits API
// =============================================================================

export async function fetchCircuits(
  season: number
): Promise<CircuitsResponse> {
  return apiFetch<CircuitsResponse>(`/circuits/${season}`);
}

export async function fetchCircuitDetail(
  season: number,
  circuitId: string
): Promise<CircuitDetailResponse> {
  return apiFetch<CircuitDetailResponse>(`/circuits/${season}/${circuitId}`);
}

export async function fetchCircuitTrends(
  circuitId: string
): Promise<CircuitTrendsResponse> {
  return apiFetch<CircuitTrendsResponse>(`/circuits/trends/${circuitId}`);
}

// =============================================================================
// Testing API
// =============================================================================

export async function fetchTestingEvents(
  season: number
): Promise<TestingEventsResponse> {
  return apiFetch<TestingEventsResponse>(`/testing/${season}`);
}

export async function fetchTestingDay(
  season: number,
  eventId: string,
  day: number,
  options?: { drivers?: string[]; includeLaps?: boolean }
): Promise<TestingDayResponse> {
  const query: Record<string, QueryParam> = {};
  if (options?.drivers && options.drivers.length > 0) {
    query.drivers = options.drivers;
  }
  if (options?.includeLaps) {
    query.include_laps = "true";
  }
  return apiFetch<TestingDayResponse>(`/testing/${season}/${eventId}/${day}`, { query });
}

export async function fetchTestingLaps(
  season: number,
  eventId: string,
  day: number,
  options?: { drivers?: string[]; offset?: number; limit?: number }
): Promise<TestingLapsResponse> {
  const url = new URL(
    `${getBaseUrl()}${BASE_URL}/testing/${season}/${eventId}/${day}/laps`,
    getBaseUrl() || "http://localhost"
  );

  if (options?.drivers) {
    options.drivers.forEach((d) => url.searchParams.append("drivers", d));
  }
  if (options?.offset !== undefined) {
    url.searchParams.set("offset", options.offset.toString());
  }
  if (options?.limit !== undefined) {
    url.searchParams.set("limit", options.limit.toString());
  }

  const res = await fetch(url.toString(), fetchOptions());

  if (!res.ok) {
    throw new Error(`Failed to fetch testing laps: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Helper to get base URL for server-side fetching
// =============================================================================

function getBaseUrl(): string {
  // On the server, we need the full URL
  if (typeof window === "undefined") {
    // Use the FASTAPI_URL directly for server-side requests
    return process.env.FASTAPI_URL || "http://localhost:8000";
  }
  // On the client, use relative URLs (will go through Next.js proxy)
  return "";
}

// =============================================================================
// Client-side fetcher for React Query
// =============================================================================

export async function clientFetchAnalytics(
  season: number,
  round: number,
  drivers?: string[]
): Promise<AnalyticsResponse> {
  const url = new URL(`${BASE_URL}/analytics/${season}/${round}`, window.location.origin);

  if (drivers && drivers.length > 0) {
    drivers.forEach((d) => url.searchParams.append("drivers", d));
  }

  const res = await fetch(url.toString());

  if (!res.ok) {
    throw new Error(`Failed to fetch analytics: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Race Weekend API
// =============================================================================

export async function fetchRaceWeekendSchedule(
  season: number,
  round: number
): Promise<RaceWeekendSchedule> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/race/${season}/${round}/schedule`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch race schedule: ${res.status}`);
  }

  return res.json();
}

export async function fetchSessionResults(
  season: number,
  round: number,
  sessionType: string
): Promise<SessionResultsResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/race/${season}/${round}/session/${sessionType}/results`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch session results: ${res.status}`);
  }

  return res.json();
}

export async function fetchCircuitHistory(
  season: number,
  circuitId: string
): Promise<CircuitHistoryResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/circuits/${season}/${circuitId}/history`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch circuit history: ${res.status}`);
  }

  return res.json();
}

export async function fetchWeekendData(
  season: number,
  round: number
): Promise<WeekendResponse> {
  return apiFetch<WeekendResponse>(`/race/${season}/${round}/weekend`, {
    revalidate: 5,
  });
}

export async function fetchWeekendSummary(
  season: number
): Promise<WeekendSummaryResponse> {
  return apiFetch<WeekendSummaryResponse>(`/race/${season}/weekend/summary`, {
    revalidate: 5,
  });
}

// =============================================================================
// Circuit Characteristics API
// =============================================================================

export async function fetchCircuitsCharacteristics(): Promise<CircuitsCharacteristicsResponse> {
  return apiFetch<CircuitsCharacteristicsResponse>(`/circuits/characteristics`);
}

export async function fetchCircuitCharacteristics(
  circuitId: number,
  year?: number
): Promise<CircuitWithCharacteristics> {
  return apiFetch<CircuitWithCharacteristics>(
    `/circuits/characteristics/${circuitId}`,
    { query: year ? { year } : undefined }
  );
}

export async function fetchCircuitsCompare(
  ids: number[]
): Promise<CircuitsCompareResponse> {
  return apiFetch<CircuitsCompareResponse>(`/circuits/characteristics/compare`, {
    query: { ids: ids.join(",") },
  });
}

export async function fetchCircuitsRanking(
  field: string,
  order: "asc" | "desc" = "desc",
  limit?: number
): Promise<CircuitsRankingResponse> {
  return apiFetch<CircuitsRankingResponse>(`/circuits/characteristics/rank`, {
    query: { by: field, order, limit },
  });
}

// Characteristic fields with their display info
// Note: API expects field names with _score suffix
const CHARACTERISTIC_FIELDS = [
  { field: "full_throttle_score", label: "Full Throttle", highIsNotable: true },
  { field: "average_speed_score", label: "Fastest", highIsNotable: true },
  { field: "tire_degradation_score", label: "High Tire Deg", highIsNotable: true },
  { field: "track_abrasion_score", label: "High Abrasion", highIsNotable: true },
  { field: "downforce_score", label: "High Downforce", highIsNotable: true },
  { field: "overtaking_difficulty_score", label: "Easy Overtaking", highIsNotable: true },
] as const;

// Compute notable rankings for all circuits
export async function fetchAllCircuitRankings(): Promise<Map<string, Array<{ field: string; label: string; rank: number; value: number; isTop: boolean }>>> {
  // Fetch rankings for each characteristic (top and bottom 8)
  const rankingPromises = CHARACTERISTIC_FIELDS.flatMap(({ field, label, highIsNotable }) => [
    // Top 8 (high values)
    fetchCircuitsRanking(field, "desc", 8).then(res => ({
      ranking: res.ranking,
      label: highIsNotable ? label : label.replace("High", "Low"),
      isTop: highIsNotable,
    })),
    // Bottom 8 (low values) - only for some metrics where low is notable
    fetchCircuitsRanking(field, "asc", 8).then(res => ({
      ranking: res.ranking,
      label: highIsNotable ? label.replace("High", "Low").replace("Easy", "Hard").replace("Fastest", "Slowest").replace("Full Throttle", "Low Throttle") : label,
      isTop: !highIsNotable,
    })),
  ]);

  const results = await Promise.all(rankingPromises);

  // Build map of circuit name -> notable rankings
  const circuitRankings = new Map<string, Array<{ field: string; label: string; rank: number; value: number; isTop: boolean }>>();

  results.forEach(({ ranking, label, isTop }) => {
    ranking.forEach(r => {
      const existing = circuitRankings.get(r.name) || [];
      existing.push({
        field: label,
        label,
        rank: r.rank,
        value: r.value,
        isTop,
      });
      circuitRankings.set(r.name, existing);
    });
  });

  // Sort each circuit's rankings by rank (best first) and limit to top 3
  circuitRankings.forEach((rankings, name) => {
    const sorted = rankings
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 3);
    circuitRankings.set(name, sorted);
  });

  return circuitRankings;
}
