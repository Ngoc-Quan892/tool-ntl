import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Prediction } from "../types";
import { useAudio } from "../hooks/useAudio";
import { usePredictionStore } from "../stores";
import { Brain, TrendingUp } from "lucide-react";

interface Props {
  prediction?: Prediction;
  loading?: boolean;
}

const RecommendationBadge = ({ recommend }: { recommend: "B" | "P" }) => (
  <span
    className={`text-4xl font-bold ${
      recommend === "B" ? "text-banker-light" : "text-player-light"
    }`}
  >
    {recommend === "B" ? "🏦 BANKER" : "👤 PLAYER"}
  </span>
);

export const PredictionBox = ({ prediction, loading }: Props) => {
  const { playConfidence } = useAudio();
  const { useML } = usePredictionStore();
  const lastTimestamp = useRef<string | null>(null);

  useEffect(() => {
    if (prediction && prediction.timestamp !== lastTimestamp.current) {
      lastTimestamp.current = prediction.timestamp;
      if (prediction.confidence >= 70) {
        playConfidence(prediction.confidence);
      }
    }
  }, [prediction, playConfidence]);

  const confidenceLevel =
    prediction && prediction.confidence >= 70
      ? "high"
      : prediction && prediction.confidence >= 55
      ? "medium"
      : "low";

  return (
    <motion.div
      className="bg-casino-card rounded-3xl p-8 shadow-2xl border border-casino-border"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm uppercase tracking-widest text-casino-gold flex items-center gap-2">
          🎯 Prediction
          {useML && (
            <span className="flex items-center gap-1 text-xs bg-purple-600 px-2 py-1 rounded">
              <Brain size={12} />
              ML
            </span>
          )}
        </div>
        {prediction && (
          <div className="text-xs text-slate-400">
            {new Date(prediction.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>

      {loading || !prediction ? (
        <div className="text-2xl text-casino-gold mt-6 animate-pulse">Đang tải...</div>
      ) : (
        <>
          <RecommendationBadge recommend={prediction.recommend} />
          <div className="mt-6 space-y-4">
            <div className="flex items-end gap-4">
              <div className="text-5xl font-black">
                {Math.round(prediction.confidence * 100)}%
              </div>
              <div className="flex-1 h-3 bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${
                    confidenceLevel === "high"
                      ? "bg-casino-gold"
                      : confidenceLevel === "medium"
                      ? "bg-yellow-500"
                      : "bg-slate-500"
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${prediction.confidence * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 uppercase tracking-wide">Pattern</div>
                <div className="text-lg font-semibold mt-1">{prediction.pattern}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 uppercase tracking-wide flex items-center gap-1">
                  <TrendingUp size={12} />
                  Edge
                </div>
                <div className="text-lg font-semibold mt-1">
                  {prediction.edge_pct > 0 ? "+" : ""}
                  {prediction.edge_pct.toFixed(2)}%
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4">
                <div className="text-xs text-slate-400 uppercase tracking-wide">True Count</div>
                <div className="text-lg font-semibold mt-1">
                  {prediction.true_count > 0 ? "+" : ""}
                  {prediction.true_count.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
};

export default PredictionBox;
