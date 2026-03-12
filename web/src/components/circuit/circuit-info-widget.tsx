import type { CircuitCharacteristics, LapRecord } from "@/types/api";
import { ScoreBadge } from "@/components/ui/score-indicator";

interface CircuitInfoWidgetProps {
  characteristics: CircuitCharacteristics | null;
  allTimeLapRecord: LapRecord | null;
  seasonFastestLap: LapRecord | null;
  season: number;
}

export function CircuitInfoWidget({
  characteristics,
  allTimeLapRecord,
  seasonFastestLap,
  season,
}: CircuitInfoWidgetProps) {
  const chars = characteristics;

  return (
    <div className="grid gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
      {/* Circuit Characteristics */}
      <article className="border-2 border-ink bg-paper p-4 sm:p-5 lg:col-span-2">
        <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-5">
          Track Characteristics
        </h2>
        {chars ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* Performance */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Full Throttle</span>
                <div className="flex items-center gap-2">
                  {chars.full_throttle?.value && (
                    <span className="text-xs text-muted">{chars.full_throttle.value}%</span>
                  )}
                  <ScoreBadge score={chars.full_throttle?.score ?? null} />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Avg Speed</span>
                <div className="flex items-center gap-2">
                  {chars.average_speed?.value && (
                    <span className="text-xs text-muted">{chars.average_speed.value} km/h</span>
                  )}
                  <ScoreBadge score={chars.average_speed?.score ?? null} />
                </div>
              </div>
            </div>

            {/* Tire & Surface */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Tire Deg</span>
                <div className="flex items-center gap-2">
                  {chars.tire_degradation?.label && (
                    <span className="text-xs text-muted">{chars.tire_degradation.label}</span>
                  )}
                  <ScoreBadge score={chars.tire_degradation?.score ?? null} />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Abrasion</span>
                <div className="flex items-center gap-2">
                  {chars.track_abrasion?.label && (
                    <span className="text-xs text-muted">{chars.track_abrasion.label}</span>
                  )}
                  <ScoreBadge score={chars.track_abrasion?.score ?? null} />
                </div>
              </div>
            </div>

            {/* Racing */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Downforce</span>
                <div className="flex items-center gap-2">
                  {chars.downforce?.label && (
                    <span className="text-xs text-muted">{chars.downforce.label}</span>
                  )}
                  <ScoreBadge score={chars.downforce?.score ?? null} />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Overtaking</span>
                <div className="flex items-center gap-2">
                  {chars.overtaking?.label && (
                    <span className="text-xs text-muted">{chars.overtaking.label}</span>
                  )}
                  <ScoreBadge score={chars.overtaking?.score ?? null} />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-muted text-sm">No characteristics data available</p>
        )}

        {/* Track info row */}
        {chars && (
          <div className="mt-4 pt-4 border-t border-border-light flex flex-wrap items-center gap-4 text-sm">
            {chars.circuit_type && (
              <span className="inline-flex items-center gap-1.5">
                <span className="text-muted">Type:</span>
                <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium">
                  {chars.circuit_type}
                </span>
              </span>
            )}
            {chars.track_length_km && (
              <span className="inline-flex items-center gap-1.5">
                <span className="text-muted">Length:</span>
                <span className="font-mono font-medium">{chars.track_length_km} km</span>
              </span>
            )}
            {chars.drs_zones !== null && (
              <span className="inline-flex items-center gap-1.5">
                <span className="text-muted">DRS Zones:</span>
                <span className="font-mono font-medium text-accent">{chars.drs_zones}</span>
              </span>
            )}
            {chars.corners?.total != null && (
              <span className="inline-flex items-center gap-1.5">
                <span className="text-muted">Corners:</span>
                <span className="font-mono font-medium">{chars.corners?.total}</span>
              </span>
            )}
          </div>
        )}
      </article>

      {/* Lap Records */}
      <article className="border-2 border-ink bg-paper p-4 sm:p-5">
        <h2 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-5">
          Lap Records
        </h2>
        <div className="space-y-4">
          {/* All-Time Record */}
          <div>
            <p className="text-xs text-muted uppercase tracking-wide mb-1">All-Time Fastest</p>
            {allTimeLapRecord ? (
              <>
                <p className="text-xl sm:text-2xl font-bold font-mono">{allTimeLapRecord.time}</p>
                <p className="text-sm text-muted">
                  {allTimeLapRecord.driver} &middot; {allTimeLapRecord.year}
                </p>
              </>
            ) : (
              <p className="text-muted text-sm">No data</p>
            )}
          </div>

          {/* Season Fastest */}
          <div className="pt-4 border-t border-border-light">
            <p className="text-xs text-muted uppercase tracking-wide mb-1">{season} Fastest</p>
            {seasonFastestLap ? (
              <>
                <p className="text-xl sm:text-2xl font-bold font-mono">{seasonFastestLap.time}</p>
                <p className="text-sm text-muted">{seasonFastestLap.driver}</p>
              </>
            ) : (
              <p className="text-muted text-sm">Race not yet run</p>
            )}
          </div>
        </div>
      </article>
    </div>
  );
}
