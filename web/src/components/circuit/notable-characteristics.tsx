interface NotableRanking {
  field: string;
  label: string;
  rank: number;
  value: number;
  isTop: boolean;
}

interface NotableCharacteristicsBadgesProps {
  rankings: NotableRanking[];
  maxBadges?: number;
}

function getRankIcon(rank: number): string {
  if (rank === 1) return "🥇";
  if (rank === 2) return "🥈";
  if (rank === 3) return "🥉";
  return "📊";
}

function getRankStyle(rank: number, isTop: boolean): string {
  // Top 3 get highlighted
  if (rank <= 3) {
    return isTop
      ? "bg-accent/10 text-accent border-accent/30"
      : "bg-blue-500/10 text-blue-600 border-blue-500/30";
  }
  // Ranks 4-8 get subtle styling
  return "bg-gray-100 text-gray-600 border-gray-200";
}

export function NotableCharacteristicsBadges({
  rankings,
  maxBadges = 3,
}: NotableCharacteristicsBadgesProps) {
  if (!rankings || rankings.length === 0) {
    return null;
  }

  // Take top N rankings by rank
  const displayRankings = rankings
    .sort((a, b) => a.rank - b.rank)
    .slice(0, maxBadges);

  return (
    <div className="flex flex-wrap gap-1.5">
      {displayRankings.map((r, idx) => (
        <span
          key={`${r.field}-${idx}`}
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border ${getRankStyle(r.rank, r.isTop)}`}
          title={`#${r.rank} in ${r.label}`}
        >
          <span>{getRankIcon(r.rank)}</span>
          <span>#{r.rank}</span>
          <span className="hidden sm:inline">{r.label}</span>
        </span>
      ))}
    </div>
  );
}

// Compact inline version for tighter spaces
export function NotableCharacteristicsInline({
  rankings,
  maxBadges = 2,
}: NotableCharacteristicsBadgesProps) {
  if (!rankings || rankings.length === 0) {
    return null;
  }

  const displayRankings = rankings
    .sort((a, b) => a.rank - b.rank)
    .slice(0, maxBadges);

  return (
    <span className="inline-flex items-center gap-1 text-[10px]">
      {displayRankings.map((r, idx) => (
        <span
          key={`${r.field}-${idx}`}
          className={`inline-flex items-center gap-0.5 px-1 py-0.5 rounded ${getRankStyle(r.rank, r.isTop)}`}
          title={`#${r.rank} in ${r.label}`}
        >
          {getRankIcon(r.rank)}#{r.rank}
        </span>
      ))}
    </span>
  );
}
