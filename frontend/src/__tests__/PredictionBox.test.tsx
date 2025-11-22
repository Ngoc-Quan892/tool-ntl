import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PredictionBox } from "../components/PredictionBox";

const mockPrediction = {
  recommend: "B" as const,
  confidence: 80,
  edge_pct: 0.12,
  pattern: "Dragon",
  true_count: 2.5,
  next_suggested: "B" as const,
  timestamp: new Date().toISOString(),
};

describe("PredictionBox", () => {
  it("shows prediction info", () => {
    render(<PredictionBox prediction={mockPrediction} />);
    expect(screen.getByText(/BANKER/i)).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });
});
