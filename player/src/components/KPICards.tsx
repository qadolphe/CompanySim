import type { MacroState } from "../types";
import { formatCurrency, formatNumber } from "../utils/format";

interface KPICardsProps {
  year: number;
  macro: MacroState;
}

interface Tile {
  label: string;
  value: string;
  color: string;
}

export default function KPICards({ year, macro }: KPICardsProps) {
  const tiles: Tile[] = [
    { label: "Year", value: String(year), color: "text-gray-900" },
    {
      label: "Legacy Capital",
      value: formatCurrency(macro.legacy_capital),
      color: "text-blue-600",
    },
    {
      label: "Startup Capital",
      value: formatCurrency(macro.startup_capital),
      color: "text-emerald-600",
    },
    {
      label: "EV Tax Credit",
      value: formatCurrency(macro.ev_tax_credit),
      color: "text-violet-600",
    },
    {
      label: "Gas Price",
      value: `$${formatNumber(macro.gas_price_per_gallon, 2)}/gal`,
      color: "text-amber-600",
    },
    {
      label: "Emissions Penalty",
      value: formatCurrency(macro.emissions_penalty_per_unit),
      color: "text-rose-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {tiles.map((t) => (
        <div
          key={t.label}
          className="bg-white rounded-xl p-3 shadow-sm border border-gray-200"
        >
          <div className="text-xs text-gray-500 uppercase tracking-wide">
            {t.label}
          </div>
          <div className={`text-xl font-bold font-mono tabular-nums ${t.color}`}>
            {t.value}
          </div>
        </div>
      ))}
    </div>
  );
}
