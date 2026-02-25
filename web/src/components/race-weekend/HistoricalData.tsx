import { TeamWithLogo } from "@/components/ui/team-logo";
import type { HistoricalDataProps } from "./types";

const POSITION_MEDALS = ["1st", "2nd", "3rd"];
const POSITION_EMOJIS = ["\u{1F947}", "\u{1F948}", "\u{1F949}"]; // Gold, Silver, Bronze medals

interface PodiumItemProps {
  position: number;
  driverCode: string;
  driverName: string | null;
  team: string | null;
}

function PodiumItem({ position, driverCode, driverName, team }: PodiumItemProps) {
  const positionIndex = position - 1;
  const podiumClass = `podium-${position}`;

  return (
    <div className={`podium-item ${podiumClass}`}>
      <span
        className="text-xl sm:text-2xl"
        role="img"
        aria-label={`${POSITION_MEDALS[positionIndex]} place`}
      >
        {POSITION_EMOJIS[positionIndex]}
      </span>
      <div className="flex flex-col min-w-0">
        <span className="font-bold text-sm sm:text-base">{driverCode}</span>
        {driverName && (
          <span className="text-xs text-muted truncate hidden sm:block">
            {driverName}
          </span>
        )}
      </div>
      {team && (
        <span className="ml-auto text-muted">
          <TeamWithLogo team={team} />
        </span>
      )}
    </div>
  );
}

function StatItem({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 py-2 px-3 bg-ink/5 rounded-lg">
      <span className="text-base" role="img" aria-hidden="true">{icon}</span>
      <div className="flex flex-col">
        <span className="text-[10px] uppercase tracking-wider text-muted">{label}</span>
        <span className="font-semibold text-sm">{value}</span>
      </div>
    </div>
  );
}

export function HistoricalData({ history }: HistoricalDataProps) {
  const { previous_year } = history;

  if (!previous_year) {
    return null;
  }

  const podium = [previous_year.winner, previous_year.second, previous_year.third];
  const hasPodium = podium.some((p) => p !== null);

  if (!hasPodium) {
    return null;
  }

  return (
    <div className="border-t-2 border-ink/10 pt-5 mt-5 animate-fadeInUp animation-delay-300">
      <h3 className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted mb-4">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Last Year ({previous_year.season})
      </h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Podium */}
        <div className="space-y-2">
          {podium.map((driver, idx) => (
            driver && (
              <PodiumItem
                key={idx}
                position={idx + 1}
                driverCode={driver.driver_code}
                driverName={driver.driver_name}
                team={driver.team}
              />
            )
          ))}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 content-start">
          {previous_year.pole && (
            <StatItem
              icon="\u{2B50}"
              label="Pole Position"
              value={previous_year.pole.driver_code}
            />
          )}
          {previous_year.fastest_lap && (
            <StatItem
              icon="\u{26A1}"
              label="Fastest Lap"
              value={`${previous_year.fastest_lap.driver_code}${
                previous_year.fastest_lap.time ? ` ${previous_year.fastest_lap.time}` : ""
              }`}
            />
          )}
        </div>
      </div>
    </div>
  );
}
