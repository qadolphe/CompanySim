export type VehicleType = "ICE" | "HYBRID" | "EV";

export type Scenario = "baseline" | "trump";

export interface MacroState {
  ev_tax_credit: number;
  gas_price_per_gallon: number;
  emissions_penalty_per_unit: number;
  cafe_ev_mandate_pct: number;
  charging_infrastructure_index: number;

  legacy_capital: number;
  legacy_revenue: number;
  legacy_net_income: number;
  legacy_fcf: number;
  legacy_ev_cogs_pct: number;
  legacy_gross_margin_pct: number;

  startup_capital: number;
  startup_revenue: number;
  startup_net_income: number;
  startup_fcf: number;
  startup_is_bankrupt: boolean;
  startup_ev_cogs_pct: number;
}

export interface SimulationEvent {
  year: number;
  category: "policy" | "corporate";
  severity: "info" | "warning" | "critical";
  label: string;
  detail: string;
}

export interface ConsumerSnapshot {
  id: number;
  income: number;
  vehicle: VehicleType;
  just_bought: boolean;
}

export interface Tick {
  year: number;
  macro_state: MacroState;
  events: SimulationEvent[];
  micro_state: ConsumerSnapshot[];
}

export type SimulationData = Tick[];

export type ScenarioDatasets = Record<Scenario, SimulationData>;
