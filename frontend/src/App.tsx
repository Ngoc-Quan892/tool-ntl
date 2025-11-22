import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastContainer } from "./components/Toast";
import Layout from "./components/Layout";
import PredictionBox from "./components/PredictionBox";
import RoadmapGrid from "./components/RoadmapGrid";
import ControlPanel from "./components/ControlPanel";
import StatsPanel from "./components/StatsPanel";
import HistoryTable from "./components/HistoryTable";
import SimulationModal from "./components/SimulationModal";
import { usePredictionData } from "./hooks/usePredictor";
import { useWebSocket } from "./hooks/useWebSocket";
import { useUIStore, useToastStore } from "./stores";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

function AppContent() {
  const { 
    predictionQuery, 
    statsQuery, 
    roadmapQuery, 
    addResult, 
    reset,
    isAddingResult,
    isResetting,
  } = usePredictionData();
  const { simulationModalOpen, setSimulationModalOpen } = useUIStore();
  useWebSocket();

  return (
    <div className="space-y-6">
      <PredictionBox 
        prediction={predictionQuery.data} 
        loading={predictionQuery.isLoading || predictionQuery.isError} 
      />

      <ControlPanel
        onAdd={(value) => addResult(value)}
        onReset={() => reset()}
        onOpenSimulation={() => setSimulationModalOpen(true)}
        isAddingResult={isAddingResult}
        isResetting={isResetting}
      />

      <RoadmapGrid data={roadmapQuery.data} />

      <StatsPanel stats={statsQuery.data} />

      <HistoryTable />

      <SimulationModal open={simulationModalOpen} onClose={() => setSimulationModalOpen(false)} />
    </div>
  );
}

function App() {
  const { toasts, removeToast } = useToastStore();

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Layout>
          <AppContent />
        </Layout>
        <ToastContainer toasts={toasts} onClose={removeToast} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
