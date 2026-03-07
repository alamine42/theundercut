import { TeamWithLogo } from "@/components/ui/team-logo";
import type { SessionCardCompactProps } from "./types";

const POSITION_EMOJIS = ["\u{1F947}", "\u{1F948}", "\u{1F949}"]; // Gold, Silver, Bronze

export function SessionCardCompact({ results, sessionType }: SessionCardCompactProps) {
  const top3 = results.slice(0, 3);

  if (top3.length === 0) {
    return (
      <p className="text-sm text-muted">No results available</p>
    );
  }

  // For qualifying, show Q3 time if available
  const isQualifying = sessionType === "qualifying" || sessionType === "sprint_qualifying";
  // Only show podium medals for race sessions
  const isRace = sessionType === "race" || sessionType === "sprint_race" || sessionType === "sprint";

  return (
    <div className="space-y-2">
      {top3.map((result, idx) => (
        <div
          key={result.driver_code}
          className="flex items-center gap-2 sm:gap-3 py-1.5 sm:py-2 px-2 sm:px-3 bg-ink/5 rounded-lg"
        >
          {isRace ? (
            <span
              className="text-base sm:text-lg flex-shrink-0"
              role="img"
              aria-label={`Position ${idx + 1}`}
            >
              {POSITION_EMOJIS[idx]}
            </span>
          ) : (
            <span className="w-5 sm:w-6 text-center font-semibold text-sm sm:text-base text-muted flex-shrink-0">
              {idx + 1}
            </span>
          )}
          <span className="font-bold text-sm sm:text-base">{result.driver_code}</span>
          {result.team && (
            <span className="text-muted text-xs sm:text-sm">
              <TeamWithLogo team={result.team} size={14} />
            </span>
          )}
          <span className="ml-auto text-xs sm:text-sm text-muted font-mono">
            {isQualifying && result.q3_time
              ? result.q3_time
              : result.time || "-"}
          </span>
        </div>
      ))}
      {results.length > 3 && (
        <p className="text-xs text-muted text-center pt-1">
          +{results.length - 3} more drivers
        </p>
      )}
    </div>
  );
}
