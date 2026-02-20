"use client";

import { useRouter } from "next/navigation";
import { getRaceName } from "@/lib/constants";

interface RaceSelectorProps {
  currentRound: number;
  season: number;
  maxRounds?: number;
}

export function RaceSelector({ currentRound, season, maxRounds = 24 }: RaceSelectorProps) {
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const round = e.target.value;
    router.push(`/analytics/${season}/${round}`);
  };

  // Generate rounds 1 to maxRounds
  const rounds = Array.from({ length: maxRounds }, (_, i) => i + 1);

  return (
    <select
      value={currentRound}
      onChange={handleChange}
      className="h-10 px-3 border-2 border-ink bg-paper text-ink font-mono text-sm
                 focus:outline-none focus:ring-2 focus:ring-ink cursor-pointer
                 hover:bg-ink hover:text-paper transition-colors"
    >
      {rounds.map((round) => (
        <option key={round} value={round}>
          R{round}: {getRaceName(season, round)}
        </option>
      ))}
    </select>
  );
}
