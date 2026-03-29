interface ControlBarProps {
  year: number;
  step: number;
  totalSteps: number;
  onPrev: () => void;
  onNext: () => void;
}

export default function ControlBar({
  year,
  step,
  totalSteps,
  onPrev,
  onNext,
}: ControlBarProps) {
  return (
    <div className="flex items-center justify-center gap-6 py-4 bg-white/80 backdrop-blur border-t border-gray-200">
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
  );
}
