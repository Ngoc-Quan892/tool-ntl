import { useMemo } from "react";
import { motion } from "framer-motion";
import { RoadmapMatrix } from "../types";

interface Props {
  data?: RoadmapMatrix;
  highlightPatterns?: boolean;
}

const colorFor = (value?: string | null) => {
  if (!value) return "bg-transparent border-slate-800";
  if (value === "B") return "bg-banker border-banker-light";
  if (value === "P") return "bg-player border-player-light";
  return "bg-tie border-tie";
};

const getStreakLength = (data: RoadmapMatrix, row: number, col: number): number => {
  if (!data[row]?.[col]?.value) return 0;
  const value = data[row][col]?.value;
  let streak = 1;
  
  // Check horizontal streak
  for (let c = col - 1; c >= 0; c--) {
    if (data[row]?.[c]?.value === value) {
      streak++;
    } else {
      break;
    }
  }
  
  return streak;
};

export const BigRoad = ({ data, highlightPatterns = true }: Props) => {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    // Find max columns
    const maxCols = Math.max(...data.map(row => row.length));
    
    // Pad rows to same length
    const padded = data.map(row => {
      const paddedRow = [...row];
      while (paddedRow.length < maxCols) {
        paddedRow.push(null);
      }
      return paddedRow;
    });
    
    return padded;
  }, [data]);

  const columns = processedData?.[0]?.length ?? 0;
  const rows = processedData?.length ?? 0;

  return (
    <div className="bg-casino-card border border-casino-border rounded-2xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📊</span>
          <div>
            <h3 className="text-lg font-semibold text-casino-gold">Big Road</h3>
            <p className="text-xs text-slate-400">Main betting pattern</p>
          </div>
        </div>
        {data && (
          <div className="text-xs text-slate-400">
            {rows} rows × {columns} cols
          </div>
        )}
      </div>
      
      <div className="overflow-auto max-h-[500px]">
        {processedData && columns > 0 ? (
          <div className="inline-block">
            <div 
              className="inline-grid gap-1" 
              style={{ gridTemplateColumns: `repeat(${columns}, minmax(24px, 24px))` }}
            >
              {processedData.map((row, rowIndex) =>
                row.map((cell, colIndex) => {
                  const streak = highlightPatterns ? getStreakLength(processedData, rowIndex, colIndex) : 0;
                  const isStreak = streak >= 3;
                  
                  return (
                    <motion.div
                      key={`${rowIndex}-${colIndex}`}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: (rowIndex + colIndex) * 0.01 }}
                      className={`
                        w-6 h-6 border-2 rounded-sm flex items-center justify-center text-xs font-bold
                        ${colorFor(cell?.value)}
                        ${isStreak ? 'ring-2 ring-yellow-400 ring-opacity-50' : ''}
                        ${cell?.value ? 'shadow-md' : ''}
                        transition-all duration-200
                      `}
                      title={cell?.value ? `${cell.value}${cell.ties ? ` (${cell.ties} ties)` : ''}` : ''}
                    >
                      {cell?.value === "T" ? (
                        <span className="text-[8px]">T</span>
                      ) : cell?.value ? (
                        <span className="text-[10px]">{cell.value}</span>
                      ) : null}
                      {cell?.ties && cell.ties > 0 && (
                        <span className="absolute -top-1 -right-1 bg-tie text-white text-[8px] rounded-full w-3 h-3 flex items-center justify-center">
                          {cell.ties}
                        </span>
                      )}
                    </motion.div>
                  );
                })
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-500 text-sm">
            <div className="text-4xl mb-2">📊</div>
            <div>Chưa có dữ liệu</div>
            <div className="text-xs mt-1">Dữ liệu sẽ hiển thị khi có kết quả</div>
          </div>
        )}
      </div>
      
      {data && data.length > 0 && (
        <div className="mt-4 flex gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-banker rounded-sm"></div>
            <span>Banker</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-player rounded-sm"></div>
            <span>Player</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-tie rounded-sm"></div>
            <span>Tie</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default BigRoad;
