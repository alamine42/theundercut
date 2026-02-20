import { notFound } from "next/navigation";
import { fetchAnalytics } from "@/lib/api";
import { AnalyticsView } from "./analytics-view";

export const revalidate = 300; // 5 minutes ISR

interface AnalyticsPageProps {
  params: Promise<{ season: string; round: string }>;
}

export async function generateMetadata({ params }: AnalyticsPageProps) {
  const { season, round } = await params;
  return {
    title: `Race ${round} Analytics - ${season} | The Undercut`,
    description: `F1 ${season} Round ${round} race analytics - lap times, stint strategy, and driver grades`,
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
