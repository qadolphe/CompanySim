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

from domain.consumer.models import ConsumerProfile
from domain.consumer.utility import VehicleUtilityCalculator
from domain.environment.service import EnvironmentService
from simulation.config import (
    START_YEAR,
    END_YEAR,
    CONSUMER_MULTIPLIER,
    DEFAULT_VEHICLE_CATALOG,
    EV_COGS_LEARNING_RATE,
    EV_COGS_REFERENCE_UNITS,
    GLOBAL_EV_MSRP_PASS_THROUGH,
    BATTERY_COST_INDEX_START,
)


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

        share_cols = [c for c in self.df.columns if c.startswith("share_type_")]
        labels = [c.replace("share_type_", "").replace("_pct", "").upper()
                  for c in share_cols]
        colors = [PALETTE.get(l, "#95A5A6") for l in labels]

        if share_cols:
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

    def plot_brand_market_share(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Stacked area chart: Firm market share over time."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        share_cols = [c for c in self.df.columns if c.startswith("share_firm_")]
        labels = [c.replace("share_firm_", "").replace("_pct", "").title()
                  for c in share_cols]

        if share_cols:
            ax.stackplot(
                self.df.index,
                [self.df[c] * 100 for c in share_cols],
                labels=labels,
                alpha=0.85,
            )
        ax.set_title("Market Share by Brand", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Market Share (%)")
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left")

        return fig or ax.get_figure()

    def plot_automaker_financials(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Line chart: Capital over time for all firms."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        capital_cols = [c for c in self.df.columns if c.endswith("_capital")]
        for col in capital_cols:
            firm_name = col.replace("_capital", "").title()
            capital_billions = self.df[col] / 1e9
            ax.plot(self.df.index, capital_billions,
                    linewidth=2.5, marker="o", markersize=5, label=firm_name)
            ax.fill_between(self.df.index, capital_billions, alpha=0.15)

        ax.set_title("Automaker Capital Over Time", fontsize=14,
                      fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Capital ($B)")
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"${x:.1f}B")
        )
        ax.legend()

        return fig or ax.get_figure()

    def plot_vehicle_pricing(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Line chart: Effective MSRP by drivetrain (with R&D reductions)."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        from simulation.config import DEFAULT_VEHICLE_CATALOG
        for dt in ["ICE", "HYBRID", "EV"]:
            base = DEFAULT_VEHICLE_CATALOG[dt]["msrp"]
            
            # Find all reduction columns for this drivetrain (across firms)
            dt_cols = [c for c in self.df.columns if c.endswith(f"_msrp_reduction_{dt.lower()}_pct")]
            
            if dt_cols:
                # Average the reduction across active firms producing this DT
                # Simple approximation: take the max reduction to represent the market leading price
                max_reduction = self.df[dt_cols].max(axis=1)
                prices = base * (1 - max_reduction)
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

        cap_cols = [c for c in self.df.columns if "_capacity_" in c]
        labels = [c.split("_capacity_")[-1].upper() for c in cap_cols]
        # Group by drivetrain to sum up across firms
        agg_cols = {}
        for col, label in zip(cap_cols, labels):
            if label not in agg_cols:
                agg_cols[label] = pd.Series(0.0, index=self.df.index)
            agg_cols[label] += self.df[col]

        ordered_labels = ["ICE", "HYBRID", "EV"]
        ordered_labels = [l for l in ordered_labels if l in agg_cols]
        colors = [PALETTE.get(l, "#95A5A6") for l in ordered_labels]

        bottom = pd.Series(0, index=self.df.index, dtype=float)
        for label, color in zip(ordered_labels, colors):
            series = agg_cols[label]
            ax.bar(self.df.index, series, bottom=bottom,
                   label=label, color=color, alpha=0.85, width=0.6)
            bottom += series

        ax.set_title("Total Production Capacity Allocation",
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

        drivetrain_sales = {}
        for dt in ["ICE", "HYBRID", "EV"]:
            dt_key = dt.lower()
            dt_cols = [
                c for c in self.df.columns
                if c.startswith("sales_") and c.endswith("_units")
                and c not in {"sales_total_units"}
                and c.endswith(f"_{dt_key}_units")
            ]
            if dt_cols:
                drivetrain_sales[dt] = self.df[dt_cols].sum(axis=1)

        labels = list(drivetrain_sales.keys())

        x = range(len(self.df.index))
        width = 0.25
        for i, label in enumerate(labels):
            offset = (i - 1) * width
            ax.bar([xi + offset for xi in x], drivetrain_sales[label],
                   width=width, label=label, color=PALETTE.get(label, "#95A5A6"),
                   alpha=0.85)

        ax.set_title("Sales Volume by Drivetrain",
                      fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Units Sold")
        ax.set_xticks(list(x))
        ax.set_xticklabels(self.df.index)
        if labels:
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

    def plot_wrights_law_explainer(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Explainer chart: battery curve, exogenous MSRP factor, and Wright's-law volume factor."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        years = list(range(START_YEAR, END_YEAR + 1))
        env = EnvironmentService(START_YEAR, END_YEAR)
        battery_index = []
        exogenous_msrp_factor = []

        for _ in years:
            snap = env.snapshot()
            battery_index.append(snap.battery_cost_index)
            exogenous_msrp_factor.append(snap.battery_cost_index ** GLOBAL_EV_MSRP_PASS_THROUGH)
            if not env.is_complete:
                env.tick()

        # Wright's-law component (unit scale curve)
        doubling_counts = list(range(0, 9))
        wright_factor = [(1.0 - EV_COGS_LEARNING_RATE) ** d for d in doubling_counts]

        ax.plot(years, battery_index, color="#3b82f6", linewidth=2.5, marker="o", label="Global Battery Cost Index")
        ax.plot(years, exogenous_msrp_factor, color="#16a34a", linewidth=2.5, marker="s", label="Exogenous EV MSRP Factor")
        ax.set_title("Explainer: Exogenous Battery Curve and EV MSRP Drift", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Index / Factor")
        ax.set_ylim(0.45, 1.05)

        ax2 = ax.twiny()
        ax2.set_xlim(ax.get_xlim())
        # Place Wright's-law curve as annotations at right side for readability.
        for d, factor in zip(doubling_counts, wright_factor):
            if d in (0, 2, 4, 6, 8):
                ax.text(years[-1] + 0.1, factor, f"Wright {d}x: {factor:.2f}", fontsize=8, color="#6b7280")

        ax.legend(loc="upper right")
        return fig or ax.get_figure()

    def plot_utility_penalty_explainer(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Explainer chart: EV friction over time for contrasting consumer cohorts."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        years = list(range(START_YEAR, END_YEAR + 1))
        util = VehicleUtilityCalculator()
        env = EnvironmentService(START_YEAR, END_YEAR)

        ev_offering = {
            "offering_id": "Explainer_EV",
            "product_type": "EV",
            "msrp": DEFAULT_VEHICLE_CATALOG["EV"]["msrp"],
            "mpg": None,
            "range_mi": DEFAULT_VEHICLE_CATALOG["EV"]["range_mi"],
            "annual_maintenance": DEFAULT_VEHICLE_CATALOG["EV"]["annual_maintenance"],
            "kwh_per_mile": DEFAULT_VEHICLE_CATALOG["EV"]["kwh_per_mile"],
        }

        high_income_homeowner = ConsumerProfile(
            id=90001,
            annual_income=150_000,
            annual_commute_miles=8_000,
            green_preference=0.7,
            price_sensitivity=0.2,
            is_homeowner=True,
            current_vehicle="ICE",
            years_owned=4,
        )
        lower_income_renter = ConsumerProfile(
            id=90002,
            annual_income=42_000,
            annual_commute_miles=12_000,
            green_preference=0.4,
            price_sensitivity=0.8,
            is_homeowner=False,
            current_vehicle="ICE",
            years_owned=4,
        )

        hi_penalties = []
        lo_penalties = []
        for _ in years:
            snap = env.snapshot()
            hi_pen = util._compute_range_anxiety(high_income_homeowner, ev_offering, snap) + util._compute_ownership_hassle(high_income_homeowner, snap)
            lo_pen = util._compute_range_anxiety(lower_income_renter, ev_offering, snap) + util._compute_ownership_hassle(lower_income_renter, snap)
            hi_penalties.append(hi_pen)
            lo_penalties.append(lo_pen)
            if not env.is_complete:
                env.tick()

        ax.plot(years, hi_penalties, color="#0ea5e9", linewidth=2.5, marker="o", label="High-income Homeowner EV Penalty")
        ax.plot(years, lo_penalties, color="#ef4444", linewidth=2.5, marker="s", label="Lower-income Renter EV Penalty")
        ax.fill_between(years, lo_penalties, hi_penalties, color="#fca5a5", alpha=0.15)

        ax.set_title("Explainer: EV Utility Friction by Demographic Cohort", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Penalty Magnitude (utility points)")
        ax.legend(loc="upper right")

        return fig or ax.get_figure()

    def plot_startup_valley_of_death(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Explainer chart: startup capital versus cumulative VC funding and dilution."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        if "pureevstartup_capital" in self.df.columns:
            capital = self.df["pureevstartup_capital"] / 1e9
            ax.plot(self.df.index, capital, color="#111827", linewidth=2.5, marker="o", label="Startup Capital ($B)")

        if "pureevstartup_vc_funding_raised" in self.df.columns:
            vc = self.df["pureevstartup_vc_funding_raised"] / 1e9
            ax.plot(self.df.index, vc, color="#a855f7", linewidth=2.0, linestyle="--", marker="s", label="Cumulative VC Raised ($B)")

        ax.set_title("Explainer: Startup Valley-of-Death and VC Bridge", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("$ Billions")
        ax.legend(loc="upper right")

        return fig or ax.get_figure()

    def plot_scaling_sanity_explainer(self, ax: plt.Axes | None = None) -> plt.Figure:
        """Explainer chart: verify macro sales scale tracks micro buyers with fixed multiplier."""
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=FIG_SIZE)

        if "consumers_bought" in self.df.columns and "sales_total_units" in self.df.columns:
            buyers = self.df["consumers_bought"].astype(float)
            macro_units = self.df["sales_total_units"].astype(float)
            expected_units = buyers * CONSUMER_MULTIPLIER

            ax.plot(self.df.index, macro_units, color="#1d4ed8", linewidth=2.5, marker="o", label="Macro Units Sold")
            ax.plot(self.df.index, expected_units, color="#16a34a", linewidth=2.0, linestyle="--", marker="s", label=f"Expected: buyers x {CONSUMER_MULTIPLIER:,}")

            ax2 = ax.twinx()
            safe_buyers = buyers.replace(0, pd.NA)
            observed_ratio = (macro_units / safe_buyers).fillna(0)
            ax2.plot(self.df.index, observed_ratio, color="#dc2626", linewidth=1.8, marker="^", label="Observed Scaling Ratio")
            ax2.set_ylabel("Units per Simulated Buyer", color="#dc2626")
            ax2.tick_params(axis="y", labelcolor="#dc2626")

            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        ax.set_title("Explainer: Micro-to-Macro Scaling Sanity Check", fontsize=14, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Units")

        return fig or ax.get_figure()

    def export_all(self, output_dir: str = "output") -> None:
        """Save all plots as PNGs and export raw data as CSV."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        plots = {
            "01_drivetrain_market_share": self.plot_market_share,
            "01_brand_market_share": self.plot_brand_market_share,
            "02_automaker_financials": self.plot_automaker_financials,
            "03_vehicle_pricing": self.plot_vehicle_pricing,
            "04_production_capacity": self.plot_production_capacity,
            "05_policy_environment": self.plot_policy_environment,
            "06_sales_volume": self.plot_sales_volume,
            "07_consumer_activity": self.plot_consumer_activity,
            "08_explainer_wrights_battery_curve": self.plot_wrights_law_explainer,
            "09_explainer_utility_penalty": self.plot_utility_penalty_explainer,
            "10_explainer_startup_valley_of_death": self.plot_startup_valley_of_death,
            "11_explainer_scaling_sanity": self.plot_scaling_sanity_explainer,
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
