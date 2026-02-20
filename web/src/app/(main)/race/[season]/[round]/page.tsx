import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { fetchLaps } from "@/lib/api";
import { formatLapTime, groupBy } from "@/lib/utils";

export const revalidate = 300; // 5 minutes ISR

interface RacePageProps {
  params: Promise<{ season: string; round: string }>;
}

export async function generateMetadata({ params }: RacePageProps) {
  const { season, round } = await params;
  return {
    title: `Race ${round} Laps - ${season} | The Undercut`,
    description: `F1 ${season} Round ${round} lap time data`,
  };
}

export default async function RacePage({ params }: RacePageProps) {
  const { season: seasonStr, round: roundStr } = await params;
  const season = parseInt(seasonStr, 10);
  const round = parseInt(roundStr, 10);

  if (
    isNaN(season) ||
    isNaN(round) ||
    season < 2018 ||
    season > 2030 ||
    round < 1 ||
    round > 30
  ) {
    notFound();
  }

  let laps;
  try {
    laps = await fetchLaps(season, round);
  } catch {
    notFound();
  }

  const lapsByDriver = groupBy(laps, "driver");
  const drivers = Object.keys(lapsByDriver).sort();
  const totalLaps = Math.max(...laps.map((l) => l.lap), 0);

  // Calculate fastest lap for each driver
  const driverFastest = Object.entries(lapsByDriver).map(([driver, driverLaps]) => {
    const validLaps = driverLaps.filter((l) => l.lap_ms > 0);
    const fastest = validLaps.length > 0 ? Math.min(...validLaps.map((l) => l.lap_ms)) : null;
    const avgLap = validLaps.length > 0
      ? validLaps.reduce((sum, l) => sum + l.lap_ms, 0) / validLaps.length
      : null;
    return { driver, fastest, avgLap, lapsCompleted: driverLaps.length };
  }).sort((a, b) => (a.fastest ?? Infinity) - (b.fastest ?? Infinity));

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>Round {round} Race Data</HeroTitle>
          <HeroSubtitle>{season} Season - Lap time records</HeroSubtitle>

          <HeroStats>
            <HeroStat label="Season" value={season} />
            <HeroStat label="Round" value={round} />
            <HeroStat label="Total Laps" value={totalLaps} />
            <HeroStat label="Drivers" value={drivers.length} />
          </HeroStats>

          <div className="mt-8">
            <Link href={`/analytics/${season}/${round}`}>
              <Button>View Full Analytics</Button>
            </Link>
          </div>
        </div>
      </Hero>

      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <Card accent>
            <CardHeader>
              <CardTitle>Fastest Laps Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Driver</TableHead>
                    <TableHead className="text-right">Fastest Lap</TableHead>
                    <TableHead className="text-right">Avg Lap</TableHead>
                    <TableHead className="text-right">Laps</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {driverFastest.map((row) => (
                    <TableRow key={row.driver}>
                      <TableCell className="font-semibold">{row.driver}</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatLapTime(row.fastest)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted">
                        {formatLapTime(row.avgLap)}
                      </TableCell>
                      <TableCell className="text-right">{row.lapsCompleted}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
