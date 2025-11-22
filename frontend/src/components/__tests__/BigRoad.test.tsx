import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import BigRoad from "../BigRoad";
import { RoadmapMatrix } from "../../types";

describe("BigRoad", () => {
  const mockData: RoadmapMatrix = [
    [
      { value: "B", ties: 0 },
      { value: "P", ties: 0 },
      { value: "B", ties: 0 },
    ],
    [
      { value: "B", ties: 0 },
      { value: "P", ties: 0 },
      null,
    ],
  ];

  it("renders roadmap data", () => {
    render(<BigRoad data={mockData} />);
    expect(screen.getByText(/Big Road/i)).toBeInTheDocument();
  });

  it("renders empty state when no data", () => {
    render(<BigRoad data={undefined} />);
    expect(screen.getByText(/Chưa có dữ liệu/i)).toBeInTheDocument();
  });

  it("highlights patterns when enabled", () => {
    const streakData: RoadmapMatrix = [
      [
        { value: "B", ties: 0 },
        { value: "B", ties: 0 },
        { value: "B", ties: 0 },
      ],
    ];
    
    render(<BigRoad data={streakData} highlightPatterns={true} />);
    expect(screen.getByText(/Big Road/i)).toBeInTheDocument();
  });
});

