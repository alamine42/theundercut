"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import { RaceSelector } from "@/components/ui/race-selector";
import { useRouter } from "next/navigation";
import { LapTimeChart } from "@/components/charts/lap-time-chart";
import { PaceComparisonChart } from "@/components/charts/pace-comparison-chart";
import { StintTimelineChart } from "@/components/charts/stint-timeline-chart";
import { DriverGradesRadar } from "@/components/charts/driver-grades-radar";
import { clientFetchAnalytics } from "@/lib/api";
import { getDriverColor, getRaceName, AVAILABLE_SEASONS } from "@/lib/constants";
import { uniqueDrivers } from "@/lib/utils";
import type { AnalyticsResponse } from "@/types/api";

interface AnalyticsViewProps {
  initialData: AnalyticsResponse;
  season: number;
  round: number;
}

export function AnalyticsView({ initialData, season, round }: AnalyticsViewProps) {
  const router = useRouter();
  const [selectedDrivers, setSelectedDrivers] = useState<string[]>([]);

  const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    router.push(`/analytics/${e.target.value}/1`);
  };

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
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <HeroTitle>{getRaceName(season, round)}</HeroTitle>
              <HeroSubtitle>
                {season} Season &middot; Round {round} &middot; Lap times, strategy, and performance grades
              </HeroSubtitle>
            </div>
            <div className="flex gap-2">
              <select
                value={season}
                onChange={handleYearChange}
                className="h-10 px-3 border-2 border-ink bg-paper text-ink font-mono text-sm
                           focus:outline-none focus:ring-2 focus:ring-ink cursor-pointer
                           hover:bg-ink hover:text-paper transition-colors"
              >
                {AVAILABLE_SEASONS.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
              <RaceSelector
                currentRound={round}
                season={season}
              />
            </div>
          </div>

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
