"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { CircuitWithCharacteristics, CircuitCharacteristics } from "@/types/api";
import { CircuitCompareRadarChart } from "@/components/charts/circuit-radar-chart";
import { ScoreBadge } from "@/components/ui/score-indicator";
import { getCountryFlag } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface CircuitCompareClientProps {
  circuits: CircuitWithCharacteristics[];
}

const COMPARE_COLORS = [
  "#d9731a", // accent
  "#3671C6", // blue
  "#2d8a39", // green
  "#9333ea", // purple
  "#0891b2", // cyan
];

type CharacteristicKey = keyof CircuitCharacteristics;

interface ComparisonRow {
  key: CharacteristicKey;
  label: string;
  format: (value: number | string | null) => string;
  type: "score" | "number" | "text";
}

const COMPARISON_ROWS: ComparisonRow[] = [
  { key: "circuit_type", label: "Circuit Type", format: (v) => v?.toString() || "--", type: "text" },
  { key: "track_length_km", label: "Track Length", format: (v) => v ? `${v} km` : "--", type: "number" },
  { key: "full_throttle_pct", label: "Full Throttle %", format: (v) => v ? `${v}%` : "--", type: "number" },
  { key: "full_throttle_score", label: "Full Throttle Score", format: (v) => v?.toString() || "--", type: "score" },
  { key: "average_speed_kph", label: "Avg Speed", format: (v) => v ? `${v} km/h` : "--", type: "number" },
  { key: "average_speed_score", label: "Speed Score", format: (v) => v?.toString() || "--", type: "score" },
  { key: "tire_degradation_score", label: "Tire Degradation", format: (v) => v?.toString() || "--", type: "score" },
  { key: "tire_degradation_label", label: "Tire Deg Level", format: (v) => v?.toString() || "--", type: "text" },
  { key: "track_abrasion_score", label: "Track Abrasion", format: (v) => v?.toString() || "--", type: "score" },
  { key: "track_abrasion_label", label: "Abrasion Level", format: (v) => v?.toString() || "--", type: "text" },
  { key: "downforce_score", label: "Downforce", format: (v) => v?.toString() || "--", type: "score" },
  { key: "downforce_label", label: "Downforce Level", format: (v) => v?.toString() || "--", type: "text" },
  { key: "overtaking_difficulty_score", label: "Overtaking", format: (v) => v?.toString() || "--", type: "score" },
  { key: "overtaking_difficulty_label", label: "Overtake Level", format: (v) => v?.toString() || "--", type: "text" },
  { key: "corners_slow", label: "Slow Corners", format: (v) => v?.toString() || "--", type: "number" },
  { key: "corners_medium", label: "Medium Corners", format: (v) => v?.toString() || "--", type: "number" },
  { key: "corners_fast", label: "Fast Corners", format: (v) => v?.toString() || "--", type: "number" },
  { key: "drs_zones", label: "DRS Zones", format: (v) => v?.toString() || "--", type: "number" },
];

export function CircuitCompareClient({ circuits }: CircuitCompareClientProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const selectedCircuits = useMemo(
    () => circuits.filter((c) => selectedIds.includes(c.id)),
    [circuits, selectedIds]
  );

  const handleToggle = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      if (prev.length >= 5) {
        return prev;
      }
      return [...prev, id];
    });
  };

  const clearSelection = () => setSelectedIds([]);

  // Filter only circuits with characteristics for comparison
  const comparableCircuits = circuits.filter((c) => c.characteristics !== null);

  return (
    <div className="space-y-8">
      {/* Circuit Selection */}
      <article className="border-2 border-ink bg-paper p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Select Circuits ({selectedIds.length}/5)</h2>
          {selectedIds.length > 0 && (
            <button
              onClick={clearSelection}
              className="text-sm text-muted hover:text-ink transition-colors"
            >
              Clear all
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {comparableCircuits.map((circuit) => {
            const isSelected = selectedIds.includes(circuit.id);
            const isDisabled = !isSelected && selectedIds.length >= 5;
            const colorIndex = selectedIds.indexOf(circuit.id);

            return (
              <button
                key={circuit.id}
                onClick={() => handleToggle(circuit.id)}
                disabled={isDisabled}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium border-2 transition-all",
                  isSelected
                    ? "border-ink bg-ink text-paper"
                    : "border-border-light bg-paper text-ink hover:border-ink",
                  isDisabled && "opacity-50 cursor-not-allowed"
                )}
                style={
                  isSelected && colorIndex >= 0
                    ? { backgroundColor: COMPARE_COLORS[colorIndex], borderColor: COMPARE_COLORS[colorIndex] }
                    : undefined
                }
              >
                {getCountryFlag(circuit.country)} {circuit.name}
              </button>
            );
          })}
        </div>
      </article>

      {/* Comparison View */}
      {selectedCircuits.length >= 2 ? (
        <>
          {/* Radar Chart */}
          <CircuitCompareRadarChart
            circuits={selectedCircuits
              .filter((c) => c.characteristics)
              .map((c, i) => ({
                name: c.name,
                characteristics: c.characteristics!,
                color: COMPARE_COLORS[i % COMPARE_COLORS.length],
              }))}
          />

          {/* Comparison Table */}
          <article className="border-2 border-ink bg-paper">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-ink text-paper">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide whitespace-nowrap sticky left-0 bg-ink z-10">
                      Characteristic
                    </th>
                    {selectedCircuits.map((circuit, i) => (
                      <th
                        key={circuit.id}
                        className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide whitespace-nowrap min-w-[120px]"
                        style={{ backgroundColor: COMPARE_COLORS[i % COMPARE_COLORS.length] }}
                      >
                        {circuit.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-light">
                  {COMPARISON_ROWS.map((row) => (
                    <tr key={row.key} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm font-medium sticky left-0 bg-paper">
                        {row.label}
                      </td>
                      {selectedCircuits.map((circuit) => {
                        const chars = circuit.characteristics;
                        const value = chars ? chars[row.key] : null;

                        return (
                          <td key={circuit.id} className="px-4 py-3 text-center text-sm">
                            {row.type === "score" && typeof value === "number" ? (
                              <ScoreBadge score={value} />
                            ) : row.type === "number" ? (
                              <span className="font-mono">{row.format(value as number | null)}</span>
                            ) : (
                              <span>{row.format(value as string | null)}</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </>
      ) : (
        <div className="border-2 border-dashed border-border-light p-12 text-center">
          <p className="text-muted">
            {selectedIds.length === 0
              ? "Select at least 2 circuits to compare"
              : "Select one more circuit to compare"}
          </p>
        </div>
      )}

      {/* Back Link */}
      <div className="flex gap-4">
        <Link
          href="/circuits/characteristics"
          className="inline-flex items-center text-sm text-muted hover:text-ink transition-colors"
        >
          <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Characteristics
        </Link>
      </div>
    </div>
  );
}
