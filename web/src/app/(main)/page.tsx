import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TeamWithLogo } from "@/components/ui/team-logo";
import { SeasonResultsTable } from "@/components/season-results-table";
import { RaceWeekendWidget } from "@/components/race-weekend";
import { fetchStandings, fetchTestingEvents, fetchCircuits, fetchWeekendData } from "@/lib/api";
import { DEFAULT_SEASON } from "@/lib/constants";
import { getCountryFlag } from "@/lib/utils";
import type { TestingEvent, WeekendResponse, Circuit } from "@/types/api";
import type { NextRaceInfo } from "@/components/race-weekend/types";

export const revalidate = 300; // 5 minutes ISR

/** Hours after race date to consider the race weekend still "active" for display */
const RACE_ACTIVE_HOURS_ESTIMATE = 42; // Race date + ~18h for race end + 24h window

async function getHomeData() {
  try {
    const [standings, testingData, circuitsData] = await Promise.all([
      fetchStandings(DEFAULT_SEASON).catch(() => null),
      fetchTestingEvents(DEFAULT_SEASON).catch(() => ({ events: [] })),
      fetchCircuits(DEFAULT_SEASON).catch(() => ({ circuits: [] })),
    ]);

    // Determine the next/current race round
    const now = new Date();
    const circuits = circuitsData.circuits || [];
    const upcomingRace = circuits.find((c) => c.date && new Date(c.date) >= now);
    const lastRace = [...circuits].reverse().find((c) => c.date && new Date(c.date) < now);

    // Check if we're still within the 24-hour post-race window
    // Race typically ends ~18 hours after race date starts (e.g., race at 2pm on Sunday)
    // We extend the window by 24 hours for post-race display
    let isWithinPostRaceWindow = false;
    if (lastRace?.date) {
      const lastRaceDate = new Date(lastRace.date);
      const hoursSinceRaceDate = (now.getTime() - lastRaceDate.getTime()) / (1000 * 60 * 60);
      isWithinPostRaceWindow = hoursSinceRaceDate < RACE_ACTIVE_HOURS_ESTIMATE;
    }

    // If within post-race window, show the last race; otherwise show upcoming
    const currentRound = isWithinPostRaceWindow
      ? lastRace?.round
      : (upcomingRace?.round || lastRace?.round || 1);

    // Fetch weekend data for the current/next round
    let weekendData: WeekendResponse | null = null;
    if (currentRound) {
      try {
        weekendData = await fetchWeekendData(DEFAULT_SEASON, currentRound);
      } catch {
        // Weekend data fetch failed, continue without it
      }
    }

    // Build nextRaceInfo - this should be the NEXT upcoming race
    // When showing a completed race, nextRaceInfo should point to the race after it
    let nextRaceInfo: NextRaceInfo | null = null;
    if (upcomingRace) {
      nextRaceInfo = {
        raceName: upcomingRace.race_name || null,
        circuitName: upcomingRace.name || null,
        circuitCountry: upcomingRace.country || null,
        fp1Date: upcomingRace.date || null, // Using race date as approximation for FP1
        round: upcomingRace.round || 1,
      };
    }

    return {
      standings,
      testingEvents: testingData.events,
      weekendData,
      nextRaceInfo,
      error: null,
    };
  } catch (error) {
    console.error("Failed to fetch homepage data:", error);
    return { standings: null, testingEvents: [], weekendData: null, nextRaceInfo: null, error: "Failed to load data" };
  }
}

export default async function HomePage() {
  const { standings, testingEvents, weekendData, nextRaceInfo, error } = await getHomeData();

  const topDrivers = standings?.drivers.slice(0, 5) ?? [];
  const topConstructors = standings?.constructors.slice(0, 5) ?? [];
  const racesCompleted = standings?.races_completed ?? 0;
  const racesRemaining = standings?.races_remaining ?? 0;
  const raceSummaries = standings?.race_summaries ?? [];
  // Determine if pre-season testing widget should be shown:
  // Only before the first race, and hide once we're within 24 hours of the first session
  const showPreSeasonTesting = (() => {
    if (racesCompleted > 0 || testingEvents.length === 0) return false;

    const now = new Date();
    const sessions = weekendData?.schedule?.sessions ?? [];
    const firstSessionStart = sessions
      .map((s) => s.start_time)
      .filter((t): t is string => t !== null)
      .sort()[0];

    if (firstSessionStart) {
      const msUntilFirstSession = new Date(firstSessionStart).getTime() - now.getTime();
      const twentyFourHoursMs = 24 * 60 * 60 * 1000;
      if (msUntilFirstSession <= twentyFourHoursMs) return false;
    }

    return true;
  })();

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>THE UNDERCUT</HeroTitle>
          <HeroSubtitle>
            F1 Analytics Dashboard - Race strategy, lap times, and championship standings
          </HeroSubtitle>

          <HeroStats>
            <HeroStat label="Season" value={DEFAULT_SEASON} />
            <HeroStat label="Races Completed" value={racesCompleted} />
            <HeroStat label="Races Remaining" value={racesRemaining} />
          </HeroStats>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link href={`/standings/${DEFAULT_SEASON}`}>
              <Button>View Full Standings</Button>
            </Link>
            <Link href={`/analytics/${DEFAULT_SEASON}/1`}>
              <Button variant="outline">Explore Analytics</Button>
            </Link>
          </div>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {error ? (
            <Card>
              <CardContent>
                <p className="text-muted">{error}</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-8">
              {/* Race Weekend Widget - shows current/upcoming race info and results */}
              <RaceWeekendWidget weekendData={weekendData} nextRaceInfo={nextRaceInfo} />

              {/* Pre-Season Testing Widget - only shown before first race and >24h from first session */}
              {showPreSeasonTesting && (
                <PreSeasonTestingWidget events={testingEvents} />
              )}

              {/* Season Results Summary */}
              {raceSummaries.length > 0 && (
                <SeasonResultsTable season={DEFAULT_SEASON} raceSummaries={raceSummaries} />
              )}

              {/* Championship Standings */}
              <div className="grid gap-8 lg:grid-cols-2">
              {/* Driver Standings */}
              <Card accent>
                <CardHeader>
                  <CardTitle>{DEFAULT_SEASON} Driver Championship</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Pos</TableHead>
                        <TableHead>Driver</TableHead>
                        <TableHead>Team</TableHead>
                        <TableHead className="text-right">Points</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topDrivers.map((driver, idx) => (
                        <TableRow key={driver.driver_code}>
                          <TableCell className="font-semibold">{idx + 1}</TableCell>
                          <TableCell>{driver.driver_code}</TableCell>
                          <TableCell className="text-muted"><TeamWithLogo team={driver.constructor_name} /></TableCell>
                          <TableCell className="text-right font-semibold">{driver.points}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="mt-4">
                    <Link href={`/standings/${DEFAULT_SEASON}`}>
                      <Button variant="ghost" size="sm">
                        View all drivers →
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>

              {/* Constructor Standings */}
              <Card accent>
                <CardHeader>
                  <CardTitle>{DEFAULT_SEASON} Constructor Championship</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Pos</TableHead>
                        <TableHead>Team</TableHead>
                        <TableHead className="text-right">Points</TableHead>
                        <TableHead className="text-right">Wins</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {topConstructors.map((constructor, idx) => (
                        <TableRow key={constructor.constructor_id}>
                          <TableCell className="font-semibold">{idx + 1}</TableCell>
                          <TableCell><TeamWithLogo team={constructor.constructor_name} /></TableCell>
                          <TableCell className="text-right font-semibold">{constructor.points}</TableCell>
                          <TableCell className="text-right text-muted">{constructor.wins}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <div className="mt-4">
                    <Link href={`/standings/${DEFAULT_SEASON}`}>
                      <Button variant="ghost" size="sm">
                        View all teams →
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}

function PreSeasonTestingWidget({ events }: { events: TestingEvent[] }) {
  const circuitCountries: Record<string, string> = {
    bahrain: "Bahrain",
    barcelona: "Spain",
    catalunya: "Spain",
    silverstone: "UK",
    albert_park: "Australia",
  };

  const formatDateRange = (start: string | null, end: string | null) => {
    if (!start) return "TBD";
    const startDate = new Date(start);
    const endDate = end ? new Date(end) : null;
    const startStr = startDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    if (!endDate) return startStr;
    const endStr = endDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    return `${startStr} – ${endStr}`;
  };

  const completedEvents = events.filter((e) => e.status === "completed").length;
  const totalDays = events.reduce((sum, e) => sum + e.total_days, 0);

  return (
    <Card accent>
      <CardHeader>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle>{DEFAULT_SEASON} Pre-Season Testing</CardTitle>
          <span className="text-sm text-muted">
            {completedEvents}/{events.length} events completed
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {events.map((event) => {
            const country = circuitCountries[event.circuit_id] || "";
            const statusColors = {
              scheduled: "bg-ink/10 text-ink",
              running: "bg-accent/20 text-accent",
              completed: "bg-green-100 text-green-800",
            };
            const statusLabels = {
              scheduled: "Upcoming",
              running: "Live",
              completed: "Completed",
            };

            return (
              <Link
                key={event.event_id}
                href={`/testing/${DEFAULT_SEASON}/${event.event_id}`}
                className="block group"
              >
                <div className="flex items-center justify-between p-4 border-2 border-ink/10 hover:border-ink hover:bg-ink hover:text-paper transition-all duration-200">
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col items-center justify-center bg-ink text-paper px-3 py-1.5 group-hover:bg-paper group-hover:text-ink transition-colors">
                      <span className="text-lg font-bold">{event.total_days}</span>
                      <span className="text-[10px] uppercase tracking-wider">Days</span>
                    </div>
                    <div>
                      <h3 className="font-semibold">{event.event_name}</h3>
                      <p className="text-sm text-muted group-hover:text-paper/70">
                        {getCountryFlag(country)} {event.circuit_name} · {formatDateRange(event.start_date, event.end_date)}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${statusColors[event.status]}`}>
                    {statusLabels[event.status]}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
        <div className="mt-4 pt-4 border-t border-ink/10 flex items-center justify-between">
          <p className="text-sm text-muted">
            {totalDays} total testing days
          </p>
          <Link href={`/testing/${DEFAULT_SEASON}`}>
            <Button variant="ghost" size="sm">
              View all testing data →
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
