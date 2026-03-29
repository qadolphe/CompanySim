import type { SimulationData } from "../types";

export async function loadSimulationData(): Promise<SimulationData> {
  const res = await fetch("/simulation_micro.json");
  if (!res.ok) throw new Error(`Failed to load simulation data: ${res.status}`);
  return res.json();
}
