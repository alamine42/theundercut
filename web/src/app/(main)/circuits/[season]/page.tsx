import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { YearSelector } from "@/components/ui/year-selector";
import { fetchCircuits } from "@/lib/api";
import { AVAILABLE_SEASONS } from "@/lib/constants";

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

  if (isNaN(season) || season < 2018 || season > 2030) {
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

      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {circuits.map((circuit) => (
              <Link
                key={circuit.circuit_id}
                href={`/circuits/${season}/${circuit.circuit_id}`}
                className="group block"
              >
                <article className="h-full border-2 border-ink bg-paper p-6 transition-colors group-hover:bg-ink group-hover:text-paper">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h2 className="font-semibold tracking-tight">
                        {circuit.name}
                      </h2>
                      <p className="mt-1 text-sm text-muted group-hover:text-paper/70">
                        {circuit.city}, {circuit.country}
                      </p>
                    </div>
                    {circuit.round && (
                      <span className="ml-2 flex h-8 w-8 items-center justify-center border-2 border-current text-xs font-bold">
                        R{circuit.round}
                      </span>
                    )}
                  </div>

                  <div className="mt-4 border-t border-current pt-4">
                    <p className="text-sm font-medium">{circuit.race_name}</p>
                    {circuit.date && (
                      <p className="mt-1 text-xs text-muted group-hover:text-paper/70">
                        {new Date(circuit.date).toLocaleDateString("en-US", {
                          month: "long",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </p>
                    )}
                  </div>

                  <div className="mt-4 flex items-center text-xs text-muted group-hover:text-paper/70">
                    <span>View analytics</span>
                    <svg
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
                </article>
              </Link>
            ))}
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
