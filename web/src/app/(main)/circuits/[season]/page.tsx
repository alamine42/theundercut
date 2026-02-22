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
                        <p className="text-sm font-medium truncate">{circuit.race_name}</p>
                        <div className="mt-2 flex items-center justify-between">
                          {raceDate && (
                            <p className={`text-xs ${
                              isPastRace
                                ? 'text-muted group-hover:text-paper/70'
                                : 'font-semibold text-ink group-hover:text-paper'
                            }`}>
                              {raceDate.toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </p>
                          )}

                          {/* Dominant driver stat */}
                          {circuit.preview?.dominant_driver && circuit.preview.dominant_driver_wins > 1 ? (
                            <span className="text-xs text-muted group-hover:text-paper/70 font-medium">
                              {circuit.preview.dominant_driver} × {circuit.preview.dominant_driver_wins}
                            </span>
                          ) : circuit.preview?.last_winner && (
                            <span className="text-xs text-muted group-hover:text-paper/70">
                              Last: {circuit.preview.last_winner}
                            </span>
                          )}
                        </div>
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
