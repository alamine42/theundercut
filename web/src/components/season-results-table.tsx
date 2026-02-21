"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TeamLogo } from "@/components/ui/team-logo";
import { getRaceShortname, TEAM_COLORS, getDriverTeam } from "@/lib/constants";
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
                  <th className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wider hidden md:table-cell">2nd</th>
                  <th className="h-10 px-4 text-left text-xs font-semibold uppercase tracking-wider hidden md:table-cell">3rd</th>
                  <th className="h-10 px-4 text-center text-xs font-semibold uppercase tracking-wider w-20 hidden sm:table-cell">Pole</th>
                </tr>
              </thead>
              <tbody>
                {displayedRaces.map((race, index) => {
                  const teamColor = TEAM_COLORS[race.winner_team] || "#888888";
                  const secondTeam = race.second ? getDriverTeam(race.second, season) : null;
                  const thirdTeam = race.third ? getDriverTeam(race.third, season) : null;
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
                        <div className="flex items-center gap-2">
                          <TeamLogo team={race.winner_team} size={18} />
                          <span className="font-bold tracking-wide">{race.winner_code}</span>
                        </div>
                      </td>

                      {/* 2nd place with team logo */}
                      <td className="px-4 py-3 hidden md:table-cell">
                        {race.second ? (
                          <div className="flex items-center gap-2">
                            {secondTeam && secondTeam !== "Unknown" && (
                              <TeamLogo team={secondTeam} size={18} />
                            )}
                            <span className="text-muted group-hover:text-paper/70">{race.second}</span>
                          </div>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>

                      {/* 3rd place with team logo */}
                      <td className="px-4 py-3 hidden md:table-cell">
                        {race.third ? (
                          <div className="flex items-center gap-2">
                            {thirdTeam && thirdTeam !== "Unknown" && (
                              <TeamLogo team={thirdTeam} size={18} />
                            )}
                            <span className="text-muted group-hover:text-paper/70">{race.third}</span>
                          </div>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>

                      {/* Pole position */}
                      <td className="px-4 py-3 text-center hidden sm:table-cell">
                        <span className="text-muted group-hover:text-paper/70 font-medium">
                          {race.pole || "—"}
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
            const secondTeam = race.second ? getDriverTeam(race.second, season) : null;
            const thirdTeam = race.third ? getDriverTeam(race.third, season) : null;
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
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-muted tabular-nums">R{race.round}</span>
                      <span className="font-semibold">{getRaceShortname(season, race.round)}</span>
                    </div>
                    {race.pole && (
                      <span className="text-xs text-muted" title="Pole Position">
                        PP {race.pole}
                      </span>
                    )}
                  </div>

                  {/* Podium row with team logos */}
                  <div className="flex items-center justify-between">
                    {/* Winner */}
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold bg-ink text-paper w-5 h-5 flex items-center justify-center text-xs">1</span>
                      <TeamLogo team={race.winner_team} size={16} />
                      <span className="font-bold text-sm">{race.winner_code}</span>
                    </div>

                    {/* 2nd */}
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold bg-ink/10 w-5 h-5 flex items-center justify-center text-xs">2</span>
                      {race.second ? (
                        <>
                          {secondTeam && secondTeam !== "Unknown" && (
                            <TeamLogo team={secondTeam} size={16} />
                          )}
                          <span className="text-sm text-muted">{race.second}</span>
                        </>
                      ) : (
                        <span className="text-sm text-muted">—</span>
                      )}
                    </div>

                    {/* 3rd */}
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold bg-ink/5 w-5 h-5 flex items-center justify-center text-xs">3</span>
                      {race.third ? (
                        <>
                          {thirdTeam && thirdTeam !== "Unknown" && (
                            <TeamLogo team={thirdTeam} size={16} />
                          )}
                          <span className="text-sm text-muted">{race.third}</span>
                        </>
                      ) : (
                        <span className="text-sm text-muted">—</span>
                      )}
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
