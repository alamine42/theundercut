import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TeamWithLogo } from "@/components/ui/team-logo";
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

export default async function HomePage() {
  const { standings, error } = await getHomeData();

  const topDrivers = standings?.drivers.slice(0, 5) ?? [];
  const topConstructors = standings?.constructors.slice(0, 5) ?? [];
  const racesCompleted = standings?.races_completed ?? 0;
  const racesRemaining = standings?.races_remaining ?? 0;

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

      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {error ? (
            <Card>
              <CardContent>
                <p className="text-muted">{error}</p>
              </CardContent>
            </Card>
          ) : (
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
          )}
        </div>
      </section>
    </>
  );
}
