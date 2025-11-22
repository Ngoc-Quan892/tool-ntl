export const WS_URL =
  typeof window !== "undefined" ? `${window.location.origin.replace(/^http/, "ws")}/ws` : "ws://localhost:8000/ws";
export const BUTTONS = [
  { label: "Banker", value: "B", color: "bg-banker" },
  { label: "Player", value: "P", color: "bg-player" },
  { label: "Tie", value: "T", color: "bg-tie" }
];
