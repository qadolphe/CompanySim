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

        # ── Sales by type ──
        total_units = 0
        total_revenue = 0.0
        for ptype, record in sales.items():
            row[f"sales_{ptype.lower()}_units"] = record.units_sold
            row[f"sales_{ptype.lower()}_revenue"] = record.revenue
            total_units += record.units_sold
            total_revenue += record.revenue
        row["sales_total_units"] = total_units
        row["sales_total_revenue"] = total_revenue

        # ── Market Share ──
        if total_units > 0:
            for ptype, record in sales.items():
                row[f"share_{ptype.lower()}_pct"] = (
                    record.units_sold / total_units
                )
        else:
            for ptype in sales:
                row[f"share_{ptype.lower()}_pct"] = 0.0

        # ── Producer State ──
        row["capital"] = producer_state.get("capital", 0)
        row["total_capacity"] = producer_state.get("total_capacity", 0)

        capacity = producer_state.get("capacity", {})
        for ptype, cap in capacity.items():
            row[f"capacity_{ptype.lower()}"] = cap

        msrp_reductions = producer_state.get("msrp_reductions", {})
        for ptype, red in msrp_reductions.items():
            row[f"msrp_reduction_{ptype.lower()}_pct"] = red

        range_bonuses = producer_state.get("range_bonuses", {})
        for ptype, bonus in range_bonuses.items():
            row[f"range_bonus_{ptype.lower()}_mi"] = bonus

        financials = producer_state.get("financials", {})
        for key, val in financials.items():
            row[f"fin_{key}"] = val

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
