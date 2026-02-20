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

export interface StandingsResponse {
  season: number;
  last_updated: string;
  races_completed: number;
  races_remaining: number;
  drivers: DriverStanding[];
  constructors: ConstructorStanding[];
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
