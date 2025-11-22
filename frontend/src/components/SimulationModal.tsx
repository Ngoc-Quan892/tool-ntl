import { useEffect, useState } from "react";
import { getSimulationStatus, runSimulation } from "../lib/api";
import { SimulationStatus } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

export const SimulationModal = ({ open, onClose }: Props) => {
  const [shoes, setShoes] = useState(1000);
  const [hands, setHands] = useState(80);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let timer: number | undefined;
    if (status && status.status === "running") {
      timer = window.setInterval(async () => {
        const update = await getSimulationStatus(status.task_id);
        setStatus(update);
      }, 1500);
    }
    return () => {
      if (timer) window.clearInterval(timer);
    };
  }, [status]);

  if (!open) return null;

  const handleStart = async () => {
    setLoading(true);
    try {
      const response = await runSimulation({ shoes, hands_per_shoe: hands });
      setStatus(response);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-casino-card rounded-2xl p-6 w-full max-w-lg space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-xl font-semibold">🎲 Simulation</h3>
          <button onClick={onClose} className="text-slate-300">�?/button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <label className="flex flex-col text-sm">
            S�?shoe
            <input
              type="number"
              value={shoes}
              min={1}
              max={10000}
              onChange={(e) => setShoes(Number(e.target.value))}
              className="mt-1 rounded-xl bg-slate-800 border border-slate-600 px-4 py-2 text-white"
            />
          </label>
          <label className="flex flex-col text-sm">
            Tay mỗi shoe
            <input
              type="number"
              value={hands}
              min={1}
              max={100}
              onChange={(e) => setHands(Number(e.target.value))}
              className="mt-1 rounded-xl bg-slate-800 border border-slate-600 px-4 py-2 text-white"
            />
          </label>
        </div>
        <button
          className="w-full bg-casino-gold text-slate-900 font-semibold py-3 rounded-xl hover:opacity-90"
          onClick={handleStart}
          disabled={loading}
        >
          {loading ? "Đang chạy..." : "Bắt đầu mô phỏng"}
        </button>
        {status && (
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-700 text-sm space-y-2">
            <div>Trạng thái: {status.status}</div>
            <div>
              Tiến đ�? {status.completed_shoes}/{status.total_shoes}
            </div>
            {status.results && (
              <pre className="bg-slate-800 rounded-lg p-3 text-xs overflow-auto max-h-40">
                {JSON.stringify(status.results, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationModal;
