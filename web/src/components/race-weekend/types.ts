// Component-specific types for Race Weekend Widget

import type {
  RaceSession,
  RaceWeekendSchedule,
  SessionResult,
  SessionResultsResponse,
  CircuitHistoryResponse,
  WeekendResponse,
  WeekendTimeline,
  CircuitCharacteristics,
} from "@/types/api";

export type WidgetState =
  | "pre-weekend"   // >3 days before FP1
  | "race-week"     // Within 3 days of FP1
  | "during-weekend" // FP1 started
  | "post-race"     // Race completed
  | "off-week";     // >7 days to next race

export interface NextRaceInfo {
  raceName: string | null;
  circuitName: string | null;
  circuitCountry: string | null;
  fp1Date: string | null;
  round: number;
}

export interface RaceWeekendWidgetProps {
  weekendData: WeekendResponse | null;
  nextRaceInfo?: NextRaceInfo | null;
  circuitCharacteristics?: CircuitCharacteristics | null;
  error?: string | null;
  liveUpdate?: boolean;
}

export interface RaceHeaderProps {
  raceName: string | null;
  round: number;
  totalRounds?: number;
  circuitName: string | null;
  circuitCountry: string | null;
  isSprintWeekend: boolean;
  isRaceWeekendActive?: boolean;
}

export interface RaceCountdownProps {
  targetDate: string;
  sessionType?: string;
  label?: string;
}

export interface HistoricalDataProps {
  history: CircuitHistoryResponse;
  circuitName: string | null;
}

export interface SessionGridProps {
  sessions: RaceSession[];
  sessionResults: Record<string, SessionResultsResponse | null>;
}

export interface SessionCardProps {
  session: RaceSession;
  results: SessionResultsResponse | null;
  isExpanded: boolean;
  onToggle: () => void;
}

export interface SessionCardCompactProps {
  results: SessionResult[];
  sessionType: string;
}

export interface SessionCardExpandedProps {
  results: SessionResult[];
  sessionType: string;
}

export {
  RaceSession,
  SessionResult,
  SessionResultsResponse,
  RaceWeekendSchedule,
  CircuitHistoryResponse,
  WeekendResponse,
  WeekendTimeline,
  CircuitCharacteristics,
};
