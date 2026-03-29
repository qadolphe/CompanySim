import { useState, useEffect, useCallback } from "react";
import type { SimulationData } from "../types";
import { loadSimulationData } from "../data/loadData";
import ControlBar from "./ControlBar";
import MacroDashboard from "./MacroDashboard";
import MicroSwarm from "./MicroSwarm";

export default function SimulationPlayer() {
  const [data, setData] = useState<SimulationData | null>(null);
  const [step, setStep] = useState(0);

  useEffect(() => {
    loadSimulationData().then(setData);
  }, []);

  const maxStep = data ? data.length - 1 : 0;

  const prev = useCallback(() => setStep((s) => Math.max(s - 1, 0)), []);
  const next = useCallback(
    () => setStep((s) => Math.min(s + 1, maxStep)),
    [maxStep]
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev]);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100 text-gray-500">
        Loading simulation…
      </div>
    );
  }

  const tick = data[step];
  const chartData = data.slice(0, step + 1);

  return (
    <div className="flex flex-col h-screen bg-gray-100 text-gray-900">
      <div className="flex-1 grid grid-cols-[420px_1fr] min-h-0">
        <MacroDashboard tick={tick} chartData={chartData} />
        <MicroSwarm tick={tick} />
      </div>
      <ControlBar
        year={tick.year}
        step={step}
        totalSteps={data.length}
        onPrev={prev}
        onNext={next}
      />
    </div>
  );
}
