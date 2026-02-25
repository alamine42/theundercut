import Link from "next/link";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RaceHeader } from "./RaceHeader";
import { RaceCountdown } from "./RaceCountdown";
import { HistoricalData } from "./HistoricalData";
import { SessionGrid } from "./SessionGrid";
import { getCountryFlag } from "@/lib/utils";
import type { RaceWeekendWidgetProps, WidgetState, NextRaceInfo } from "./types";

function determineWidgetState(
  schedule: { sessions: Array<{ session_type: string; start_time: string | null; status: string }> } | null
): WidgetState {
  if (!schedule || schedule.sessions.length === 0) {
    return "off-week";
  }

  const now = new Date();
  const sessions = schedule.sessions;

  // Find race session
  const raceSession = sessions.find(
    (s) => s.session_type.toLowerCase() === "race"
  );

  // Find first session (usually FP1)
  const sortedSessions = [...sessions]
    .filter((s) => s.start_time)
    .sort((a, b) => {
      const timeA = new Date(a.start_time!).getTime();
      const timeB = new Date(b.start_time!).getTime();
      return timeA - timeB;
    });

  const firstSession = sortedSessions[0];

  // Check if race is completed
  if (raceSession?.status === "completed" || raceSession?.status === "ingested") {
    return "post-race";
  }

  // Check if any session has started
  const anyStarted = sessions.some((s) => {
    if (!s.start_time) return false;
    return new Date(s.start_time) <= now || s.status === "completed" || s.status === "ingested";
  });

  if (anyStarted) {
    return "during-weekend";
  }

  // Check if within 3 days of first session
  if (firstSession?.start_time) {
    const firstSessionTime = new Date(firstSession.start_time);
    const daysUntil = (firstSessionTime.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);

    if (daysUntil <= 3) {
      return "race-week";
    }

    if (daysUntil <= 7) {
      return "pre-weekend";
    }
  }

  return "off-week";
}

function getNextSession(
  sessions: Array<{ session_type: string; start_time: string | null; status: string }>
): { session_type: string; start_time: string | null } | null {
  const now = new Date();
  const upcoming = sessions
    .filter((s) => {
      if (!s.start_time) return false;
      if (s.status === "completed" || s.status === "ingested") return false;
      return new Date(s.start_time) > now;
    })
    .sort((a, b) => {
      const timeA = new Date(a.start_time!).getTime();
      const timeB = new Date(b.start_time!).getTime();
      return timeA - timeB;
    });

  return upcoming[0] || null;
}

function StaleDataBanner({ lastUpdated }: { lastUpdated?: string }) {
  const relativeTime = lastUpdated
    ? new Date(lastUpdated).toLocaleString()
    : "unknown";

  return (
    <div className="stale-warning mb-4 animate-fadeInUp">
      <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <p className="font-semibold text-sm">Data may be outdated</p>
        <p className="text-xs text-yellow-700">Last updated: {relativeTime}</p>
      </div>
    </div>
  );
}

function getDaysUntilFP1(
  sessions: Array<{ session_type: string; start_time: string | null }> | null
): number | null {
  if (!sessions) return null;

  // Find FP1 or first session
  const fp1 = sessions.find(
    (s) => s.session_type.toLowerCase() === "fp1" || s.session_type.toLowerCase() === "practice_1"
  );
  const firstSession = fp1 || sessions.find((s) => s.start_time);

  if (!firstSession?.start_time) return null;

  const now = new Date();
  const fp1Date = new Date(firstSession.start_time);
  const diffMs = fp1Date.getTime() - now.getTime();
  const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  return days > 0 ? days : null;
}

function OffWeekState({
  daysUntil,
  nextRaceInfo,
}: {
  daysUntil: number;
  nextRaceInfo?: { raceName: string | null; circuitCountry: string | null; round: number } | null;
}) {
  const flag = nextRaceInfo?.circuitCountry ? getCountryFlag(nextRaceInfo.circuitCountry) : "";

  return (
    <Card accent>
      <CardContent className="py-8 sm:py-12">
        <div className="text-center">
          <div className="text-4xl mb-4">🏁</div>
          <h3 className="font-semibold text-lg mb-2">No Race This Week</h3>
          <p className="text-muted text-sm mb-4">
            Next race weekend begins in{" "}
            <span className="font-bold text-ink">{daysUntil} day{daysUntil !== 1 ? "s" : ""}</span>
          </p>
          {nextRaceInfo?.raceName && (
            <p className="text-sm text-ink/80 mb-4">
              {flag && <span className="mr-1.5">{flag}</span>}
              <span className="font-medium">{nextRaceInfo.raceName}</span>
              <span className="text-muted"> • Round {nextRaceInfo.round}</span>
            </p>
          )}
          <Link href="/circuits">
            <Button variant="outline" size="sm">
              View Full Calendar
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ nextRaceInfo }: { nextRaceInfo?: NextRaceInfo | null }) {
  // If we have info about the next race from circuits data, show it
  if (nextRaceInfo?.fp1Date) {
    const now = new Date();
    const fp1Date = new Date(nextRaceInfo.fp1Date);
    const diffMs = fp1Date.getTime() - now.getTime();
    const daysUntil = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (daysUntil > 0) {
      return (
        <OffWeekState
          daysUntil={daysUntil}
          nextRaceInfo={{
            raceName: nextRaceInfo.raceName,
            circuitCountry: nextRaceInfo.circuitCountry,
            round: nextRaceInfo.round,
          }}
        />
      );
    }
  }

  return (
    <Card accent>
      <CardContent className="py-8 sm:py-12">
        <div className="text-center">
          <div className="text-4xl mb-4">🏎️</div>
          <h3 className="font-semibold text-lg mb-2">No Upcoming Race</h3>
          <p className="text-muted text-sm mb-4">
            Check back later for the next race weekend schedule
          </p>
          <Link href="/circuits">
            <Button variant="outline" size="sm">
              View All Circuits
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <Card accent>
      <CardContent className="py-8 sm:py-12">
        <div className="text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h3 className="font-semibold text-lg mb-2">Unable to Load Race Data</h3>
          <p className="text-muted text-sm mb-4">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
          >
            Try Again
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function RaceWeekendWidget({ weekendData, nextRaceInfo, error }: RaceWeekendWidgetProps) {
  if (error) {
    return <ErrorState error={error} />;
  }

  if (!weekendData || !weekendData.schedule) {
    return <EmptyState nextRaceInfo={nextRaceInfo} />;
  }

  const { schedule, history, sessions: sessionResults, meta } = weekendData;
  const widgetState = determineWidgetState(schedule);
  const nextSession = getNextSession(schedule.sessions);

  // For off-week state (>7 days until race), show simplified message
  if (widgetState === "off-week") {
    const daysUntil = getDaysUntilFP1(schedule.sessions);
    if (daysUntil && daysUntil > 0) {
      return (
        <OffWeekState
          daysUntil={daysUntil}
          nextRaceInfo={{
            raceName: schedule.race_name,
            circuitCountry: schedule.circuit_country,
            round: schedule.round,
          }}
        />
      );
    }
  }

  // Show stale indicator if data is old
  const isStale = meta?.stale || false;
  const lastUpdated = meta?.last_updated;

  const showCountdown = (widgetState === "pre-weekend" || widgetState === "race-week") && nextSession?.start_time;
  const showDuringWeekendCountdown = widgetState === "during-weekend" && nextSession?.start_time;
  const showSessionGrid = widgetState === "during-weekend" || widgetState === "post-race";
  const showHistoricalData = (widgetState === "pre-weekend" || widgetState === "race-week") && history;

  return (
    <Card accent>
      <CardHeader className="animate-fadeInUp animation-delay-0">
        <RaceHeader
          raceName={schedule.race_name}
          round={schedule.round}
          circuitName={schedule.circuit_name}
          circuitCountry={schedule.circuit_country}
          isSprintWeekend={schedule.is_sprint_weekend}
        />
      </CardHeader>

      <CardContent>
        {isStale && <StaleDataBanner lastUpdated={lastUpdated} />}

        {/* Show countdown for pre-weekend or during-weekend states */}
        {showCountdown && (
          <div className="mb-5 -mx-4 sm:-mx-6">
            <RaceCountdown
              targetDate={nextSession.start_time!}
              sessionType={nextSession.session_type}
            />
          </div>
        )}

        {/* Show countdown to next session during weekend */}
        {showDuringWeekendCountdown && (
          <div className="mb-5 -mx-4 sm:-mx-6">
            <RaceCountdown
              targetDate={nextSession.start_time!}
              sessionType={nextSession.session_type}
              label={`NEXT: ${nextSession.session_type.replace(/_/g, " ").toUpperCase()}`}
            />
          </div>
        )}

        {/* Session Grid - show during and after weekend */}
        {showSessionGrid && (
          <div className="animate-fadeInUp animation-delay-200">
            <SessionGrid
              sessions={schedule.sessions}
              sessionResults={sessionResults}
              isSprintWeekend={schedule.is_sprint_weekend}
            />
          </div>
        )}

        {/* Historical Data - show before race weekend */}
        {showHistoricalData && (
          <HistoricalData
            history={history}
            circuitName={schedule.circuit_name}
          />
        )}

        {/* Errors from individual sections */}
        {meta?.errors && meta.errors.length > 0 && (
          <div className="mt-5 pt-4 border-t border-ink/10">
            <p className="text-xs text-muted flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Some data may be unavailable
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
