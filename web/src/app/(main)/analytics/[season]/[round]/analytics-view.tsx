"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import { LapTimeChart } from "@/components/charts/lap-time-chart";
import { PaceComparisonChart } from "@/components/charts/pace-comparison-chart";
import { StintTimelineChart } from "@/components/charts/stint-timeline-chart";
import { DriverGradesRadar } from "@/components/charts/driver-grades-radar";
import { clientFetchAnalytics } from "@/lib/api";
import { getDriverColor, getRaceName } from "@/lib/constants";
import { uniqueDrivers } from "@/lib/utils";
import type { AnalyticsResponse } from "@/types/api";

interface AnalyticsViewProps {
  initialData: AnalyticsResponse;
  season: number;
  round: number;
}

export function AnalyticsView({ initialData, season, round }: AnalyticsViewProps) {
  const [selectedDrivers, setSelectedDrivers] = useState<string[]>([]);

  // Use React Query for client-side filtering
  const { data } = useQuery({
    queryKey: ["analytics", season, round, selectedDrivers],
    queryFn: () =>
      selectedDrivers.length > 0
        ? clientFetchAnalytics(season, round, selectedDrivers)
        : Promise.resolve(initialData),
    initialData,
    staleTime: 60000, // 1 minute
  });

  const allDrivers = uniqueDrivers(initialData.laps);
  const totalLaps = Math.max(...data.laps.map((l) => l.lap), 0);

  const toggleDriver = (driver: string) => {
    setSelectedDrivers((prev) =>
      prev.includes(driver)
        ? prev.filter((d) => d !== driver)
        : [...prev, driver]
    );
  };

  const clearSelection = () => {
    setSelectedDrivers([]);
  };

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>{getRaceName(season, round)}</HeroTitle>
          <HeroSubtitle>
            {season} Season &middot; Round {round} &middot; Lap times, strategy, and performance grades
          </HeroSubtitle>

          <HeroStats>
            <HeroStat label="Season" value={season} />
            <HeroStat label="Round" value={round} />
            <HeroStat label="Total Laps" value={totalLaps} />
            <HeroStat label="Drivers" value={allDrivers.length} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {/* Driver Filter */}
          <Card className="mb-8">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Filter Drivers</CardTitle>
                {selectedDrivers.length > 0 && (
                  <button
                    onClick={clearSelection}
                    className="text-xs text-muted hover:text-ink transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {allDrivers.map((driver) => (
                  <Chip
                    key={driver}
                    active={selectedDrivers.includes(driver)}
                    color={getDriverColor(driver, season)}
                    onClick={() => toggleDriver(driver)}
                  >
                    {driver}
                  </Chip>
                ))}
              </div>
              {selectedDrivers.length > 0 && (
                <p className="mt-3 text-xs text-muted">
                  Showing {selectedDrivers.length} driver{selectedDrivers.length > 1 ? "s" : ""}:{" "}
                  {selectedDrivers.join(", ")}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Charts Grid */}
          <div className="space-y-8">
            {/* Lap Times Chart */}
            <LapTimeChart
              laps={data.laps}
              season={season}
              selectedDrivers={selectedDrivers}
            />

            {/* Two Column Grid for smaller charts */}
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Pace Comparison */}
              <PaceComparisonChart
                grades={data.driver_pace_grades}
                season={season}
              />

              {/* Driver Grades Radar */}
              <DriverGradesRadar
                grades={data.driver_pace_grades}
                season={season}
                selectedDrivers={selectedDrivers}
              />
            </div>

            {/* Stint Timeline */}
            <StintTimelineChart
              stints={data.stints}
              selectedDrivers={selectedDrivers}
            />
          </div>
        </div>
      </section>
    </>
  );
}
