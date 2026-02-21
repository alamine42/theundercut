// API Response Types for The Undercut

// =============================================================================
// Lap Data
// =============================================================================

export interface LapData {
  driver: string;
  lap: number;
  lap_ms: number | null;
  compound: string | null;
  stint_no: number | null;
  pit: boolean;
}

// =============================================================================
// Stint Data
// =============================================================================

export interface StintData {
  driver: string;
  stint_no: number;
  compound: string;
  laps: number;
  avg_lap_ms: number | null;
}

// =============================================================================
// Driver Grades
// =============================================================================

export interface DriverPaceGrade {
  driver: string;
  pace_ms?: number;
  pace_delta_ms?: number;
  score?: number;
  total_grade?: number;
  consistency?: number;
  team_strategy?: number;
  racecraft?: number;
  penalties?: number;
  source: "lap_time_heuristic" | "drive_grade_db";
}

// =============================================================================
// Analytics Response
// =============================================================================

export interface RaceInfo {
  season: number;
  round: number;
}

export interface AnalyticsResponse {
  race: RaceInfo;
  last_updated: string;
  laps: LapData[];
  stints: StintData[];
  driver_pace_grades: DriverPaceGrade[];
}

// =============================================================================
// Standings Data
// =============================================================================

export interface DriverStanding {
  driver_code: string;
  driver_name: string;
  constructor_name: string;
  points: number;
  wins: number;
  pts_last_5: number;
  points_per_race: number;
  points_won_lost: number;
  alt_points: number;
  total_races: number;
  poles: number;
  avg_start_pos: number;
  avg_finish_pos: number;
  positions_gained: number;
  positions_gained_per_race: number;
}

export interface ConstructorStanding {
  constructor_id: string;
  constructor_name: string;
  points: number;
  wins: number;
  pts_last_5: number;
  positions_gained: number;
  points_won_lost: number;
  alt_points: number;
}

// Last Race Result Entry
export interface LastRaceResultEntry {
  position: number;
  driver_code: string;
  driver_name: string;
  team: string;
  grid: number;
  points: number;
  positions_gained: number;
  status: string;
}

// Last Race Results
export interface LastRaceResults {
  round: number;
  race_name: string;
  date: string;
  circuit: string;
  results: LastRaceResultEntry[];
}

// Race Summary (for season overview)
export interface RaceSummary {
  round: number;
  race_name: string;
  circuit_id: string;
  date: string;
  winner_code: string;
  winner_team: string;
  pole: string | null;
  second: string | null;
  third: string | null;
}

export interface StandingsResponse {
  season: number;
  last_updated: string;
  races_completed: number;
  races_remaining: number;
  drivers: DriverStanding[];
  constructors: ConstructorStanding[];
  last_race: LastRaceResults | null;
  race_summaries: RaceSummary[];
}

// =============================================================================
// Race Laps Response (simple)
// =============================================================================

export interface SimpleLapData {
  driver: string;
  lap: number;
  lap_ms: number;
}

// =============================================================================
// Homepage Data
// =============================================================================

export interface LatestRace {
  race_id: string;
  round: number;
  name: string;
  season: number;
}

export interface PodiumEntry {
  position: number;
  driver: string;
  team: string;
}

export interface HomepageResponse {
  season: number;
  latest_race: LatestRace | null;
  podium: PodiumEntry[];
}

// =============================================================================
// Circuit Data
// =============================================================================

export interface Circuit {
  circuit_id: string;
  name: string;
  shortname: string;
  country: string;
  city: string;
  round: number | null;
  race_name: string;
  date: string;
}

export interface CircuitsResponse {
  season: number;
  circuits: Circuit[];
}

export interface CircuitInfo {
  id: string;
  name: string;
  shortname: string;
  country: string;
  city: string;
  lat: string | null;
  lng: string | null;
  url: string;
}

export interface RaceInfoDetail {
  round: number;
  date: string;
  race_name: string;
  winner: string | null;
  winner_team: string | null;
  pole: string | null;
  fastest_lap: string | null;
  fastest_lap_time: string | null;
}

export interface LapRecord {
  driver: string;
  time: string;
  year: number;
}

export interface HistoricalWinner {
  year: number;
  driver: string;
  driver_name: string;
  team: string;
}

export interface CircuitDriverStats {
  driver: string;
  races: number;
  wins: number;
  podiums: number;
  points: number;
  avg_finish: number;
}

export interface CircuitTeamStats {
  team: string;
  races: number;
  wins: number;
  podiums: number;
  points: number;
}

export interface StrategyPattern {
  year: number;
  most_common_stops: number;
  compounds_used: string[];
}

export interface CircuitDetailResponse {
  circuit: CircuitInfo;
  season: number;
  race_info: RaceInfoDetail | null;
  lap_records: {
    all_time_fastest: LapRecord | null;
    season_fastest: LapRecord | null;
  };
  historical_winners: HistoricalWinner[];
  driver_stats: CircuitDriverStats[];
  team_stats: CircuitTeamStats[];
  strategy_patterns: StrategyPattern[];
}

// =============================================================================
// Circuit Trends Data
// =============================================================================

export interface CircuitTrend {
  year: number;
  pole_driver: string | null;
  pole_time: string | null;
  pole_time_ms: number | null;
  fastest_lap_driver: string | null;
  fastest_lap_time: string | null;
  fastest_lap_ms: number | null;
  winner: string | null;
  winner_team: string | null;
  winner_time_ms: number | null;
}

export interface CircuitTrendsResponse {
  circuit_id: string;
  trends: CircuitTrend[];
}
