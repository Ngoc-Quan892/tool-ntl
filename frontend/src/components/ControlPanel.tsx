import { BUTTONS } from "../lib/constants";
import { useAudio } from "../hooks/useAudio";
import { useGameStore, useUIStore } from "../stores";
import { RotateCcw, Play, Settings } from "lucide-react";
import { ExportButton } from "./ExportButton";
import { LoadingSpinner } from "./LoadingSpinner";

interface Props {
  onAdd: (value: "B" | "P" | "T") => void;
  onReset: () => void;
  onOpenSimulation: () => void;
  isAddingResult?: boolean;
  isResetting?: boolean;
}

export const ControlPanel = ({ onAdd, onReset, onOpenSimulation, isAddingResult = false, isResetting = false }: Props) => {
  const { playClick, playReset } = useAudio();
  const { isPlaying, setIsPlaying } = useGameStore();
  const { setSimulationModalOpen } = useUIStore();

  return (
    <div className="bg-casino-card border border-casino-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-casino-gold">Game Controls</h2>
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              isPlaying ? "bg-green-500 animate-pulse" : "bg-slate-500"
            }`}
          />
          <span className="text-sm text-slate-400">
            {isPlaying ? "Playing" : "Idle"}
          </span>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        {BUTTONS.map((btn) => (
          <button
            key={btn.value}
            className={`${btn.color} px-6 py-4 rounded-xl text-lg font-semibold shadow-lg hover:scale-95 active:scale-90 transition-transform flex-1 min-w-[120px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed`}
            onClick={() => {
              playClick();
              setIsPlaying(true);
              onAdd(btn.value as "B" | "P" | "T");
              setTimeout(() => setIsPlaying(false), 500);
            }}
            disabled={isPlaying || isAddingResult}
          >
            {isAddingResult && btn.value === "B" ? (
              <>
                <LoadingSpinner size="sm" />
                Adding...
              </>
            ) : (
              btn.label
            )}
          </button>
        ))}
      </div>

      <div className="flex gap-4 flex-wrap pt-4 border-t border-slate-700">
        <button
          className="px-6 py-3 rounded-xl border border-slate-600 text-slate-200 hover:bg-slate-800 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={() => {
            playReset();
            onReset();
          }}
          disabled={isResetting}
        >
          {isResetting ? (
            <>
              <LoadingSpinner size="sm" />
              Resetting...
            </>
          ) : (
            <>
              <RotateCcw size={18} />
              Reset
            </>
          )}
        </button>
        <button
          className="px-6 py-3 rounded-xl border border-slate-600 text-slate-200 hover:bg-slate-800 transition-colors flex items-center gap-2"
          onClick={onOpenSimulation}
        >
          <Play size={18} />
          Simulation
        </button>
        <ExportButton format="csv" />
        <ExportButton format="json" />
        <button
          className="px-6 py-3 rounded-xl border border-slate-600 text-slate-200 hover:bg-slate-800 transition-colors flex items-center gap-2"
          onClick={() => setSimulationModalOpen(true)}
        >
          <Settings size={18} />
          Settings
        </button>
      </div>
    </div>
  );
};

export default ControlPanel;
