import { useState, useEffect, useCallback, useRef } from "react";
import type { MethodologyMap, Scenario, ScenarioDatasets } from "../types";
import { loadAllScenarios } from "../data/loadData";
import ControlBar from "./ControlBar";
import DashboardTabs from "./DashboardTabs";
import MicroSwarm from "./MicroSwarm";

export default function SimulationPlayer() {
  const [datasets, setDatasets] = useState<ScenarioDatasets | null>(null);
  const [methodology, setMethodology] = useState<Record<Scenario, MethodologyMap> | null>(null);
  const [scenario, setScenario] = useState<Scenario>("baseline");
  const [step, setStep] = useState(0);
  const prevStepRef = useRef(0);

  useEffect(() => {
    loadAllScenarios().then(({ datasets, methodology }) => {
      setDatasets(datasets);
      setMethodology(methodology);
    });
  }, []);

  const data = datasets ? datasets[scenario] : null;
  const maxStep = data ? data.length - 1 : 0;

  // Clamp step when switching scenarios
  const switchScenario = useCallback(
    (s: Scenario) => {
      setScenario(s);
      if (datasets) {
        const newMax = datasets[s].length - 1;
        setStep((prev) => Math.min(prev, newMax));
      }
    },
    [datasets],
  );

  const prev = useCallback(() => {
    setStep((s) => {
      prevStepRef.current = s;
      return Math.max(s - 1, 0);
    });
  }, []);

  const next = useCallback(() => {
    setStep((s) => {
      prevStepRef.current = s;
      return Math.min(s + 1, maxStep);
    });
  }, [maxStep]);

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
  const prevTick = step > 0 ? data[step - 1] : null;
  const chartData = data.slice(0, step + 1);

  return (
    <div className="flex flex-col h-screen bg-gray-100 text-gray-900">
      <div className="flex-1 grid grid-cols-[440px_1fr] min-h-0">
        <DashboardTabs
          tick={tick}
          chartData={chartData}
          methodology={methodology?.[scenario] ?? {}}
        />
        <MicroSwarm tick={tick} prevTick={prevTick} />
      </div>
      <ControlBar
        year={tick.year}
        step={step}
        totalSteps={data.length}
        scenario={scenario}
        onScenarioChange={switchScenario}
        onPrev={prev}
        onNext={next}
      />
    </div>
  );
}
