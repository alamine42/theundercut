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
import { getCompoundColor, VOID_THEME, CHART_CONFIG } from "@/lib/constants";
import { formatLapTime } from "@/lib/utils";
import type { StintData } from "@/types/api";

interface StintTimelineChartProps {
  stints: StintData[];
  selectedDrivers: string[];
}

interface StintBarData {
  driver: string;
  stints: Array<{
    stint_no: number;
    compound: string;
    laps: number;
    start: number;
    avg_lap_ms: number | null;
  }>;
  totalLaps: number;
}

export function StintTimelineChart({ stints, selectedDrivers }: StintTimelineChartProps) {
  // Get unique drivers to show
  const drivers =
    selectedDrivers.length > 0
      ? selectedDrivers
      : [...new Set(stints.map((s) => s.driver))].slice(0, 10);

  // Group stints by driver and calculate start positions
  const driverStints: StintBarData[] = drivers.map((driver) => {
    const driverStintList = stints
      .filter((s) => s.driver === driver)
      .sort((a, b) => a.stint_no - b.stint_no);

    let runningStart = 0;
    const processedStints = driverStintList.map((stint) => {
      const result = {
        stint_no: stint.stint_no,
        compound: stint.compound,
        laps: stint.laps,
        start: runningStart,
        avg_lap_ms: stint.avg_lap_ms,
      };
      runningStart += stint.laps;
      return result;
    });

    return {
      driver,
      stints: processedStints,
      totalLaps: runningStart,
    };
  });

  // Calculate max laps for x-axis
  const maxLaps = Math.max(...driverStints.map((d) => d.totalLaps), 0);

  // Transform data for stacked bar chart
  const chartData = driverStints.map((d) => {
    const row: Record<string, string | number | null> = { driver: d.driver };
    d.stints.forEach((stint, idx) => {
      row[`stint_${idx}_laps`] = stint.laps;
      row[`stint_${idx}_compound`] = stint.compound;
      row[`stint_${idx}_avg`] = stint.avg_lap_ms;
    });
    return row;
  });

  // Get max number of stints
  const maxStints = Math.max(...driverStints.map((d) => d.stints.length), 0);

  return (
    <ChartContainer
      title="Stint Strategy"
      description="Tire compound and stint length by driver"
      height={Math.max(300, drivers.length * 40)}
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
            domain={[0, maxLaps + 5]}
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
            tickLine={{ stroke: VOID_THEME.border }}
            axisLine={{ stroke: VOID_THEME.border }}
            label={{
              value: "Laps",
              position: "insideBottom",
              offset: -10,
              fontSize: 12,
              fill: VOID_THEME.muted,
            }}
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
            formatter={(value, name, props) => {
              const nameStr = String(name);
              const stintIdx = parseInt(nameStr.split("_")[1], 10);
              const compound = props.payload[`stint_${stintIdx}_compound`];
              const avgLap = props.payload[`stint_${stintIdx}_avg`];
              return [
                `${value} laps (${compound}) - Avg: ${formatLapTime(typeof avgLap === "number" ? avgLap : null)}`,
                `Stint ${stintIdx + 1}`,
              ];
            }}
          />
          {Array.from({ length: maxStints }).map((_, idx) => (
            <Bar
              key={`stint_${idx}`}
              dataKey={`stint_${idx}_laps`}
              stackId="stints"
              radius={idx === maxStints - 1 ? [0, 2, 2, 0] : 0}
            >
              {chartData.map((entry, entryIdx) => {
                const compound = entry[`stint_${idx}_compound`] as string | null;
                return (
                  <Cell
                    key={`cell-${entryIdx}`}
                    fill={getCompoundColor(compound)}
                    stroke={VOID_THEME.ink}
                    strokeWidth={1}
                  />
                );
              })}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
