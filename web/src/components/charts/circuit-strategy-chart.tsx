"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from "recharts";
import { ChartContainer } from "./chart-container";
import { VOID_THEME, COMPOUND_COLORS, CHART_CONFIG } from "@/lib/constants";
import type { StrategyPattern } from "@/types/api";

interface CircuitStrategyChartProps {
  patterns: StrategyPattern[];
  circuitName?: string;
}

export function CircuitStrategyChart({ patterns, circuitName }: CircuitStrategyChartProps) {
  if (patterns.length === 0) {
    return (
      <ChartContainer
        title="Strategy Patterns"
        description="No strategy data available for this circuit"
        height={300}
      >
        <div className="flex items-center justify-center h-full text-muted">
          No data available
        </div>
      </ChartContainer>
    );
  }

  // Transform data for pit stop distribution chart
  const chartData = patterns
    .slice()
    .sort((a, b) => a.year - b.year)
    .map((p) => ({
      year: p.year,
      stops: p.most_common_stops,
      compounds: p.compounds_used,
      soft: p.compounds_used.includes("SOFT") ? 1 : 0,
      medium: p.compounds_used.includes("MEDIUM") ? 1 : 0,
      hard: p.compounds_used.includes("HARD") ? 1 : 0,
      intermediate: p.compounds_used.includes("INTERMEDIATE") ? 1 : 0,
      wet: p.compounds_used.includes("WET") ? 1 : 0,
    }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number; payload: typeof chartData[0] }>;
    label?: number;
  }) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload;

    return (
      <div className="bg-paper border-2 border-ink p-3 font-mono text-xs">
        <p className="font-bold text-sm mb-2">{label}</p>
        <p className="mb-2">
          <span className="text-muted">Most Common:</span> {data.stops} stop{data.stops !== 1 ? "s" : ""}
        </p>
        <p className="text-muted mb-1">Compounds Used:</p>
        <div className="flex gap-2">
          {data.compounds.map((compound: string) => (
            <span
              key={compound}
              className="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold"
              style={{
                backgroundColor: getCompoundColor(compound),
                color: compound === "MEDIUM" || compound === "HARD" ? VOID_THEME.ink : "#fff",
              }}
            >
              {compound.charAt(0)}
            </span>
          ))}
        </div>
      </div>
    );
  };

  return (
    <ChartContainer
      title="Strategy Patterns"
      description={circuitName ? `Most common pit strategies at ${circuitName}` : "Most common pit strategies across seasons"}
      height={300}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ ...CHART_CONFIG.margin, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={VOID_THEME.borderLight} />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            label={{
              value: "Year",
              position: "insideBottom",
              offset: -15,
              fontSize: 12,
              fill: VOID_THEME.muted,
            }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            label={{
              value: "Pit Stops",
              angle: -90,
              position: "insideLeft",
              fontSize: 12,
              fill: VOID_THEME.muted,
            }}
            domain={[0, "auto"]}
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="stops" name="Pit Stops" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  entry.stops === 1
                    ? VOID_THEME.accent
                    : entry.stops === 2
                    ? "#8b5cf6"
                    : entry.stops >= 3
                    ? "#059669"
                    : VOID_THEME.muted
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

function getCompoundColor(compound: string): string {
  switch (compound) {
    case "SOFT":
      return COMPOUND_COLORS.soft;
    case "MEDIUM":
      return COMPOUND_COLORS.medium;
    case "HARD":
      return COMPOUND_COLORS.hard;
    case "INTERMEDIATE":
      return COMPOUND_COLORS.intermediate;
    case "WET":
      return COMPOUND_COLORS.wet;
    default:
      return VOID_THEME.muted;
  }
}
