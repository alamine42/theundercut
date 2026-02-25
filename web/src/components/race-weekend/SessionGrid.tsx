"use client";

import { useState } from "react";
import { SessionCard } from "./SessionCard";
import type { SessionGridProps } from "./types";

// Order sessions for display
const STANDARD_ORDER = ["fp1", "fp2", "fp3", "qualifying", "race"];
const SPRINT_ORDER = ["fp1", "sprint_qualifying", "sprint_race", "sprint", "qualifying", "race"];

function normalizeSessionType(type: string): string {
  return type.toLowerCase().replace(/\s+/g, "_");
}

export function SessionGrid({
  sessions,
  sessionResults,
  isSprintWeekend,
}: SessionGridProps) {
  const [expandedSession, setExpandedSession] = useState<string | null>(null);

  const sessionOrder = isSprintWeekend ? SPRINT_ORDER : STANDARD_ORDER;

  // Sort sessions by predefined order
  const sortedSessions = [...sessions].sort((a, b) => {
    const typeA = normalizeSessionType(a.session_type);
    const typeB = normalizeSessionType(b.session_type);
    const indexA = sessionOrder.indexOf(typeA);
    const indexB = sessionOrder.indexOf(typeB);

    // If not in predefined order, sort by start time
    if (indexA === -1 && indexB === -1) {
      const timeA = a.start_time ? new Date(a.start_time).getTime() : 0;
      const timeB = b.start_time ? new Date(b.start_time).getTime() : 0;
      return timeA - timeB;
    }
    if (indexA === -1) return 1;
    if (indexB === -1) return -1;
    return indexA - indexB;
  });

  const handleToggle = (sessionType: string) => {
    setExpandedSession((prev) => (prev === sessionType ? null : sessionType));
  };

  if (sortedSessions.length === 0) {
    return (
      <p className="text-sm text-muted">No session schedule available</p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {sortedSessions.map((session) => {
        const normalizedType = normalizeSessionType(session.session_type);
        const results = sessionResults[normalizedType] || null;

        return (
          <SessionCard
            key={normalizedType}
            session={{ ...session, session_type: normalizedType }}
            results={results}
            isExpanded={expandedSession === normalizedType}
            onToggle={() => handleToggle(normalizedType)}
          />
        );
      })}
    </div>
  );
}
