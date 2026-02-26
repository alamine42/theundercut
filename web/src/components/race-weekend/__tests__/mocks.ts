import type { WeekendResponse, SessionResultsResponse, CircuitHistoryResponse, RaceSession } from "../types";

// Fixed base date for deterministic testing - tests should use vi.setSystemTime(BASE_DATE)
export const BASE_DATE = new Date("2026-03-15T12:00:00Z");

// Helper to create dates relative to a base date (defaults to BASE_DATE for determinism)
export function futureDate(days: number, hours = 0, baseDate: Date = BASE_DATE): string {
  const date = new Date(baseDate);
  date.setDate(date.getDate() + days);
  date.setHours(date.getHours() + hours);
  return date.toISOString();
}

export function pastDate(days: number, hours = 0, baseDate: Date = BASE_DATE): string {
  const date = new Date(baseDate);
  date.setDate(date.getDate() - days);
  date.setHours(date.getHours() - hours);
  return date.toISOString();
}

// Mock session with results
export const mockFP1Results: SessionResultsResponse = {
  season: 2026,
  round: 1,
  session_type: "fp1",
  results: [
    { position: 1, driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull", time: "1:30.123", gap: null, laps: 25 },
    { position: 2, driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren", time: "1:30.234", gap: "+0.111", laps: 28 },
    { position: 3, driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari", time: "1:30.345", gap: "+0.222", laps: 22 },
    { position: 4, driver_code: "HAM", driver_name: "Lewis Hamilton", team: "Ferrari", time: "1:30.456", gap: "+0.333", laps: 24 },
    { position: 5, driver_code: "RUS", driver_name: "George Russell", team: "Mercedes", time: "1:30.567", gap: "+0.444", laps: 26 },
  ],
};

export const mockQualifyingResults: SessionResultsResponse = {
  season: 2026,
  round: 1,
  session_type: "qualifying",
  results: [
    { position: 1, driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull", time: "1:28.500", gap: null, q1_time: "1:29.500", q2_time: "1:29.000", q3_time: "1:28.500" },
    { position: 2, driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren", time: "1:28.600", gap: "+0.100", q1_time: "1:29.600", q2_time: "1:29.100", q3_time: "1:28.600" },
    { position: 3, driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari", time: "1:28.700", gap: "+0.200", q1_time: "1:29.700", q2_time: "1:29.200", q3_time: "1:28.700" },
  ],
};

export const mockRaceResults: SessionResultsResponse = {
  season: 2026,
  round: 1,
  session_type: "race",
  results: [
    { position: 1, driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull", time: "1:32:45.123", gap: null, laps: 57 },
    { position: 2, driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren", time: "1:32:50.456", gap: "+5.333", laps: 57 },
    { position: 3, driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari", time: "1:32:55.789", gap: "+10.666", laps: 57 },
  ],
};

// Mock history
export const mockHistory: CircuitHistoryResponse = {
  circuit_id: "monza",
  circuit_name: "Autodromo Nazionale Monza",
  previous_year: {
    season: 2025,
    winner: { driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull" },
    second: { driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren" },
    third: { driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari" },
    pole: { driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull" },
    fastest_lap: { driver_code: "HAM", driver_name: "Lewis Hamilton", team: "Ferrari", time: "1:24.567" },
  },
};

export const mockHistoryEmpty: CircuitHistoryResponse = {
  circuit_id: "new_circuit",
  circuit_name: "New Circuit",
  previous_year: null,
};

// Sprint session results
export const mockSprintQualifyingResults: SessionResultsResponse = {
  season: 2026,
  round: 1,
  session_type: "sprint_qualifying",
  results: [
    { position: 1, driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull", time: "1:29.100", gap: null, q1_time: "1:29.800", q2_time: "1:29.400", q3_time: "1:29.100" },
    { position: 2, driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren", time: "1:29.200", gap: "+0.100", q1_time: "1:29.900", q2_time: "1:29.500", q3_time: "1:29.200" },
    { position: 3, driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari", time: "1:29.300", gap: "+0.200", q1_time: "1:30.000", q2_time: "1:29.600", q3_time: "1:29.300" },
  ],
};

export const mockSprintResults: SessionResultsResponse = {
  season: 2026,
  round: 1,
  session_type: "sprint",
  results: [
    { position: 1, driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull", time: "25:45.123", gap: null, laps: 19 },
    { position: 2, driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren", time: "25:48.456", gap: "+3.333", laps: 19 },
    { position: 3, driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari", time: "25:52.789", gap: "+7.666", laps: 19 },
  ],
};

// Sessions for different states
export function createMockSessions(state: "pre-weekend" | "race-week" | "during-weekend" | "post-race" | "off-week", isSprint = false): RaceSession[] {
  // Standard weekend sessions
  const standardSessions = {
    "off-week": [
      { session_type: "fp1", start_time: futureDate(10), end_time: futureDate(10, 1), status: "scheduled" },
      { session_type: "fp2", start_time: futureDate(10, 4), end_time: futureDate(10, 5), status: "scheduled" },
      { session_type: "fp3", start_time: futureDate(11), end_time: futureDate(11, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(11, 4), end_time: futureDate(11, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(12, 2), end_time: futureDate(12, 4), status: "scheduled" },
    ],
    "pre-weekend": [
      { session_type: "fp1", start_time: futureDate(5), end_time: futureDate(5, 1), status: "scheduled" },
      { session_type: "fp2", start_time: futureDate(5, 4), end_time: futureDate(5, 5), status: "scheduled" },
      { session_type: "fp3", start_time: futureDate(6), end_time: futureDate(6, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(6, 4), end_time: futureDate(6, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(7, 2), end_time: futureDate(7, 4), status: "scheduled" },
    ],
    "race-week": [
      { session_type: "fp1", start_time: futureDate(2), end_time: futureDate(2, 1), status: "scheduled" },
      { session_type: "fp2", start_time: futureDate(2, 4), end_time: futureDate(2, 5), status: "scheduled" },
      { session_type: "fp3", start_time: futureDate(3), end_time: futureDate(3, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(3, 4), end_time: futureDate(3, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(4, 2), end_time: futureDate(4, 4), status: "scheduled" },
    ],
    "during-weekend": [
      { session_type: "fp1", start_time: pastDate(1), end_time: pastDate(1, -1), status: "completed" },
      { session_type: "fp2", start_time: pastDate(0, 4), end_time: pastDate(0, 3), status: "completed" },
      { session_type: "fp3", start_time: futureDate(0, 2), end_time: futureDate(0, 3), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(0, 6), end_time: futureDate(0, 7), status: "scheduled" },
      { session_type: "race", start_time: futureDate(1, 2), end_time: futureDate(1, 4), status: "scheduled" },
    ],
    "post-race": [
      { session_type: "fp1", start_time: pastDate(3), end_time: pastDate(3, -1), status: "completed" },
      { session_type: "fp2", start_time: pastDate(3, -4), end_time: pastDate(3, -5), status: "completed" },
      { session_type: "fp3", start_time: pastDate(2), end_time: pastDate(2, -1), status: "completed" },
      { session_type: "qualifying", start_time: pastDate(2, -4), end_time: pastDate(2, -5), status: "ingested" },
      { session_type: "race", start_time: pastDate(1), end_time: pastDate(1, -2), status: "ingested" },
    ],
  };

  // Sprint weekend sessions (different order and session types)
  const sprintSessions = {
    "off-week": [
      { session_type: "fp1", start_time: futureDate(10), end_time: futureDate(10, 1), status: "scheduled" },
      { session_type: "sprint_qualifying", start_time: futureDate(10, 4), end_time: futureDate(10, 5), status: "scheduled" },
      { session_type: "sprint", start_time: futureDate(11), end_time: futureDate(11, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(11, 4), end_time: futureDate(11, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(12, 2), end_time: futureDate(12, 4), status: "scheduled" },
    ],
    "pre-weekend": [
      { session_type: "fp1", start_time: futureDate(5), end_time: futureDate(5, 1), status: "scheduled" },
      { session_type: "sprint_qualifying", start_time: futureDate(5, 4), end_time: futureDate(5, 5), status: "scheduled" },
      { session_type: "sprint", start_time: futureDate(6), end_time: futureDate(6, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(6, 4), end_time: futureDate(6, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(7, 2), end_time: futureDate(7, 4), status: "scheduled" },
    ],
    "race-week": [
      { session_type: "fp1", start_time: futureDate(2), end_time: futureDate(2, 1), status: "scheduled" },
      { session_type: "sprint_qualifying", start_time: futureDate(2, 4), end_time: futureDate(2, 5), status: "scheduled" },
      { session_type: "sprint", start_time: futureDate(3), end_time: futureDate(3, 1), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(3, 4), end_time: futureDate(3, 5), status: "scheduled" },
      { session_type: "race", start_time: futureDate(4, 2), end_time: futureDate(4, 4), status: "scheduled" },
    ],
    "during-weekend": [
      { session_type: "fp1", start_time: pastDate(1), end_time: pastDate(1, -1), status: "completed" },
      { session_type: "sprint_qualifying", start_time: pastDate(0, 4), end_time: pastDate(0, 3), status: "ingested" },
      { session_type: "sprint", start_time: futureDate(0, 2), end_time: futureDate(0, 3), status: "scheduled" },
      { session_type: "qualifying", start_time: futureDate(0, 6), end_time: futureDate(0, 7), status: "scheduled" },
      { session_type: "race", start_time: futureDate(1, 2), end_time: futureDate(1, 4), status: "scheduled" },
    ],
    "post-race": [
      { session_type: "fp1", start_time: pastDate(3), end_time: pastDate(3, -1), status: "completed" },
      { session_type: "sprint_qualifying", start_time: pastDate(3, -4), end_time: pastDate(3, -5), status: "ingested" },
      { session_type: "sprint", start_time: pastDate(2), end_time: pastDate(2, -1), status: "ingested" },
      { session_type: "qualifying", start_time: pastDate(2, -4), end_time: pastDate(2, -5), status: "ingested" },
      { session_type: "race", start_time: pastDate(1), end_time: pastDate(1, -2), status: "ingested" },
    ],
  };

  return (isSprint ? sprintSessions : standardSessions)[state] as RaceSession[];
}

// Full weekend response mocks
export function createMockWeekendResponse(
  state: "pre-weekend" | "race-week" | "during-weekend" | "post-race" | "off-week",
  options: { isSprint?: boolean } = {}
): WeekendResponse {
  const { isSprint = false } = options;
  const sessions = createMockSessions(state, isSprint);

  const sessionResults: Record<string, SessionResultsResponse | null> = {
    fp1: null,
    qualifying: null,
    race: null,
  };

  // Add sprint-specific session slots if sprint weekend
  if (isSprint) {
    sessionResults.sprint_qualifying = null;
    sessionResults.sprint = null;
  } else {
    sessionResults.fp2 = null;
    sessionResults.fp3 = null;
  }

  // Add results for completed sessions
  if (state === "during-weekend") {
    sessionResults.fp1 = mockFP1Results;
    if (isSprint) {
      sessionResults.sprint_qualifying = mockSprintQualifyingResults;
    }
  } else if (state === "post-race") {
    sessionResults.fp1 = mockFP1Results;
    if (isSprint) {
      sessionResults.sprint_qualifying = mockSprintQualifyingResults;
      sessionResults.sprint = mockSprintResults;
    } else {
      sessionResults.fp2 = { ...mockFP1Results, session_type: "fp2" };
      sessionResults.fp3 = { ...mockFP1Results, session_type: "fp3" };
    }
    sessionResults.qualifying = mockQualifyingResults;
    sessionResults.race = mockRaceResults;
  }

  return {
    schedule: {
      season: 2026,
      round: 1,
      race_name: isSprint ? "Austrian Grand Prix" : "Italian Grand Prix",
      circuit_id: isSprint ? "red_bull_ring" : "monza",
      circuit_name: isSprint ? "Red Bull Ring" : "Autodromo Nazionale Monza",
      circuit_country: isSprint ? "Austria" : "Italy",
      is_sprint_weekend: isSprint,
      sessions,
    },
    history: mockHistory,
    sessions: sessionResults,
    meta: {
      last_updated: BASE_DATE.toISOString(),
      stale: false,
      errors: [],
    },
  };
}
