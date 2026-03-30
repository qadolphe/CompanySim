"""
CompanySim — Auto Industry Policy Simulator

Entry point: runs the full simulation and generates all output.

Usage:
    python run.py                     # default (baseline)
    python run.py --scenario baseline
    python run.py --scenario trump
"""

import argparse
import importlib

from simulation.config import NUM_CONSUMERS, START_YEAR, END_YEAR, Scenario
from simulation.engine import SimulationEngine
from simulation.visualize import SimulationVisualizer


def _set_scenario(name: str) -> Scenario:
    """Validate and apply the scenario toggle before anything else runs."""
    import simulation.config as cfg
    scenario = Scenario(name.lower())
    cfg.SCENARIO = scenario
    # Re-resolve policy schedules based on new scenario
    cfg.EV_TAX_CREDIT_SCHEDULE = cfg._pick(
        cfg._BASELINE_EV_TAX_CREDIT, cfg._TRUMP_EV_TAX_CREDIT
    )
    cfg.EMISSIONS_PENALTY_SCHEDULE = cfg._pick(
        cfg._BASELINE_EMISSIONS_PENALTY, cfg._TRUMP_EMISSIONS_PENALTY
    )
    cfg.CAFE_EV_MANDATE_SCHEDULE = cfg._pick(
        cfg._BASELINE_CAFE_EV_MANDATE, cfg._TRUMP_CAFE_EV_MANDATE
    )
    cfg.CHARGING_INFRASTRUCTURE_SCHEDULE = cfg._pick(
        cfg._BASELINE_CHARGING_INFRA, cfg._TRUMP_CHARGING_INFRA
    )
    return scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto Industry Policy Simulator")
    parser.add_argument(
        "--scenario",
        choices=["baseline", "trump"],
        default="baseline",
        help="Policy scenario to simulate (default: baseline)",
    )
    args = parser.parse_args()

    scenario = _set_scenario(args.scenario)
    tag = scenario.value.upper()

    print("=" * 60)
    print(f"  Auto Industry Policy Simulator — {tag} Scenario")
    print(f"  {START_YEAR} — {END_YEAR} | {NUM_CONSUMERS:,} Consumers")
    print(f"  Legacy Automaker + Pure EV Startup")
    print("=" * 60)
    print()

    # Run simulation
    print("Running simulation...")
    sim = SimulationEngine()
    results = sim.run()

    print(f"Simulation complete. {len(results)} years simulated.")
    print()

    # Print summary table
    print("── Market Share by Year ──")
    share_cols = [c for c in results.columns if c.startswith("share_")]
    if share_cols:
        share_df = (results[share_cols] * 100).round(1)
        share_df.columns = [c.replace("share_", "").replace("_pct", "").upper()
                            for c in share_cols]
        print(share_df.to_string())
    print()

    print("── Automaker Capital ──")
    cap_cols = [c for c in results.columns if c.endswith("_capital")]
    if cap_cols:
        for year, row in results.iterrows():
            parts = []
            for col in cap_cols:
                label = col.replace("_capital", "").title()
                val = row[col] / 1e9
                parts.append(f"{label}: ${val:.2f}B")
            print(f"  {year}: {' | '.join(parts)}")
    print()

    # Generate charts
    print("Generating charts...")
    viz = SimulationVisualizer(results)
    viz.export_all("output")

    print()
    print(f"Done! [{tag}] Check the output/ directory for charts and data.")


if __name__ == "__main__":
    main()
