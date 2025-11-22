import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPrediction, playHand, fetchStatistics, fetchRoadmap, fetchHandHistory, triggerReset } from "../lib/api";
import { usePredictionStore, useGameStore } from "../stores";
import { useToastStore } from "../stores/toastStore";
import { Prediction, Result } from "../types";

export const usePredictionData = () => {
  const queryClient = useQueryClient();
  const { useML, setPrediction, setLoading } = usePredictionStore();
  const { currentShoeId, setStats } = useGameStore();
  const { success, error } = useToastStore();

  // Prediction query
  const predictionQuery = useQuery<Prediction>({
    queryKey: ["prediction", useML],
    queryFn: () => fetchPrediction(useML),
    refetchInterval: 5000, // Refetch every 5 seconds
    retry: 2,
    retryDelay: 1000,
    onSuccess: (data) => {
      setPrediction(data);
      setLoading(false);
    },
    onError: (err: any) => {
      setLoading(false);
      if (err?.status !== 404) {
        error(`Failed to fetch prediction: ${err?.message || "Unknown error"}`);
      }
    },
  });

  // Statistics query
  const statsQuery = useQuery({
    queryKey: ["statistics", currentShoeId],
    queryFn: () => fetchStatistics(currentShoeId || undefined),
    refetchInterval: 10000, // Refetch every 10 seconds
    retry: 2,
    onSuccess: (data) => {
      if (data) {
        setStats({
          total_hands: data.total_hands || 0,
          banker_wins: data.banker_wins || 0,
          player_wins: data.player_wins || 0,
          ties: data.ties || 0,
          banker_streak: 0,
          player_streak: 0,
          current_shoe: 1,
          accuracy: 0,
        });
      }
    },
    onError: (err: any) => {
      if (err?.status !== 404) {
        console.error("Failed to fetch statistics:", err);
      }
    },
  });

  // Roadmap query
  const roadmapQuery = useQuery({
    queryKey: ["roadmap", currentShoeId],
    queryFn: () => fetchRoadmap(),
    refetchInterval: 5000,
  });

  // History query
  const historyQuery = useQuery({
    queryKey: ["history", currentShoeId],
    queryFn: () => fetchHandHistory(currentShoeId || undefined),
    refetchInterval: 5000,
  });

  // Add result mutation
  const addResultMutation = useMutation({
    mutationFn: (result: Result) => playHand(result, currentShoeId || undefined),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["prediction"] });
      queryClient.invalidateQueries({ queryKey: ["statistics"] });
      queryClient.invalidateQueries({ queryKey: ["roadmap"] });
      queryClient.invalidateQueries({ queryKey: ["history"] });
      success(`Result added: ${result}`);
    },
    onError: (err: any) => {
      error(`Failed to add result: ${err?.message || "Unknown error"}`);
      setLoading(false);
    },
  });

  // Reset mutation
  const resetMutation = useMutation({
    mutationFn: () => triggerReset(),
    onSuccess: () => {
      queryClient.invalidateQueries();
      usePredictionStore.getState().reset();
      useGameStore.getState().reset();
      success("Game reset successfully");
    },
    onError: (err: any) => {
      error(`Failed to reset: ${err?.message || "Unknown error"}`);
    },
  });

  return {
    predictionQuery,
    statsQuery,
    roadmapQuery,
    historyQuery,
    addResult: (result: Result) => {
      setLoading(true);
      addResultMutation.mutate(result, {
        onSettled: () => {
          setLoading(false);
        },
      });
    },
    reset: () => {
      resetMutation.mutate();
    },
    isAddingResult: addResultMutation.isPending,
    isResetting: resetMutation.isPending,
  };
};
