export interface MacroState {
  legacy_capital: number;
  startup_capital: number;
  ev_tax_credit: number;
  gas_price_per_gallon: number;
  emissions_penalty_per_unit: number;
}

export interface ConsumerSnapshot {
  id: number;
  income: number;
  vehicle: "ICE" | "HYBRID" | "EV";
  just_bought: boolean;
}

export interface Tick {
  year: number;
  macro_state: MacroState;
  micro_state: ConsumerSnapshot[];
}

export type SimulationData = Tick[];
