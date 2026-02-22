import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { fetchTestingEvents, fetchTestingDay } from "@/lib/api";
import { getCountryFlag } from "@/lib/utils";
import { TestingDayTabs } from "./testing-day-tabs";

export const revalidate = 300; // 5 minutes ISR

interface PageProps {
  params: Promise<{ season: string; eventId: string }>;
  searchParams: Promise<{ day?: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { season, eventId } = await params;
  return {
    title: `${eventId.replace(/_/g, " ")} Testing ${season} | The Undercut`,
    description: `Pre-season testing lap times, stints, and driver performance for ${season}`,
  };
}

export default async function TestingEventPage({ params, searchParams }: PageProps) {
  const { season: seasonStr, eventId } = await params;
  const { day: dayParam } = await searchParams;
  const season = parseInt(seasonStr, 10);
  const initialDay = dayParam ? parseInt(dayParam, 10) : 1;

  if (isNaN(season) || season < 2020 || season > 2030) {
    notFound();
  }

  // Fetch event list to get event metadata
  let eventsData;
  try {
    eventsData = await fetchTestingEvents(season);
  } catch {
    notFound();
  }

  const event = eventsData.events.find((e) => e.event_id === eventId);
  if (!event) {
    notFound();
  }

  // Fetch initial day data
  let dayData;
  try {
    dayData = await fetchTestingDay(season, eventId, initialDay);
  } catch {
    // Day might not exist yet, that's OK
    dayData = null;
  }

  // Get country for flag
  const circuitCountries: Record<string, string> = {
    bahrain: "Bahrain",
    barcelona: "Spain",
    catalunya: "Spain",
    silverstone: "UK",
    albert_park: "Australia",
  };
  const country = circuitCountries[event.circuit_id] || "";

  // Format date range
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const dateRange =
    event.start_date && event.end_date
      ? `${formatDate(event.start_date)} - ${formatDate(event.end_date)}`
      : "TBD";

  // Calculate total laps from day data
  const totalLaps = dayData?.results.reduce((sum, r) => sum + r.total_laps, 0) || 0;
  const driverCount = dayData?.results.length || 0;

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {/* Back link */}
          <Link
            href={`/testing/${season}`}
            className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink transition-colors mb-4"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Testing
          </Link>

          <div>
            <HeroTitle>{event.event_name}</HeroTitle>
            <HeroSubtitle>
              {getCountryFlag(country)} {event.circuit_name} &middot; {dateRange}
            </HeroSubtitle>
          </div>

          <HeroStats>
            <HeroStat label="Days" value={event.total_days} />
            <HeroStat label="Drivers" value={driverCount} />
            <HeroStat label="Laps" value={totalLaps} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <TestingDayTabs
            season={season}
            eventId={eventId}
            totalDays={event.total_days}
            initialDay={initialDay}
            initialData={dayData}
          />
        </div>
      </section>
    </>
  );
}
