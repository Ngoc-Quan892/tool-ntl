export const formatResult = (value: string) => {
  switch (value) {
    case "B":
      return "Banker";
    case "P":
      return "Player";
    case "T":
      return "Tie";
    case "R":
      return "Red";
    case "L":
      return "Blue";
    default:
      return value;
  }
};

export const confidenceColor = (confidence: number) => {
  if (confidence >= 85) return "text-banker-light";
  if (confidence >= 70) return "text-player-light";
  return "text-white";
};

export const formatTimestamp = (value: string) => new Date(value).toLocaleTimeString();
