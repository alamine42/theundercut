"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ScoreBadge } from "@/components/ui/score-indicator";
import { getCountryFlag } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface RankingItem {
  rank: number;
  circuit_id: number;
  circuit_name: string;
  country: string;
  value: number;
}

interface RankingResponse {
  field: string;
  order: "asc" | "desc";
  rankings: RankingItem[];
}

interface RankingField {
  key: string;
  label: string;
  description: string;
  unit?: string;
  isScore: boolean;
}

const RANKING_FIELDS: RankingField[] = [
  {
    key: "full_throttle_score",
    label: "Full Throttle",
    description: "Highest full throttle percentage circuits",
    isScore: true,
  },
  {
    key: "average_speed_score",
    label: "Average Speed",
    description: "Fastest average speed circuits",
    isScore: true,
  },
  {
    key: "tire_degradation_score",
    label: "Tire Degradation",
    description: "Highest tire wear circuits",
    isScore: true,
  },
  {
    key: "track_abrasion_score",
    label: "Track Abrasion",
    description: "Most abrasive track surfaces",
    isScore: true,
  },
  {
    key: "downforce_score",
    label: "Downforce",
    description: "Highest downforce requirement circuits",
    isScore: true,
  },
  {
    key: "overtaking_difficulty_score",
    label: "Overtaking Difficulty",
    description: "Most difficult circuits for overtaking",
    isScore: true,
  },
  {
    key: "drs_zones",
    label: "DRS Zones",
    description: "Circuits with most DRS zones",
    unit: "zones",
    isScore: false,
  },
  {
    key: "track_length_km",
    label: "Track Length",
    description: "Longest circuits",
    unit: "km",
    isScore: false,
  },
];

export function CircuitRankingClient() {
  const [selectedField, setSelectedField] = useState(RANKING_FIELDS[0].key);
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [rankings, setRankings] = useState<RankingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selectedFieldInfo = RANKING_FIELDS.find((f) => f.key === selectedField);

  useEffect(() => {
    async function fetchRankings() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/v1/circuits/characteristics/rank?by=${selectedField}&order=${order}&limit=20`
        );
        if (!res.ok) {
          throw new Error("Failed to fetch rankings");
        }
        const data: RankingResponse = await res.json();
        setRankings(data.rankings || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchRankings();
  }, [selectedField, order]);

  return (
    <div className="space-y-8">
      {/* Field Selection */}
      <article className="border-2 border-ink bg-paper p-4 sm:p-6">
        <h2 className="text-lg font-semibold mb-4">Rank By</h2>
        <div className="flex flex-wrap gap-2">
          {RANKING_FIELDS.map((field) => (
            <button
              key={field.key}
              onClick={() => setSelectedField(field.key)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium border-2 transition-colors",
                selectedField === field.key
                  ? "border-accent bg-accent text-paper"
                  : "border-border-light bg-paper text-ink hover:border-ink"
              )}
            >
              {field.label}
            </button>
          ))}
        </div>

        {selectedFieldInfo && (
          <p className="mt-4 text-sm text-muted">{selectedFieldInfo.description}</p>
        )}
      </article>

      {/* Order Toggle */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium">Order:</span>
        <div className="flex border-2 border-ink">
          <button
            onClick={() => setOrder("desc")}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors",
              order === "desc" ? "bg-ink text-paper" : "bg-paper text-ink hover:bg-gray-100"
            )}
          >
            Highest First
          </button>
          <button
            onClick={() => setOrder("asc")}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-l-2 border-ink",
              order === "asc" ? "bg-ink text-paper" : "bg-paper text-ink hover:bg-gray-100"
            )}
          >
            Lowest First
          </button>
        </div>
      </div>

      {/* Rankings Table */}
      <article className="border-2 border-ink bg-paper">
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-6 w-6 border-2 border-accent border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-2 text-sm text-muted">Loading rankings...</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center">
            <p className="text-error">{error}</p>
          </div>
        ) : rankings.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-muted">No data available for this ranking</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-ink text-paper">
                <tr>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide w-16">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide">
                    Circuit
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide">
                    {selectedFieldInfo?.label || "Value"}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {rankings.map((item, index) => (
                  <tr key={item.circuit_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-4 text-center">
                      <span
                        className={cn(
                          "inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm",
                          index === 0 && "bg-amber-400 text-amber-900",
                          index === 1 && "bg-gray-300 text-gray-800",
                          index === 2 && "bg-orange-300 text-orange-900",
                          index > 2 && "bg-gray-100 text-gray-600"
                        )}
                      >
                        {item.rank}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div>
                        <p className="font-semibold">{item.circuit_name}</p>
                        <p className="text-xs text-muted">
                          {getCountryFlag(item.country)} {item.country}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-center">
                      {selectedFieldInfo?.isScore ? (
                        <ScoreBadge score={item.value} />
                      ) : (
                        <span className="font-mono font-medium">
                          {item.value}
                          {selectedFieldInfo?.unit && (
                            <span className="text-muted ml-1">{selectedFieldInfo.unit}</span>
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {/* Back Link */}
      <div className="flex gap-4">
        <Link
          href="/circuits/characteristics"
          className="inline-flex items-center text-sm text-muted hover:text-ink transition-colors"
        >
          <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Characteristics
        </Link>
        <Link
          href="/circuits/characteristics/compare"
          className="inline-flex items-center text-sm text-accent hover:underline"
        >
          Compare Circuits
          <svg className="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
