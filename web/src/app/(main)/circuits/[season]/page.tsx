import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { YearSelector } from "@/components/ui/year-selector";
import { fetchCircuits } from "@/lib/api";
import { AVAILABLE_SEASONS } from "@/lib/constants";
import { getCountryFlag } from "@/lib/utils";

export const revalidate = 300; // 5 minutes ISR

interface CircuitsPageProps {
  params: Promise<{ season: string }>;
}

export async function generateMetadata({ params }: CircuitsPageProps) {
  const { season } = await params;
  return {
    title: `${season} Circuits | The Undercut`,
    description: `F1 ${season} circuit analytics - lap records, driver performance, and race statistics`,
  };
}

export default async function CircuitsPage({ params }: CircuitsPageProps) {
  const { season: seasonStr } = await params;
  const season = parseInt(seasonStr, 10);

  if (isNaN(season) || !AVAILABLE_SEASONS.includes(season)) {
    notFound();
  }

  let circuitsData;
  try {
    circuitsData = await fetchCircuits(season);
  } catch {
    notFound();
  }

  const { circuits } = circuitsData;

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <HeroTitle>{season} Circuits</HeroTitle>
              <HeroSubtitle>
                Explore circuit analytics, lap records, and historical performance
              </HeroSubtitle>
            </div>
            <YearSelector currentYear={season} basePath="/circuits" availableYears={AVAILABLE_SEASONS} />
          </div>

          <HeroStats>
            <HeroStat label="Circuits" value={circuits.length} />
            <HeroStat label="Season" value={season} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {circuits.map((circuit) => {
              const raceDate = circuit.date ? new Date(circuit.date) : null;
              const isPastRace = raceDate && raceDate < new Date();

              return (
                <Link
                  key={circuit.circuit_id}
                  href={`/circuits/${season}/${circuit.circuit_id}`}
                  aria-label={`View ${circuit.race_name} circuit analytics`}
                  className="group block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
                >
                  <article className="relative h-full overflow-hidden border-2 border-ink bg-paper transition-all duration-200 group-hover:border-ink/80 group-active:scale-[0.98]">
                    {/* Track layout hero section */}
                    <div className="relative bg-ink/[0.03] group-hover:bg-ink/[0.06] transition-colors duration-200">
                      {/* Round badge - positioned over track */}
                      {circuit.round && (
                        <div className="absolute top-3 right-3 z-10 flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center bg-ink text-paper text-[10px] sm:text-xs font-bold">
                          R{circuit.round}
                        </div>
                      )}

                      {/* Track SVG - prominent display */}
                      <div className="flex items-center justify-center p-6 sm:p-8 h-32 sm:h-40">
                        <img
                          src={`/circuits/${circuit.circuit_id}.svg`}
                          alt={`${circuit.name} track layout`}
                          className="w-full h-full object-contain opacity-80 group-hover:opacity-100 transition-opacity duration-200"
                          style={{ filter: 'brightness(0)' }}
                        />
                      </div>
                    </div>

                    {/* Info section */}
                    <div className="p-4 sm:p-5 border-t-2 border-ink group-hover:bg-ink group-hover:text-paper transition-colors duration-200">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <h2 className="font-semibold tracking-tight truncate">
                            {circuit.name}
                          </h2>
                          <p className="mt-0.5 text-sm text-muted group-hover:text-paper/80 truncate">
                            {getCountryFlag(circuit.country)} {circuit.city}, {circuit.country}
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 pt-3 border-t border-ink/20 group-hover:border-paper/20">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium truncate flex-1">{circuit.race_name}</p>
                          {raceDate && (
                            <p className={`text-xs ml-2 whitespace-nowrap ${
                              isPastRace
                                ? 'text-muted group-hover:text-paper/70'
                                : 'font-semibold text-ink group-hover:text-paper'
                            }`}>
                              {raceDate.toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                              })}
                            </p>
                          )}
                        </div>

                        {/* Stats row - compelling data */}
                        {circuit.preview && (circuit.preview.dominant_driver || circuit.preview.last_winner) && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {/* Dominant driver badge */}
                            {circuit.preview.dominant_driver && circuit.preview.dominant_driver_wins > 1 && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink/10 group-hover:bg-paper/20 text-xs font-medium rounded-sm">
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <circle cx="12" cy="8" r="4" />
                                  <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
                                </svg>
                                {circuit.preview.dominant_driver}
                                <span className="text-muted group-hover:text-paper/60">
                                  {circuit.preview.dominant_driver_wins}W
                                </span>
                              </span>
                            )}

                            {/* Dominant team badge */}
                            {circuit.preview.dominant_team && circuit.preview.dominant_team_wins > 1 && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink/10 group-hover:bg-paper/20 text-xs font-medium rounded-sm">
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                                  <circle cx="9" cy="7" r="4" />
                                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                                </svg>
                                {circuit.preview.dominant_team}
                                <span className="text-muted group-hover:text-paper/60">
                                  {circuit.preview.dominant_team_wins}W
                                </span>
                              </span>
                            )}

                            {/* Last winner - only if no dominant driver */}
                            {!circuit.preview.dominant_driver && circuit.preview.last_winner && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink/10 group-hover:bg-paper/20 text-xs font-medium rounded-sm">
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                                  <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                                  <path d="M4 22h16" />
                                  <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22" />
                                  <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22" />
                                  <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
                                </svg>
                                Last: {circuit.preview.last_winner}
                                {circuit.preview.last_winner_team && (
                                  <span className="text-muted group-hover:text-paper/60">
                                    ({circuit.preview.last_winner_team})
                                  </span>
                                )}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="mt-3 flex items-center text-xs font-medium text-ink group-hover:text-paper">
                        <span>{isPastRace ? 'View analytics' : 'Preview circuit'}</span>
                        <svg
                          aria-hidden="true"
                          className="ml-1 h-3 w-3 transition-transform group-hover:translate-x-1"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </div>
                    </div>
                  </article>
                </Link>
              );
            })}
          </div>

          {circuits.length === 0 && (
            <div className="text-center py-12">
              <p className="text-muted">No circuits found for {season}</p>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
