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
import { VOID_THEME, CHART_CONFIG } from "@/lib/constants";
import { formatLapTime } from "@/lib/utils";
import type { CircuitTrend } from "@/types/api";

interface CircuitTrendsChartProps {
  trends: CircuitTrend[];
  circuitName?: string;
}

export function CircuitTrendsChart({ trends, circuitName }: CircuitTrendsChartProps) {
  // Transform data for Recharts
  const chartData = trends
    .filter((t) => t.pole_time_ms || t.fastest_lap_ms)
    .map((t) => ({
      year: t.year,
      pole: t.pole_time_ms,
      poleDriver: t.pole_driver,
      fastestLap: t.fastest_lap_ms,
      fastestLapDriver: t.fastest_lap_driver,
      winner: t.winner,
      winnerTeam: t.winner_team,
    }))
    .sort((a, b) => a.year - b.year);

  if (chartData.length === 0) {
    return (
      <ChartContainer
        title="Lap Time Evolution"
        description="No timing data available for this circuit"
        height={400}
      >
        <div className="flex items-center justify-center h-full text-muted">
          No data available
        </div>
      </ChartContainer>
    );
  }

  // Calculate Y-axis domain
  const allTimes = chartData.flatMap((d) => [d.pole, d.fastestLap].filter(Boolean)) as number[];
  const minTime = Math.min(...allTimes);
  const maxTime = Math.max(...allTimes);
  const padding = (maxTime - minTime) * 0.15;

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ dataKey: string; value: number; payload: typeof chartData[0] }>;
    label?: number
  }) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload;

    return (
      <div className="bg-paper border-2 border-ink p-3 font-mono text-xs">
        <p className="font-bold text-sm mb-2">{label}</p>
        {data.winner && (
          <p className="mb-2">
            <span className="text-muted">Winner:</span> {data.winner}
            {data.winnerTeam && <span className="text-muted"> ({data.winnerTeam})</span>}
          </p>
        )}
        {data.pole && (
          <p>
            <span className="inline-block w-3 h-3 mr-2" style={{ backgroundColor: VOID_THEME.accent }} />
            <span className="text-muted">Pole:</span> {formatLapTime(data.pole)}
            {data.poleDriver && <span className="text-muted"> ({data.poleDriver})</span>}
          </p>
        )}
        {data.fastestLap && (
          <p>
            <span className="inline-block w-3 h-3 mr-2" style={{ backgroundColor: "#8b5cf6" }} />
            <span className="text-muted">Fastest Lap:</span> {formatLapTime(data.fastestLap)}
            {data.fastestLapDriver && <span className="text-muted"> ({data.fastestLapDriver})</span>}
          </p>
        )}
      </div>
    );
  };

  return (
    <ChartContainer
      title="Lap Time Evolution"
      description={circuitName ? `Pole and fastest lap times at ${circuitName} across seasons` : "Pole and fastest lap times across seasons"}
      height={400}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={CHART_CONFIG.margin}>
          <CartesianGrid strokeDasharray="3 3" stroke={VOID_THEME.borderLight} />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            label={{
              value: "Year",
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
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="pole"
            name="Pole Time"
            stroke={VOID_THEME.accent}
            strokeWidth={CHART_CONFIG.strokeWidth}
            dot={{ r: CHART_CONFIG.dotRadius, fill: VOID_THEME.accent }}
            activeDot={{ r: CHART_CONFIG.dotRadius + 2 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="fastestLap"
            name="Fastest Lap"
            stroke="#8b5cf6"
            strokeWidth={CHART_CONFIG.strokeWidth}
            dot={{ r: CHART_CONFIG.dotRadius, fill: "#8b5cf6" }}
            activeDot={{ r: CHART_CONFIG.dotRadius + 2 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
