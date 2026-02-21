import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TeamWithLogo } from "@/components/ui/team-logo";
import { SeasonResultsTable } from "@/components/season-results-table";
import { fetchStandings } from "@/lib/api";
import { DEFAULT_SEASON } from "@/lib/constants";

export const revalidate = 300; // 5 minutes ISR

async function getHomeData() {
  try {
    const standings = await fetchStandings(DEFAULT_SEASON);
    return { standings, error: null };
  } catch (error) {
    console.error("Failed to fetch homepage data:", error);
    return { standings: null, error: "Failed to load data" };
  }
}

function formatRaceDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function PositionChange({ gained }: { gained: number }) {
  if (gained === 0) {
    return <span className="text-muted">—</span>;
  }
  if (gained > 0) {
    return <span className="text-success">+{gained} ↑</span>;
  }
  return <span className="text-error">{gained} ↓</span>;
}

export default async function HomePage() {
  const { standings, error } = await getHomeData();

  const topDrivers = standings?.drivers.slice(0, 5) ?? [];
  const topConstructors = standings?.constructors.slice(0, 5) ?? [];
  const racesCompleted = standings?.races_completed ?? 0;
  const racesRemaining = standings?.races_remaining ?? 0;
  const lastRace = standings?.last_race ?? null;
  const raceSummaries = standings?.race_summaries ?? [];

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
              {/* Last Race Results */}
              {lastRace && lastRace.results.length > 0 && (
                <Card accent>
                  <CardHeader>
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <CardTitle>{lastRace.race_name} Results</CardTitle>
                      <span className="text-sm text-muted">{formatRaceDate(lastRace.date)}</span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Pos</TableHead>
                            <TableHead>Driver</TableHead>
                            <TableHead className="hidden sm:table-cell">Team</TableHead>
                            <TableHead className="text-center hidden sm:table-cell">Grid</TableHead>
                            <TableHead className="text-right">Points</TableHead>
                            <TableHead className="text-center">+/-</TableHead>
                            <TableHead className="hidden md:table-cell">Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {lastRace.results.map((result) => (
                            <TableRow key={result.driver_code}>
                              <TableCell className="font-semibold">{result.position}</TableCell>
                              <TableCell className="font-semibold">{result.driver_code}</TableCell>
                              <TableCell className="hidden sm:table-cell"><TeamWithLogo team={result.team} /></TableCell>
                              <TableCell className="text-center text-muted hidden sm:table-cell">{result.grid}</TableCell>
                              <TableCell className="text-right font-semibold">{result.points}</TableCell>
                              <TableCell className="text-center">
                                <PositionChange gained={result.positions_gained} />
                              </TableCell>
                              <TableCell className="text-muted hidden md:table-cell">{result.status}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="mt-4">
                      <Link href={`/analytics/${DEFAULT_SEASON}/${lastRace.round}`}>
                        <Button variant="ghost" size="sm">
                          View race analytics →
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
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
                  <CardTitle>Driver Championship</CardTitle>
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
                  <CardTitle>Constructor Championship</CardTitle>
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
