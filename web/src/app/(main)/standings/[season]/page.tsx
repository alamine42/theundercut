import { notFound } from "next/navigation";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { YearSelector } from "@/components/ui/year-selector";
import { fetchStandings } from "@/lib/api";
import { AVAILABLE_SEASONS } from "@/lib/constants";
import { formatNumber } from "@/lib/utils";

export const revalidate = 300; // 5 minutes ISR

interface StandingsPageProps {
  params: Promise<{ season: string }>;
}

export async function generateMetadata({ params }: StandingsPageProps) {
  const { season } = await params;
  return {
    title: `${season} Championship Standings | The Undercut`,
    description: `F1 ${season} driver and constructor championship standings with detailed metrics`,
  };
}

export default async function StandingsPage({ params }: StandingsPageProps) {
  const { season: seasonStr } = await params;
  const season = parseInt(seasonStr, 10);

  if (isNaN(season) || season < 2018 || season > 2030) {
    notFound();
  }

  let standings;
  try {
    standings = await fetchStandings(season);
  } catch {
    notFound();
  }

  const { drivers, constructors, races_completed, races_remaining } = standings;

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <HeroTitle>{season} Championship</HeroTitle>
              <HeroSubtitle>
                Driver and constructor standings with performance metrics
              </HeroSubtitle>
            </div>
            <YearSelector currentYear={season} basePath="/standings" availableYears={AVAILABLE_SEASONS} />
          </div>

          <HeroStats>
            <HeroStat label="Races Completed" value={races_completed} />
            <HeroStat label="Races Remaining" value={races_remaining} />
            <HeroStat label="Drivers" value={drivers.length} />
            <HeroStat label="Teams" value={constructors.length} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-12">
            {/* Driver Championship */}
            <Card accent>
              <CardHeader>
                <CardTitle>Driver Championship</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Pos</TableHead>
                        <TableHead>Driver</TableHead>
                        <TableHead>Team</TableHead>
                        <TableHead className="text-right">Points</TableHead>
                        <TableHead className="text-right">Wins</TableHead>
                        <TableHead className="text-right">Races</TableHead>
                        <TableHead className="text-right">Last 5</TableHead>
                        <TableHead className="text-right">Pts/Race</TableHead>
                        <TableHead className="text-right">Avg Start</TableHead>
                        <TableHead className="text-right">Avg Finish</TableHead>
                        <TableHead className="text-right">Pos Gained</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {drivers.map((driver, idx) => (
                        <TableRow key={driver.driver_code}>
                          <TableCell className="font-semibold">{idx + 1}</TableCell>
                          <TableCell className="font-semibold">{driver.driver_code}</TableCell>
                          <TableCell className="text-muted">{driver.constructor_name}</TableCell>
                          <TableCell className="text-right font-semibold">{driver.points}</TableCell>
                          <TableCell className="text-right">{driver.wins}</TableCell>
                          <TableCell className="text-right">{driver.total_races}</TableCell>
                          <TableCell className="text-right">{driver.pts_last_5}</TableCell>
                          <TableCell className="text-right">{formatNumber(driver.points_per_race)}</TableCell>
                          <TableCell className="text-right">{formatNumber(driver.avg_start_pos)}</TableCell>
                          <TableCell className="text-right">{formatNumber(driver.avg_finish_pos)}</TableCell>
                          <TableCell className="text-right">
                            <span className={driver.positions_gained >= 0 ? "text-success" : "text-error"}>
                              {driver.positions_gained >= 0 ? "+" : ""}{driver.positions_gained}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Constructor Championship */}
            <Card accent>
              <CardHeader>
                <CardTitle>Constructor Championship</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Pos</TableHead>
                        <TableHead>Team</TableHead>
                        <TableHead className="text-right">Points</TableHead>
                        <TableHead className="text-right">Wins</TableHead>
                        <TableHead className="text-right">Last 5</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {constructors.map((constructor, idx) => (
                        <TableRow key={constructor.constructor_id}>
                          <TableCell className="font-semibold">{idx + 1}</TableCell>
                          <TableCell className="font-semibold">{constructor.constructor_name}</TableCell>
                          <TableCell className="text-right font-semibold">{constructor.points}</TableCell>
                          <TableCell className="text-right">{constructor.wins}</TableCell>
                          <TableCell className="text-right">{constructor.pts_last_5}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </>
  );
}
