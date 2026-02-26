import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { RaceCountdown } from "../RaceCountdown";

describe("RaceCountdown", () => {
  beforeEach(() => {
    // Fix the current time for consistent testing
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-15T10:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Countdown display", () => {
    it("shows days, hours, and minutes for future session", () => {
      // Session in 2 days, 5 hours, 30 minutes
      const targetDate = new Date("2026-03-17T15:30:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="fp1" />);

      // Should show countdown values
      expect(screen.getByText("02")).toBeInTheDocument(); // days
      expect(screen.getByText("05")).toBeInTheDocument(); // hours
      expect(screen.getByText("30")).toBeInTheDocument(); // minutes
    });

    it("omits days when less than 24 hours away", () => {
      // Session in 5 hours
      const targetDate = new Date("2026-03-15T15:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="qualifying" />);

      // Should not show days label
      expect(screen.queryByText("days")).not.toBeInTheDocument();
      // Should show hours
      expect(screen.getByText("hours")).toBeInTheDocument();
    });

    it("shows correct session label", () => {
      const targetDate = new Date("2026-03-17T15:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="qualifying" />);

      expect(screen.getByText("QUALIFYING STARTS IN")).toBeInTheDocument();
    });

    it("shows custom label when provided", () => {
      const targetDate = new Date("2026-03-17T15:00:00Z").toISOString();

      render(
        <RaceCountdown
          targetDate={targetDate}
          sessionType="race"
          label="NEXT: RACE"
        />
      );

      expect(screen.getByText("NEXT: RACE")).toBeInTheDocument();
    });
  });

  describe("Session started state", () => {
    it("shows 'In Progress' when session has started", () => {
      // Session started 30 minutes ago
      const targetDate = new Date("2026-03-15T09:30:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="race" />);

      expect(screen.getByText("In Progress")).toBeInTheDocument();
    });

    it("removes timer role when session has started", () => {
      // Session started 30 minutes ago
      const targetDate = new Date("2026-03-15T09:30:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="race" />);

      // Timer role should not be present when session is in progress
      expect(screen.queryByRole("timer")).not.toBeInTheDocument();
    });
  });

  describe("Imminent session styling", () => {
    it("applies pulse animation when less than 24 hours away", () => {
      // Session in 12 hours
      const targetDate = new Date("2026-03-15T22:00:00Z").toISOString();

      const { container } = render(
        <RaceCountdown targetDate={targetDate} sessionType="fp1" />
      );

      const countdown = container.querySelector(".countdown-container");
      expect(countdown?.className).toContain("animate-countdownPulse");
    });

    it("does not apply pulse animation when more than 24 hours away", () => {
      // Session in 2 days
      const targetDate = new Date("2026-03-17T10:00:00Z").toISOString();

      const { container } = render(
        <RaceCountdown targetDate={targetDate} sessionType="fp1" />
      );

      const countdown = container.querySelector(".countdown-container");
      expect(countdown?.className).not.toContain("animate-countdownPulse");
    });
  });

  describe("Date and time display", () => {
    it("shows formatted date and time", () => {
      const targetDate = new Date("2026-03-17T14:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="race" />);

      const timer = screen.getByRole("timer");
      expect(timer).toBeInTheDocument();

      // Verify that date/time strings are actually rendered (not just the timer role)
      // The date should contain "Mar" (month) and "17" (day)
      expect(timer.textContent).toMatch(/Mar/i);
      expect(timer.textContent).toMatch(/17/);
    });
  });

  describe("Progress bar", () => {
    it("shows progress bar when within 7 days", () => {
      // Session in 3 days
      const targetDate = new Date("2026-03-18T10:00:00Z").toISOString();

      const { container } = render(
        <RaceCountdown targetDate={targetDate} sessionType="race" />
      );

      // Progress bar should be present
      const progressBar = container.querySelector(".bg-accent");
      expect(progressBar).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has role='timer' and aria-live='polite'", () => {
      const targetDate = new Date("2026-03-17T14:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="race" />);

      const timer = screen.getByRole("timer");
      expect(timer).toHaveAttribute("aria-live", "polite");
    });

    it("has descriptive aria-label", () => {
      const targetDate = new Date("2026-03-17T15:30:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="race" />);

      const timer = screen.getByRole("timer");
      expect(timer).toHaveAttribute(
        "aria-label",
        expect.stringContaining("RACE STARTS IN")
      );
    });
  });

  describe("Session type formatting", () => {
    it("replaces underscores with spaces in session type", () => {
      const targetDate = new Date("2026-03-17T14:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} sessionType="sprint_qualifying" />);

      expect(screen.getByText("SPRINT QUALIFYING STARTS IN")).toBeInTheDocument();
    });

    it("defaults to 'RACE STARTS IN' when no session type", () => {
      const targetDate = new Date("2026-03-17T14:00:00Z").toISOString();

      render(<RaceCountdown targetDate={targetDate} />);

      expect(screen.getByText("RACE STARTS IN")).toBeInTheDocument();
    });
  });
});
