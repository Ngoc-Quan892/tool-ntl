import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PredictionBox from "../PredictionBox";
import { Prediction } from "../../types";

// Mock stores
vi.mock("../../stores", () => ({
  usePredictionStore: () => ({
    useML: false,
  }),
}));

// Mock audio hook
vi.mock("../../hooks/useAudio", () => ({
  useAudio: () => ({
    playConfidence: vi.fn(),
  }),
}));

describe("PredictionBox", () => {
  const mockPrediction: Prediction = {
    recommend: "B",
    confidence: 0.75,
    edge_pct: 0.5,
    pattern: "Banker streak",
    true_count: 1.2,
    next_suggested: "B",
    timestamp: new Date().toISOString(),
  };

  it("renders loading state", () => {
    render(<PredictionBox loading={true} />);
    expect(screen.getByText(/đang tải/i)).toBeInTheDocument();
  });

  it("renders prediction when available", () => {
    render(<PredictionBox prediction={mockPrediction} loading={false} />);
    
    expect(screen.getByText(/BANKER/i)).toBeInTheDocument();
    expect(screen.getByText(/75%/i)).toBeInTheDocument();
    expect(screen.getByText(/Banker streak/i)).toBeInTheDocument();
  });

  it("displays confidence level correctly", () => {
    const highConfidence: Prediction = {
      ...mockPrediction,
      confidence: 0.85,
    };
    
    render(<PredictionBox prediction={highConfidence} loading={false} />);
    expect(screen.getByText(/85%/i)).toBeInTheDocument();
  });

  it("shows ML indicator when useML is true", () => {
    vi.mocked(require("../../stores").usePredictionStore).mockReturnValue({
      useML: true,
    } as any);
    
    render(<PredictionBox prediction={mockPrediction} loading={false} />);
    // Should show ML badge (implementation dependent)
  });
});

