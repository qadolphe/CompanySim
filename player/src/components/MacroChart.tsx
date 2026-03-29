import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { Tick } from "../types";

interface MacroChartProps {
  chartData: Tick[];
}

interface ChartPoint {
  year: number;
  legacy: number;
  startup: number;
}

function formatYAxis(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

export default function MacroChart({ chartData }: MacroChartProps) {
  const points: ChartPoint[] = chartData.map((t) => ({
    year: t.year,
    legacy: t.macro_state.legacy_capital,
    startup: t.macro_state.startup_capital,
  }));

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
        Capital Over Time
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            stroke="#d1d5db"
          />
          <YAxis
            tickFormatter={formatYAxis}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            stroke="#d1d5db"
            width={60}
          />
          <Tooltip
            formatter={(val) => formatYAxis(Number(val))}
            contentStyle={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
          />
          <Line
            type="monotone"
            dataKey="legacy"
            name="Legacy Automaker"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#3b82f6" }}
            animationDuration={600}
          />
          <Line
            type="monotone"
            dataKey="startup"
            name="EV Startup"
            stroke="#10b981"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#10b981" }}
            animationDuration={600}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
