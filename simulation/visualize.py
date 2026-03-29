"""
Visualization module — produces publication-quality charts from
the simulation log DataFrame.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd


# ── Style Configuration ──
sns.set_theme(style="darkgrid")
PALETTE = {
    "ICE": "#E74C3C",      # Red
    "HYBRID": "#F39C12",   # Amber
    "EV": "#2ECC71",       # Green
}
FIG_SIZE = (12, 6)
DPI = 150


class SimulationVisualizer:
    """
    Produces all charts from the simulation log DataFrame.

    Each plot method creates and saves a figure. The export_all
    method runs all of them and saves to an output directory.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def plot_market_share(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Stacked area chart: ICE vs Hybrid vs EV share over time."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        share_cols = [c for c in self.df.columns if c.startswith("share_")]
        labels = [c.replace("share_", "").replace("_pct", "").upper()
                  for c in share_cols]
        colors = [PALETTE.get(l, "#95A5A6") for l in labels]

        ax.stackplot(
            self.df.index,
            [self.df[c] * 100 for c in share_cols],
            labels=labels,
            colors=colors,
            alpha=0.85,
        )
        ax.set_title("Market Share by Drivetrain", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Market Share (%)")
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left")

        return fig or ax.get_figure()

    def plot_automaker_financials(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Line chart: Capital over time."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        capital_billions = self.df["capital"] / 1e9
        ax.plot(self.df.index, capital_billions, color="#3498DB",
                linewidth=2.5, marker="o", markersize=5)
        ax.fill_between(self.df.index, capital_billions, alpha=0.15,
                        color="#3498DB")
        ax.set_title("Automaker Capital Over Time", fontsize=14,
                      fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Capital ($B)")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"${x:.1f}B")
        )

        return fig or ax.get_figure()

    def plot_vehicle_pricing(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Line chart: Effective MSRP by drivetrain (with R&D reductions)."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        from simulation.config import DEFAULT_VEHICLE_CATALOG
        for dt in ["ICE", "HYBRID", "EV"]:
            base = DEFAULT_VEHICLE_CATALOG[dt]["msrp"]
            col = f"msrp_reduction_{dt.lower()}_pct"
            if col in self.df.columns:
                prices = base * (1 - self.df[col])
                ax.plot(self.df.index, prices / 1000, label=dt,
                        color=PALETTE[dt], linewidth=2, marker="s",
                        markersize=4)

        ax.set_title("Vehicle MSRP Over Time (R&D Effects)",
                      fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("MSRP ($K)")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"${x:.0f}K")
        )
        ax.legend()

        return fig or ax.get_figure()

    def plot_production_capacity(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Stacked bar chart: Production allocation by drivetrain."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        cap_cols = [f"capacity_{dt.lower()}" for dt in ["ICE", "HYBRID", "EV"]
                    if f"capacity_{dt.lower()}" in self.df.columns]
        labels = [c.replace("capacity_", "").upper() for c in cap_cols]
        colors = [PALETTE.get(l, "#95A5A6") for l in labels]

        bottom = pd.Series(0, index=self.df.index, dtype=float)
        for col, label, color in zip(cap_cols, labels, colors):
            ax.bar(self.df.index, self.df[col], bottom=bottom,
                   label=label, color=color, alpha=0.85, width=0.6)
            bottom += self.df[col]

        ax.set_title("Production Capacity Allocation",
                      fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Units")
        ax.legend()

        return fig or ax.get_figure()

    def plot_policy_environment(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Multi-axis chart: Gas price, EV credit, emissions penalty."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        ax.plot(self.df.index, self.df["gas_price_per_gallon"],
                color="#E74C3C", linewidth=2, label="Gas Price ($/gal)",
                marker="o", markersize=4)
        ax.set_xlabel("Year")
        ax.set_ylabel("Gas Price ($/gal)", color="#E74C3C")
        ax.tick_params(axis="y", labelcolor="#E74C3C")

        ax2 = ax.twinx()
        ax2.plot(self.df.index, self.df["ev_tax_credit"],
                 color="#2ECC71", linewidth=2, linestyle="--",
                 label="EV Tax Credit ($)", marker="s", markersize=4)
        ax2.set_ylabel("EV Tax Credit ($)", color="#2ECC71")
        ax2.tick_params(axis="y", labelcolor="#2ECC71")

        # Combined legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="center right")

        ax.set_title("Policy Environment Over Time",
                      fontsize=14, fontweight="bold")

        return fig or ax.get_figure()

    def plot_sales_volume(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Grouped bar chart: Units sold by drivetrain per year."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        sales_cols = [f"sales_{dt.lower()}_units" for dt in ["ICE", "HYBRID", "EV"]
                      if f"sales_{dt.lower()}_units" in self.df.columns]
        labels = [c.replace("sales_", "").replace("_units", "").upper()
                  for c in sales_cols]

        x = range(len(self.df.index))
        width = 0.25
        for i, (col, label) in enumerate(zip(sales_cols, labels)):
            offset = (i - 1) * width
            ax.bar([xi + offset for xi in x], self.df[col],
                   width=width, label=label, color=PALETTE.get(label, "#95A5A6"),
                   alpha=0.85)

        ax.set_title("Sales Volume by Drivetrain",
                      fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Units Sold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(self.df.index)
        ax.legend()

        return fig or ax.get_figure()

    def plot_consumer_activity(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Line chart: Consumers shopping vs. buying."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        if "consumers_shopping" in self.df.columns:
            ax.plot(self.df.index, self.df["consumers_shopping"],
                    color="#9B59B6", linewidth=2, label="Shopping",
                    marker="o", markersize=5)
        if "consumers_bought" in self.df.columns:
            ax.plot(self.df.index, self.df["consumers_bought"],
                    color="#1ABC9C", linewidth=2, label="Bought",
                    marker="s", markersize=5)

        ax.set_title("Consumer Market Activity",
                      fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Consumers")
        ax.legend()

        return fig or ax.get_figure()

    def export_all(self, output_dir: str = "output") -> None:
        """Save all plots as PNGs and export raw data as CSV."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        plots = {
            "01_market_share": self.plot_market_share,
            "02_automaker_financials": self.plot_automaker_financials,
            "03_vehicle_pricing": self.plot_vehicle_pricing,
            "04_production_capacity": self.plot_production_capacity,
            "05_policy_environment": self.plot_policy_environment,
            "06_sales_volume": self.plot_sales_volume,
            "07_consumer_activity": self.plot_consumer_activity,
        }

        for name, plot_fn in plots.items():
            fig = plot_fn()
            fig.tight_layout()
            fig.savefig(
                os.path.join(output_dir, f"{name}.png"),
                dpi=DPI,
                bbox_inches="tight",
            )
            plt.close(fig)

        # Export raw data
        self.df.to_csv(os.path.join(output_dir, "simulation_results.csv"))
        print(f"Exported {len(plots)} charts and CSV to {output_dir}/")
