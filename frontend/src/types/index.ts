export type Result = "B" | "P" | "T";

export interface Prediction {
  recommend: "B" | "P";
  confidence: number;
  edge_pct: number;
  pattern: string;
  true_count: number;
  next_suggested: "B" | "P";
  timestamp: string;
}

export interface Stats {
  total_hands: number;
  banker_wins: number;
  player_wins: number;
  ties: number;
  banker_streak: number;
  player_streak: number;
  current_shoe: number;
  accuracy: number;
}

export type RoadCell = {
  value: string;
  ties?: number;
} | null;

export type RoadmapMatrix = RoadCell[][];

export interface RoadmapPayload {
  big_road: RoadmapMatrix;
  big_eye_boy: RoadmapMatrix;
  small_road: RoadmapMatrix;
  cockroach_pig: RoadmapMatrix;
}

export interface HistoryItem {
  id: number;
  result: Result;
  prediction: Prediction;
  shoe_number: number;
  hand_number: number;
  timestamp: string;
}

export interface HistoryResponse {
  total: number;
  items: HistoryItem[];
}

export interface SimulationStatus {
  task_id: string;
  status: string;
  total_shoes: number;
  completed_shoes: number;
  results?: Record<string, unknown> | null;
}
