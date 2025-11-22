import { create } from "zustand";
import { Result, Stats } from "../types";

interface GameState {
  currentShoeId: string | null;
  history: Result[];
  stats: Stats | null;
  isPlaying: boolean;
  setCurrentShoeId: (shoeId: string | null) => void;
  addToHistory: (result: Result) => void;
  setStats: (stats: Stats | null) => void;
  setIsPlaying: (isPlaying: boolean) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  currentShoeId: null,
  history: [],
  stats: null,
  isPlaying: false,
  setCurrentShoeId: (shoeId) => set({ currentShoeId: shoeId }),
  addToHistory: (result) => set((state) => ({ history: [...state.history, result] })),
  setStats: (stats) => set({ stats }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  reset: () => set({
    currentShoeId: null,
    history: [],
    stats: null,
    isPlaying: false,
  }),
}));

