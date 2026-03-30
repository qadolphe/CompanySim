import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Tick, VehicleType } from "../types";

interface SalesVsFleetComparisonProps {
  tick: Tick;
}

const VEHICLE_COLORS: Record<VehicleType, string> = {
  ICE: "#fb7185",
  HYBRID: "#60a5fa",
  EV: "#34d399",
};

function pct(value: number): string {
  return `${value.toFixed(1)}%`;
}

function computeFleetMix(tick: Tick): Record<VehicleType, number> {
  const macro = tick.macro_state;
  if (
    typeof macro.fleet_ice_pct === "number"
    && typeof macro.fleet_hybrid_pct === "number"
    && typeof macro.fleet_ev_pct === "number"
  ) {
    return {
      ICE: macro.fleet_ice_pct * 100,
      HYBRID: macro.fleet_hybrid_pct * 100,
      EV: macro.fleet_ev_pct * 100,
    };
  }

  // Backward-compatible fallback for older payloads.
  const counts: Record<VehicleType, number> = { ICE: 0, HYBRID: 0, EV: 0 };
  for (const c of tick.micro_state) counts[c.vehicle] += 1;
  const total = tick.micro_state.length || 1;
  return {
    ICE: (counts.ICE / total) * 100,
    HYBRID: (counts.HYBRID / total) * 100,
    EV: (counts.EV / total) * 100,
  };
}

function BreakdownCard({
  title,
  values,
}: {
  title: string;
  values: Record<VehicleType, number>;
}) {
  const data = [
    { vehicle: "ICE", value: values.ICE },
    { vehicle: "HYBRID", value: values.HYBRID },
    { vehicle: "EV", value: values.EV },
  ];

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="vehicle"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            stroke="#d1d5db"
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            stroke="#d1d5db"
            width={44}
          />
          <Tooltip
            formatter={(value) => pct(Number(value))}
            contentStyle={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.vehicle}
                fill={VEHICLE_COLORS[entry.vehicle as VehicleType]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs font-mono text-gray-600 tabular-nums">
        <span>ICE {pct(values.ICE)}</span>
        <span>HYB {pct(values.HYBRID)}</span>
        <span>EV {pct(values.EV)}</span>
      </div>
    </div>
  );
}

export default function SalesVsFleetComparison({ tick }: SalesVsFleetComparisonProps) {
  const fleetMix = computeFleetMix(tick);

  return (
    <div className="grid grid-cols-1 gap-4">
      <BreakdownCard title="Total Fleet Mix" values={fleetMix} />
    </div>
  );
}
