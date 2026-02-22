import { notFound } from "next/navigation";
import Link from "next/link";
import { Hero, HeroTitle, HeroSubtitle, HeroStat, HeroStats } from "@/components/ui/hero";
import { fetchTestingEvents } from "@/lib/api";
import { getCountryFlag } from "@/lib/utils";

export const revalidate = 300; // 5 minutes ISR

interface PageProps {
  params: Promise<{ season: string }>;
}

export async function generateMetadata({ params }: PageProps) {
  const { season } = await params;
  return {
    title: `${season} Pre-Season Testing | The Undercut`,
    description: `Pre-season testing data, lap times, and stint analysis for the ${season} F1 season`,
  };
}

export default async function TestingPage({ params }: PageProps) {
  const { season: seasonStr } = await params;
  const season = parseInt(seasonStr, 10);

  if (isNaN(season) || season < 2020 || season > 2030) {
    notFound();
  }

  let testingData;
  try {
    testingData = await fetchTestingEvents(season);
  } catch {
    notFound();
  }

  const { events } = testingData;

  // Count events by status
  const completedEvents = events.filter((e) => e.status === "completed").length;
  const upcomingEvents = events.filter((e) => e.status === "scheduled").length;

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div>
            <HeroTitle>Pre-Season Testing</HeroTitle>
            <HeroSubtitle>
              {season} testing sessions - lap times, stints, and performance analysis
            </HeroSubtitle>
          </div>

          <HeroStats>
            <HeroStat label="Season" value={season} />
            <HeroStat label="Events" value={events.length} />
            <HeroStat label="Completed" value={completedEvents} />
          </HeroStats>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          {events.length === 0 ? (
            <div className="text-center py-16 border-2 border-dashed border-ink/20">
              <div className="text-4xl mb-4">🏎️</div>
              <h2 className="text-xl font-semibold mb-2">No Testing Events</h2>
              <p className="text-muted">
                No pre-season testing data available for {season}
              </p>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-1">
              {events.map((event) => (
                <TestingEventCard
                  key={event.event_id}
                  event={event}
                  season={season}
                />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

interface TestingEventCardProps {
  event: {
    event_id: string;
    event_name: string;
    circuit_id: string;
    circuit_name: string;
    start_date: string | null;
    end_date: string | null;
    total_days: number;
    status: "scheduled" | "running" | "completed";
  };
  season: number;
}

function TestingEventCard({ event, season }: TestingEventCardProps) {
  const statusColors = {
    scheduled: "bg-ink/10 text-ink",
    running: "bg-accent/20 text-accent",
    completed: "bg-green-100 text-green-800",
  };

  const statusLabels = {
    scheduled: "Upcoming",
    running: "Live",
    completed: "Completed",
  };

  // Format dates
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const dateRange =
    event.start_date && event.end_date
      ? `${formatDate(event.start_date)} - ${formatDate(event.end_date)}`
      : event.start_date
      ? formatDate(event.start_date)
      : "TBD";

  // Get country flag from circuit
  const circuitCountries: Record<string, string> = {
    bahrain: "Bahrain",
    barcelona: "Spain",
    catalunya: "Spain",
    silverstone: "UK",
    albert_park: "Australia",
  };
  const country = circuitCountries[event.circuit_id] || "";

  return (
    <Link
      href={`/testing/${season}/${event.event_id}`}
      className="group block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
    >
      <article className="relative overflow-hidden border-2 border-ink bg-paper transition-all duration-200 group-hover:border-ink/80 group-active:scale-[0.99]">
        <div className="p-6 sm:p-8">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight">
                  {event.event_name}
                </h2>
                <span
                  className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    statusColors[event.status]
                  }`}
                >
                  {statusLabels[event.status]}
                </span>
              </div>
              <p className="text-muted">
                {getCountryFlag(country)} {event.circuit_name}
              </p>
            </div>

            {/* Days badge */}
            <div className="flex flex-col items-center justify-center bg-ink text-paper px-4 py-2">
              <span className="text-2xl font-bold">{event.total_days}</span>
              <span className="text-xs uppercase tracking-wider">Days</span>
            </div>
          </div>

          {/* Info grid */}
          <div className="mt-6 pt-6 border-t border-ink/10 grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-muted uppercase tracking-wider mb-1">
                Dates
              </p>
              <p className="font-medium">{dateRange}</p>
            </div>
            <div>
              <p className="text-xs text-muted uppercase tracking-wider mb-1">
                Circuit
              </p>
              <p className="font-medium capitalize">
                {event.circuit_id.replace(/_/g, " ")}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <p className="text-xs text-muted uppercase tracking-wider mb-1">
                Status
              </p>
              <p className="font-medium">{statusLabels[event.status]}</p>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-6 flex items-center text-sm font-medium text-ink group-hover:text-accent transition-colors">
            <span>View testing data</span>
            <svg
              aria-hidden="true"
              className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </div>
      </article>
    </Link>
  );
}
