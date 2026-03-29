"""
CompanySim — Auto Industry Policy Simulator

Entry point: runs the full simulation and generates all output.
"""

from simulation.engine import SimulationEngine
from simulation.visualize import SimulationVisualizer


def main() -> None:
    print("=" * 60)
    print("  Auto Industry Policy Simulator")
    print("  2024 — 2035 | 1,000 Consumers | 1 Legacy Automaker")
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
    if "capital" in results.columns:
        for year, row in results.iterrows():
            cap = row["capital"] / 1e9
            print(f"  {year}: ${cap:.2f}B")
    print()

    # Generate charts
    print("Generating charts...")
    viz = SimulationVisualizer(results)
    viz.export_all("output")

    print()
    print("Done! Check the output/ directory for charts and data.")


if __name__ == "__main__":
    main()
