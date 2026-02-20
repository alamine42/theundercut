import { API_CONFIG } from "./constants";
import type {
  AnalyticsResponse,
  StandingsResponse,
  SimpleLapData,
  HomepageResponse,
  CircuitsResponse,
  CircuitDetailResponse,
  CircuitTrendsResponse,
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
