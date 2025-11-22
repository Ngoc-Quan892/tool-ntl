import { useQuery } from "@tanstack/react-query";
import { fetchHandHistory } from "../lib/api";
import { formatTimestamp } from "../lib/utils";
import { LoadingSpinner } from "./LoadingSpinner";
import { useGameStore } from "../stores";

export const HistoryTable = () => {
  const { currentShoeId } = useGameStore();
  const { data, isLoading, error } = useQuery({
    queryKey: ["history", currentShoeId],
    queryFn: () => fetchHandHistory(currentShoeId || undefined, 50),
    retry: 2,
  });

  return (
    <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold">📜 History</h3>
        <span className="text-sm text-slate-400">Total: {data?.total ?? 0}</span>
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-400">
          <div className="text-sm">Failed to load history</div>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          <div className="text-4xl mb-2">📜</div>
          <div>No history available</div>
        </div>
      ) : (
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-700">
                <th className="pb-2">Result</th>
                <th className="pb-2">Hand</th>
                <th className="pb-2">Prediction</th>
                <th className="pb-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id} className="border-t border-slate-800 hover:bg-slate-800/50 transition-colors">
                  <td className="py-2">
                    <span
                      className={`font-semibold ${
                        row.result === "B"
                          ? "text-blue-400"
                          : row.result === "P"
                          ? "text-red-400"
                          : "text-green-400"
                      }`}
                    >
                      {row.result}
                    </span>
                  </td>
                  <td className="py-2 text-slate-300">#{row.hand_number || "-"}</td>
                  <td className="py-2">
                    <span
                      className={`${
                        row.prediction?.recommend === "B" ? "text-blue-400" : "text-red-400"
                      }`}
                    >
                      {row.prediction?.recommend || "-"}
                    </span>
                  </td>
                  <td className="py-2 text-slate-400 text-xs">
                    {formatTimestamp(row.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default HistoryTable;
