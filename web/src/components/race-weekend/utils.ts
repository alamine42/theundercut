import type { RaceSession, SessionResultsResponse, WeekendResponse } from "./types";

const SESSION_DURATION_FALLBACK_MS = 2 * 60 * 60 * 1000; // 2 hours

const SESSION_TYPE_MAP: Record<string, string> = {
  practice_1: "fp1",
  practice_2: "fp2",
  practice_3: "fp3",
  sprint: "sprint_race",
  sprint_shootout: "sprint_qualifying",
  sprint_shootout_qualifying: "sprint_qualifying",
};

export function normalizeSessionType(type: string): string {
  const normalized = type.toLowerCase().replace(/\s+/g, "_");
  return SESSION_TYPE_MAP[normalized] ?? normalized;
}

export function hasSessionEnded(session: RaceSession, now: Date = new Date()): boolean {
  if (session.status === "completed" || session.status === "ingested") {
    return true;
  }

  if (session.status === "live" || session.status === "running") {
    return false;
  }

  if (session.end_time) {
    const end = new Date(session.end_time);
    return !Number.isNaN(end.getTime()) && end <= now;
  }

  if (session.start_time) {
    const start = new Date(session.start_time);
    if (!Number.isNaN(start.getTime())) {
      return start.getTime() + SESSION_DURATION_FALLBACK_MS <= now.getTime();
    }
  }

  return false;
}

export function sessionHasResults(
  session: RaceSession,
  sessionResults: Record<string, SessionResultsResponse | null>
): boolean {
  const normalizedType = normalizeSessionType(session.session_type);
  const results = sessionResults[normalizedType];
  return Boolean(results && results.results.length > 0);
}

export function hasMissingSessionResults(
  weekendData: WeekendResponse | null,
  now: Date = new Date()
): boolean {
  if (!weekendData?.schedule) {
    return false;
  }

  return weekendData.schedule.sessions.some((session) => {
    if (!hasSessionEnded(session, now)) {
      return false;
    }
    return !sessionHasResults(session, weekendData.sessions ?? {});
  });
}
