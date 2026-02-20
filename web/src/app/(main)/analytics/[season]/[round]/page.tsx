import { notFound } from "next/navigation";
import { fetchAnalytics } from "@/lib/api";
import { getRaceName } from "@/lib/constants";
import { AnalyticsView } from "./analytics-view";

export const revalidate = 300; // 5 minutes ISR

interface AnalyticsPageProps {
  params: Promise<{ season: string; round: string }>;
}

export async function generateMetadata({ params }: AnalyticsPageProps) {
  const { season, round } = await params;
  const raceName = getRaceName(parseInt(season, 10), parseInt(round, 10));
  return {
    title: `${raceName} Analytics - ${season} | The Undercut`,
    description: `F1 ${season} ${raceName} race analytics - lap times, stint strategy, and driver grades`,
  };
}

export default async function AnalyticsPage({ params }: AnalyticsPageProps) {
  const { season: seasonStr, round: roundStr } = await params;
  const season = parseInt(seasonStr, 10);
  const round = parseInt(roundStr, 10);

  if (
    isNaN(season) ||
    isNaN(round) ||
    season < 2018 ||
    season > 2030 ||
    round < 1 ||
    round > 30
  ) {
    notFound();
  }

  let analytics;
  try {
    analytics = await fetchAnalytics(season, round);
  } catch {
    notFound();
  }

  return <AnalyticsView initialData={analytics} season={season} round={round} />;
}
