import axios from "axios";
import { HistoryResponse, Prediction, RoadmapPayload, SimulationStatus, Stats } from "../types";

// API v2 client
export const api = axios.create({
  baseURL: "/api/v2",
  headers: {
    "Content-Type": "application/json",
  },
});

// Legacy API v1 (fallback)
export const apiV1 = axios.create({
  baseURL: "/api",
});

// Request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "An error occurred";
    console.error("API Error:", error.response?.data || error.message);
    
    // You can add toast notification here if needed
    // For now, we'll let components handle errors individually
    
    return Promise.reject({
      ...error,
      message: errorMessage,
      status: error.response?.status,
      data: error.response?.data,
    });
  }
);

// Also add to v1 API
apiV1.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || "An error occurred";
    return Promise.reject({
      ...error,
      message: errorMessage,
      status: error.response?.status,
      data: error.response?.data,
    });
  }
);

// ==================== PREDICTIONS ====================

export const fetchPrediction = async (useML = false): Promise<Prediction> => {
  const { data } = await api.post<Prediction>("/predictions/predict", {}, {
    params: { use_ml: useML },
  });
  return data;
};

export const fetchAccuracyMetrics = async () => {
  const { data } = await api.get("/predictions/accuracy");
  return data;
};

export const fetchConfidenceScores = async () => {
  const { data } = await api.get("/predictions/confidence");
  return data;
};

// ==================== HANDS ====================

export const playHand = async (result?: "B" | "P" | "T", shoeId?: string) => {
  const { data } = await api.post("/hands/play", {
    result,
    shoe_id: shoeId,
  });
  return data;
};

export const fetchHandHistory = async (shoeId?: string, limit = 50) => {
  const { data } = await api.get<HistoryResponse>("/hands/history", {
    params: { shoe_id: shoeId, limit },
  });
  return data;
};

// ==================== SHOES ====================

export const createShoe = async (decks = 8, reshufflePoint?: number) => {
  const { data } = await api.post("/shoes/create", {
    decks,
    reshuffle_point: reshufflePoint,
  });
  return data;
};

export const fetchShoeState = async (shoeId: string) => {
  const { data } = await api.get(`/shoes/${shoeId}`);
  return data;
};

export const resetShoe = async (shoeId: string) => {
  const { data } = await api.post(`/shoes/${shoeId}/reset`);
  return data;
};

// ==================== ANALYSIS ====================

export const fetchStatistics = async (shoeId?: string) => {
  const { data } = await api.get("/analysis/statistics", {
    params: { shoe_id: shoeId },
  });
  return data;
};

export const fetchPatternAnalysis = async (shoeId?: string, limit = 100) => {
  const { data } = await api.get("/analysis/patterns", {
    params: { shoe_id: shoeId, limit },
  });
  return data;
};

export const fetchEdgeCalculation = async (shoeId?: string) => {
  const { data } = await api.get("/analysis/edge", {
    params: { shoe_id: shoeId },
  });
  return data;
};

export const analyzeShoe = async (shoeId?: string, includeNumeric = false) => {
  const { data } = await api.post("/analysis/analyze/shoe", {
    shoe_id: shoeId,
    include_numeric_data: includeNumeric,
  });
  return data;
};

// ==================== LEGACY V1 ENDPOINTS (Fallback) ====================

export const addResult = async (result: "B" | "P" | "T") => {
  const { data } = await apiV1.post("/add", { result });
  return data;
};

export const fetchStats = async () => {
  const { data } = await apiV1.get<Stats>("/stats");
  return data;
};

export const fetchRoadmap = async () => {
  const { data } = await apiV1.get<RoadmapPayload>("/roadmap");
  return data;
};

export const fetchHistory = async (limit = 50) => {
  const { data } = await apiV1.get<HistoryResponse>("/history", { params: { limit } });
  return data;
};

export const triggerReset = async () => apiV1.post("/reset");

export const runSimulation = async (payload: { shoes: number; hands_per_shoe: number }) => {
  const { data } = await apiV1.post<SimulationStatus>("/simulate", payload);
  return data;
};

export const getSimulationStatus = async (taskId: string) => {
  const { data } = await apiV1.get<SimulationStatus>(`/simulate/${taskId}`);
  return data;
};
