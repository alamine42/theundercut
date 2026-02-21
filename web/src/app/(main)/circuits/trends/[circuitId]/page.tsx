import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { CircuitTrendsChart } from "@/components/charts/circuit-trends-chart";
import { TeamWithLogo } from "@/components/ui/team-logo";
import { fetchCircuitTrends } from "@/lib/api";

export const revalidate = 300; // 5 minutes ISR

interface CircuitTrendsPageProps {
  params: Promise<{ circuitId: string }>;
}

export async function generateMetadata({ params }: CircuitTrendsPageProps) {
  const { circuitId } = await params;
  return {
    title: `${circuitId} Trends | The Undercut`,
    description: `Multi-season lap time trends and performance evolution for ${circuitId}`,
  };
}

export default async function CircuitTrendsPage({ params }: CircuitTrendsPageProps) {
  const { circuitId } = await params;

  let data;
  try {
    data = await fetchCircuitTrends(circuitId);
  } catch {
    notFound();
  }

  const { trends } = data;

  // Calculate stats
  const yearsWithData = trends.filter((t) => t.pole_time_ms || t.fastest_lap_ms);
  const latestYear = yearsWithData.length > 0 ? Math.max(...yearsWithData.map((t) => t.year)) : null;
  const earliestYear = yearsWithData.length > 0 ? Math.min(...yearsWithData.map((t) => t.year)) : null;

  // Find fastest ever pole and fastest lap
  const fastestPole = trends
    .filter((t) => t.pole_time_ms)
    .sort((a, b) => (a.pole_time_ms ?? Infinity) - (b.pole_time_ms ?? Infinity))[0];
  const fastestLap = trends
    .filter((t) => t.fastest_lap_ms)
    .sort((a, b) => (a.fastest_lap_ms ?? Infinity) - (b.fastest_lap_ms ?? Infinity))[0];

  // Most successful driver (most wins)
  const winnerCounts: Record<string, number> = {};
  for (const t of trends) {
    if (t.winner) {
      winnerCounts[t.winner] = (winnerCounts[t.winner] || 0) + 1;
    }
  }
  const mostWins = Object.entries(winnerCounts).sort((a, b) => b[1] - a[1])[0];

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-4">
            <Link
              href="/circuits/2024"
              className="inline-flex items-center text-sm text-muted hover:text-ink transition-colors"
            >
              <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Circuits
            </Link>
          </div>

          <HeroTitle>{circuitId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Trends</HeroTitle>
          <HeroSubtitle>
            Multi-season lap time evolution and performance history
          </HeroSubtitle>

          <HeroStats>
            {earliestYear && latestYear && (
              <HeroStat label="Data Range" value={`${earliestYear}–${latestYear}`} />
            )}
            <HeroStat label="Seasons" value={yearsWithData.length} />
            {mostWins && <HeroStat label="Most Wins" value={`${mostWins[0]} (${mostWins[1]})`} />}
          </HeroStats>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-8 sm:space-y-12">
          {/* Lap Time Evolution Chart */}
          <CircuitTrendsChart trends={trends} />

          {/* Records Summary */}
          <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
            {fastestPole && (
              <article className="border-2 border-ink bg-paper p-4 sm:p-6">
                <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                  Fastest Pole Ever
                </h2>
                <p className="text-2xl sm:text-3xl font-bold font-mono">{fastestPole.pole_time}</p>
                <p className="mt-2 text-muted">
                  {fastestPole.pole_driver} &middot; {fastestPole.year}
                </p>
              </article>
            )}

            {fastestLap && (
              <article className="border-2 border-ink bg-paper p-4 sm:p-6">
                <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                  Fastest Race Lap Ever
                </h2>
                <p className="text-2xl sm:text-3xl font-bold font-mono">{fastestLap.fastest_lap_time}</p>
                <p className="mt-2 text-muted">
                  {fastestLap.fastest_lap_driver} &middot; {fastestLap.year}
                </p>
              </article>
            )}
          </div>

          {/* Season-by-Season Table */}
          {trends.length > 0 && (
            <article className="border-2 border-ink bg-paper">
              <h2 className="relative px-4 sm:p-6 pt-6 pb-4 text-lg font-semibold tracking-tight before:absolute before:left-0 before:top-6 before:h-6 before:w-1 before:bg-accent">
                Season by Season
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-ink text-paper">
                    <tr>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Year</th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Winner</th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Team</th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Pole</th>
                      <th className="px-3 sm:px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Pole Time</th>
                      <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">Fastest Lap</th>
                      <th className="px-3 sm:px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide whitespace-nowrap">FL Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-light">
                    {trends
                      .slice()
                      .sort((a, b) => b.year - a.year)
                      .map((trend) => (
                        <tr key={trend.year} className="hover:bg-ink hover:text-paper transition-colors">
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm font-semibold">{trend.year}</td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm">
                            {trend.winner ? (
                              <span className="font-semibold">{trend.winner}</span>
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm">
                            {trend.winner_team ? (
                              <TeamWithLogo team={trend.winner_team} />
                            ) : (
                              <span className="text-muted">—</span>
                            )}
                          </td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm">{trend.pole_driver || "—"}</td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm text-right font-mono">
                            {trend.pole_time || "—"}
                          </td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm">{trend.fastest_lap_driver || "—"}</td>
                          <td className="px-3 sm:px-6 py-3 sm:py-4 text-sm text-right font-mono">
                            {trend.fastest_lap_time || "—"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}
        </div>
      </section>
    </>
  );
}
