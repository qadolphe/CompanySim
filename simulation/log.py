"""
Simulation log — structured data collection backing a Pandas DataFrame.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from domain.environment.models import PolicySnapshot
from domain.market.models import SalesRecord


class SimulationLog:
    """
    Collects simulation state each tick and converts to a DataFrame.

    Logs environment state, sales results, and producer state as
    flat rows for easy analysis and visualization.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(
        self,
        env: PolicySnapshot,
        sales: dict[str, SalesRecord],
        producer_state: dict,
        consumer_stats: dict | None = None,
    ) -> None:
        """
        Record one tick of simulation state.

        Args:
            env: Current environment snapshot
            sales: Sales results by product type
            producer_state: Producer agent state dict
            consumer_stats: Optional consumer population statistics
        """
        row: dict[str, Any] = {}

        # ── Environment ──
        row.update(env.to_dict())

        # ── Sales & Market Share ──
        total_units = 0
        total_revenue = 0.0
        type_units = {}
        firm_units = {}

        for off_id, record in sales.items():
            ptype = record.product_type
            firm = off_id.split("_")[0] if "_" in off_id else "unknown"

            # Raw counts per offering
            row[f"sales_{off_id.lower()}_units"] = record.units_sold
            row[f"sales_{off_id.lower()}_revenue"] = record.revenue

            # Aggregates
            total_units += record.units_sold
            total_revenue += record.revenue
            type_units[ptype] = type_units.get(ptype, 0) + record.units_sold
            firm_units[firm] = firm_units.get(firm, 0) + record.units_sold

        row["sales_total_units"] = total_units
        row["sales_total_revenue"] = total_revenue

        if total_units > 0:
            for ptype, count in type_units.items():
                row[f"share_type_{ptype.lower()}_pct"] = count / total_units
            for firm, count in firm_units.items():
                row[f"share_firm_{firm.lower()}_pct"] = count / total_units
        else:
            for ptype in type_units:
                row[f"share_type_{ptype.lower()}_pct"] = 0.0
            for firm in firm_units:
                row[f"share_firm_{firm.lower()}_pct"] = 0.0

        # ── Producer State ──
        # producer_state is now { firm_name: state_dict }
        for firm_name, state in producer_state.items():
            prefix = firm_name.lower()
            row[f"{prefix}_capital"] = state.get("capital", 0)
            row[f"{prefix}_total_capacity"] = state.get("total_capacity", 0)

            capacity = state.get("capacity", {})
            for ptype, cap in capacity.items():
                row[f"{prefix}_capacity_{ptype.lower()}"] = cap

            msrp_reductions = state.get("msrp_reductions", {})
            for ptype, red in msrp_reductions.items():
                row[f"{prefix}_msrp_reduction_{ptype.lower()}_pct"] = red

            range_bonuses = state.get("range_bonuses", {})
            for ptype, bonus in range_bonuses.items():
                row[f"{prefix}_range_bonus_{ptype.lower()}_mi"] = bonus

            financials = state.get("financials", {})
            for key, val in financials.items():
                row[f"{prefix}_fin_{key}"] = val

        # ── Consumer Stats (if provided) ──
        if consumer_stats:
            row.update(consumer_stats)

        self._records.append(row)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all recorded ticks to a DataFrame."""
        if not self._records:
            return pd.DataFrame()
        df = pd.DataFrame(self._records)
        df.set_index("year", inplace=True)
        return df

    @property
    def tick_count(self) -> int:
        return len(self._records)
