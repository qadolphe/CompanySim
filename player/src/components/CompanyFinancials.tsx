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
  onExplain?: (key: string, title: string) => void;
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
  onExplain,
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
        <KPITile
          label="EV COGS Ratio"
          value={`${evCogs.toFixed(2)}x`}
          color="text-amber-600"
          infoAction={
            onExplain
              ? () => onExplain("ev_cogs_curve", "EV COGS Curve")
              : undefined
          }
        />
      </div>

      {/* Revenue chart */}
      <ChartCard
        title={`${companyLabel} — Revenue`}
        infoAction={
          onExplain
            ? () => onExplain("r_and_d_policy", "R&D Policy")
            : undefined
        }
      >
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

function KPITile(
  {
    label,
    value,
    color,
    infoAction,
  }: { label: string; value: string; color: string; infoAction?: () => void },
) {
  return (
    <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-200">
      <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wide">
        <span>{label}</span>
        {infoAction && <InfoButton onClick={infoAction} />}
      </div>
      <div className={`text-lg font-bold font-mono tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function ChartCard(
  {
    title,
    children,
    infoAction,
  }: { title: string; children: React.ReactNode; infoAction?: () => void },
) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
          {title}
        </h3>
        {infoAction && <InfoButton onClick={infoAction} />}
      </div>
      {children}
    </div>
  );
}

function InfoButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-gray-300 text-[10px] font-bold text-gray-500 hover:bg-gray-100"
      aria-label="Open methodology explainer"
      title="Open methodology explainer"
    >
      i
    </button>
  );
}

const tooltipStyle = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  fontSize: 12,
};
