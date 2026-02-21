"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TeamLogo } from "@/components/ui/team-logo";
import { getRaceShortname } from "@/lib/constants";
import { TEAM_COLORS } from "@/lib/constants";
import type { RaceSummary } from "@/types/api";

interface SeasonResultsTableProps {
  season: number;
  raceSummaries: RaceSummary[];
}

export function SeasonResultsTable({ season, raceSummaries }: SeasonResultsTableProps) {
  const [expanded, setExpanded] = useState(false);

  if (raceSummaries.length === 0) {
    return null;
  }

  // Sort by round descending (most recent first)
  const sortedRaces = [...raceSummaries].sort((a, b) => b.round - a.round);

  // Show last 5 or all
  const displayedRaces = expanded ? sortedRaces : sortedRaces.slice(0, 5);
  const hasMore = sortedRaces.length > 5;

  return (
    <Card accent>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{season} Season Results</CardTitle>
          <span className="text-xs text-muted font-normal tracking-wide">
            {sortedRaces.length} RACES
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {/* Desktop Table View */}
        <div className="hidden sm:block">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-ink text-paper">
                  <th className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wider w-16">R</th>
                  <th className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wider">Circuit</th>
                  <th className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wider">Winner</th>
                  <th className="h-10 px-4 text-center text-xs font-semibold uppercase tracking-wider w-20">Pole</th>
                  <th className="h-10 px-4 text-center text-xs font-semibold uppercase tracking-wider w-20 hidden md:table-cell">2nd</th>
                  <th className="h-10 px-4 text-center text-xs font-semibold uppercase tracking-wider w-20 hidden md:table-cell">3rd</th>
                </tr>
              </thead>
              <tbody>
                {displayedRaces.map((race, index) => {
                  const teamColor = TEAM_COLORS[race.winner_team] || "#888888";
                  return (
                    <tr
                      key={race.round}
                      className="border-b border-border-light group transition-all duration-200 hover:bg-ink hover:text-paper"
                      style={{
                        animationDelay: expanded ? `${index * 30}ms` : "0ms",
                      }}
                    >
                      {/* Round number with team color accent */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-1 h-5 flex-shrink-0 transition-all duration-200 group-hover:h-6"
                            style={{ backgroundColor: teamColor }}
                          />
                          <span className="font-bold tabular-nums">{race.round}</span>
                        </div>
                      </td>

                      {/* Circuit name as link */}
                      <td className="px-4 py-3">
                        <Link
                          href={`/analytics/${season}/${race.round}`}
                          className="hover:text-accent transition-colors group-hover:text-paper group-hover:underline underline-offset-2"
                        >
                          {getRaceShortname(season, race.round)}
                        </Link>
                      </td>

                      {/* Winner with team logo */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="relative flex-shrink-0">
                            <TeamLogo team={race.winner_team} size={20} />
                          </div>
                          <span className="font-bold tracking-wide">{race.winner_code}</span>
                        </div>
                      </td>

                      {/* Pole position */}
                      <td className="px-4 py-3 text-center">
                        <span className="text-muted group-hover:text-paper/70 font-medium">
                          {race.pole || "—"}
                        </span>
                      </td>

                      {/* 2nd place */}
                      <td className="px-4 py-3 text-center hidden md:table-cell">
                        <span className="text-muted group-hover:text-paper/70 font-medium">
                          {race.second || "—"}
                        </span>
                      </td>

                      {/* 3rd place */}
                      <td className="px-4 py-3 text-center hidden md:table-cell">
                        <span className="text-muted group-hover:text-paper/70 font-medium">
                          {race.third || "—"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mobile Card View */}
        <div className="sm:hidden space-y-3">
          {displayedRaces.map((race, index) => {
            const teamColor = TEAM_COLORS[race.winner_team] || "#888888";
            return (
              <Link
                key={race.round}
                href={`/analytics/${season}/${race.round}`}
                className="block"
                style={{
                  animationDelay: expanded ? `${index * 30}ms` : "0ms",
                }}
              >
                <div
                  className="border-2 border-ink p-3 active:bg-ink active:text-paper transition-colors duration-150"
                  style={{ borderLeftWidth: "4px", borderLeftColor: teamColor }}
                >
                  {/* Header row: Round + Circuit */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-muted">R{race.round}</span>
                      <span className="font-semibold">{getRaceShortname(season, race.round)}</span>
                    </div>
                  </div>

                  {/* Winner row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TeamLogo team={race.winner_team} size={18} />
                      <span className="font-bold">{race.winner_code}</span>
                      <span className="text-xs text-muted">P1</span>
                    </div>

                    {/* Podium summary */}
                    <div className="flex items-center gap-1.5">
                      {race.pole && (
                        <span className="text-xs text-muted" title="Pole">
                          <span className="opacity-50">PP</span> {race.pole}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Podium row */}
                  <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border-light">
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="font-bold bg-ink text-paper w-5 h-5 flex items-center justify-center">1</span>
                      <span>{race.winner_code}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted">
                      <span className="font-bold bg-ink/10 w-5 h-5 flex items-center justify-center">2</span>
                      <span>{race.second || "—"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted">
                      <span className="font-bold bg-ink/5 w-5 h-5 flex items-center justify-center">3</span>
                      <span>{race.third || "—"}</span>
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Expand/Collapse Button */}
        {hasMore && (
          <div className="mt-4 flex justify-center">
            <button
              onClick={() => setExpanded(!expanded)}
              className="group inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-2 border-ink hover:bg-ink hover:text-paper transition-all duration-200"
            >
              <span>{expanded ? "Show less" : `Show all ${sortedRaces.length} races`}</span>
              <span
                className="transition-transform duration-200"
                style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}
              >
                ↓
              </span>
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
