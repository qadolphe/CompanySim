import type {
  MethodologyMap,
  Scenario,
  ScenarioBundle,
  SimulationData,
  SimulationEnvelope,
} from "../types";

const SCENARIO_FILES = {
  baseline: "/simulation_micro_baseline.json",
  trump: "/simulation_micro_trump.json",
} as const;

const EMPTY_METHODOLOGY: MethodologyMap = {
  ev_cogs_curve:
    "# EV COGS Curve\nEV COGS declines with cumulative scale (Wright's Law) and battery-cost trends toward 2030.",
  consumer_replacement_rate:
    "# Consumer Replacement Rate\nHousehold market entry is income-weighted and probabilistic rather than a flat fixed cycle.",
  legacy_capex_burden:
    "# Legacy CapEx Burden\nCapacity shifts require retooling spend per unit moved, reflecting factory conversion burden.",
  r_and_d_policy:
    "# R&D Policy\nR&D is modeled as revenue-linked spending with a minimum floor, not a flat burn on total capital.",
};

function parsePayload(payload: unknown): { ticks: SimulationData; methodology: MethodologyMap } {
  if (Array.isArray(payload)) {
    return { ticks: payload as SimulationData, methodology: EMPTY_METHODOLOGY };
  }

  const maybeEnvelope = payload as Partial<SimulationEnvelope>;
  if (Array.isArray(maybeEnvelope.ticks)) {
    return {
      ticks: maybeEnvelope.ticks,
      methodology: maybeEnvelope.methodology ?? EMPTY_METHODOLOGY,
    };
  }

  throw new Error("Invalid simulation payload shape");
}

async function fetchScenario(file: string): Promise<{ ticks: SimulationData; methodology: MethodologyMap }> {
  const res = await fetch(file);
  if (!res.ok) throw new Error(`Failed to load ${file}: ${res.status}`);
  const payload = await res.json();
  return parsePayload(payload);
}

export async function loadAllScenarios(): Promise<ScenarioBundle> {
  const [baseline, trump] = await Promise.all([
    fetchScenario(SCENARIO_FILES.baseline),
    fetchScenario(SCENARIO_FILES.trump),
  ]);
  const datasets: Record<Scenario, SimulationData> = {
    baseline: baseline.ticks,
    trump: trump.ticks,
  };
  const methodology: Record<Scenario, MethodologyMap> = {
    baseline: baseline.methodology,
    trump: trump.methodology,
  };
  return { datasets, methodology };
}
