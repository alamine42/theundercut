"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { TestingDayResponse, TestingDriverResult, TestingLap } from "@/types/api";
import { getCompoundColor, getTeamId } from "@/lib/constants";
import { TestingLapChart } from "@/components/charts/testing-lap-chart";

interface TestingDayTabsProps {
  season: number;
  eventId: string;
  totalDays: number;
  initialDay: number;
  initialData: TestingDayResponse | null;
}

export function TestingDayTabs({
  season,
  eventId,
  totalDays,
  initialDay,
  initialData,
}: TestingDayTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeDay, setActiveDay] = useState(initialDay);
  const [dayData, setDayData] = useState<TestingDayResponse | null>(initialData);
  const [laps, setLaps] = useState<TestingLap[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch day data when tab changes
  useEffect(() => {
    if (activeDay === initialDay && initialData) {
      setDayData(initialData);
      // Also fetch laps for the chart
      fetchLapsData(activeDay);
      return;
    }

    const fetchDayData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/v1/testing/${season}/${eventId}/${activeDay}`);
        if (!res.ok) {
          throw new Error(`Failed to fetch day ${activeDay} data`);
        }
        const data = await res.json();
        setDayData(data);
        // Also fetch laps for the chart
        await fetchLapsData(activeDay);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
        setDayData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchDayData();
  }, [activeDay, season, eventId, initialDay, initialData]);

  // Fetch laps data for the chart
  const fetchLapsData = async (day: number) => {
    try {
      const res = await fetch(`/api/v1/testing/${season}/${eventId}/${day}/laps?limit=1000`);
      if (res.ok) {
        const data = await res.json();
        setLaps(data.laps || []);
      }
    } catch {
      // Silently fail - chart just won't show
      setLaps([]);
    }
  };

  // Update URL when tab changes
  const handleTabChange = (day: number) => {
    setActiveDay(day);
    const params = new URLSearchParams(searchParams.toString());
    params.set("day", day.toString());
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const days = Array.from({ length: totalDays }, (_, i) => i + 1);

  return (
    <div>
      {/* Day Tabs */}
      <div className="border-b-2 border-ink mb-6">
        <nav className="flex gap-0 -mb-[2px]" aria-label="Testing days">
          {days.map((day) => (
            <button
              key={day}
              onClick={() => handleTabChange(day)}
              className={`
                px-6 py-3 text-sm font-semibold border-2 border-b-0 transition-colors
                ${
                  activeDay === day
                    ? "bg-ink text-paper border-ink"
                    : "bg-paper text-ink border-transparent hover:border-ink/20"
                }
              `}
              aria-current={activeDay === day ? "page" : undefined}
            >
              Day {day}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-12 text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-ink border-r-transparent" />
          <p className="mt-4 text-muted">Loading Day {activeDay} data...</p>
        </div>
      ) : error ? (
        <div className="py-12 text-center border-2 border-dashed border-red-200 bg-red-50">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={() => handleTabChange(activeDay)}
            className="mt-4 px-4 py-2 text-sm bg-ink text-paper hover:bg-ink/80 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : !dayData || dayData.results.length === 0 ? (
        <div className="py-12 text-center border-2 border-dashed border-ink/20">
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-lg font-semibold mb-2">No Data Available</h3>
          <p className="text-muted">
            Day {activeDay} testing data is not yet available
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Results Table */}
          <TestingResultsTable results={dayData.results} />

          {/* Lap Progression Chart */}
          {laps.length > 0 && (
            <TestingLapChart
              laps={laps}
              results={dayData.results}
              season={season}
            />
          )}

          {/* Stint Summary */}
          <TestingStintsSummary results={dayData.results} />
        </div>
      )}
    </div>
  );
}

interface TestingResultsTableProps {
  results: TestingDriverResult[];
}

function TestingResultsTable({ results }: TestingResultsTableProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Lap Times</h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b-2 border-ink">
              <th className="text-left py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Pos
              </th>
              <th className="text-left py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Driver
              </th>
              <th className="text-left py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Team
              </th>
              <th className="text-right py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Best Lap
              </th>
              <th className="text-right py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Gap
              </th>
              <th className="text-center py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Tyre
              </th>
              <th className="text-right py-3 px-4 font-semibold text-xs uppercase tracking-wider">
                Laps
              </th>
            </tr>
          </thead>
          <tbody>
            {results.map((result, idx) => (
              <tr
                key={result.driver}
                className={`border-b border-ink/10 hover:bg-ink/[0.02] transition-colors ${
                  idx === 0 ? "bg-accent/5" : ""
                }`}
              >
                <td className="py-3 px-4">
                  <span
                    className={`inline-flex items-center justify-center w-7 h-7 text-sm font-bold ${
                      idx === 0
                        ? "bg-ink text-paper"
                        : idx < 3
                        ? "bg-ink/10"
                        : ""
                    }`}
                  >
                    {result.position}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <img
                      src={`/teams/${getTeamId(result.team || "")}.svg`}
                      alt={result.team || ""}
                      className="w-5 h-5 object-contain"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <span className="font-semibold">{result.driver}</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-muted">{result.team || "-"}</td>
                <td className="py-3 px-4 text-right font-mono font-semibold">
                  {result.best_lap_formatted || "-"}
                </td>
                <td className="py-3 px-4 text-right font-mono text-muted">
                  {result.gap_formatted || "-"}
                </td>
                <td className="py-3 px-4 text-center">
                  {result.best_lap_compound && (
                    <span
                      className="inline-block w-3 h-3 rounded-full"
                      style={{
                        backgroundColor: getCompoundColor(result.best_lap_compound),
                      }}
                      title={result.best_lap_compound}
                    />
                  )}
                </td>
                <td className="py-3 px-4 text-right">{result.total_laps}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface TestingStintsSummaryProps {
  results: TestingDriverResult[];
}

function TestingStintsSummary({ results }: TestingStintsSummaryProps) {
  // Flatten all stints with driver info
  const allStints = results.flatMap((r) =>
    r.stints.map((s) => ({
      ...s,
      driver: r.driver,
      team: r.team,
    }))
  );

  if (allStints.length === 0) {
    return null;
  }

  // Group by compound for summary
  const compoundSummary = allStints.reduce((acc, stint) => {
    const compound = stint.compound || "Unknown";
    if (!acc[compound]) {
      acc[compound] = { count: 0, totalLaps: 0 };
    }
    acc[compound].count++;
    acc[compound].totalLaps += stint.lap_count;
    return acc;
  }, {} as Record<string, { count: number; totalLaps: number }>);

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Stint Summary</h3>

      {/* Compound breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {Object.entries(compoundSummary).map(([compound, data]) => (
          <div
            key={compound}
            className="border-2 border-ink/10 p-4 flex items-center gap-3"
          >
            <span
              className="w-4 h-4 rounded-full flex-shrink-0"
              style={{ backgroundColor: getCompoundColor(compound) }}
            />
            <div>
              <p className="font-semibold">{compound}</p>
              <p className="text-sm text-muted">
                {data.count} stints &middot; {data.totalLaps} laps
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Detailed stint table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-ink">
              <th className="text-left py-2 px-3 font-semibold text-xs uppercase tracking-wider">
                Driver
              </th>
              <th className="text-center py-2 px-3 font-semibold text-xs uppercase tracking-wider">
                Stint
              </th>
              <th className="text-center py-2 px-3 font-semibold text-xs uppercase tracking-wider">
                Compound
              </th>
              <th className="text-right py-2 px-3 font-semibold text-xs uppercase tracking-wider">
                Laps
              </th>
              <th className="text-right py-2 px-3 font-semibold text-xs uppercase tracking-wider">
                Avg Pace
              </th>
            </tr>
          </thead>
          <tbody>
            {allStints.slice(0, 20).map((stint, idx) => (
              <tr
                key={`${stint.driver}-${stint.stint_number}`}
                className="border-b border-ink/10 hover:bg-ink/[0.02]"
              >
                <td className="py-2 px-3 font-medium">{stint.driver}</td>
                <td className="py-2 px-3 text-center">{stint.stint_number}</td>
                <td className="py-2 px-3 text-center">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{
                        backgroundColor: getCompoundColor(stint.compound || ""),
                      }}
                    />
                    <span>{stint.compound || "-"}</span>
                  </span>
                </td>
                <td className="py-2 px-3 text-right">{stint.lap_count}</td>
                <td className="py-2 px-3 text-right font-mono">
                  {stint.avg_pace_formatted || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {allStints.length > 20 && (
          <p className="text-sm text-muted mt-2 text-center">
            Showing 20 of {allStints.length} stints
          </p>
        )}
      </div>
    </div>
  );
}
