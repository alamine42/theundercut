import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { fetchCircuitDetail } from "@/lib/api";

export const revalidate = 300; // 5 minutes ISR

interface CircuitDetailPageProps {
  params: Promise<{ season: string; circuitId: string }>;
}

export async function generateMetadata({ params }: CircuitDetailPageProps) {
  const { season, circuitId } = await params;
  return {
    title: `${circuitId} ${season} | The Undercut`,
    description: `Circuit analytics for ${circuitId} in ${season} - lap records, driver stats, and historical data`,
  };
}

export default async function CircuitDetailPage({ params }: CircuitDetailPageProps) {
  const { season: seasonStr, circuitId } = await params;
  const season = parseInt(seasonStr, 10);

  if (isNaN(season) || season < 2018 || season > 2030) {
    notFound();
  }

  let data;
  try {
    data = await fetchCircuitDetail(season, circuitId);
  } catch {
    notFound();
  }

  const { circuit, race_info, lap_records, historical_winners, driver_stats, team_stats, strategy_patterns } = data;

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="mb-4">
            <Link
              href={`/circuits/${season}`}
              className="inline-flex items-center text-sm text-muted hover:text-ink transition-colors"
            >
              <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to {season} Circuits
            </Link>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <HeroTitle>{circuit.name}</HeroTitle>
              <HeroSubtitle>
                {circuit.city}, {circuit.country}
              </HeroSubtitle>
              {race_info && (
                <p className="mt-2 text-sm text-muted">
                  Round {race_info.round} &middot; {race_info.race_name}
                </p>
              )}
            </div>
            {race_info?.round && (
              <span className="flex h-12 w-12 items-center justify-center border-2 border-ink text-lg font-bold">
                R{race_info.round}
              </span>
            )}
          </div>

          <HeroStats>
            {race_info?.winner && <HeroStat label="Winner" value={race_info.winner} />}
            {race_info?.pole && <HeroStat label="Pole" value={race_info.pole} />}
            {race_info?.fastest_lap && <HeroStat label="Fastest Lap" value={race_info.fastest_lap} />}
            <HeroStat label="Season" value={season} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Lap Records */}
          <div className="grid gap-6 md:grid-cols-2">
            <article className="border-2 border-ink bg-paper p-6">
              <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                All-Time Lap Record
              </h2>
              {lap_records.all_time_fastest ? (
                <div className="space-y-2">
                  <p className="text-3xl font-bold font-mono">{lap_records.all_time_fastest.time}</p>
                  <p className="text-muted">
                    {lap_records.all_time_fastest.driver} &middot; {lap_records.all_time_fastest.year}
                  </p>
                </div>
              ) : (
                <p className="text-muted">No data available</p>
              )}
            </article>

            <article className="border-2 border-ink bg-paper p-6">
              <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                {season} Fastest Lap
              </h2>
              {lap_records.season_fastest ? (
                <div className="space-y-2">
                  <p className="text-3xl font-bold font-mono">{lap_records.season_fastest.time}</p>
                  <p className="text-muted">{lap_records.season_fastest.driver}</p>
                </div>
              ) : (
                <p className="text-muted">No data available</p>
              )}
            </article>
          </div>

          {/* Race Info Card */}
          {race_info && (
            <article className="border-2 border-ink bg-paper p-6">
              <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                {season} Race Results
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Date</p>
                  <p className="font-semibold">
                    {new Date(race_info.date).toLocaleDateString("en-US", {
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Winner</p>
                  <p className="font-semibold">{race_info.winner || "—"}</p>
                  <p className="text-xs text-muted">{race_info.winner_team}</p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Pole Position</p>
                  <p className="font-semibold">{race_info.pole || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Fastest Lap</p>
                  <p className="font-semibold">{race_info.fastest_lap || "—"}</p>
                  <p className="text-xs text-muted font-mono">{race_info.fastest_lap_time}</p>
                </div>
              </div>
            </article>
          )}

          {/* Historical Winners */}
          {historical_winners.length > 0 && (
            <article className="border-2 border-ink bg-paper">
              <h2 className="relative p-6 pb-4 text-lg font-semibold tracking-tight before:absolute before:left-0 before:top-6 before:h-6 before:w-1 before:bg-accent">
                Historical Winners
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-ink text-paper">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Year</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Driver</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Team</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-light">
                    {historical_winners.map((winner) => (
                      <tr key={winner.year} className="hover:bg-ink hover:text-paper transition-colors">
                        <td className="px-6 py-4 text-sm font-semibold">{winner.year}</td>
                        <td className="px-6 py-4 text-sm">
                          <span className="font-semibold">{winner.driver}</span>
                          <span className="ml-2 text-muted">{winner.driver_name}</span>
                        </td>
                        <td className="px-6 py-4 text-sm">{winner.team}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}

          {/* Driver Performance at Circuit */}
          {driver_stats.length > 0 && (
            <article className="border-2 border-ink bg-paper">
              <h2 className="relative p-6 pb-4 text-lg font-semibold tracking-tight before:absolute before:left-0 before:top-6 before:h-6 before:w-1 before:bg-accent">
                Driver Performance at {circuit.name}
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-ink text-paper">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Driver</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Races</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Wins</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Podiums</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Points</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Avg Finish</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-light">
                    {driver_stats.map((driver) => (
                      <tr key={driver.driver} className="hover:bg-ink hover:text-paper transition-colors">
                        <td className="px-6 py-4 text-sm font-semibold">{driver.driver}</td>
                        <td className="px-6 py-4 text-sm text-center">{driver.races}</td>
                        <td className="px-6 py-4 text-sm text-center font-semibold">{driver.wins}</td>
                        <td className="px-6 py-4 text-sm text-center">{driver.podiums}</td>
                        <td className="px-6 py-4 text-sm text-center">{driver.points}</td>
                        <td className="px-6 py-4 text-sm text-center font-mono">{driver.avg_finish.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}

          {/* Team Performance at Circuit */}
          {team_stats.length > 0 && (
            <article className="border-2 border-ink bg-paper">
              <h2 className="relative p-6 pb-4 text-lg font-semibold tracking-tight before:absolute before:left-0 before:top-6 before:h-6 before:w-1 before:bg-accent">
                Team Performance at {circuit.name}
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-ink text-paper">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide">Team</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Races</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Wins</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Podiums</th>
                      <th className="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide">Points</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-light">
                    {team_stats.map((team) => (
                      <tr key={team.team} className="hover:bg-ink hover:text-paper transition-colors">
                        <td className="px-6 py-4 text-sm font-semibold">{team.team}</td>
                        <td className="px-6 py-4 text-sm text-center">{team.races}</td>
                        <td className="px-6 py-4 text-sm text-center font-semibold">{team.wins}</td>
                        <td className="px-6 py-4 text-sm text-center">{team.podiums}</td>
                        <td className="px-6 py-4 text-sm text-center">{team.points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          )}

          {/* Strategy Patterns */}
          {strategy_patterns.length > 0 && (
            <article className="border-2 border-ink bg-paper p-6">
              <h2 className="relative mb-6 text-lg font-semibold tracking-tight before:absolute before:-left-6 before:top-0 before:h-full before:w-1 before:bg-accent">
                Strategy Patterns
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {strategy_patterns.map((pattern) => (
                  <div key={pattern.year} className="border border-border-light p-4">
                    <p className="text-xs text-muted uppercase tracking-wide mb-2">{pattern.year}</p>
                    <p className="font-semibold">
                      {pattern.most_common_stops} stop{pattern.most_common_stops !== 1 ? "s" : ""}
                    </p>
                    <div className="mt-2 flex gap-2">
                      {pattern.compounds_used.map((compound) => (
                        <span
                          key={compound}
                          className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                            compound === "SOFT"
                              ? "bg-[#c41e3a] text-white"
                              : compound === "MEDIUM"
                              ? "bg-[#f5d547] text-ink"
                              : compound === "HARD"
                              ? "bg-[#eeeeee] text-ink"
                              : compound === "INTERMEDIATE"
                              ? "bg-[#43b02a] text-white"
                              : compound === "WET"
                              ? "bg-[#0067b1] text-white"
                              : "bg-muted text-white"
                          }`}
                          title={compound}
                        >
                          {compound.charAt(0)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          )}

          {/* Link to trends */}
          <div className="text-center">
            <Link
              href={`/circuits/trends/${circuitId}`}
              className="inline-flex items-center border-2 border-ink bg-paper px-6 py-3 font-semibold transition-colors hover:bg-ink hover:text-paper"
            >
              View Multi-Season Trends
              <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
