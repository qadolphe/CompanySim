"""
Unit tests for the StrategyEngine — production reallocation and R&D logic.
"""

import pytest

from domain.environment.models import PolicySnapshot
from domain.producer.strategy import StrategyEngine
from domain.market.models import SalesRecord


# ═══════════════════════════════════════════════════════════════════
# Production Reallocation
# ═══════════════════════════════════════════════════════════════════

class TestCapacityShifts:

    def test_high_demand_increases_capacity(self) -> None:
        """When a product sells out (>90%) and another underperforms (<50%),
        capacity should shift from the underperformer to the sellout."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=180, revenue=5_760_000),  # 30% — underperforming
            "EV": SalesRecord("EV", "EV", units_sold=148, revenue=6_216_000),  # 98.7% sellthrough
        }
        capacity = {"ICE": 600, "EV": 150}
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity)
        assert shifts["EV"] > 0, "EV should get more capacity when selling out"

    def test_low_demand_decreases_capacity(self) -> None:
        """When demand is <50% of capacity, capacity should decrease."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=200, revenue=6_400_000),  # 33%
            "EV": SalesRecord("EV", "EV", units_sold=148, revenue=6_216_000),  # 98.7%
        }
        capacity = {"ICE": 600, "EV": 150}
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity)
        assert shifts["ICE"] < 0, "ICE should lose capacity when underperforming"

    def test_shifts_are_zero_sum(self) -> None:
        """Net capacity change must be zero."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=550, revenue=17_600_000),
            "HYBRID": SalesRecord("HYBRID", "HYBRID", units_sold=100, revenue=3_500_000),
            "EV": SalesRecord("EV", "EV", units_sold=148, revenue=6_216_000),
        }
        capacity = {"ICE": 600, "HYBRID": 250, "EV": 150}
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity)
        assert sum(shifts.values()) == 0, f"Shifts not zero-sum: {shifts}"

    def test_moderate_demand_no_shift(self) -> None:
        """Demand between 50-90% should trigger no shift."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=420, revenue=13_440_000),  # 70%
            "EV": SalesRecord("EV", "EV", units_sold=105, revenue=4_410_000),  # 70%
        }
        capacity = {"ICE": 600, "EV": 150}
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity)
        assert shifts["ICE"] == 0
        assert shifts["EV"] == 0

    def test_capacity_never_goes_negative(self) -> None:
        """Even with large decreases, capacity should not go below 0."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=5, revenue=160_000),  # ~1%
            "EV": SalesRecord("EV", "EV", units_sold=48, revenue=2_016_000),  # 96%
        }
        capacity = {"ICE": 600, "EV": 50}
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity)
        for ptype in capacity:
            assert capacity[ptype] + shifts[ptype] >= 0, (
                f"{ptype} capacity would go negative: "
                f"{capacity[ptype]} + {shifts[ptype]}"
            )

    def test_high_penalty_shifts_away_from_ice_even_with_demand(self) -> None:
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=590, revenue=18_880_000),
            "HYBRID": SalesRecord("HYBRID", "HYBRID", units_sold=120, revenue=4_200_000),
            "EV": SalesRecord("EV", "EV", units_sold=130, revenue=5_460_000),
        }
        capacity = {"ICE": 600, "HYBRID": 250, "EV": 150}
        high_penalty_env = PolicySnapshot(
            year=2031,
            ev_tax_credit=0,
            gas_price_per_gallon=4.2,
            electricity_price_per_kwh=0.18,
            interest_rate=0.06,
            emissions_penalty_per_unit=3_500,
            cafe_ev_mandate_pct=0.50,
            charging_infrastructure_index=0.6,
        )
        shifts = StrategyEngine.compute_capacity_shifts(sales, capacity, high_penalty_env)
        assert shifts["ICE"] < 0
        assert shifts["HYBRID"] + shifts["EV"] > 0


class TestRetoolingCost:

    def test_retooling_cost_calculation(self) -> None:
        from simulation.config import RETOOLING_COST_PER_UNIT
        shifts = {"ICE": -1000, "EV": 1000}
        cost = StrategyEngine.compute_retooling_cost(shifts)
        assert cost == 2000 * RETOOLING_COST_PER_UNIT  # both sides count

    def test_no_shift_no_cost(self) -> None:
        shifts = {"ICE": 0, "EV": 0}
        assert StrategyEngine.compute_retooling_cost(shifts) == 0.0


# ═══════════════════════════════════════════════════════════════════
# R&D Allocation
# ═══════════════════════════════════════════════════════════════════

class TestRAndDAllocation:

    def test_ice_gets_no_r_and_d(self) -> None:
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=500, revenue=16_000_000),
            "HYBRID": SalesRecord("HYBRID", "HYBRID", units_sold=200, revenue=7_000_000),
            "EV": SalesRecord("EV", "EV", units_sold=100, revenue=4_200_000),
        }
        alloc = StrategyEngine.compute_r_and_d_allocation(
            r_and_d_budget=80_000_000, sales=sales, product_types=["ICE", "HYBRID", "EV"]
        )
        assert alloc["ICE"] == 0.0

    def test_ev_gets_floor_minimum(self) -> None:
        """EV should get at least 30% of R&D budget."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=500, revenue=16_000_000),
            "HYBRID": SalesRecord("HYBRID", "HYBRID", units_sold=200, revenue=7_000_000),
            "EV": SalesRecord("EV", "EV", units_sold=10, revenue=420_000),  # tiny EV sales
        }
        alloc = StrategyEngine.compute_r_and_d_allocation(
            r_and_d_budget=80_000_000, sales=sales, product_types=["ICE", "HYBRID", "EV"]
        )
        budget = 80_000_000
        assert alloc["EV"] >= budget * 0.30 - 1  # allow tiny fp error

    def test_total_r_and_d_equals_budget(self) -> None:
        """All R&D allocation should sum to the provided budget."""
        sales = {
            "ICE": SalesRecord("ICE", "ICE", units_sold=500, revenue=16_000_000),
            "HYBRID": SalesRecord("HYBRID", "HYBRID", units_sold=200, revenue=7_000_000),
            "EV": SalesRecord("EV", "EV", units_sold=100, revenue=4_200_000),
        }
        budget = 80_000_000
        alloc = StrategyEngine.compute_r_and_d_allocation(
            r_and_d_budget=budget, sales=sales, product_types=["ICE", "HYBRID", "EV"]
        )
        assert sum(alloc.values()) == pytest.approx(budget, rel=0.01)

    def test_zero_budget_zero_r_and_d(self) -> None:
        sales = {"ICE": SalesRecord("ICE", "ICE", 0, 0)}
        alloc = StrategyEngine.compute_r_and_d_allocation(
            r_and_d_budget=0, sales=sales, product_types=["ICE"]
        )
        assert alloc["ICE"] == 0.0
