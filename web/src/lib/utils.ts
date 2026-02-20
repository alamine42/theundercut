import { type ClassValue, clsx } from "clsx";

// =============================================================================
// Class Name Utility
// =============================================================================

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

// =============================================================================
// Time Formatting
// =============================================================================

export function formatLapTime(ms: number | null): string {
  if (ms === null || ms <= 0) return "-";

  const totalSeconds = ms / 1000;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes > 0) {
    return `${minutes}:${seconds.toFixed(3).padStart(6, "0")}`;
  }
  return seconds.toFixed(3);
}

export function formatDelta(ms: number | null): string {
  if (ms === null) return "-";
  if (ms === 0) return "0.000";

  const sign = ms > 0 ? "+" : "-";
  const absMs = Math.abs(ms);
  const seconds = absMs / 1000;

  return `${sign}${seconds.toFixed(3)}`;
}

// =============================================================================
// Number Formatting
// =============================================================================

export function formatNumber(value: number, decimals = 1): string {
  return value.toFixed(decimals);
}

export function formatPosition(position: number): string {
  const suffixes: Record<number, string> = { 1: "st", 2: "nd", 3: "rd" };
  const suffix = suffixes[position] || "th";
  return `${position}${suffix}`;
}

// =============================================================================
// Color Utilities
// =============================================================================

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// =============================================================================
// Data Utilities
// =============================================================================

export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce(
    (groups, item) => {
      const groupKey = String(item[key]);
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(item);
      return groups;
    },
    {} as Record<string, T[]>
  );
}

export function uniqueDrivers(
  items: { driver: string }[]
): string[] {
  return [...new Set(items.map((item) => item.driver))].sort();
}

// =============================================================================
// Country Flags
// =============================================================================

const COUNTRY_FLAGS: Record<string, string> = {
  "Australia": "🇦🇺",
  "Austria": "🇦🇹",
  "Azerbaijan": "🇦🇿",
  "Bahrain": "🇧🇭",
  "Belgium": "🇧🇪",
  "Brazil": "🇧🇷",
  "Canada": "🇨🇦",
  "China": "🇨🇳",
  "France": "🇫🇷",
  "Germany": "🇩🇪",
  "Hungary": "🇭🇺",
  "Italy": "🇮🇹",
  "Japan": "🇯🇵",
  "Mexico": "🇲🇽",
  "Monaco": "🇲🇨",
  "Netherlands": "🇳🇱",
  "Portugal": "🇵🇹",
  "Qatar": "🇶🇦",
  "Russia": "🇷🇺",
  "Saudi Arabia": "🇸🇦",
  "Singapore": "🇸🇬",
  "Spain": "🇪🇸",
  "Turkey": "🇹🇷",
  "UAE": "🇦🇪",
  "United Arab Emirates": "🇦🇪",
  "UK": "🇬🇧",
  "United Kingdom": "🇬🇧",
  "United States": "🇺🇸",
  "USA": "🇺🇸",
  "Vietnam": "🇻🇳",
  "Las Vegas": "🇺🇸",
  "Miami": "🇺🇸",
};

export function getCountryFlag(country: string): string {
  return COUNTRY_FLAGS[country] || "🏁";
}
