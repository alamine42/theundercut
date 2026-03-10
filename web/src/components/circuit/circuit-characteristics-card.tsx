"use client";

import type { CircuitCharacteristics } from "@/types/api";
import { ScoreIndicator, ScoreBadge } from "@/components/ui/score-indicator";
import { CircuitRadarChart } from "@/components/charts/circuit-radar-chart";

interface CircuitCharacteristicsCardProps {
  characteristics: CircuitCharacteristics;
  circuitName: string;
  showRadar?: boolean;
}

interface StatRowProps {
  label: string;
  value: React.ReactNode;
  subLabel?: string;
}

function StatRow({ label, value, subLabel }: StatRowProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border-light last:border-b-0">
      <div>
        <span className="text-sm font-medium">{label}</span>
        {subLabel && <span className="text-xs text-muted ml-1">({subLabel})</span>}
      </div>
      <div>{value}</div>
    </div>
  );
}

export function CircuitCharacteristicsCard({
  characteristics,
  circuitName,
  showRadar = true,
}: CircuitCharacteristicsCardProps) {
  const chars = characteristics;

  return (
    <div className="space-y-6">
      {/* Radar Chart */}
      {showRadar && (
        <CircuitRadarChart characteristics={chars} circuitName={circuitName} />
      )}

      {/* Detailed Stats */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Performance Characteristics */}
        <article className="border-2 border-ink bg-paper p-4 sm:p-6">
          <h3 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-6">
            Performance
          </h3>
          <div className="space-y-1">
            <StatRow
              label="Full Throttle"
              subLabel={chars.full_throttle_pct ? `${chars.full_throttle_pct}%` : undefined}
              value={<ScoreIndicator score={chars.full_throttle_score} size="sm" />}
            />
            <StatRow
              label="Average Speed"
              subLabel={chars.average_speed_kph ? `${chars.average_speed_kph} km/h` : undefined}
              value={<ScoreIndicator score={chars.average_speed_score} size="sm" />}
            />
            <StatRow
              label="Track Length"
              value={
                chars.track_length_km ? (
                  <span className="font-mono text-sm">{chars.track_length_km} km</span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
          </div>
        </article>

        {/* Tire & Surface */}
        <article className="border-2 border-ink bg-paper p-4 sm:p-6">
          <h3 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-6">
            Tire & Surface
          </h3>
          <div className="space-y-1">
            <StatRow
              label="Tire Degradation"
              value={
                <ScoreIndicator
                  score={chars.tire_degradation_score}
                  label={chars.tire_degradation_label}
                  showLabel
                  size="sm"
                />
              }
            />
            <StatRow
              label="Track Abrasion"
              value={
                <ScoreIndicator
                  score={chars.track_abrasion_score}
                  label={chars.track_abrasion_label}
                  showLabel
                  size="sm"
                />
              }
            />
            <StatRow
              label="Circuit Type"
              value={
                chars.circuit_type ? (
                  <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-gray-100">
                    {chars.circuit_type}
                  </span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
          </div>
        </article>

        {/* Corner Profile */}
        <article className="border-2 border-ink bg-paper p-4 sm:p-6">
          <h3 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-6">
            Corner Profile
          </h3>
          <div className="space-y-1">
            <StatRow
              label="Slow Corners"
              subLabel="<100 km/h"
              value={
                chars.corners_slow !== null ? (
                  <span className="font-mono font-medium text-amber-600">{chars.corners_slow}</span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
            <StatRow
              label="Medium Corners"
              subLabel="100-170 km/h"
              value={
                chars.corners_medium !== null ? (
                  <span className="font-mono font-medium text-orange-600">{chars.corners_medium}</span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
            <StatRow
              label="Fast Corners"
              subLabel=">170 km/h"
              value={
                chars.corners_fast !== null ? (
                  <span className="font-mono font-medium text-red-600">{chars.corners_fast}</span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
            <StatRow
              label="Total Corners"
              value={
                chars.corners_slow !== null &&
                chars.corners_medium !== null &&
                chars.corners_fast !== null ? (
                  <span className="font-mono font-medium">
                    {chars.corners_slow + chars.corners_medium + chars.corners_fast}
                  </span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
          </div>
        </article>

        {/* Racing Characteristics */}
        <article className="border-2 border-ink bg-paper p-4 sm:p-6">
          <h3 className="relative mb-4 text-lg font-semibold tracking-tight before:absolute before:-left-4 before:top-0 before:h-full before:w-1 before:bg-accent sm:before:-left-6">
            Racing Characteristics
          </h3>
          <div className="space-y-1">
            <StatRow
              label="Downforce Level"
              value={
                <ScoreIndicator
                  score={chars.downforce_score}
                  label={chars.downforce_label}
                  showLabel
                  size="sm"
                />
              }
            />
            <StatRow
              label="Overtaking Difficulty"
              value={
                <ScoreIndicator
                  score={chars.overtaking_difficulty_score}
                  label={chars.overtaking_difficulty_label}
                  showLabel
                  size="sm"
                />
              }
            />
            <StatRow
              label="DRS Zones"
              value={
                chars.drs_zones !== null ? (
                  <span className="inline-flex items-center gap-1">
                    <span className="font-mono font-medium text-accent">{chars.drs_zones}</span>
                    <span className="text-xs text-muted">zones</span>
                  </span>
                ) : (
                  <span className="text-muted">--</span>
                )
              }
            />
          </div>
        </article>
      </div>

      {/* Data Source Info */}
      <div className="flex items-center justify-between text-xs text-muted">
        <span>
          Data completeness:{" "}
          <span
            className={
              chars.data_completeness === "complete"
                ? "text-emerald-600"
                : chars.data_completeness === "partial"
                ? "text-amber-600"
                : "text-muted"
            }
          >
            {chars.data_completeness}
          </span>
        </span>
        {chars.last_updated && (
          <span>
            Updated: {new Date(chars.last_updated).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}

// Compact version for list views
interface CircuitCharacteristicsSummaryProps {
  characteristics: CircuitCharacteristics | null;
}

export function CircuitCharacteristicsSummary({
  characteristics,
}: CircuitCharacteristicsSummaryProps) {
  if (!characteristics) {
    return <span className="text-xs text-muted">No data</span>;
  }

  const chars = characteristics;

  return (
    <div className="flex flex-wrap gap-2">
      {chars.full_throttle_score && (
        <div className="flex items-center gap-1 text-xs">
          <span className="text-muted">Throttle:</span>
          <ScoreBadge score={chars.full_throttle_score} />
        </div>
      )}
      {chars.tire_degradation_score && (
        <div className="flex items-center gap-1 text-xs">
          <span className="text-muted">Tire:</span>
          <ScoreBadge score={chars.tire_degradation_score} />
        </div>
      )}
      {chars.overtaking_difficulty_score && (
        <div className="flex items-center gap-1 text-xs">
          <span className="text-muted">Overtake:</span>
          <ScoreBadge score={chars.overtaking_difficulty_score} />
        </div>
      )}
      {chars.circuit_type && (
        <span className="inline-flex items-center px-1.5 py-0.5 text-xs bg-gray-100 rounded">
          {chars.circuit_type}
        </span>
      )}
    </div>
  );
}
