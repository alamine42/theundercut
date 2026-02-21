"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { TeamWithLogo } from "@/components/ui/team-logo";
import { getRaceShortname } from "@/lib/constants";
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
        <CardTitle>{season} Season Results</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Round</TableHead>
                <TableHead>Race</TableHead>
                <TableHead>Winner</TableHead>
                <TableHead className="text-center">Pole</TableHead>
                <TableHead className="text-center">2nd</TableHead>
                <TableHead className="text-center">3rd</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayedRaces.map((race) => (
                <TableRow key={race.round}>
                  <TableCell className="font-semibold">{race.round}</TableCell>
                  <TableCell>
                    <Link
                      href={`/analytics/${season}/${race.round}`}
                      className="hover:text-accent transition-colors"
                    >
                      {getRaceShortname(season, race.round)}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <TeamWithLogo team={race.winner_team} />
                    <span className="ml-2 font-semibold">{race.winner_code}</span>
                  </TableCell>
                  <TableCell className="text-center text-muted">{race.pole || "—"}</TableCell>
                  <TableCell className="text-center text-muted">{race.second || "—"}</TableCell>
                  <TableCell className="text-center text-muted">{race.third || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {hasMore && (
          <div className="mt-4 flex justify-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded
                ? "Show less ↑"
                : `Show all ${sortedRaces.length} races →`
              }
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
