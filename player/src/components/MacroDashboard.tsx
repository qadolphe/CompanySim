import type { Tick } from "../types";
import KPICards from "./KPICards";
import MacroChart from "./MacroChart";

interface MacroDashboardProps {
  tick: Tick;
  chartData: Tick[];
}

export default function MacroDashboard({ tick, chartData }: MacroDashboardProps) {
  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto border-r border-gray-200 bg-gray-50">
      <KPICards year={tick.year} macro={tick.macro_state} />
      <MacroChart chartData={chartData} />

      {/* Vehicle mix summary */}
      <VehicleMixBar consumers={tick.micro_state} />
    </div>
  );
}

function VehicleMixBar({ consumers }: { consumers: Tick["micro_state"] }) {
  const counts = { ICE: 0, HYBRID: 0, EV: 0 };
  for (const c of consumers) counts[c.vehicle]++;
  const total = consumers.length;

  const segments: { type: string; pct: number; color: string }[] = [
    { type: "ICE", pct: (counts.ICE / total) * 100, color: "bg-rose-400" },
    { type: "HYBRID", pct: (counts.HYBRID / total) * 100, color: "bg-blue-400" },
    { type: "EV", pct: (counts.EV / total) * 100, color: "bg-emerald-400" },
  ];

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <h3 className="text-sm font-semibold text-gray-600 mb-2 uppercase tracking-wide">
        Vehicle Mix
      </h3>
      <div className="flex h-5 rounded-full overflow-hidden">
        {segments.map((s) => (
          <div
            key={s.type}
            className={`${s.color} transition-all duration-500`}
            style={{ width: `${s.pct}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-500 font-mono">
        {segments.map((s) => (
          <span key={s.type}>
            {s.type} {s.pct.toFixed(1)}%
          </span>
        ))}
      </div>
    </div>
  );
}
