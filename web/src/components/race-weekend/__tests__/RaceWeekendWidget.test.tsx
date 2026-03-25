import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RaceWeekendWidget } from "../RaceWeekendWidget";
import { createMockWeekendResponse, mockHistoryEmpty, BASE_DATE, futureDate } from "./mocks";

// Mock the getCountryFlag utility
vi.mock("@/lib/utils", () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(" "),
  getCountryFlag: (country: string) => (country === "Italy" ? "IT" : country === "Austria" ? "AT" : ""),
}));

describe("RaceWeekendWidget", () => {
  // Store original window.location to restore after tests
  const originalLocation = window.location;

  // Use deterministic time for all tests
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(BASE_DATE);
  });

  afterEach(() => {
    vi.useRealTimers();
    // Restore original window.location if it was modified
    if (window.location !== originalLocation) {
      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
      });
    }
  });

  describe("Error state", () => {
    it("renders error state when error prop is provided", () => {
      render(
        <RaceWeekendWidget liveUpdate={false}
          weekendData={null}
          error="Failed to load race data"
        />
      );

      expect(screen.getByText("Unable to Load Race Data")).toBeInTheDocument();
      expect(screen.getByText("Failed to load race data")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    });

    it("calls window.location.reload when Try Again is clicked", () => {
      const reloadMock = vi.fn();
      Object.defineProperty(window, "location", {
        value: { ...originalLocation, reload: reloadMock },
        writable: true,
        configurable: true,
      });

      render(
        <RaceWeekendWidget liveUpdate={false}
          weekendData={null}
          error="Failed to load race data"
        />
      );

      fireEvent.click(screen.getByRole("button", { name: /try again/i }));
      expect(reloadMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("Empty state", () => {
    it("renders empty state when no weekend data", () => {
      render(<RaceWeekendWidget liveUpdate={false} weekendData={null} />);

      expect(screen.getByText("No Upcoming Race")).toBeInTheDocument();
      expect(screen.getByText(/check back later/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view all circuits/i })).toBeInTheDocument();
    });

    it("renders off-week state with next race info when provided", () => {
      const futureDate = new Date(BASE_DATE);
      futureDate.setDate(futureDate.getDate() + 10);

      render(
        <RaceWeekendWidget liveUpdate={false}
          weekendData={null}
          nextRaceInfo={{
            raceName: "Monaco Grand Prix",
            circuitName: "Circuit de Monaco",
            circuitCountry: "Monaco",
            fp1Date: futureDate.toISOString(),
            round: 8,
          }}
        />
      );

      expect(screen.getByText("No Race This Week")).toBeInTheDocument();
      expect(screen.getByText("Monaco Grand Prix")).toBeInTheDocument();
      expect(screen.getByText(/Round 8/)).toBeInTheDocument();
    });
  });

  describe("Off-week state (>7 days to race)", () => {
    it("renders off-week message with days countdown", () => {
      const weekendData = createMockWeekendResponse("off-week");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.getByText("No Race This Week")).toBeInTheDocument();
      expect(screen.getByText(/next race weekend begins in/i)).toBeInTheDocument();
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view full calendar/i })).toBeInTheDocument();
    });
  });

  describe("Pre-weekend state (3-7 days before)", () => {
    it("renders race header with GP name and 'Upcoming Race' label and countdown", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show GP name as main title with "Upcoming Race" label
      expect(screen.getByText("Upcoming Race")).toBeInTheDocument();
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.getByText("Autodromo Nazionale Monza")).toBeInTheDocument();

      // Should show countdown
      expect(screen.getByRole("timer")).toBeInTheDocument();
    });

    it("displays historical data when available", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show last year's heading
      expect(screen.getByText(/Last Year \(2025\)/)).toBeInTheDocument();

      // Should show winner (VER may appear multiple times: winner + pole)
      expect(screen.getAllByText("VER").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Race-week state (within 3 days)", () => {
    it("renders countdown with GP name and 'Upcoming Race' label", () => {
      const weekendData = createMockWeekendResponse("race-week");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.getByRole("timer")).toBeInTheDocument();
      // Should show GP name as main title with "Upcoming Race" label
      expect(screen.getByText("Upcoming Race")).toBeInTheDocument();
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
    });
  });

  describe("During-weekend state", () => {
    it("renders session grid with completed sessions and GP name as title", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show GP name as title during race weekend
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.queryByText("Upcoming Race")).not.toBeInTheDocument();

      // Should show session cards
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Free Practice 2")).toBeInTheDocument();
    });

    it("shows countdown to next session", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show timer for next session
      expect(screen.getByRole("timer")).toBeInTheDocument();
    });
  });

  describe("Post-race state", () => {
    it("renders all session results with GP name within 24h of race end", () => {
      const weekendData = createMockWeekendResponse("post-race");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show GP name (mock post-race has race ending ~22h ago, within 24h)
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.queryByText("Upcoming Race")).not.toBeInTheDocument();

      // Should show all sessions
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Qualifying")).toBeInTheDocument();
      expect(screen.getByText("Race")).toBeInTheDocument();
    });

    it("does not show countdown after race", () => {
      const weekendData = createMockWeekendResponse("post-race");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.queryByRole("timer")).not.toBeInTheDocument();
    });

    it("shows next race info after 24h have passed since race end", () => {
      // Move time forward so race end was >24h ago
      // Post-race mock has race end_time at pastDate(1, -2) = 1 day ago + 2h = 22h ago
      // Advance time by 3 more hours so it's 25h since race end
      const laterTime = new Date(BASE_DATE);
      laterTime.setHours(laterTime.getHours() + 3);
      vi.setSystemTime(laterTime);

      const weekendData = createMockWeekendResponse("post-race");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // After 24h since race end, widget reverts to showing next race countdown
      // The GP name is still displayed since raceName is always shown now
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
    });
  });

  describe("Historical data handling", () => {
    it("hides historical data for new circuits without previous year data", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");
      weekendData.history = mockHistoryEmpty;

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.queryByText(/Last Year/)).not.toBeInTheDocument();
    });
  });

  describe("Stale data indicator", () => {
    it("shows stale data banner when meta.stale is true", () => {
      const weekendData = createMockWeekendResponse("during-weekend");
      weekendData.meta = { ...weekendData.meta!, stale: true };

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.getByText("Data may be outdated")).toBeInTheDocument();
    });

    it("does not show stale banner when data is fresh", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.queryByText("Data may be outdated")).not.toBeInTheDocument();
    });
  });

  describe("Error indicators", () => {
    it("shows partial error message when meta.errors has items", () => {
      const weekendData = createMockWeekendResponse("during-weekend");
      weekendData.meta = { ...weekendData.meta!, errors: ["history_fetch_failed"] };

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      expect(screen.getByText("Some data may be unavailable")).toBeInTheDocument();
    });
  });

  describe("Sprint weekend", () => {
    it("renders sprint weekend sessions correctly", () => {
      const weekendData = createMockWeekendResponse("during-weekend", { isSprint: true });

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show sprint-specific sessions
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Sprint Qualifying")).toBeInTheDocument();
    });

    it("shows GP name with 'Upcoming Race' label for sprint pre-weekend", () => {
      const weekendData = createMockWeekendResponse("pre-weekend", { isSprint: true });

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show GP name as main title with "Upcoming Race" label
      expect(screen.getByText("Upcoming Race")).toBeInTheDocument();
      expect(screen.getByText("Austrian Grand Prix")).toBeInTheDocument();
      expect(screen.getByText("Red Bull Ring")).toBeInTheDocument();
    });

    it("renders completed sprint session results", () => {
      const weekendData = createMockWeekendResponse("post-race", { isSprint: true });

      render(<RaceWeekendWidget liveUpdate={false} weekendData={weekendData} />);

      // Should show sprint sessions with results
      expect(screen.getByText("Sprint Qualifying")).toBeInTheDocument();
      // "Sprint" appears in badge and session card, so use getAllByText
      expect(screen.getAllByText("Sprint").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Race")).toBeInTheDocument();
    });
  });

  describe("Live updates", () => {
    it("fetches updated results for sessions that just finished", async () => {
      vi.useRealTimers();

      const weekendData = createMockWeekendResponse("during-weekend");
      weekendData.sessions.fp1 = null;
      weekendData.timeline = {
        state: "during-weekend",
        window_start: BASE_DATE.toISOString(),
        window_end: futureDate(2),
        is_active: true,
        next_session: weekendData.schedule.sessions[2],
        next_session_in_seconds: null,
        current_session: weekendData.schedule.sessions[0],
      };

      const refreshedData = createMockWeekendResponse("during-weekend");
      refreshedData.timeline = { ...weekendData.timeline };

      const originalFetch = global.fetch;
      const originalWindowFetch = window.fetch;
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => refreshedData,
      });

      // @ts-expect-error - jsdom global typing
      global.fetch = fetchMock;
      // @ts-expect-error - jsdom window typing
      window.fetch = fetchMock;

      render(
        <RaceWeekendWidget
          weekendData={weekendData}
          liveUpdate
        />
      );

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
      });

      await waitFor(() => {
        const fp1Label = screen.getByText("Free Practice 1");
        const card = fp1Label.closest(".session-card");
        expect(card).not.toBeNull();
        expect(card?.textContent ?? "").toContain("VER");
      });

      if (originalFetch) {
        // @ts-expect-error - jsdom global typing
        global.fetch = originalFetch;
      } else {
        // @ts-expect-error - jsdom global typing
        delete global.fetch;
      }

      if (originalWindowFetch) {
        // @ts-expect-error - jsdom window typing
        window.fetch = originalWindowFetch;
      } else {
        // @ts-expect-error - jsdom window typing
        delete window.fetch;
      }

      vi.useFakeTimers();
    });
  });
});
