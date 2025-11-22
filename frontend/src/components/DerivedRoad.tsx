import { useMemo } from "react";
import { motion } from "framer-motion";
import { RoadmapMatrix } from "../types";

interface Props {
  title: string;
  data?: RoadmapMatrix;
  icon?: string;
  description?: string;
}

const colorFor = (value?: string | null) => {
  if (!value) return "bg-transparent border-slate-800";
  if (value === "B") return "bg-blue-600/30 border-blue-400";
  if (value === "P") return "bg-red-600/30 border-red-400";
  return "bg-green-600/30 border-green-400";
};

export const DerivedRoad = ({ title, data, icon = "📈", description }: Props) => {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    const maxCols = Math.max(...data.map(row => row.length));
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
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="text-lg font-semibold text-casino-gold">{title}</h3>
            {description && (
              <p className="text-xs text-slate-400">{description}</p>
            )}
          </div>
        </div>
        {data && (
          <div className="text-xs text-slate-400">
            {rows} × {columns}
          </div>
        )}
      </div>
      
      <div className="overflow-auto max-h-[400px]">
        {processedData && columns > 0 ? (
          <div className="inline-block">
            <div 
              className="inline-grid gap-1" 
              style={{ gridTemplateColumns: `repeat(${columns}, minmax(20px, 20px))` }}
            >
              {processedData.map((row, rowIndex) =>
                row.map((cell, colIndex) => (
                  <motion.div
                    key={`${rowIndex}-${colIndex}`}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: (rowIndex + colIndex) * 0.01 }}
                    className={`
                      w-5 h-5 border rounded-sm flex items-center justify-center text-[8px] font-bold
                      ${colorFor(cell?.value)}
                      ${cell?.value ? 'shadow-sm' : ''}
                      transition-all duration-200
                    `}
                    title={cell?.value || ''}
                  >
                    {cell?.value || ''}
                  </motion.div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-sm">
            <div className="text-3xl mb-2">{icon}</div>
            <div>Chưa có dữ liệu</div>
          </div>
        )}
      </div>
    </div>
  );
};
