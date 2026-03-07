"use client";

import { useState } from "react";
import { SessionCard } from "./SessionCard";
import type { SessionGridProps } from "./types";

function normalizeSessionType(type: string): string {
  const normalized = type.toLowerCase().replace(/\s+/g, "_");
  // Map practice_X to fpX for results lookup
  const sessionTypeMap: Record<string, string> = {
    practice_1: "fp1",
    practice_2: "fp2",
    practice_3: "fp3",
  };
  return sessionTypeMap[normalized] || normalized;
}

export function SessionGrid({
  sessions,
  sessionResults,
}: SessionGridProps) {
  const [expandedSession, setExpandedSession] = useState<string | null>(null);

  // Sort sessions by start time
  const sortedSessions = [...sessions].sort((a, b) => {
    const timeA = a.start_time ? new Date(a.start_time).getTime() : 0;
    const timeB = b.start_time ? new Date(b.start_time).getTime() : 0;
    return timeA - timeB;
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
