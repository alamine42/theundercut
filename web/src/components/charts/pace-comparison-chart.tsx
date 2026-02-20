"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { ChartContainer } from "./chart-container";
import { getDriverColor, VOID_THEME, CHART_CONFIG } from "@/lib/constants";
import { formatDelta } from "@/lib/utils";
import type { DriverPaceGrade } from "@/types/api";

interface PaceComparisonChartProps {
  grades: DriverPaceGrade[];
  season: number;
}

export function PaceComparisonChart({ grades, season }: PaceComparisonChartProps) {
  // Sort by pace delta (best = smallest delta)
  const sortedGrades = [...grades]
    .filter((g) => g.pace_delta_ms !== undefined)
    .sort((a, b) => (a.pace_delta_ms ?? 0) - (b.pace_delta_ms ?? 0));

  const chartData = sortedGrades.map((grade) => ({
    driver: grade.driver,
    delta: grade.pace_delta_ms ?? 0,
    pace: grade.pace_ms ?? 0,
    score: grade.score ?? 0,
  }));

  // Calculate max delta for axis
  const maxDelta = Math.max(...chartData.map((d) => d.delta));

  return (
    <ChartContainer
      title="Pace Comparison"
      description="Average pace delta to race leader"
      height={Math.max(300, chartData.length * 35)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ ...CHART_CONFIG.margin, left: 50 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={VOID_THEME.borderLight}
            horizontal={false}
          />
          <XAxis
            type="number"
            domain={[0, maxDelta * 1.1]}
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            tickFormatter={(value) => formatDelta(value)}
          />
          <YAxis
            type="category"
            dataKey="driver"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            width={40}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: VOID_THEME.paper,
              border: `2px solid ${VOID_THEME.ink}`,
              fontFamily: "var(--font-ibm-plex-mono)",
              fontSize: 12,
            }}
            formatter={(value, name) => {
              const numValue = typeof value === "number" ? value : 0;
              if (name === "delta") {
                return [formatDelta(numValue), "Gap"];
              }
              return [numValue, String(name)];
            }}
          />
          <Bar
            dataKey="delta"
            radius={[0, 2, 2, 0]}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.driver}
                fill={getDriverColor(entry.driver, season)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
