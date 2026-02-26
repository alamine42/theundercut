import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionCard } from "../SessionCard";
import { mockFP1Results, mockQualifyingResults, mockSprintQualifyingResults, futureDate, pastDate, BASE_DATE } from "./mocks";
import type { RaceSession } from "../types";

// Mock TeamWithLogo component
vi.mock("@/components/ui/team-logo", () => ({
  TeamWithLogo: ({ team }: { team: string }) => <span data-testid="team-logo">{team}</span>,
}));

describe("SessionCard", () => {
  const mockOnToggle = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(BASE_DATE);
    mockOnToggle.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Compact view", () => {
    it("renders session name and status", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
      expect(screen.getByText("Done")).toBeInTheDocument();
    });

    it("shows top 3 results in compact view", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("VER")).toBeInTheDocument();
      expect(screen.getByText("NOR")).toBeInTheDocument();
      expect(screen.getByText("LEC")).toBeInTheDocument();
    });

    it("shows remaining drivers count when more than 3", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      // mockFP1Results has 5 drivers, so +2 more
      expect(screen.getByText("+2 more drivers")).toBeInTheDocument();
    });
  });

  describe("Expanded view", () => {
    it("shows full grid when expanded", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={true}
          onToggle={mockOnToggle}
        />
      );

      // Should show all 5 drivers in expanded view
      expect(screen.getByText("VER")).toBeInTheDocument();
      expect(screen.getByText("HAM")).toBeInTheDocument();
      expect(screen.getByText("RUS")).toBeInTheDocument();
    });

    it("calls onToggle when clicked", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe("Status badges", () => {
    it("shows 'Done' badge for completed sessions", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Done")).toBeInTheDocument();
    });

    it("shows 'Done' badge for ingested sessions (post-race)", () => {
      const session: RaceSession = {
        session_type: "qualifying",
        start_time: pastDate(2),
        end_time: pastDate(2, -1),
        status: "ingested",
      };

      render(
        <SessionCard
          session={session}
          results={mockQualifyingResults}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Done")).toBeInTheDocument();
    });

    it("shows countdown for scheduled sessions", () => {
      const session: RaceSession = {
        session_type: "qualifying",
        start_time: futureDate(0, 5),
        end_time: futureDate(0, 6),
        status: "scheduled",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      // Should show time countdown (e.g., "in 5h 0m")
      expect(screen.getByText(/in \d+h/)).toBeInTheDocument();
    });

    it("shows 'Live' badge for running sessions", () => {
      const session: RaceSession = {
        session_type: "race",
        start_time: pastDate(0, 1),
        end_time: futureDate(0, 1),
        status: "running",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Live")).toBeInTheDocument();
    });
  });

  describe("Session types", () => {
    it("renders FP1 with correct label", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Free Practice 1")).toBeInTheDocument();
    });

    it("renders Qualifying with Q times", () => {
      const session: RaceSession = {
        session_type: "qualifying",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockQualifyingResults}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Qualifying")).toBeInTheDocument();
      // Should show Q3 time for qualifying
      expect(screen.getByText("1:28.500")).toBeInTheDocument();
    });

    it("renders Race with correct label", () => {
      const session: RaceSession = {
        session_type: "race",
        start_time: futureDate(1),
        end_time: futureDate(1, 2),
        status: "scheduled",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Race")).toBeInTheDocument();
    });

    it("renders Sprint Qualifying with correct label", () => {
      const session: RaceSession = {
        session_type: "sprint_qualifying",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "ingested",
      };

      render(
        <SessionCard
          session={session}
          results={mockSprintQualifyingResults}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Sprint Qualifying")).toBeInTheDocument();
    });

    it("renders Sprint with correct label", () => {
      const session: RaceSession = {
        session_type: "sprint",
        start_time: futureDate(1),
        end_time: futureDate(1, 1),
        status: "scheduled",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      expect(screen.getByText("Sprint")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has correct aria-expanded attribute when results exist", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={mockFP1Results}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("button is disabled when no results", () => {
      const session: RaceSession = {
        session_type: "race",
        start_time: futureDate(1),
        end_time: futureDate(1, 2),
        status: "scheduled",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });

  describe("Edge cases", () => {
    it("handles empty results by disabling expand", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      const emptyResults = { ...mockFP1Results, results: [] };

      render(
        <SessionCard
          session={session}
          results={emptyResults}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      // When results are empty, button should be disabled (no expandable content)
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("handles null results gracefully", () => {
      const session: RaceSession = {
        session_type: "fp1",
        start_time: pastDate(1),
        end_time: pastDate(1, -1),
        status: "completed",
      };

      render(
        <SessionCard
          session={session}
          results={null}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      // When results are null, button should be disabled
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });
});
