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

// =============================================================================
// Analytics API
// =============================================================================

export async function fetchAnalytics(
  season: number,
  round: number,
  drivers?: string[]
): Promise<AnalyticsResponse> {
  const url = new URL(`${BASE_URL}/analytics/${season}/${round}`, getBaseUrl());

  if (drivers && drivers.length > 0) {
    drivers.forEach((d) => url.searchParams.append("drivers", d));
  }

  const res = await fetch(url.toString(), fetchOptions());

  if (!res.ok) {
    throw new Error(`Failed to fetch analytics: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Standings API
// =============================================================================

export async function fetchStandings(
  season: number
): Promise<StandingsResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/standings/${season}`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch standings: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Race Laps API
// =============================================================================

export async function fetchLaps(
  season: number,
  round: number,
  drivers?: string[]
): Promise<SimpleLapData[]> {
  const url = new URL(`${BASE_URL}/race/${season}/${round}/laps`, getBaseUrl());

  if (drivers && drivers.length > 0) {
    drivers.forEach((d) => url.searchParams.append("drivers", d));
  }

  const res = await fetch(url.toString(), fetchOptions());

  if (!res.ok) {
    throw new Error(`Failed to fetch laps: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Homepage API
// =============================================================================

export async function fetchHomepage(): Promise<HomepageResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/homepage`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch homepage: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Circuits API
// =============================================================================

export async function fetchCircuits(
  season: number
): Promise<CircuitsResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/circuits/${season}`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch circuits: ${res.status}`);
  }

  return res.json();
}

export async function fetchCircuitDetail(
  season: number,
  circuitId: string
): Promise<CircuitDetailResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/circuits/${season}/${circuitId}`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch circuit detail: ${res.status}`);
  }

  return res.json();
}

export async function fetchCircuitTrends(
  circuitId: string
): Promise<CircuitTrendsResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/circuits/trends/${circuitId}`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch circuit trends: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Testing API
// =============================================================================

export async function fetchTestingEvents(
  season: number
): Promise<TestingEventsResponse> {
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/testing/${season}`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch testing events: ${res.status}`);
  }

  return res.json();
}

export async function fetchTestingDay(
  season: number,
  eventId: string,
  day: number,
  options?: { drivers?: string[]; includeLaps?: boolean }
): Promise<TestingDayResponse> {
  const url = new URL(
    `${getBaseUrl()}${BASE_URL}/testing/${season}/${eventId}/${day}`,
    getBaseUrl() || "http://localhost"
  );

  if (options?.drivers) {
    options.drivers.forEach((d) => url.searchParams.append("drivers", d));
  }
  if (options?.includeLaps) {
    url.searchParams.set("include_laps", "true");
  }

  const res = await fetch(url.toString(), fetchOptions());

  if (!res.ok) {
    throw new Error(`Failed to fetch testing day: ${res.status}`);
  }

  return res.json();
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
  const res = await fetch(
    `${getBaseUrl()}${BASE_URL}/race/${season}/${round}/weekend`,
    fetchOptions()
  );

  if (!res.ok) {
    throw new Error(`Failed to fetch weekend data: ${res.status}`);
  }

  return res.json();
}
