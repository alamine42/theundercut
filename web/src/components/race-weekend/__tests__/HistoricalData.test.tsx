import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { HistoricalData } from "../HistoricalData";
import { mockHistory, mockHistoryEmpty } from "./mocks";
import type { CircuitHistoryResponse } from "../types";

// Mock TeamWithLogo component
vi.mock("@/components/ui/team-logo", () => ({
  TeamWithLogo: ({ team }: { team: string }) => <span data-testid="team-logo">{team}</span>,
}));

describe("HistoricalData", () => {
  describe("Rendering podium", () => {
    it("renders previous year's podium finishers", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      // Should show year heading
      expect(screen.getByText(/Last Year \(2025\)/)).toBeInTheDocument();

      // Should show all three podium positions (VER appears twice: winner + pole)
      expect(screen.getAllByText("VER").length).toBeGreaterThanOrEqual(1); // Winner
      expect(screen.getByText("NOR")).toBeInTheDocument(); // Second
      expect(screen.getByText("LEC")).toBeInTheDocument(); // Third
    });

    it("shows position medals with correct aria-labels", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      expect(screen.getByLabelText("1st place")).toBeInTheDocument();
      expect(screen.getByLabelText("2nd place")).toBeInTheDocument();
      expect(screen.getByLabelText("3rd place")).toBeInTheDocument();
    });

    it("shows driver names on larger screens", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      expect(screen.getByText("Max Verstappen")).toBeInTheDocument();
      expect(screen.getByText("Lando Norris")).toBeInTheDocument();
      expect(screen.getByText("Charles Leclerc")).toBeInTheDocument();
    });

    it("shows team logos", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      const teamLogos = screen.getAllByTestId("team-logo");
      expect(teamLogos.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Stats display", () => {
    it("shows pole position when available", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      expect(screen.getByText("Pole Position")).toBeInTheDocument();
      // VER appears multiple times (winner and pole)
      expect(screen.getAllByText("VER").length).toBeGreaterThanOrEqual(1);
    });

    it("shows fastest lap when available", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      expect(screen.getByText("Fastest Lap")).toBeInTheDocument();
      expect(screen.getByText(/HAM/)).toBeInTheDocument();
      expect(screen.getByText(/1:24.567/)).toBeInTheDocument();
    });
  });

  describe("Empty states", () => {
    it("returns null when no previous year data", () => {
      const { container } = render(
        <HistoricalData
          history={mockHistoryEmpty}
          circuitName="New Circuit"
        />
      );

      expect(container.firstChild).toBeNull();
    });

    it("returns null when previous year has no podium", () => {
      const emptyPodium: CircuitHistoryResponse = {
        circuit_id: "monza",
        circuit_name: "Monza",
        previous_year: {
          season: 2025,
          winner: null,
          second: null,
          third: null,
          pole: null,
          fastest_lap: null,
        },
      };

      const { container } = render(
        <HistoricalData history={emptyPodium} circuitName="Monza" />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe("Partial data", () => {
    it("renders with only winner data", () => {
      const partialHistory: CircuitHistoryResponse = {
        circuit_id: "monza",
        circuit_name: "Monza",
        previous_year: {
          season: 2025,
          winner: { driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull" },
          second: null,
          third: null,
          pole: null,
          fastest_lap: null,
        },
      };

      render(<HistoricalData history={partialHistory} circuitName="Monza" />);

      expect(screen.getByText("VER")).toBeInTheDocument();
      expect(screen.getByLabelText("1st place")).toBeInTheDocument();
    });

    it("handles missing pole and fastest lap gracefully", () => {
      const noPoleHistory: CircuitHistoryResponse = {
        circuit_id: "monza",
        circuit_name: "Monza",
        previous_year: {
          season: 2025,
          winner: { driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull" },
          second: { driver_code: "NOR", driver_name: "Lando Norris", team: "McLaren" },
          third: { driver_code: "LEC", driver_name: "Charles Leclerc", team: "Ferrari" },
          pole: null,
          fastest_lap: null,
        },
      };

      render(<HistoricalData history={noPoleHistory} circuitName="Monza" />);

      // Podium should render
      expect(screen.getByText("VER")).toBeInTheDocument();
      // Stats should not render
      expect(screen.queryByText("Pole Position")).not.toBeInTheDocument();
      expect(screen.queryByText("Fastest Lap")).not.toBeInTheDocument();
    });

    it("handles fastest lap without time", () => {
      const noTimeHistory: CircuitHistoryResponse = {
        circuit_id: "monza",
        circuit_name: "Monza",
        previous_year: {
          season: 2025,
          winner: { driver_code: "VER", driver_name: "Max Verstappen", team: "Red Bull" },
          second: null,
          third: null,
          pole: null,
          fastest_lap: { driver_code: "HAM", driver_name: "Lewis Hamilton", team: "Ferrari" },
        },
      };

      render(<HistoricalData history={noTimeHistory} circuitName="Monza" />);

      expect(screen.getByText("Fastest Lap")).toBeInTheDocument();
      // Should show driver code without time
      expect(screen.getByText("HAM")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper heading structure", () => {
      render(
        <HistoricalData
          history={mockHistory}
          circuitName="Autodromo Nazionale Monza"
        />
      );

      const heading = screen.getByRole("heading", { level: 3 });
      expect(heading).toHaveTextContent(/Last Year/);
    });
  });
});
