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
  return apiFetch<WeekendResponse>(`/race/${season}/${round}/weekend`);
}
