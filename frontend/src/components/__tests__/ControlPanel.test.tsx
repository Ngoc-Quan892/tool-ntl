import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ControlPanel from "../ControlPanel";
import { useGameStore, useUIStore } from "../../stores";

// Mock stores
vi.mock("../../stores", () => ({
  useGameStore: vi.fn(),
  useUIStore: vi.fn(),
}));

// Mock audio hook
vi.mock("../../hooks/useAudio", () => ({
  useAudio: () => ({
    playClick: vi.fn(),
    playReset: vi.fn(),
  }),
}));

describe("ControlPanel", () => {
  const mockOnAdd = vi.fn();
  const mockOnReset = vi.fn();
  const mockOnOpenSimulation = vi.fn();

  beforeEach(() => {
    vi.mocked(useGameStore).mockReturnValue({
      isPlaying: false,
      setIsPlaying: vi.fn(),
    } as any);
    
    vi.mocked(useUIStore).mockReturnValue({
      setSimulationModalOpen: vi.fn(),
    } as any);
  });

  it("renders all buttons", () => {
    render(
      <ControlPanel
        onAdd={mockOnAdd}
        onReset={mockOnReset}
        onOpenSimulation={mockOnOpenSimulation}
      />
    );

    expect(screen.getByText("Banker")).toBeInTheDocument();
    expect(screen.getByText("Player")).toBeInTheDocument();
    expect(screen.getByText("Tie")).toBeInTheDocument();
    expect(screen.getByText("Reset")).toBeInTheDocument();
    expect(screen.getByText("Simulation")).toBeInTheDocument();
  });

  it("calls onAdd when button is clicked", () => {
    render(
      <ControlPanel
        onAdd={mockOnAdd}
        onReset={mockOnReset}
        onOpenSimulation={mockOnOpenSimulation}
      />
    );

    fireEvent.click(screen.getByText("Banker"));
    expect(mockOnAdd).toHaveBeenCalledWith("B");

    fireEvent.click(screen.getByText("Player"));
    expect(mockOnAdd).toHaveBeenCalledWith("P");

    fireEvent.click(screen.getByText("Tie"));
    expect(mockOnAdd).toHaveBeenCalledWith("T");
  });

  it("calls onReset when reset button is clicked", () => {
    render(
      <ControlPanel
        onAdd={mockOnAdd}
        onReset={mockOnReset}
        onOpenSimulation={mockOnOpenSimulation}
      />
    );

    fireEvent.click(screen.getByText("Reset"));
    expect(mockOnReset).toHaveBeenCalled();
  });

  it("disables buttons when isAddingResult is true", () => {
    render(
      <ControlPanel
        onAdd={mockOnAdd}
        onReset={mockOnReset}
        onOpenSimulation={mockOnOpenSimulation}
        isAddingResult={true}
      />
    );

    const bankerButton = screen.getByText("Banker").closest("button");
    expect(bankerButton).toBeDisabled();
  });
});

