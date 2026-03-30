import { useState } from "react";
import type { MethodologyMap, Tick } from "../types";
import KPICards from "./KPICards";
import MacroChart from "./MacroChart";
import CompanyFinancials from "./CompanyFinancials";
import ExplainerModal from "./ExplainerModal";
import SalesVsFleetComparison from "./SalesVsFleetComparison";

type Tab = "overview" | "legacy" | "startup";

interface DashboardTabsProps {
  tick: Tick;
  chartData: Tick[];
  methodology: MethodologyMap;
}

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Market Overview" },
  { key: "legacy", label: "Legacy Auto" },
  { key: "startup", label: "EV Startup" },
];

export default function DashboardTabs({ tick, chartData, methodology }: DashboardTabsProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [showEvents, setShowEvents] = useState(false);
  const [explainer, setExplainer] = useState<{ title: string; content: string } | null>(null);

  const openExplainer = (key: string, fallbackTitle: string) => {
    const text = methodology[key];
    if (!text) return;
    setExplainer({ title: fallbackTitle, content: text });
  };

  return (
    <div className="flex flex-col border-r border-gray-200 bg-gray-50 min-h-0">
      {/* Tab bar */}
      <div className="flex border-b border-gray-200 shrink-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide transition-colors
              ${activeTab === t.key
                ? "text-blue-600 border-b-2 border-blue-600 bg-white"
                : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Events toggle (visible on financials tabs) */}
      {activeTab !== "overview" && (
        <div className="flex items-center gap-2 px-4 pt-3 shrink-0">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={showEvents}
              onChange={(e) => setShowEvents(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-300 peer-checked:bg-blue-600 rounded-full transition-colors after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
          </label>
          <span className="text-xs text-gray-500 font-medium">Show Policy Events</span>
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === "overview" && (
          <OverviewPanel
            tick={tick}
            chartData={chartData}
            onExplain={openExplainer}
          />
        )}
        {activeTab === "legacy" && (
          <CompanyFinancials
            company="legacy"
            companyLabel="Legacy Automaker"
            tick={tick}
            chartData={chartData}
            showEvents={showEvents}
            onExplain={openExplainer}
          />
        )}
        {activeTab === "startup" && (
          <CompanyFinancials
            company="startup"
            companyLabel="EV Startup"
            tick={tick}
            chartData={chartData}
            showEvents={showEvents}
            onExplain={openExplainer}
          />
        )}
      </div>

      <ExplainerModal
        open={Boolean(explainer)}
        title={explainer?.title ?? "Methodology"}
        content={explainer?.content ?? ""}
        onClose={() => setExplainer(null)}
      />
    </div>
  );
}

// ── Overview panel (moved from MacroDashboard) ─────────────────────

function OverviewPanel(
  {
    tick,
    chartData,
    onExplain,
  }: { tick: Tick; chartData: Tick[]; onExplain: (key: string, title: string) => void },
) {
  return (
    <>
      <KPICards year={tick.year} macro={tick.macro_state} />
      <MacroChart chartData={chartData} />
      <SalesVsFleetComparison tick={tick} />

      {/* Events timeline for current tick */}
      {tick.events.length > 0 && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
              Events — {tick.year}
            </h3>
            <InfoButton onClick={() => onExplain("legacy_capex_burden", "Legacy CapEx Burden")} />
          </div>
          <div className="space-y-2">
            {tick.events.map((ev, i) => (
              <div
                key={i}
                className={`text-xs px-3 py-2 rounded-lg border ${
                  ev.severity === "critical"
                    ? "border-red-200 bg-red-50 text-red-700"
                    : ev.severity === "warning"
                      ? "border-amber-200 bg-amber-50 text-amber-700"
                      : "border-blue-200 bg-blue-50 text-blue-700"
                }`}
              >
                <div className="font-semibold">{ev.label}</div>
                <div className="opacity-80">{ev.detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
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
