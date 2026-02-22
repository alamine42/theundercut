"use client";

import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { ChartContainer } from "./chart-container";
import { getDriverColor, VOID_THEME, CHART_CONFIG, getCompoundColor } from "@/lib/constants";
import { formatLapTime } from "@/lib/utils";
import type { TestingLap, TestingDriverResult } from "@/types/api";

interface TestingLapChartProps {
  laps: TestingLap[];
  results: TestingDriverResult[];
  season: number;
}

export function TestingLapChart({ laps, results, season }: TestingLapChartProps) {
  // Get top 5 drivers by default
  const topDrivers = useMemo(() => {
    return results.slice(0, 5).map((r) => r.driver);
  }, [results]);

  const [selectedDrivers, setSelectedDrivers] = useState<string[]>(topDrivers);

  // Get all unique drivers
  const allDrivers = useMemo(() => {
    return [...new Set(laps.map((l) => l.driver))];
  }, [laps]);

  // Filter out outliers (install laps, pit laps - typically > 150% of median)
  const filteredLaps = useMemo(() => {
    if (laps.length === 0) return [];

    // Calculate median lap time per driver
    const driverLaps: Record<string, number[]> = {};
    laps.forEach((lap) => {
      if (lap.lap_time_ms && lap.is_valid) {
        if (!driverLaps[lap.driver]) driverLaps[lap.driver] = [];
        driverLaps[lap.driver].push(lap.lap_time_ms);
      }
    });

    const driverMedians: Record<string, number> = {};
    Object.entries(driverLaps).forEach(([driver, times]) => {
      const sorted = [...times].sort((a, b) => a - b);
      driverMedians[driver] = sorted[Math.floor(sorted.length / 2)] || 0;
    });

    // Filter laps that are within 120% of median (excludes outliers)
    return laps.filter((lap) => {
      if (!lap.lap_time_ms) return false;
      const median = driverMedians[lap.driver];
      if (!median) return false;
      return lap.lap_time_ms < median * 1.2;
    });
  }, [laps]);

  // Transform data for chart
  const chartData = useMemo(() => {
    const driversToShow = selectedDrivers.length > 0 ? selectedDrivers : topDrivers;
    const lapNumbers = [...new Set(filteredLaps.map((l) => l.lap_number))].sort(
      (a, b) => a - b
    );

    return lapNumbers.map((lapNum) => {
      const point: Record<string, number | string | null> = { lap: lapNum };
      for (const driver of driversToShow) {
        const lapData = filteredLaps.find(
          (l) => l.driver === driver && l.lap_number === lapNum
        );
        point[driver] = lapData?.lap_time_ms ?? null;
        // Store compound for tooltip
        if (lapData?.compound) {
          point[`${driver}_compound`] = lapData.compound;
        }
      }
      return point;
    });
  }, [filteredLaps, selectedDrivers, topDrivers]);

  // Calculate Y-axis domain
  const [minTime, maxTime] = useMemo(() => {
    const driversToShow = selectedDrivers.length > 0 ? selectedDrivers : topDrivers;
    const validTimes = filteredLaps
      .filter((l) => driversToShow.includes(l.driver) && l.lap_time_ms)
      .map((l) => l.lap_time_ms!);

    if (validTimes.length === 0) return [0, 100000];

    const min = Math.min(...validTimes);
    const max = Math.max(...validTimes);
    const padding = (max - min) * 0.1;

    return [min - padding, max + padding];
  }, [filteredLaps, selectedDrivers, topDrivers]);

  // Toggle driver selection
  const toggleDriver = (driver: string) => {
    setSelectedDrivers((prev) =>
      prev.includes(driver)
        ? prev.filter((d) => d !== driver)
        : [...prev, driver]
    );
  };

  const driversToShow = selectedDrivers.length > 0 ? selectedDrivers : topDrivers;

  if (laps.length === 0) {
    return (
      <ChartContainer
        title="Lap Time Progression"
        description="No lap data available"
        height={300}
      >
        <div className="flex items-center justify-center h-full text-muted">
          No lap data to display
        </div>
      </ChartContainer>
    );
  }

  return (
    <div className="space-y-4">
      {/* Driver selector */}
      <div className="flex flex-wrap gap-2">
        {allDrivers.map((driver) => {
          const isSelected = selectedDrivers.includes(driver);
          const color = getDriverColor(driver, season);
          return (
            <button
              key={driver}
              onClick={() => toggleDriver(driver)}
              className={`
                px-3 py-1.5 text-sm font-medium border-2 transition-all
                ${
                  isSelected
                    ? "border-ink bg-ink text-paper"
                    : "border-ink/20 bg-paper text-ink hover:border-ink/40"
                }
              `}
              style={{
                borderLeftColor: color,
                borderLeftWidth: "4px",
              }}
            >
              {driver}
            </button>
          );
        })}
      </div>

      <ChartContainer
        title="Lap Time Progression"
        description="Lap times throughout the testing session (outliers filtered)"
        height={400}
        mobileHeight={300}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={CHART_CONFIG.margin}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={VOID_THEME.borderLight}
            />
            <XAxis
              dataKey="lap"
              tick={{ fontSize: 11, fill: VOID_THEME.ink }}
              tickLine={{ stroke: VOID_THEME.border }}
              axisLine={{ stroke: VOID_THEME.border }}
              label={{
                value: "Lap",
                position: "insideBottom",
                offset: -10,
                fontSize: 12,
                fill: VOID_THEME.muted,
              }}
            />
            <YAxis
              domain={[minTime, maxTime]}
              tick={{ fontSize: 11, fill: VOID_THEME.ink }}
              tickLine={{ stroke: VOID_THEME.border }}
              axisLine={{ stroke: VOID_THEME.border }}
              tickFormatter={(value) => formatLapTime(value)}
              label={{
                value: "Lap Time",
                angle: -90,
                position: "insideLeft",
                fontSize: 12,
                fill: VOID_THEME.muted,
              }}
            />
            <Tooltip
              content={<CustomTooltip season={season} />}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {driversToShow.map((driver) => (
              <Line
                key={driver}
                type="monotone"
                dataKey={driver}
                name={driver}
                stroke={getDriverColor(driver, season)}
                strokeWidth={CHART_CONFIG.strokeWidth}
                dot={false}
                connectNulls
                activeDot={{ r: CHART_CONFIG.dotRadius + 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    payload: Record<string, unknown>;
  }>;
  label?: number;
  season: number;
}

function CustomTooltip({ active, payload, label, season }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      className="bg-paper border-2 border-ink p-3 shadow-lg"
      style={{ fontFamily: "var(--font-ibm-plex-mono)", fontSize: 12 }}
    >
      <p className="font-semibold mb-2">Lap {label}</p>
      <div className="space-y-1">
        {payload.map((entry) => {
          const compound = entry.payload[`${entry.name}_compound`] as string | undefined;
          return (
            <div key={entry.name} className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="font-medium">{entry.name}:</span>
              <span>{formatLapTime(entry.value)}</span>
              {compound && (
                <span
                  className="w-2.5 h-2.5 rounded-full ml-1"
                  style={{ backgroundColor: getCompoundColor(compound) }}
                  title={compound}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
