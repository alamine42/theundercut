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
                  <article className="relative h-full overflow-hidden border-2 border-ink bg-paper p-4 sm:p-6 transition-all duration-200 group-hover:bg-ink group-hover:text-paper group-active:scale-[0.98]">
                    {/* Track silhouette watermark */}
                    <div
                      className="absolute -right-4 -bottom-4 w-24 h-24 sm:w-28 sm:h-28 md:w-32 md:h-32 opacity-[0.06] group-hover:opacity-[0.15] transition-all duration-200 pointer-events-none"
                      style={{
                        backgroundImage: `url(/circuits/${circuit.circuit_id}.svg)`,
                        backgroundSize: 'contain',
                        backgroundRepeat: 'no-repeat',
                        backgroundPosition: 'center',
                      }}
                    />

                    {/* Content with z-index */}
                    <div className="relative z-10">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h2 className="font-semibold tracking-tight">
                            {circuit.name}
                          </h2>
                          <p className="mt-1 text-sm text-muted group-hover:text-paper/80">
                            {getCountryFlag(circuit.country)} {circuit.city}, {circuit.country}
                          </p>
                        </div>
                        {circuit.round && (
                          <span className="ml-2 flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center border-2 border-current text-[10px] sm:text-xs font-bold">
                            R{circuit.round}
                          </span>
                        )}
                      </div>

                      <div className="mt-4 border-t border-current pt-4">
                        <p className="text-sm font-medium">{circuit.race_name}</p>
                        {raceDate && (
                          <p className={`mt-1 text-xs ${
                            isPastRace
                              ? 'text-muted group-hover:text-paper/80'
                              : 'font-semibold text-ink group-hover:text-paper'
                          }`}>
                            {raceDate.toLocaleDateString("en-US", {
                              month: "long",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </p>
                        )}
                      </div>

                      {/* Headline stat */}
                      {circuit.preview?.dominant_driver && circuit.preview.dominant_driver_wins > 1 ? (
                        <div className="mt-3 text-xs text-muted group-hover:text-paper/80">
                          <span className="font-bold">{circuit.preview.dominant_driver}</span>
                          <span> dominates ({circuit.preview.dominant_driver_wins} wins)</span>
                        </div>
                      ) : circuit.preview?.last_winner && (
                        <div className="mt-3 text-xs text-muted group-hover:text-paper/80">
                          <span className="font-bold">{circuit.preview.last_winner}</span>
                          <span> won last</span>
                        </div>
                      )}

                      <div className="mt-4 flex items-center text-xs text-muted group-hover:text-paper/80">
                        <span>{isPastRace ? 'View analytics' : 'Preview'}</span>
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
