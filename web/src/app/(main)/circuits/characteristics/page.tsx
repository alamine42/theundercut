import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle } from "@/components/ui/hero";
import { fetchCircuitsCharacteristics } from "@/lib/api";
import { ScoreBadge } from "@/components/ui/score-indicator";
import { getCountryFlag } from "@/lib/utils";

export const revalidate = 300; // 5 minutes ISR

export const metadata = {
  title: "Circuit Characteristics | The Undercut",
  description: "Compare F1 circuit characteristics - tire degradation, overtaking difficulty, downforce levels, and more.",
};

export default async function CircuitCharacteristicsPage() {
  const data = await fetchCircuitsCharacteristics();

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <HeroTitle>Circuit Characteristics</HeroTitle>
              <HeroSubtitle>
                Comprehensive track data across the F1 calendar
              </HeroSubtitle>
            </div>
            <Link
              href="/circuits/characteristics/compare"
              className="inline-flex items-center border-2 border-ink bg-paper px-4 py-2 font-semibold transition-colors hover:bg-ink hover:text-paper"
            >
              Compare Circuits
              <svg className="ml-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {/* Summary Stats */}
          <div className="mb-8 grid gap-4 sm:grid-cols-3">
            <article className="border-2 border-ink bg-paper p-4">
              <p className="text-xs text-muted uppercase tracking-wide">Circuits</p>
              <p className="text-2xl font-bold">{data.total}</p>
            </article>
            <article className="border-2 border-ink bg-paper p-4">
              <p className="text-xs text-muted uppercase tracking-wide">Street Circuits</p>
              <p className="text-2xl font-bold">
                {data.circuits.filter(c => c.characteristics?.circuit_type === "Street").length}
              </p>
            </article>
            <article className="border-2 border-ink bg-paper p-4">
              <p className="text-xs text-muted uppercase tracking-wide">Permanent Circuits</p>
              <p className="text-2xl font-bold">
                {data.circuits.filter(c => c.characteristics?.circuit_type === "Permanent").length}
              </p>
            </article>
          </div>

          {/* Circuit List */}
          <article className="border-2 border-ink bg-paper">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-ink text-paper">
                  <tr>
                    <th className="px-3 sm:px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Circuit
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Type
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Length
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Throttle
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Tire Deg
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Downforce
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      Overtake
                    </th>
                    <th className="px-3 sm:px-6 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
                      DRS
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light">
                  {data.circuits.map((circuit) => {
                    const chars = circuit.characteristics;
                    return (
                      <tr key={circuit.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-3 sm:px-6 py-3 sm:py-4">
                          <div>
                            <p className="font-semibold text-sm">{circuit.name}</p>
                            <p className="text-xs text-muted">
                              {getCountryFlag(circuit.country)} {circuit.country}
                            </p>
                          </div>
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center">
                          {chars?.circuit_type ? (
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-gray-100">
                              {chars.circuit_type}
                            </span>
                          ) : (
                            <span className="text-muted">--</span>
                          )}
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center text-sm font-mono">
                          {chars?.track_length_km ? `${chars.track_length_km} km` : "--"}
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center">
                          <ScoreBadge score={chars?.full_throttle?.score ?? null} />
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center">
                          <ScoreBadge score={chars?.tire_degradation?.score ?? null} />
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center">
                          <ScoreBadge score={chars?.downforce?.score ?? null} />
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center">
                          <ScoreBadge score={chars?.overtaking?.score ?? null} />
                        </td>
                        <td className="px-3 sm:px-6 py-3 sm:py-4 text-center text-sm font-mono">
                          {chars?.drs_zones ?? "--"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </article>

          {/* Legend */}
          <div className="mt-6 flex flex-wrap items-center gap-4 text-xs text-muted">
            <span className="font-medium">Score Legend:</span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-emerald-500"></span>
              Low (1-3)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-amber-400"></span>
              Medium (4-5)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-orange-500"></span>
              High (6-7)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-red-500"></span>
              Very High (8-10)
            </span>
          </div>

          {/* Links */}
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/circuits/characteristics/rank"
              className="inline-flex items-center text-sm text-accent hover:underline"
            >
              View Circuit Rankings
              <svg className="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
            <Link
              href="/circuits"
              className="inline-flex items-center text-sm text-muted hover:text-ink"
            >
              Back to Circuits
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
