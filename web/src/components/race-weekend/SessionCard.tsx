"use client";

import { SessionCardCompact } from "./SessionCardCompact";
import { SessionCardExpanded } from "./SessionCardExpanded";
import type { SessionCardProps, RaceSession } from "./types";

const SESSION_LABELS: Record<string, string> = {
  fp1: "Free Practice 1",
  fp2: "Free Practice 2",
  fp3: "Free Practice 3",
  qualifying: "Qualifying",
  sprint_qualifying: "Sprint Qualifying",
  sprint_race: "Sprint Race",
  sprint: "Sprint",
  race: "Race",
};

const SESSION_SHORT_LABELS: Record<string, string> = {
  fp1: "FP1",
  fp2: "FP2",
  fp3: "FP3",
  qualifying: "QUALI",
  sprint_qualifying: "SPRINT Q",
  sprint_race: "SPRINT",
  sprint: "SPRINT",
  race: "RACE",
};

function getSessionTypeClass(sessionType: string): string {
  if (sessionType.includes("qualifying")) return "session-type-qualifying";
  if (sessionType.includes("sprint")) return "session-type-sprint";
  if (sessionType === "race") return "session-type-race";
  return "session-type-practice";
}

function formatSessionTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function formatCountdownShort(targetDate: string): string {
  const target = new Date(targetDate);
  const now = new Date();
  const diffMs = target.getTime() - now.getTime();

  if (diffMs <= 0) {
    return "Now";
  }

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `in ${days}d`;
  }
  if (hours > 0) {
    return `in ${hours}h ${minutes}m`;
  }
  return `in ${minutes}m`;
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={`chevron-icon w-4 h-4 sm:w-5 sm:h-5 text-ink/40 ${expanded ? "expanded" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function StatusBadge({
  status,
  startTime,
  endTime,
  hasResults
}: {
  status: RaceSession["status"];
  startTime: string | null;
  endTime: string | null;
  hasResults: boolean;
}) {
  const isCompleted = status === "completed" || status === "ingested";
  const isLive = status === "live" || status === "running";

  // Check if session has ended based on time
  const now = new Date();
  const sessionEnded = endTime ? new Date(endTime) < now :
    (startTime ? new Date(startTime).getTime() + (2 * 60 * 60 * 1000) < now.getTime() : false);

  if (isLive) {
    return (
      <span className="status-live" role="status" aria-label="Session currently in progress">
        <span className="sr-only">Status: Currently live - </span>
        Live
      </span>
    );
  }

  // Show green badge if session is completed, has results, OR time has passed
  if (isCompleted || hasResults || sessionEnded) {
    return (
      <span className="status-completed">
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        <span className="sr-only">Status:</span>
        {hasResults ? "See Results" : "Done"}
      </span>
    );
  }

  const countdownText = startTime ? formatCountdownShort(startTime) : "Scheduled";
  return (
    <span className="status-scheduled">
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="sr-only">Status:</span>
      {countdownText}
    </span>
  );
}

export function SessionCard({
  session,
  results,
  isExpanded,
  onToggle,
}: SessionCardProps) {
  const label = SESSION_LABELS[session.session_type] || session.session_type.toUpperCase();
  const shortLabel = SESSION_SHORT_LABELS[session.session_type] || session.session_type.toUpperCase();
  const isCompleted = session.status === "completed" || session.status === "ingested";
  const hasResults = results && results.results.length > 0;
  const sessionTypeClass = getSessionTypeClass(session.session_type);

  return (
    <div
      className={`session-card ${sessionTypeClass} ${isExpanded ? "session-card-expanded" : ""}`}
    >
      <button
        onClick={onToggle}
        className="w-full p-4 sm:p-5 text-left flex items-center justify-between gap-3 focus-ring rounded-sm min-h-[52px]"
        disabled={!hasResults}
        aria-expanded={hasResults ? isExpanded : undefined}
        aria-controls={hasResults ? `session-${session.session_type}-content` : undefined}
      >
        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
          <div className="flex flex-col min-w-0">
            <span className="font-semibold text-sm sm:text-base truncate" title={label}>
              <span className="sm:hidden">{shortLabel}</span>
              <span className="hidden sm:inline">{label}</span>
            </span>
            {!isCompleted && session.start_time && (
              <span className="text-xs text-muted mt-0.5">
                {formatSessionTime(session.start_time)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <StatusBadge
            status={session.status}
            startTime={session.start_time}
            endTime={session.end_time}
            hasResults={!!hasResults}
          />
          {hasResults && (
            <ChevronIcon expanded={isExpanded} />
          )}
        </div>
      </button>

      {hasResults && (
        <div
          id={`session-${session.session_type}-content`}
          className="expandable-content"
          data-expanded={isExpanded}
        >
          <div className="px-4 sm:px-5 pb-4 sm:pb-5 pt-0">
            {isExpanded ? (
              <SessionCardExpanded
                results={results.results}
                sessionType={session.session_type}
              />
            ) : (
              <SessionCardCompact
                results={results.results}
                sessionType={session.session_type}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
