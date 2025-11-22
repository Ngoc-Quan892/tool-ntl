import { useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { Stats } from "../types";
import { TrendingUp, TrendingDown, Activity, Target } from "lucide-react";
import { motion } from "framer-motion";

interface Props {
  stats?: Stats;
}

const COLORS = {
  banker: "#3B82F6",
  player: "#EF4444",
  tie: "#10B981",
};

export const StatsPanel = ({ stats }: Props) => {
  const chartData = useMemo(() => {
    if (!stats) return [];

    return [
      { name: "Banker", value: stats.banker_wins, fill: COLORS.banker },
      { name: "Player", value: stats.player_wins, fill: COLORS.player },
      { name: "Tie", value: stats.ties, fill: COLORS.tie },
    ];
  }, [stats]);

  const percentageData = useMemo(() => {
    if (!stats || stats.total_hands === 0) return [];

    const noTieTotal = stats.banker_wins + stats.player_wins;
    const bankerPct = noTieTotal > 0 ? (stats.banker_wins / noTieTotal) * 100 : 0;
    const playerPct = noTieTotal > 0 ? (stats.player_wins / noTieTotal) * 100 : 0;
    const tiePct = (stats.ties / stats.total_hands) * 100;

    return [
      { name: "Banker", value: bankerPct, fill: COLORS.banker },
      { name: "Player", value: playerPct, fill: COLORS.player },
      { name: "Tie", value: tiePct, fill: COLORS.tie },
    ];
  }, [stats]);

  const trendData = useMemo(() => {
    if (!stats) return [];
    
    // Simulated trend data (in real app, this would come from history)
    return [
      { period: "1-10", banker: stats.banker_wins * 0.3, player: stats.player_wins * 0.3 },
      { period: "11-20", banker: stats.banker_wins * 0.5, player: stats.player_wins * 0.5 },
      { period: "21-30", banker: stats.banker_wins * 0.7, player: stats.player_wins * 0.7 },
      { period: "31+", banker: stats.banker_wins, player: stats.player_wins },
    ];
  }, [stats]);

  if (!stats) {
    return (
      <div className="bg-casino-card border border-casino-border rounded-2xl p-8 text-center">
        <div className="animate-pulse">
          <div className="text-4xl mb-4">📈</div>
          <div className="text-slate-400">Đang tải thống kê...</div>
        </div>
      </div>
    );
  }

  const bankerPct = stats.total_hands > 0 
    ? ((stats.banker_wins / (stats.banker_wins + stats.player_wins || 1)) * 100).toFixed(1)
    : "0.0";
  const playerPct = stats.total_hands > 0
    ? ((stats.player_wins / (stats.banker_wins + stats.player_wins || 1)) * 100).toFixed(1)
    : "0.0";

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-casino-card border border-casino-border rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Total Hands</span>
            <Activity size={18} className="text-casino-gold" />
          </div>
          <div className="text-2xl font-bold">{stats.total_hands}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-casino-card border border-casino-border rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Accuracy</span>
            <Target size={18} className="text-casino-gold" />
          </div>
          <div className="text-2xl font-bold">{stats.accuracy.toFixed(1)}%</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-casino-card border border-casino-border rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Banker %</span>
            <TrendingUp size={18} className="text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400">{bankerPct}%</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-casino-card border border-casino-border rounded-xl p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">Player %</span>
            <TrendingDown size={18} className="text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400">{playerPct}%</div>
        </motion.div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-casino-gold mb-4">Win Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  background: "#1E293B",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-casino-gold mb-4">Percentage Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={percentageData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {percentageData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1E293B",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Line Chart - Trends */}
        <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-casino-gold mb-4">Win Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="period" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  background: "#1E293B",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="banker"
                stroke={COLORS.banker}
                strokeWidth={2}
                name="Banker"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="player"
                stroke={COLORS.player}
                strokeWidth={2}
                name="Player"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Details */}
        <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-casino-gold mb-4">Detailed Statistics</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Current Shoe</span>
              <span className="font-semibold text-casino-gold">#{stats.current_shoe}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Banker Wins</span>
              <span className="font-semibold text-blue-400">{stats.banker_wins}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Player Wins</span>
              <span className="font-semibold text-red-400">{stats.player_wins}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Ties</span>
              <span className="font-semibold text-green-400">{stats.ties}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Banker Streak</span>
              <span className="font-semibold">{stats.banker_streak}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
              <span className="text-slate-300">Player Streak</span>
              <span className="font-semibold">{stats.player_streak}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPanel;
