import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { Tick, SimulationEvent } from "../types";
import { formatCurrency } from "../utils/format";

type CompanyPrefix = "legacy" | "startup";

interface CompanyFinancialsProps {
  company: CompanyPrefix;
  companyLabel: string;
  tick: Tick;
  chartData: Tick[];
  showEvents: boolean;
}

interface ChartPoint {
  year: number;
  revenue: number;
  netIncome: number;
  fcf: number;
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#ef4444",
  warning: "#f59e0b",
  info: "#3b82f6",
};

function formatYAxis(value: number): string {
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
  if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value}`;
}

function getField(macro: Tick["macro_state"], company: CompanyPrefix, field: string): number {
  return (macro as unknown as Record<string, number>)[`${company}_${field}`] ?? 0;
}

export default function CompanyFinancials({
  company,
  companyLabel,
  tick,
  chartData,
  showEvents,
}: CompanyFinancialsProps) {
  const macro = tick.macro_state;

  // Current KPIs
  const capital = getField(macro, company, "capital");
  const revenue = getField(macro, company, "revenue");
  const netIncome = getField(macro, company, "net_income");
  const fcf = getField(macro, company, "fcf");
  const grossMargin = company === "legacy" ? macro.legacy_gross_margin_pct : null;
  const evCogs = getField(macro, company, "ev_cogs_pct");

  // Chart data
  const points: ChartPoint[] = chartData.map((t) => ({
    year: t.year,
    revenue: getField(t.macro_state, company, "revenue"),
    netIncome: getField(t.macro_state, company, "net_income"),
    fcf: getField(t.macro_state, company, "fcf"),
  }));

  // Collect policy events for annotations
  const policyEvents: SimulationEvent[] = [];
  if (showEvents) {
    for (const t of chartData) {
      for (const ev of t.events) {
        if (ev.category === "policy") {
          policyEvents.push(ev);
        }
      }
    }
  }

  const isLegacy = company === "legacy";

  return (
    <div className="space-y-4">
      {/* KPI tiles */}
      <div className="grid grid-cols-2 gap-3">
        <KPITile label="Capital" value={formatCurrency(capital)} color={capital < 0 ? "text-red-600" : "text-gray-900"} />
        <KPITile label="Revenue" value={formatCurrency(revenue)} color="text-blue-600" />
        <KPITile label="Net Income" value={formatCurrency(netIncome)} color={netIncome < 0 ? "text-red-600" : "text-emerald-600"} />
        <KPITile label="Free Cash Flow" value={formatCurrency(fcf)} color={fcf < 0 ? "text-red-600" : "text-emerald-600"} />
        {grossMargin !== null && (
          <KPITile label="Gross Margin" value={`${(grossMargin * 100).toFixed(1)}%`} color="text-violet-600" />
        )}
        <KPITile label="EV COGS Ratio" value={`${evCogs.toFixed(2)}x`} color="text-amber-600" />
      </div>

      {/* Revenue chart */}
      <ChartCard title={`${companyLabel} — Revenue`}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" />
            <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" width={65} />
            <Tooltip formatter={(val) => formatYAxis(Number(val))} contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="revenue" name="Revenue" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 3.5 }} animationDuration={400} />
            {policyEvents.map((ev, i) => (
              <ReferenceLine
                key={`rev-${ev.year}-${i}`}
                x={ev.year}
                stroke={SEVERITY_COLOR[ev.severity] ?? "#6b7280"}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: ev.label, position: "top", fontSize: 9, fill: SEVERITY_COLOR[ev.severity] }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Net Income chart */}
      <ChartCard title={`${companyLabel} — Net Income`}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" />
            <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" width={65} />
            <Tooltip formatter={(val) => formatYAxis(Number(val))} contentStyle={tooltipStyle} />
            <ReferenceLine y={0} stroke="#d1d5db" strokeWidth={1} />
            <Line type="monotone" dataKey="netIncome" name="Net Income" stroke={isLegacy ? "#ef4444" : "#10b981"} strokeWidth={2.5} dot={{ r: 3.5 }} animationDuration={400} />
            {policyEvents.map((ev, i) => (
              <ReferenceLine
                key={`ni-${ev.year}-${i}`}
                x={ev.year}
                stroke={SEVERITY_COLOR[ev.severity] ?? "#6b7280"}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: ev.label, position: "top", fontSize: 9, fill: SEVERITY_COLOR[ev.severity] }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* FCF chart */}
      <ChartCard title={`${companyLabel} — Free Cash Flow`}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" />
            <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 11, fill: "#6b7280" }} stroke="#d1d5db" width={65} />
            <Tooltip formatter={(val) => formatYAxis(Number(val))} contentStyle={tooltipStyle} />
            <ReferenceLine y={0} stroke="#d1d5db" strokeWidth={1} />
            <Line type="monotone" dataKey="fcf" name="Free Cash Flow" stroke="#8b5cf6" strokeWidth={2.5} dot={{ r: 3.5 }} animationDuration={400} />
            {policyEvents.map((ev, i) => (
              <ReferenceLine
                key={`fcf-${ev.year}-${i}`}
                x={ev.year}
                stroke={SEVERITY_COLOR[ev.severity] ?? "#6b7280"}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: ev.label, position: "top", fontSize: 9, fill: SEVERITY_COLOR[ev.severity] }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────

function KPITile({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-200">
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-lg font-bold font-mono tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
        {title}
      </h3>
      {children}
    </div>
  );
}

const tooltipStyle = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  fontSize: 12,
};
