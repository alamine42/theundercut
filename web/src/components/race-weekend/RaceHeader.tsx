import { getCountryFlag } from "@/lib/utils";
import type { RaceHeaderProps } from "./types";

export function RaceHeader({
  raceName,
  round,
  totalRounds,
  circuitName,
  circuitCountry,
  isSprintWeekend,
  isRaceWeekendActive = false,
}: RaceHeaderProps) {
  const flag = circuitCountry ? getCountryFlag(circuitCountry) : "";
  const roundLabel = totalRounds ? `Round ${round} of ${totalRounds}` : `Round ${round}`;
  const displayTitle = raceName || "Upcoming Race";

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {!isRaceWeekendActive && raceName && (
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-0.5">
            Upcoming Race
          </p>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          {flag && (
            <span className="text-xl sm:text-2xl" role="img" aria-label={circuitCountry || "Country"}>
              {flag}
            </span>
          )}
          <h2 className="text-lg sm:text-xl font-bold tracking-tight truncate">
            {displayTitle}
          </h2>
          {isSprintWeekend && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] sm:text-xs font-bold uppercase tracking-wider bg-accent/15 text-accent rounded">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
              Sprint
            </span>
          )}
        </div>
        {circuitName && (
          <p className="text-sm text-muted mt-1 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="truncate">
              {circuitName}
              {circuitCountry && <span className="text-ink/40">, {circuitCountry}</span>}
            </span>
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="text-xs sm:text-sm font-medium text-muted bg-ink/5 px-2.5 py-1 rounded-full">
          {roundLabel}
        </span>
      </div>
    </div>
  );
}
