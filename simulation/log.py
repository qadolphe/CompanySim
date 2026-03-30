"""
Simulation log — structured data collection backing a Pandas DataFrame.
"""

from __future__ import annotations

import json
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
        self._micro_records: list[dict[str, Any]] = []
        self._methodology: dict[str, str] = {
            "ev_cogs_curve": (
                "# EV COGS Curve\n"
                "EV COGS starts above parity and declines with two forces:\n"
                "- Battery cost decline toward 2030 (BloombergNEF-style trend proxy).\n"
                "- Wright's Law learning: each cumulative production doubling lowers costs.\n"
                "\n"
                "Assumption: battery-pack parity near $100/kWh around 2028, with continued\n"
                "decline toward ~$80/kWh by 2030 in baseline conditions."
            ),
            "consumer_replacement_rate": (
                "# Consumer Replacement Rate\n"
                "Market entry is probabilistic and income-weighted, not a flat cycle.\n"
                "- Top-income households trend toward 3-4 year replacement behavior.\n"
                "- Lower-income households trend toward 8-12 years.\n"
                "- Small random noise avoids synchronized demand spikes."
            ),
            "legacy_capex_burden": (
                "# Legacy CapEx Burden\n"
                "Capacity shifts require retooling spend per unit of moved capacity.\n"
                "This captures plant conversion burden and delayed payback in transition years.\n"
                "\n"
                "Assumption: retooling cost calibrated to roughly $10k-$15k per unit capacity."
            ),
            "r_and_d_policy": (
                "# R&D Policy\n"
                "R&D spend is based on revenue with a minimum annual floor.\n"
                "This prevents runaway cash burn when capital is high but sales are weak,\n"
                "while preserving sustained innovation pressure."
            ),
        }

    def set_methodology(self, methodology: dict[str, str]) -> None:
        """Override default methodology text for output payloads."""
        self._methodology = dict(methodology)

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
            row[f"{prefix}_vc_funding_raised"] = state.get("vc_funding_raised", 0)
            row[f"{prefix}_total_dilution"] = state.get("total_dilution", 0)

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

    def record_micro(
        self,
        year: int,
        macro_state: dict[str, Any],
        consumers: list[dict[str, Any]],
        events: list[dict[str, Any]] | None = None,
    ) -> None:
        """Record per-consumer micro state for one tick."""
        self._micro_records.append({
            "year": year,
            "macro_state": macro_state,
            "events": events or [],
            "micro_state": consumers,
        })

    def to_micro_json(self, path: str) -> None:
        """Write micro-state and methodology to a compact JSON file."""
        for tick in self._micro_records:
            for c in tick.get("micro_state", []):
                if "income" in c:
                    c["income"] = int(c["income"])
        payload = {
            "methodology": self._methodology,
            "ticks": self._micro_records,
        }
        with open(path, "w") as f:
            json.dump(payload, f, separators=(",", ":"))
