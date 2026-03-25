"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/ui/score-indicator";
import { RaceHeader } from "./RaceHeader";
import { RaceCountdown } from "./RaceCountdown";
import { HistoricalData } from "./HistoricalData";
import { SessionGrid } from "./SessionGrid";
import { getCountryFlag } from "@/lib/utils";
import type { RaceWeekendWidgetProps, WidgetState, NextRaceInfo, WeekendResponse, CircuitCharacteristics } from "./types";
import { hasMissingSessionResults } from "./utils";

/** Number of hours after race end before the widget reverts to showing next race countdown */
const RACE_WEEKEND_ACTIVE_HOURS = 24;
const LIVE_REFRESH_INTERVAL_MS = 60 * 1000;

const TIMELINE_STATE_MAP: Record<string, WidgetState> = {
  "pre-weekend": "pre-weekend",
  "race-week": "race-week",
  "during-weekend": "during-weekend",
  "post-race": "post-race",
  "off-week": "off-week",
};

function mapTimelineState(state?: string | null): WidgetState | null {
  if (!state) return null;
  return TIMELINE_STATE_MAP[state] ?? null;
}

async function fetchLatestWeekendData(season: number, round: number): Promise<WeekendResponse | null> {
  const url = `/api/v1/race/${season}/${round}/weekend?t=${Date.now()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to refresh weekend data (${res.status})`);
  }
  return res.json();
}

/**
 * Calculates hours since the race ended.
 * Returns null if race hasn't completed or timing info unavailable.
 */
function getHoursSinceRaceEnd(
  sessions: Array<{ session_type: string; start_time: string | null; end_time?: string | null; status: string }>
): number | null {
  const raceSession = sessions.find(
    (s) => s.session_type.toLowerCase() === "race"
  );

  if (!raceSession || (raceSession.status !== "completed" && raceSession.status !== "ingested")) {
    return null;
  }

  const now = new Date();
  let raceEndTime: Date;

  if (raceSession.end_time) {
    raceEndTime = new Date(raceSession.end_time);
    if (isNaN(raceEndTime.getTime())) {
      return null;
    }
  } else if (raceSession.start_time) {
    // Estimate race end as start + 2 hours
    raceEndTime = new Date(raceSession.start_time);
    raceEndTime.setHours(raceEndTime.getHours() + 2);
  } else {
    return null;
  }

  return (now.getTime() - raceEndTime.getTime()) / (1000 * 60 * 60);
}

function shouldContinuePolling(data: WeekendResponse | null): boolean {
  if (!data?.schedule) {
    return false;
  }

  const normalizedState = mapTimelineState(data.timeline?.state) ?? determineWidgetState(data.schedule);

  if (normalizedState === "during-weekend") {
    return true;
  }

  if (normalizedState === "post-race") {
    if (data.timeline?.window_end) {
      const windowEnd = new Date(data.timeline.window_end);
      if (Number.isNaN(windowEnd.getTime()) || windowEnd > new Date()) {
        return true;
      }
    } else {
      const hoursSince = getHoursSinceRaceEnd(data.schedule.sessions);
      if (hoursSince === null || hoursSince < RACE_WEEKEND_ACTIVE_HOURS) {
        return true;
      }
    }
  }

  return hasMissingSessionResults(data);
}

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
    (s) => s.session_type.toLowerCase() === "fp1"
  );
  const firstSession = fp1 || sessions.find((s) => s.start_time);

  if (!firstSession?.start_time) return null;

  const now = new Date();
  const fp1Date = new Date(firstSession.start_time);
  const diffMs = fp1Date.getTime() - now.getTime();
  const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  return days > 0 ? days : null;
}

function getDaysUntilDate(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const now = new Date();
  const target = new Date(dateStr);
  if (Number.isNaN(target.getTime())) return null;
  const diffMs = target.getTime() - now.getTime();
  const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  return days > 0 ? days : null;
}

/**
 * Determines if the race weekend is currently active.
 * Active means: FP1 has started AND less than 24 hours have passed since the race end.
 * When active, the widget title shows the GP name instead of "Upcoming Race".
 */
function fallbackRaceWeekendActive(
  widgetState: WidgetState,
  sessions: Array<{ session_type: string; start_time: string | null; end_time?: string | null; status: string }>
): boolean {
  // Race weekend is active during the weekend
  if (widgetState === "during-weekend") {
    return true;
  }

  // For post-race, check if less than 24 hours have passed since race end
  if (widgetState === "post-race") {
    const hoursSinceRaceEnd = getHoursSinceRaceEnd(sessions);
    if (hoursSinceRaceEnd === null) {
      return true; // No timing info, assume still active
    }
    return hoursSinceRaceEnd < RACE_WEEKEND_ACTIVE_HOURS;
  }

  // Pre-weekend, race-week, off-week: not active
  return false;
}

function OffWeekState({
  daysUntil,
  nextRaceInfo,
  message = "No Race This Week",
}: {
  daysUntil: number;
  nextRaceInfo?: { raceName: string | null; circuitCountry: string | null; round: number } | null;
  message?: string;
}) {
  const flag = nextRaceInfo?.circuitCountry ? getCountryFlag(nextRaceInfo.circuitCountry) : "";

  return (
    <Card accent>
      <CardContent className="py-8 sm:py-12">
        <div className="text-center">
          <div className="text-4xl mb-4">🏁</div>
          <h3 className="font-semibold text-lg mb-2">{message}</h3>
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

function CircuitHighlights({
  characteristics,
  circuitId,
  season,
}: {
  characteristics: CircuitCharacteristics;
  circuitId: string | null;
  season: number;
}) {
  const chars = characteristics;
  const circuitLink = circuitId ? `/circuits/${season}/${circuitId}` : "/circuits";

  // Collect the key highlights to show
  const highlights: Array<{ label: string; score: number | null; detail?: string }> = [];

  if (chars.downforce?.score != null) {
    highlights.push({ label: "Downforce", score: chars.downforce.score, detail: chars.downforce.label ?? undefined });
  }
  if (chars.tire_degradation?.score != null) {
    highlights.push({ label: "Tire Deg", score: chars.tire_degradation.score, detail: chars.tire_degradation.label ?? undefined });
  }
  if (chars.overtaking?.score != null) {
    highlights.push({ label: "Overtaking", score: chars.overtaking.score, detail: chars.overtaking.label ?? undefined });
  }
  if (chars.full_throttle?.score != null) {
    highlights.push({ label: "Throttle", score: chars.full_throttle.score, detail: chars.full_throttle.value ? `${chars.full_throttle.value}%` : undefined });
  }

  if (highlights.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-ink/10 animate-fadeInUp animation-delay-100">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Circuit Characteristics</h3>
        <Link
          href={circuitLink}
          className="text-xs font-medium text-accent hover:underline inline-flex items-center gap-1"
        >
          Learn more
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {highlights.map((h) => (
          <div key={h.label} className="flex flex-col items-center gap-1 p-2 bg-ink/[0.03] rounded">
            <span className="text-[11px] text-muted font-medium">{h.label}</span>
            <ScoreBadge score={h.score} />
            {h.detail && <span className="text-[10px] text-muted">{h.detail}</span>}
          </div>
        ))}
      </div>
      {/* Track info pills */}
      {(chars.circuit_type || chars.track_length_km || chars.drs_zones != null || chars.corners?.total != null) && (
        <div className="mt-2 flex flex-wrap gap-2">
          {chars.circuit_type && (
            <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium bg-ink/5 rounded">
              {chars.circuit_type}
            </span>
          )}
          {chars.track_length_km && (
            <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium bg-ink/5 rounded">
              {chars.track_length_km} km
            </span>
          )}
          {chars.drs_zones != null && (
            <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium bg-ink/5 rounded">
              {chars.drs_zones} DRS zone{chars.drs_zones !== 1 ? "s" : ""}
            </span>
          )}
          {chars.corners?.total != null && (
            <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium bg-ink/5 rounded">
              {chars.corners.total} corners
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function RaceWeekendWidget({
  weekendData,
  nextRaceInfo,
  circuitCharacteristics,
  error,
  liveUpdate = true,
}: RaceWeekendWidgetProps) {
  const [liveWeekendData, setLiveWeekendData] = useState<WeekendResponse | null>(weekendData);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    setLiveWeekendData(weekendData);
  }, [weekendData]);

  const targetSeason = weekendData?.schedule?.season ?? null;
  const targetRound = weekendData?.schedule?.round ?? null;
  const shouldPollInitially = liveUpdate && shouldContinuePolling(weekendData);

  useEffect(() => {
    if (!liveUpdate) return;
    if (targetSeason == null || targetRound == null) return;

    const season = targetSeason as number;
    const round = targetRound as number;

    let cancelled = false;
    let interval: ReturnType<typeof setInterval> | null = null;

    async function refresh() {
      try {
        setIsRefreshing(true);
        const latest = await fetchLatestWeekendData(season, round);
        if (cancelled || !latest) return;
        setLiveWeekendData(latest);
        setRefreshError(null);

        if (shouldContinuePolling(latest)) {
          if (interval === null) {
            interval = setInterval(refresh, LIVE_REFRESH_INTERVAL_MS);
          }
        } else if (interval) {
          clearInterval(interval);
          interval = null;
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to refresh weekend data", err);
          setRefreshError("Live data refresh failed");
          if (interval === null && shouldPollInitially) {
            interval = setInterval(refresh, LIVE_REFRESH_INTERVAL_MS);
          }
        }
      } finally {
        if (!cancelled) {
          setIsRefreshing(false);
        }
      }
    }

    refresh();

    if (shouldPollInitially && interval === null) {
      interval = setInterval(refresh, LIVE_REFRESH_INTERVAL_MS);
    }

    return () => {
      cancelled = true;
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [liveUpdate, targetSeason, targetRound, shouldPollInitially]);

  if (error) {
    return <ErrorState error={error} />;
  }

  const currentWeekendData = liveWeekendData ?? weekendData;

  if (!currentWeekendData || !currentWeekendData.schedule) {
    return <EmptyState nextRaceInfo={nextRaceInfo} />;
  }

  const { schedule, history, sessions: sessionResults, meta, timeline } = currentWeekendData;
  const serverState = mapTimelineState(timeline?.state);
  const widgetState = serverState ?? determineWidgetState(schedule);
  const nextSessionFromTimeline = timeline?.next_session ?? null;
  const nextSession = nextSessionFromTimeline ?? getNextSession(schedule.sessions);

  // Check if we're in "expired post-race" state (>24 hours since race ended)
  // In this state, we should show the countdown to the next race instead
  const hoursSinceRaceEnd = getHoursSinceRaceEnd(schedule.sessions);
  const isExpiredPostRace = (() => {
    if (timeline) {
      if (timeline.state !== "post-race") return false;
      if (!timeline.window_end) return false;
      return new Date(timeline.window_end) < new Date();
    }
    return widgetState === "post-race" &&
      hoursSinceRaceEnd !== null &&
      hoursSinceRaceEnd >= RACE_WEEKEND_ACTIVE_HOURS;
  })();

  // If post-race has expired and we have next race info, show countdown to next race
  if (isExpiredPostRace && nextRaceInfo?.fp1Date) {
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
          message="Upcoming Race"
        />
      );
    }
  }

  // For off-week state (>7 days until race), show simplified message
  const offWeekDays = (() => {
    const nextRaceDate = nextRaceInfo?.fp1Date ?? timeline?.next_session?.start_time ?? null;
    const daysFromNextInfo = getDaysUntilDate(nextRaceDate);
    if (daysFromNextInfo) {
      return daysFromNextInfo;
    }
    return getDaysUntilFP1(schedule.sessions);
  })();

  if (widgetState === "off-week" && offWeekDays && offWeekDays > 0) {
    const info = nextRaceInfo ?? {
      raceName: schedule.race_name,
      circuitCountry: schedule.circuit_country,
      round: schedule.round,
    };
    return (
      <OffWeekState
        daysUntil={offWeekDays}
        nextRaceInfo={info}
      />
    );
  }

  // Show stale indicator if data is old
  const isStale = meta?.stale || false;
  const lastUpdated = meta?.last_updated;

  const showCountdown = (widgetState === "pre-weekend" || widgetState === "race-week") && nextSession?.start_time;
  const showDuringWeekendCountdown = widgetState === "during-weekend" && nextSession?.start_time;
  const showSessionGrid = (widgetState === "during-weekend" || widgetState === "post-race") && !isExpiredPostRace;
  const showHistoricalData = (widgetState === "pre-weekend" || widgetState === "race-week") && history;

  // Use nextRaceInfo as fallback when schedule data is missing
  const displayRaceName = schedule.race_name || nextRaceInfo?.raceName || null;
  const displayCircuitName = schedule.circuit_name || nextRaceInfo?.circuitName || null;
  const displayCircuitCountry = schedule.circuit_country || nextRaceInfo?.circuitCountry || null;

  const isRaceWeekendActive = timeline?.is_active ?? fallbackRaceWeekendActive(widgetState, schedule.sessions);

  return (
    <Card accent>
      <CardHeader className="animate-fadeInUp animation-delay-0">
        <RaceHeader
          raceName={displayRaceName}
          round={schedule.round}
          circuitName={displayCircuitName}
          circuitCountry={displayCircuitCountry}
          isSprintWeekend={schedule.is_sprint_weekend}
          isRaceWeekendActive={isRaceWeekendActive}
        />
      </CardHeader>

      <CardContent>
        {liveUpdate && (
          <div className="flex justify-end text-[11px] text-muted mb-2">
            <span className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${isRefreshing ? "bg-emerald-500 animate-pulse" : "bg-gray-400/70"}`}
                aria-hidden="true"
              />
              Live data
            </span>
          </div>
        )}

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
            />
          </div>
        )}

        {/* Circuit Characteristics - show before race weekend */}
        {(widgetState === "pre-weekend" || widgetState === "race-week") && circuitCharacteristics && (
          <CircuitHighlights
            characteristics={circuitCharacteristics}
            circuitId={schedule.circuit_id}
            season={schedule.season}
          />
        )}

        {/* Historical Data - show before race weekend */}
        {showHistoricalData && (
          <HistoricalData
            history={history}
            circuitName={schedule.circuit_name}
          />
        )}

        {liveUpdate && refreshError && (
          <p className="mt-4 text-xs text-red-600">
            Live update failed. Showing cached data.
          </p>
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
