"""
Strategy engine — the decision-making heuristics for the producer.

Contains the production reallocation, R&D allocation, and
Innovator's Dilemma strategy logic, separated from the producer
agent to keep it testable.
"""

from __future__ import annotations

from domain.environment.models import PolicySnapshot
from domain.market.models import SalesRecord
from simulation.config import (
    CAPACITY_SHIFT_MAX_UNITS,
    CAPACITY_SHIFT_PCT,
    RETOOLING_COST_PER_UNIT,
    R_AND_D_EV_FLOOR_PCT,
)


class StrategyEngine:
    """
    Reactive strategy heuristics for production and R&D allocation.

    V1 is deliberately simple — reactive, not predictive.
    This keeps the model debuggable and the logic transparent.
    """

    # ── Production Reallocation ──

    @staticmethod
    def compute_capacity_shifts(
        sales: dict[str, SalesRecord],
        capacity: dict[str, int],
        env: PolicySnapshot | None = None,
    ) -> dict[str, int]:
        """
        Determine how many units to shift for each product type.

                Uses a soft score per drivetrain instead of hard thresholds.
                Score combines:
                    - Demand signal from sell-through
                    - Policy pressure (penalties + mandate) when env is provided
                Shifts remain zero-sum after normalization.

        Returns a dict of {product_type: shift_amount} where
        positive = increase, negative = decrease.
        """
        total_capacity = sum(capacity.values())
        max_shift = min(
            CAPACITY_SHIFT_MAX_UNITS,
            int(total_capacity * CAPACITY_SHIFT_PCT),
        )

        if total_capacity <= 0:
            return {ptype: 0 for ptype in capacity}

        scores: dict[str, float] = {}
        for ptype, cap in capacity.items():
            if cap == 0:
                scores[ptype] = -10.0
                continue

            record = sales.get(ptype)
            units_sold = record.units_sold if record else 0
            demand_ratio = units_sold / cap

            # Center around replacement sell-through and clip extremes.
            demand_signal = max(-1.0, min(1.0, (demand_ratio - 0.65) / 0.35))
            policy_signal = StrategyEngine._policy_capacity_bias(ptype, env)
            scores[ptype] = demand_signal + policy_signal

        weighted_mean = sum(scores[p] * capacity[p] for p in capacity) / total_capacity
        raw_shifts: dict[str, int] = {}
        for ptype, score in scores.items():
            centered = score - weighted_mean
            raw = int(round(centered * 0.65 * max_shift))

            # Preserve directional intent for meaningful but modest score differences.
            if raw == 0 and abs(centered) > 0.20:
                raw = 1 if centered > 0 else -1

            raw_shifts[ptype] = max(-max_shift, min(max_shift, raw))

        return StrategyEngine._enforce_zero_sum(raw_shifts, capacity)

    @staticmethod
    def _policy_capacity_bias(ptype: str, env: PolicySnapshot | None) -> float:
        """Soft policy-aware bias that nudges capacity toward compliance."""
        if env is None:
            return 0.0

        penalty_pressure = min(1.0, max(0.0, env.emissions_penalty_per_unit / 5_000.0))
        mandate_pressure = min(1.0, max(0.0, env.cafe_ev_mandate_pct / 0.67))
        transition_pressure = 0.65 * penalty_pressure + 0.35 * mandate_pressure

        if ptype == "ICE":
            return -0.90 * transition_pressure
        if ptype == "HYBRID":
            return 0.45 * transition_pressure + 0.10 * penalty_pressure
        if ptype == "EV":
            return 0.55 * transition_pressure + 0.15 * mandate_pressure
        return 0.0

    @staticmethod
    def _enforce_zero_sum(
        shifts: dict[str, int],
        capacity: dict[str, int],
    ) -> dict[str, int]:
        """
        Adjust shifts to be zero-sum while respecting capacity floors.
        No product type's capacity can go below 0.
        """
        net = sum(shifts.values())
        if net == 0:
            return shifts

        adjusted = dict(shifts)
        if net > 0:
            increasers = [k for k, v in adjusted.items() if v > 0]
            if increasers:
                reduction_each = net // len(increasers)
                remainder = net % len(increasers)
                for i, k in enumerate(increasers):
                    adjusted[k] -= reduction_each + (1 if i < remainder else 0)
        else:
            decreasers = [k for k, v in adjusted.items() if v < 0]
            if decreasers:
                increase_each = abs(net) // len(decreasers)
                remainder = abs(net) % len(decreasers)
                for i, k in enumerate(decreasers):
                    adjusted[k] += increase_each + (1 if i < remainder else 0)

        for ptype in adjusted:
            if capacity[ptype] + adjusted[ptype] < 0:
                adjusted[ptype] = -capacity[ptype]

        return adjusted

    @staticmethod
    def compute_retooling_cost(shifts: dict[str, int]) -> float:
        """Total retooling cost for the given capacity shifts."""
        total_moved = sum(abs(v) for v in shifts.values())
        return total_moved * RETOOLING_COST_PER_UNIT

    # ── R&D Allocation ──

    @staticmethod
    def compute_r_and_d_allocation(
        r_and_d_budget: float,
        sales: dict[str, SalesRecord],
        product_types: list[str],
    ) -> dict[str, float]:
        """
        Decide how to split a provided R&D budget across product types.

        Rules:
          - EV gets at least R_AND_D_EV_FLOOR_PCT of the budget
          - Remaining split proportional to non-ICE sales
          - ICE gets no R&D (legacy, not investing in improvement)
        """
        budget = r_and_d_budget
        if budget <= 0:
            return {pt: 0.0 for pt in product_types}

        total_units = sum(
            s.units_sold for s in sales.values()
            if s.product_type != "ICE"
        )

        allocation: dict[str, float] = {}
        for pt in product_types:
            if pt == "ICE":
                allocation[pt] = 0.0
            elif pt == "EV":
                if total_units > 0:
                    ev_sold = sales.get("EV")
                    ev_share = (ev_sold.units_sold / total_units) if ev_sold else 0
                    allocation[pt] = budget * max(R_AND_D_EV_FLOOR_PCT, ev_share)
                else:
                    allocation[pt] = budget * R_AND_D_EV_FLOOR_PCT
            else:
                allocation[pt] = 0.0

        ev_amount = allocation.get("EV", 0.0)
        remaining = budget - ev_amount
        other_types = [pt for pt in product_types if pt not in ("ICE", "EV")]
        if other_types:
            per_type = remaining / len(other_types)
            for pt in other_types:
                allocation[pt] = per_type

        return allocation

    # ── Innovator's Dilemma Logic ──

    @staticmethod
    def compute_dilemma_ev_tilt(
        ev_cogs_pct: float,
        cafe_mandate_pct: float,
        consecutive_negative_fcf: int,
    ) -> float:
        """
        Return an EV R&D tilt multiplier (1.0 = normal, up to 2.0 = aggressive).

        Captures the dilemma: the legacy firm must over-invest in EV R&D
        when regulatory pressure rises or when EV COGS nears breakeven,
        but pulls back into survival mode during financial distress.

        Rules:
          - CAFE mandate pressure: tilt += 0.5 * (mandate / 0.67)
          - COGS proximity to breakeven: tilt += 0.5 * max(0, 1 - ev_cogs_pct)
          - Emergency mode: 2+ consecutive negative FCF years → tilt *= 0.5
        """
        mandate_push = 0.5 * min(1.0, cafe_mandate_pct / 0.67)
        cogs_pull = 0.5 * max(0.0, 1.0 - ev_cogs_pct)

        tilt = 1.0 + mandate_push + cogs_pull
        if consecutive_negative_fcf >= 2:
            tilt *= 0.5

        return min(2.0, tilt)
