import { create } from "zustand";
import { Prediction } from "../types";

interface PredictionState {
  prediction: Prediction | null;
  isLoading: boolean;
  error: string | null;
  useML: boolean;
  setPrediction: (prediction: Prediction | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setUseML: (useML: boolean) => void;
  reset: () => void;
}

export const usePredictionStore = create<PredictionState>((set) => ({
  prediction: null,
  isLoading: false,
  error: null,
  useML: false,
  setPrediction: (prediction) => set({ prediction, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  setUseML: (useML) => set({ useML }),
  reset: () => set({ prediction: null, error: null, isLoading: false }),
}));

