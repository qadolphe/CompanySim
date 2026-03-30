import type { SimulationData, ScenarioDatasets } from "../types";

const SCENARIO_FILES = {
  baseline: "/simulation_micro_baseline.json",
  trump: "/simulation_micro_trump.json",
} as const;

async function fetchScenario(file: string): Promise<SimulationData> {
  const res = await fetch(file);
  if (!res.ok) throw new Error(`Failed to load ${file}: ${res.status}`);
  return res.json();
}

export async function loadAllScenarios(): Promise<ScenarioDatasets> {
  const [baseline, trump] = await Promise.all([
    fetchScenario(SCENARIO_FILES.baseline),
    fetchScenario(SCENARIO_FILES.trump),
  ]);
  return { baseline, trump };
}
