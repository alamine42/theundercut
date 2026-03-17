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

export interface CircuitPreview {
  last_winner: string | null;
  last_winner_team: string | null;
  dominant_driver: string | null;
  dominant_driver_wins: number;
  dominant_team: string | null;
  dominant_team_wins: number;
}

export interface Circuit {
  circuit_id: string;
  name: string;
  shortname: string;
  country: string;
  city: string;
  round: number | null;
  race_name: string;
  date: string;
  preview: CircuitPreview | null;
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

// =============================================================================
// Pre-Season Testing Data
// =============================================================================

export interface TestingEvent {
  event_id: string;
  event_name: string;
  circuit_id: string;
  circuit_name: string;
  start_date: string;
  end_date: string;
  total_days: number;
  status: "scheduled" | "running" | "completed";
}

export interface TestingEventsResponse {
  season: number;
  events: TestingEvent[];
}

export interface TestingStint {
  stint_number: number;
  compound: string;
  lap_count: number;
  avg_pace_ms: number;
  avg_pace_formatted: string;
}

export interface TestingDriverResult {
  position: number;
  driver: string;
  team: string;
  best_lap_ms: number;
  best_lap_formatted: string;
  best_lap_compound: string;
  gap_ms: number | null;
  gap_formatted: string | null;
  total_laps: number;
  stints: TestingStint[];
}

export interface TestingLap {
  driver: string;
  lap_number: number;
  lap_time_ms: number;
  lap_time_formatted: string;
  compound: string;
  stint: number;
  is_valid: boolean;
  sector_1_ms: number | null;
  sector_2_ms: number | null;
  sector_3_ms: number | null;
}

export interface TestingDayResponse {
  season: number;
  event_id: string;
  event_name: string;
  circuit_id: string;
  day: number;
  date: string;
  status: "scheduled" | "running" | "completed";
  results: TestingDriverResult[];
  laps: TestingLap[]; // Only populated if include_laps=true
}

export interface TestingLapsResponse {
  total: number;
  offset: number;
  limit: number;
  laps: TestingLap[];
}

// =============================================================================
// Race Weekend Widget Data
// =============================================================================

export interface RaceSession {
  session_type: string;
  start_time: string | null;
  end_time: string | null;
  status: "scheduled" | "live" | "running" | "ingested" | "completed";
}

export interface RaceWeekendSchedule {
  season: number;
  round: number;
  race_name: string | null;
  circuit_id: string | null;
  circuit_name: string | null;
  circuit_country: string | null;
  is_sprint_weekend: boolean;
  sessions: RaceSession[];
}

export interface SessionResult {
  position: number;
  driver_code: string;
  driver_name: string | null;
  team: string | null;
  time: string | null;
  gap: string | null;
  laps: number | null;
  points: number | null;
  // Qualifying-specific
  q1_time: string | null;
  q2_time: string | null;
  q3_time: string | null;
  eliminated_in: string | null;
}

export interface SessionResultsResponse {
  season: number;
  round: number;
  session_type: string;
  results: SessionResult[];
}

export interface HistoricalDriver {
  driver_code: string;
  driver_name: string | null;
  team: string | null;
}

export interface CircuitHistoryPreviousYear {
  season: number;
  winner: HistoricalDriver | null;
  second: HistoricalDriver | null;
  third: HistoricalDriver | null;
  pole: HistoricalDriver | null;
  fastest_lap: {
    driver_code: string;
    driver_name: string | null;
    time: string | null;
  } | null;
}

export interface CircuitHistoryResponse {
  circuit_id: string;
  circuit_name: string | null;
  previous_year: CircuitHistoryPreviousYear | null;
}

export interface WeekendMeta {
  last_updated: string;
  stale: boolean;
  errors: string[];
}

export type WeekendState =
  | "pre-weekend"
  | "race-week"
  | "during-weekend"
  | "post-race"
  | "off-week";

export interface WeekendTimeline {
  state: WeekendState;
  window_start: string | null;
  window_end: string | null;
  is_active: boolean;
  next_session: RaceSession | null;
  next_session_in_seconds: number | null;
  current_session: RaceSession | null;
}

export interface WeekendResponse {
  schedule: RaceWeekendSchedule | null;
  history: CircuitHistoryResponse | null;
  sessions: Record<string, SessionResultsResponse | null>;
  meta: WeekendMeta;
  timeline?: WeekendTimeline | null;
}

export interface NextRacePreview {
  race_name: string | null;
  circuit_name: string | null;
  circuit_country: string | null;
  fp1_date: string | null;
  round: number | null;
}

export interface WeekendSummaryResponse {
  season: number;
  display_round: number | null;
  display_weekend: WeekendResponse | null;
  next_weekend: WeekendResponse | null;
  next_race_info: NextRacePreview | null;
}

// =============================================================================
// Circuit Characteristics Data
// =============================================================================

export interface ScoreWithValue {
  value: number | null;
  score: number | null;
}

export interface ScoreWithLabel {
  score: number | null;
  label: string | null;
}

export interface CornersData {
  slow: number | null;
  medium: number | null;
  fast: number | null;
  total: number | null;
}

export interface CircuitCharacteristics {
  effective_year: number;
  data_completeness: "complete" | "partial" | "unknown";
  last_updated: string | null;
  full_throttle: ScoreWithValue | null;
  average_speed: ScoreWithValue | null;
  track_length_km: number | null;
  tire_degradation: ScoreWithLabel | null;
  track_abrasion: ScoreWithLabel | null;
  corners: CornersData | null;
  downforce: ScoreWithLabel | null;
  overtaking: ScoreWithLabel | null;
  drs_zones: number | null;
  circuit_type: "Street" | "Permanent" | "Hybrid" | null;
}

export interface CircuitWithCharacteristics {
  id: number;
  name: string;
  country: string;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  characteristics: CircuitCharacteristics | null;
}

export interface CircuitsCharacteristicsResponse {
  circuits: CircuitWithCharacteristics[];
  total: number;
}

export interface CircuitCharacteristicsRanking {
  rank: number;
  circuit_id: number;
  name: string;
  country: string | null;
  value: number;
  effective_year: number;
}

export interface CircuitsRankingResponse {
  ranked_by: string;
  order: "asc" | "desc";
  ranking: CircuitCharacteristicsRanking[];
  total: number;
}

export interface CircuitsCompareResponse {
  circuits: CircuitWithCharacteristics[];
}

// Notable characteristic ranking for a circuit
export interface NotableCharacteristic {
  field: string;
  rank: number;
  value: number;
  isTop: boolean; // true = top ranked (fastest, highest), false = bottom ranked
}

// Rankings data per circuit for UI display
export interface CircuitRankingsData {
  // Map of circuit name -> list of notable rankings
  rankings: Map<string, NotableCharacteristic[]>;
}
