import type { Scenario } from "../types";

interface ControlBarProps {
  year: number;
  step: number;
  totalSteps: number;
  scenario: Scenario;
  onScenarioChange: (s: Scenario) => void;
  onPrev: () => void;
  onNext: () => void;
}

export default function ControlBar({
  year,
  step,
  totalSteps,
  scenario,
  onScenarioChange,
  onPrev,
  onNext,
}: ControlBarProps) {
  return (
    <div className="flex items-center justify-between gap-6 px-6 py-4 bg-white/80 backdrop-blur border-t border-gray-200">
      {/* Scenario toggle */}
      <div className="flex rounded-lg overflow-hidden border border-gray-300">
        <button
          onClick={() => onScenarioChange("baseline")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            scenario === "baseline"
              ? "bg-blue-600 text-white"
              : "bg-white text-gray-600 hover:bg-gray-100"
          }`}
        >
          IRA / CAFE Baseline
        </button>
        <button
          onClick={() => onScenarioChange("trump")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            scenario === "trump"
              ? "bg-rose-600 text-white"
              : "bg-white text-gray-600 hover:bg-gray-100"
          }`}
        >
          Policy Rollback
        </button>
      </div>

      {/* Step controls */}
      <div className="flex items-center gap-6">
        <button
          onClick={onPrev}
          disabled={step === 0}
          className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-30 text-gray-700 font-medium transition-colors"
        >
          ← Prev
        </button>

        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold text-gray-900 font-mono tabular-nums w-20 text-center">
            {year}
          </span>
          <div className="flex gap-1.5">
            {Array.from({ length: totalSteps }, (_, i) => (
              <div
                key={i}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${
                  i <= step ? "bg-emerald-500" : "bg-gray-300"
                }`}
              />
            ))}
          </div>
        </div>

        <button
          onClick={onNext}
          disabled={step === totalSteps - 1}
          className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 disabled:opacity-30 text-gray-700 font-medium transition-colors"
        >
          Next →
        </button>
      </div>

      {/* Spacer to balance layout */}
      <div className="w-[220px]" />
    </div>
  );
}
