"use client";

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
import { getDriverColor, VOID_THEME, CHART_CONFIG } from "@/lib/constants";
import { formatLapTime } from "@/lib/utils";
import type { LapData } from "@/types/api";

interface LapTimeChartProps {
  laps: LapData[];
  season: number;
  selectedDrivers: string[];
}

export function LapTimeChart({ laps, season, selectedDrivers }: LapTimeChartProps) {
  // Get unique drivers to show
  const driversToShow =
    selectedDrivers.length > 0
      ? selectedDrivers
      : [...new Set(laps.map((l) => l.driver))].slice(0, 5);

  // Transform data: { lap: 1, VER: 90000, HAM: 91000, ... }
  const chartData: Record<string, number | null>[] = [];
  const lapNumbers = [...new Set(laps.map((l) => l.lap))].sort((a, b) => a - b);

  for (const lapNum of lapNumbers) {
    const point: Record<string, number | null> = { lap: lapNum };
    for (const driver of driversToShow) {
      const lapData = laps.find((l) => l.driver === driver && l.lap === lapNum);
      point[driver] = lapData?.lap_ms ?? null;
    }
    chartData.push(point);
  }

  // Calculate Y-axis domain (exclude outliers like pit laps)
  const validLapTimes = laps
    .filter((l) => driversToShow.includes(l.driver) && l.lap_ms && !l.pit)
    .map((l) => l.lap_ms!);

  const minTime = Math.min(...validLapTimes);
  const maxTime = Math.max(...validLapTimes);
  const padding = (maxTime - minTime) * 0.1;

  return (
    <ChartContainer
      title="Lap Times"
      description="Lap time progression throughout the race"
      height={400}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={CHART_CONFIG.margin}
        >
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
            domain={[minTime - padding, maxTime + padding]}
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
            contentStyle={{
              backgroundColor: VOID_THEME.paper,
              border: `2px solid ${VOID_THEME.ink}`,
              fontFamily: "var(--font-ibm-plex-mono)",
              fontSize: 12,
            }}
            formatter={(value) => [formatLapTime(typeof value === "number" ? value : null), ""]}
            labelFormatter={(label) => `Lap ${label}`}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
          />
          {driversToShow.map((driver) => (
            <Line
              key={driver}
              type="monotone"
              dataKey={driver}
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
  );
}
