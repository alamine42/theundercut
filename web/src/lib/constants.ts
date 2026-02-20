// =============================================================================
// VOID Theme Colors
// =============================================================================

export const VOID_THEME = {
  ink: "#0f0f0f",
  paper: "#ffffff",
  accent: "#d9731a",
  accentHover: "#c4650f",
  muted: "#6b6b6b",
  border: "#0f0f0f",
  borderLight: "#e0e0e0",
  success: "#2d8a39",
  error: "#c41e3a",
} as const;

// =============================================================================
// Tire Compound Colors
// =============================================================================

export const COMPOUND_COLORS: Record<string, string> = {
  SOFT: "#c41e3a",
  MEDIUM: "#f5d547",
  HARD: "#eeeeee",
  INTERMEDIATE: "#2d8a39",
  WET: "#1e90ff",
  // Fallback for unknown compounds
  UNKNOWN: "#888888",
} as const;

export function getCompoundColor(compound: string | null): string {
  if (!compound) return COMPOUND_COLORS.UNKNOWN;
  return COMPOUND_COLORS[compound.toUpperCase()] || COMPOUND_COLORS.UNKNOWN;
}

// =============================================================================
// Team Colors (2024-2025)
// =============================================================================

export const TEAM_COLORS: Record<string, string> = {
  "Red Bull": "#3671C6",
  Mercedes: "#27F4D2",
  Ferrari: "#E8002D",
  McLaren: "#FF8000",
  "Aston Martin": "#229971",
  Alpine: "#FF87BC",
  Williams: "#64C4FF",
  RB: "#6692FF",
  Sauber: "#52E252",
  Haas: "#B6BABD",
} as const;

// =============================================================================
// Driver to Team Mapping (2024)
// =============================================================================

export const DRIVER_TEAM_2024: Record<string, string> = {
  VER: "Red Bull",
  PER: "Red Bull",
  HAM: "Mercedes",
  RUS: "Mercedes",
  LEC: "Ferrari",
  SAI: "Ferrari",
  NOR: "McLaren",
  PIA: "McLaren",
  ALO: "Aston Martin",
  STR: "Aston Martin",
  OCO: "Alpine",
  GAS: "Alpine",
  TSU: "RB",
  RIC: "RB",
  LAW: "RB",
  BOT: "Sauber",
  ZHO: "Sauber",
  MAG: "Haas",
  HUL: "Haas",
  ALB: "Williams",
  SAR: "Williams",
  COL: "Williams",
};

// =============================================================================
// Driver to Team Mapping (2025)
// =============================================================================

export const DRIVER_TEAM_2025: Record<string, string> = {
  VER: "Red Bull",
  LAW: "Red Bull",
  RUS: "Mercedes",
  ANT: "Mercedes",
  LEC: "Ferrari",
  HAM: "Ferrari",
  NOR: "McLaren",
  PIA: "McLaren",
  ALO: "Aston Martin",
  STR: "Aston Martin",
  GAS: "Alpine",
  DOO: "Alpine",
  TSU: "RB",
  HAD: "RB",
  BOR: "Sauber",
  HUL: "Sauber",
  BEA: "Haas",
  OCO: "Haas",
  ALB: "Williams",
  SAI: "Williams",
  COL: "Williams",
};

export function getDriverTeam(driver: string, season: number): string {
  const mapping = season >= 2025 ? DRIVER_TEAM_2025 : DRIVER_TEAM_2024;
  return mapping[driver] || "Unknown";
}

export function getDriverColor(driver: string, season: number): string {
  const team = getDriverTeam(driver, season);
  return TEAM_COLORS[team] || VOID_THEME.muted;
}

// =============================================================================
// Chart Configuration
// =============================================================================

export const CHART_CONFIG = {
  margin: { top: 20, right: 30, bottom: 60, left: 60 },
  animationDuration: 300,
  strokeWidth: 2,
  dotRadius: 3,
} as const;

// =============================================================================
// API Configuration
// =============================================================================

export const API_CONFIG = {
  revalidateSeconds: 300, // 5 minutes for ISR
  baseUrl: "/api/v1",
} as const;

// =============================================================================
// Available Seasons (years with data, most recent first)
// =============================================================================

export const AVAILABLE_SEASONS = [2025, 2024];

// =============================================================================
// Default Season (most recent year)
// =============================================================================

export const DEFAULT_SEASON = AVAILABLE_SEASONS[0];

// =============================================================================
// Race Names by Season and Round
// =============================================================================

const RACE_NAMES: Record<string, string> = {
  // 2024 season
  "2024-1": "Bahrain Grand Prix",
  "2024-2": "Saudi Arabian Grand Prix",
  "2024-3": "Australian Grand Prix",
  "2024-4": "Japanese Grand Prix",
  "2024-5": "Chinese Grand Prix",
  "2024-6": "Miami Grand Prix",
  "2024-7": "Emilia Romagna Grand Prix",
  "2024-8": "Monaco Grand Prix",
  "2024-9": "Canadian Grand Prix",
  "2024-10": "Spanish Grand Prix",
  "2024-11": "Austrian Grand Prix",
  "2024-12": "British Grand Prix",
  "2024-13": "Hungarian Grand Prix",
  "2024-14": "Belgian Grand Prix",
  "2024-15": "Dutch Grand Prix",
  "2024-16": "Italian Grand Prix",
  "2024-17": "Azerbaijan Grand Prix",
  "2024-18": "Singapore Grand Prix",
  "2024-19": "United States Grand Prix",
  "2024-20": "Mexico City Grand Prix",
  "2024-21": "São Paulo Grand Prix",
  "2024-22": "Las Vegas Grand Prix",
  "2024-23": "Qatar Grand Prix",
  "2024-24": "Abu Dhabi Grand Prix",
  // 2025 season
  "2025-1": "Australian Grand Prix",
  "2025-2": "Chinese Grand Prix",
  "2025-3": "Japanese Grand Prix",
  "2025-4": "Bahrain Grand Prix",
  "2025-5": "Saudi Arabian Grand Prix",
  "2025-6": "Miami Grand Prix",
  "2025-7": "Emilia Romagna Grand Prix",
  "2025-8": "Monaco Grand Prix",
  "2025-9": "Spanish Grand Prix",
  "2025-10": "Canadian Grand Prix",
  "2025-11": "Austrian Grand Prix",
  "2025-12": "British Grand Prix",
  "2025-13": "Belgian Grand Prix",
  "2025-14": "Hungarian Grand Prix",
  "2025-15": "Dutch Grand Prix",
  "2025-16": "Italian Grand Prix",
  "2025-17": "Azerbaijan Grand Prix",
  "2025-18": "Singapore Grand Prix",
  "2025-19": "United States Grand Prix",
  "2025-20": "Mexico City Grand Prix",
  "2025-21": "São Paulo Grand Prix",
  "2025-22": "Las Vegas Grand Prix",
  "2025-23": "Qatar Grand Prix",
  "2025-24": "Abu Dhabi Grand Prix",
};

export function getRaceName(season: number, round: number): string {
  return RACE_NAMES[`${season}-${round}`] || `Round ${round}`;
}
