import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  simulationModalOpen: boolean;
  activeTab: string;
  setSidebarOpen: (open: boolean) => void;
  setSimulationModalOpen: (open: boolean) => void;
  setActiveTab: (tab: string) => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  simulationModalOpen: false,
  activeTab: "prediction",
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSimulationModalOpen: (open) => set({ simulationModalOpen: open }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));

