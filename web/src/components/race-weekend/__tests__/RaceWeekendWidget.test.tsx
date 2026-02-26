import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RaceWeekendWidget } from "../RaceWeekendWidget";
import { createMockWeekendResponse, mockHistory, mockHistoryEmpty, BASE_DATE } from "./mocks";

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
        <RaceWeekendWidget
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
        <RaceWeekendWidget
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
      render(<RaceWeekendWidget weekendData={null} />);

      expect(screen.getByText("No Upcoming Race")).toBeInTheDocument();
      expect(screen.getByText(/check back later/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view all circuits/i })).toBeInTheDocument();
    });

    it("renders off-week state with next race info when provided", () => {
      const futureDate = new Date(BASE_DATE);
      futureDate.setDate(futureDate.getDate() + 10);

      render(
        <RaceWeekendWidget
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

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.getByText("No Race This Week")).toBeInTheDocument();
      expect(screen.getByText(/next race weekend begins in/i)).toBeInTheDocument();
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /view full calendar/i })).toBeInTheDocument();
    });
  });

  describe("Pre-weekend state (3-7 days before)", () => {
    it("renders race header and countdown", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show race info
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
      expect(screen.getByText("Autodromo Nazionale Monza")).toBeInTheDocument();

      // Should show countdown
      expect(screen.getByRole("timer")).toBeInTheDocument();
    });

    it("displays historical data when available", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show last year's heading
      expect(screen.getByText(/Last Year \(2025\)/)).toBeInTheDocument();

      // Should show winner (VER may appear multiple times: winner + pole)
      expect(screen.getAllByText("VER").length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("Race-week state (within 3 days)", () => {
    it("renders countdown to next session", () => {
      const weekendData = createMockWeekendResponse("race-week");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.getByRole("timer")).toBeInTheDocument();
      expect(screen.getByText("Italian Grand Prix")).toBeInTheDocument();
    });
  });

  describe("During-weekend state", () => {
    it("renders session grid with completed sessions", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show session cards
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Free Practice 2")).toBeInTheDocument();
    });

    it("shows countdown to next session", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show timer for next session
      expect(screen.getByRole("timer")).toBeInTheDocument();
    });
  });

  describe("Post-race state", () => {
    it("renders all session results", () => {
      const weekendData = createMockWeekendResponse("post-race");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show all sessions
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Qualifying")).toBeInTheDocument();
      expect(screen.getByText("Race")).toBeInTheDocument();
    });

    it("does not show countdown after race", () => {
      const weekendData = createMockWeekendResponse("post-race");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.queryByRole("timer")).not.toBeInTheDocument();
    });
  });

  describe("Historical data handling", () => {
    it("hides historical data for new circuits without previous year data", () => {
      const weekendData = createMockWeekendResponse("pre-weekend");
      weekendData.history = mockHistoryEmpty;

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.queryByText(/Last Year/)).not.toBeInTheDocument();
    });
  });

  describe("Stale data indicator", () => {
    it("shows stale data banner when meta.stale is true", () => {
      const weekendData = createMockWeekendResponse("during-weekend");
      weekendData.meta = { ...weekendData.meta!, stale: true };

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.getByText("Data may be outdated")).toBeInTheDocument();
    });

    it("does not show stale banner when data is fresh", () => {
      const weekendData = createMockWeekendResponse("during-weekend");

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.queryByText("Data may be outdated")).not.toBeInTheDocument();
    });
  });

  describe("Error indicators", () => {
    it("shows partial error message when meta.errors has items", () => {
      const weekendData = createMockWeekendResponse("during-weekend");
      weekendData.meta = { ...weekendData.meta!, errors: ["history_fetch_failed"] };

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.getByText("Some data may be unavailable")).toBeInTheDocument();
    });
  });

  describe("Sprint weekend", () => {
    it("renders sprint weekend sessions correctly", () => {
      const weekendData = createMockWeekendResponse("during-weekend", { isSprint: true });

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show sprint-specific sessions
      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Sprint Qualifying")).toBeInTheDocument();
    });

    it("shows sprint weekend race info", () => {
      const weekendData = createMockWeekendResponse("pre-weekend", { isSprint: true });

      render(<RaceWeekendWidget weekendData={weekendData} />);

      expect(screen.getByText("Austrian Grand Prix")).toBeInTheDocument();
      expect(screen.getByText("Red Bull Ring")).toBeInTheDocument();
    });

    it("renders completed sprint session results", () => {
      const weekendData = createMockWeekendResponse("post-race", { isSprint: true });

      render(<RaceWeekendWidget weekendData={weekendData} />);

      // Should show sprint sessions with results
      expect(screen.getByText("Sprint Qualifying")).toBeInTheDocument();
      // "Sprint" appears in badge and session card, so use getAllByText
      expect(screen.getAllByText("Sprint").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Race")).toBeInTheDocument();
    });
  });
});
