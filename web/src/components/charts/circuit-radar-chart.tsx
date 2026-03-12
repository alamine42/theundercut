"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { ChartContainer } from "./chart-container";
import { VOID_THEME } from "@/lib/constants";
import type { CircuitCharacteristics } from "@/types/api";

interface RadarDataPoint {
  name: string;
  fullName: string;
  value: number;
}

interface CircuitRadarChartProps {
  characteristics: CircuitCharacteristics;
  circuitName?: string;
  showLabels?: boolean;
  height?: number;
}

interface CharacteristicField {
  key: string;
  short: string;
  full: string;
  getValue: (chars: CircuitCharacteristics) => number | null;
}

const CHARACTERISTIC_FIELDS: CharacteristicField[] = [
  { key: "full_throttle", short: "Throttle", full: "Full Throttle %", getValue: (c) => c.full_throttle?.score ?? null },
  { key: "average_speed", short: "Speed", full: "Average Speed", getValue: (c) => c.average_speed?.score ?? null },
  { key: "tire_degradation", short: "Tire Deg", full: "Tire Degradation", getValue: (c) => c.tire_degradation?.score ?? null },
  { key: "track_abrasion", short: "Abrasion", full: "Track Abrasion", getValue: (c) => c.track_abrasion?.score ?? null },
  { key: "downforce", short: "DF", full: "Downforce Level", getValue: (c) => c.downforce?.score ?? null },
  { key: "overtaking", short: "Overtake", full: "Overtaking Difficulty", getValue: (c) => c.overtaking?.score ?? null },
];

function transformToRadarData(chars: CircuitCharacteristics): RadarDataPoint[] {
  return CHARACTERISTIC_FIELDS
    .map((field) => ({
      name: field.short,
      fullName: field.full,
      value: field.getValue(chars) ?? 0,
    }))
    .filter((d) => d.value > 0);
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: RadarDataPoint }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;
  return (
    <div className="border-2 border-ink bg-paper px-3 py-2 text-sm">
      <p className="font-medium">{data.fullName}</p>
      <p className="text-accent font-mono">{data.value}/10</p>
    </div>
  );
}

export function CircuitRadarChart({
  characteristics,
  circuitName,
  height = 350,
}: CircuitRadarChartProps) {
  const data = transformToRadarData(characteristics);

  if (data.length === 0) {
    return (
      <ChartContainer
        title="Track Characteristics"
        description={circuitName}
        height={height}
      >
        <div className="flex h-full items-center justify-center text-muted">
          No characteristic data available
        </div>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer
      title="Track Characteristics"
      description={circuitName ? `${circuitName} performance profile` : undefined}
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
          <PolarGrid stroke={VOID_THEME.borderLight} />
          <PolarAngleAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={false}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 10]}
            tick={{ fontSize: 10, fill: VOID_THEME.muted }}
            tickCount={6}
            axisLine={false}
          />
          <Radar
            name="Score"
            dataKey="value"
            stroke={VOID_THEME.accent}
            fill={VOID_THEME.accent}
            fillOpacity={0.3}
            strokeWidth={2}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

// Multi-circuit comparison radar chart
interface CircuitCompareRadarChartProps {
  circuits: Array<{
    name: string;
    characteristics: CircuitCharacteristics;
    color?: string;
  }>;
  height?: number;
}

const COMPARE_COLORS = [
  VOID_THEME.accent,
  "#3671C6", // Blue
  "#2d8a39", // Green
  "#9333ea", // Purple
  "#0891b2", // Cyan
];

export function CircuitCompareRadarChart({
  circuits,
  height = 400,
}: CircuitCompareRadarChartProps) {
  if (circuits.length === 0) {
    return (
      <ChartContainer title="Comparison" height={height}>
        <div className="flex h-full items-center justify-center text-muted">
          Select circuits to compare
        </div>
      </ChartContainer>
    );
  }

  // Build combined data
  const data = CHARACTERISTIC_FIELDS.map((field) => {
    const point: Record<string, string | number> = {
      name: field.short,
      fullName: field.full,
    };
    circuits.forEach((circuit) => {
      point[circuit.name] = field.getValue(circuit.characteristics) ?? 0;
    });
    return point;
  });

  return (
    <ChartContainer
      title="Circuit Comparison"
      description="Compare track characteristics across circuits"
      height={height}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 20, right: 60, bottom: 20, left: 60 }}>
          <PolarGrid stroke={VOID_THEME.borderLight} />
          <PolarAngleAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={false}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 10]}
            tick={{ fontSize: 10, fill: VOID_THEME.muted }}
            tickCount={6}
            axisLine={false}
          />
          {circuits.map((circuit, i) => (
            <Radar
              key={circuit.name}
              name={circuit.name}
              dataKey={circuit.name}
              stroke={circuit.color || COMPARE_COLORS[i % COMPARE_COLORS.length]}
              fill={circuit.color || COMPARE_COLORS[i % COMPARE_COLORS.length]}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          ))}
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            iconType="line"
          />
          <Tooltip
            contentStyle={{
              border: `2px solid ${VOID_THEME.ink}`,
              background: VOID_THEME.paper,
              fontSize: 12,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
