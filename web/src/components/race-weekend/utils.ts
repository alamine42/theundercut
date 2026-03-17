import type { RaceSession, SessionResultsResponse, WeekendResponse } from "./types";

const SESSION_DURATION_FALLBACK_MS = 2 * 60 * 60 * 1000; // 2 hours

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
  const key = session.session_type.toLowerCase();
  const results = sessionResults[key];
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
