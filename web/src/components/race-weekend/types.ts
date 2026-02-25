// Component-specific types for Race Weekend Widget

import type {
  RaceSession,
  RaceWeekendSchedule,
  SessionResult,
  SessionResultsResponse,
  CircuitHistoryResponse,
  WeekendResponse,
} from "@/types/api";

export type WidgetState =
  | "pre-weekend"   // >3 days before FP1
  | "race-week"     // Within 3 days of FP1
  | "during-weekend" // FP1 started
  | "post-race"     // Race completed
  | "off-week";     // >7 days to next race

export interface RaceWeekendWidgetProps {
  weekendData: WeekendResponse | null;
  error?: string | null;
}

export interface RaceHeaderProps {
  raceName: string | null;
  round: number;
  totalRounds?: number;
  circuitName: string | null;
  circuitCountry: string | null;
  isSprintWeekend: boolean;
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
  isSprintWeekend: boolean;
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

export { RaceSession, SessionResult, SessionResultsResponse, RaceWeekendSchedule, CircuitHistoryResponse, WeekendResponse };
