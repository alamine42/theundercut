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
import { getDriverColor, VOID_THEME, CHART_CONFIG } from "@/lib/constants";
import type { DriverPaceGrade } from "@/types/api";

interface DriverGradesRadarProps {
  grades: DriverPaceGrade[];
  season: number;
  selectedDrivers: string[];
}

interface RadarDataPoint {
  metric: string;
  fullMark: number;
  [key: string]: string | number;
}

export function DriverGradesRadar({
  grades,
  season,
  selectedDrivers,
}: DriverGradesRadarProps) {
  // Filter to grades that have detailed metrics
  const detailedGrades = grades.filter(
    (g) => g.source === "drive_grade_db" && g.total_grade !== undefined
  );

  if (detailedGrades.length === 0) {
    return (
      <ChartContainer
        title="Driver Performance Grades"
        description="Multi-dimensional driver rating"
        height={350}
      >
        <div className="flex h-full items-center justify-center text-muted">
          No detailed grades available for this race
        </div>
      </ChartContainer>
    );
  }

  // Get drivers to display
  const driversToShow =
    selectedDrivers.length > 0
      ? selectedDrivers.filter((d) =>
          detailedGrades.some((g) => g.driver === d)
        )
      : detailedGrades.slice(0, 4).map((g) => g.driver);

  // Build radar data points
  const metrics = [
    { key: "total_grade", label: "Overall" },
    { key: "consistency", label: "Consistency" },
    { key: "racecraft", label: "Racecraft" },
    { key: "team_strategy", label: "Strategy" },
    { key: "penalties", label: "Clean Racing" },
  ];

  const radarData: RadarDataPoint[] = metrics.map((metric) => {
    const point: RadarDataPoint = {
      metric: metric.label,
      fullMark: 100,
    };

    driversToShow.forEach((driver) => {
      const grade = detailedGrades.find((g) => g.driver === driver);
      if (grade) {
        const value = grade[metric.key as keyof DriverPaceGrade];
        point[driver] = typeof value === "number" ? value : 0;
      }
    });

    return point;
  });

  return (
    <ChartContainer
      title="Driver Performance Grades"
      description="Multi-dimensional driver rating"
      height={350}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart
          data={radarData}
          margin={{ top: 20, right: 30, bottom: 20, left: 30 }}
        >
          <PolarGrid stroke={VOID_THEME.borderLight} />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fontSize: 11, fill: VOID_THEME.ink }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: VOID_THEME.muted }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: VOID_THEME.paper,
              border: `2px solid ${VOID_THEME.ink}`,
              fontFamily: "var(--font-ibm-plex-mono)",
              fontSize: 12,
            }}
            formatter={(value) => [typeof value === "number" ? value.toFixed(1) : String(value), ""]}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
          />
          {driversToShow.map((driver) => (
            <Radar
              key={driver}
              name={driver}
              dataKey={driver}
              stroke={getDriverColor(driver, season)}
              fill={getDriverColor(driver, season)}
              fillOpacity={0.2}
              strokeWidth={CHART_CONFIG.strokeWidth}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
