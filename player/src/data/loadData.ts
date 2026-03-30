import type { SimulationData } from "../types";

export async function loadSimulationData(): Promise<SimulationData> {
  const scenario = new URLSearchParams(window.location.search).get("scenario");
  const normalized = (scenario || "baseline").toLowerCase();
  const file = normalized === "trump"
    ? "/simulation_micro_trump.json"
    : "/simulation_micro_baseline.json";
  const res = await fetch(file);
  if (!res.ok) throw new Error(`Failed to load simulation data: ${res.status}`);
  return res.json();
}
