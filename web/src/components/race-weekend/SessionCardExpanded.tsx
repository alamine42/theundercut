import { TeamWithLogo } from "@/components/ui/team-logo";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import type { SessionCardExpandedProps } from "./types";

function PositionBadge({ position, showPodiumStyle }: { position: number; showPodiumStyle: boolean }) {
  // Only show gold/silver/bronze styling for race sessions
  if (showPodiumStyle) {
    if (position === 1) {
      return (
        <span className="position-badge position-1" title="1st Place">
          1
        </span>
      );
    }
    if (position === 2) {
      return (
        <span className="position-badge position-2" title="2nd Place">
          2
        </span>
      );
    }
    if (position === 3) {
      return (
        <span className="position-badge position-3" title="3rd Place">
          3
        </span>
      );
    }
  }
  return <span className="font-semibold text-muted">{position}</span>;
}

export function SessionCardExpanded({ results, sessionType }: SessionCardExpandedProps) {
  const isQualifying = sessionType === "qualifying" || sessionType === "sprint_qualifying";
  const isRace = sessionType === "race" || sessionType === "sprint_race" || sessionType === "sprint";
  // Only show podium (gold/silver/bronze) styling for race sessions
  const showPodiumStyle = isRace;

  if (results.length === 0) {
    return (
      <p className="text-sm text-muted py-4 text-center">No results available</p>
    );
  }

  if (isQualifying) {
    return (
      <div className="overflow-x-auto -mx-1">
        <Table className="results-table">
          <TableHeader>
            <TableRow>
              <TableHead className="w-10 text-center">P</TableHead>
              <TableHead>Driver</TableHead>
              <TableHead className="text-right text-xs">Q1</TableHead>
              <TableHead className="text-right text-xs">Q2</TableHead>
              <TableHead className="text-right text-xs">Q3</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result, idx) => (
              <TableRow
                key={result.driver_code}
                style={{ "--row-index": idx } as React.CSSProperties}
              >
                <TableCell className="text-center">
                  <PositionBadge position={result.position} showPodiumStyle={showPodiumStyle} />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{result.driver_code}</span>
                    {result.team && (
                      <span className="text-muted text-xs">
                        <TeamWithLogo team={result.team} size={14} />
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right text-xs text-muted font-mono">
                  {result.q1_time || "-"}
                </TableCell>
                <TableCell className="text-right text-xs text-muted font-mono">
                  {result.q2_time || "-"}
                </TableCell>
                <TableCell className="text-right text-xs font-mono">
                  {result.q3_time || (
                    <span className="text-muted">{result.eliminated_in || "-"}</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  // Practice or Race results
  return (
    <div className="overflow-x-auto -mx-1">
      <Table className="results-table">
        <TableHeader>
          <TableRow>
            <TableHead className="w-10 text-center">P</TableHead>
            <TableHead>Driver</TableHead>
            <TableHead className="text-right">Time</TableHead>
            <TableHead className="text-right hidden sm:table-cell">Gap</TableHead>
            {isRace && (
              <TableHead className="text-right w-12">Pts</TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((result, idx) => (
            <TableRow
              key={result.driver_code}
              style={{ "--row-index": idx } as React.CSSProperties}
            >
              <TableCell className="text-center">
                <PositionBadge position={result.position} showPodiumStyle={showPodiumStyle} />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{result.driver_code}</span>
                  {result.team && (
                    <span className="text-muted text-xs">
                      <TeamWithLogo team={result.team} size={14} />
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right text-xs font-mono">
                {result.time || "-"}
              </TableCell>
              <TableCell className="text-right text-xs text-muted font-mono hidden sm:table-cell">
                {result.gap || "-"}
              </TableCell>
              {isRace && (
                <TableCell className="text-right font-semibold">
                  {result.points ?? "-"}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
