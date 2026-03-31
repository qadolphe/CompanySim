"""
Unit tests for domain/economics.py — the time-varying macro curves module.

Tests verify directional behavior, monotonicity, and boundary conditions
for all pure-function economic curves.
"""

import pytest

from domain.economics import (
    get_fuel_cost,
    get_ev_battery_cost_per_kwh,
    get_material_cost_index,
    get_bom_cost,
    get_interest_rate,
    get_vehicle_depreciation_residual,
    get_legacy_tooling_per_unit,
    get_startup_tooling_per_unit,
    get_legacy_unit_cost,
    get_startup_unit_cost,
    get_annual_fuel_cost,
    get_annual_insurance,
    get_annual_maintenance,
)
from simulation.config import START_YEAR


# ═══════════════════════════════════════════════════════════════════
# Fuel Costs
# ═══════════════════════════════════════════════════════════════════

class TestFuelCost:

    def test_gasoline_increases_over_time(self) -> None:
        p1 = get_fuel_cost("gasoline", START_YEAR)
        p2 = get_fuel_cost("gasoline", START_YEAR + 5)
        assert p2 > p1

    def test_electricity_increases_over_time(self) -> None:
        p1 = get_fuel_cost("electricity", START_YEAR)
        p2 = get_fuel_cost("electricity", START_YEAR + 5)
        assert p2 > p1

    def test_gasoline_base_year_equals_config(self) -> None:
        from simulation.config import GAS_PRICE_BASE
        assert get_fuel_cost("gasoline", START_YEAR) == pytest.approx(GAS_PRICE_BASE)

    def test_electricity_base_year_equals_config(self) -> None:
        from simulation.config import ELECTRICITY_PRICE_BASE
        assert get_fuel_cost("electricity", START_YEAR) == pytest.approx(ELECTRICITY_PRICE_BASE)

    def test_unknown_fuel_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown fuel_type"):
            get_fuel_cost("hydrogen", START_YEAR)


# ═══════════════════════════════════════════════════════════════════
# Battery Cost
# ═══════════════════════════════════════════════════════════════════

class TestBatteryCost:

    def test_battery_declines_over_time(self) -> None:
        c1 = get_ev_battery_cost_per_kwh(START_YEAR)
        c2 = get_ev_battery_cost_per_kwh(START_YEAR + 6)
        assert c2 < c1

    def test_battery_has_floor(self) -> None:
        from simulation.config import BATTERY_COST_FLOOR_PER_KWH
        # Far future should approach but not go below floor
        c = get_ev_battery_cost_per_kwh(START_YEAR + 50)
        assert c >= BATTERY_COST_FLOOR_PER_KWH
        assert c < BATTERY_COST_FLOOR_PER_KWH + 1.0  # very close to floor

    def test_battery_base_year(self) -> None:
        from simulation.config import BATTERY_COST_PER_KWH_2024
        assert get_ev_battery_cost_per_kwh(START_YEAR) == pytest.approx(BATTERY_COST_PER_KWH_2024)


# ═══════════════════════════════════════════════════════════════════
# Material Cost Index
# ═══════════════════════════════════════════════════════════════════

class TestMaterialCostIndex:

    def test_base_year_is_one(self) -> None:
        assert get_material_cost_index(START_YEAR) == pytest.approx(1.0)

    def test_increases_over_time(self) -> None:
        assert get_material_cost_index(START_YEAR + 10) > 1.0


# ═══════════════════════════════════════════════════════════════════
# BOM Cost
# ═══════════════════════════════════════════════════════════════════

class TestBOMCost:

    def test_ice_bom_positive(self) -> None:
        assert get_bom_cost("ICE", START_YEAR) > 0

    def test_ev_bom_decreases_with_volume(self) -> None:
        c_low = get_bom_cost("EV", START_YEAR, cumulative_ev_units=100_000)
        c_high = get_bom_cost("EV", START_YEAR, cumulative_ev_units=1_000_000)
        assert c_high <= c_low

    def test_ev_bom_decreases_with_manufacturer_credit(self) -> None:
        c_no = get_bom_cost("EV", START_YEAR)
        c_credit = get_bom_cost("EV", START_YEAR, manufacturer_credit_per_kwh=35.0)
        assert c_credit < c_no

    def test_unknown_drivetrain_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown drivetrain"):
            get_bom_cost("DIESEL", START_YEAR)

    def test_ev_more_expensive_than_ice_in_2024(self) -> None:
        ev = get_bom_cost("EV", START_YEAR)
        ice = get_bom_cost("ICE", START_YEAR)
        assert ev > ice


# ═══════════════════════════════════════════════════════════════════
# Interest Rate
# ═══════════════════════════════════════════════════════════════════

class TestInterestRate:

    def test_returns_positive_rate(self) -> None:
        assert get_interest_rate(START_YEAR) > 0

    def test_smooth_between_years(self) -> None:
        """Rate should interpolate smoothly, not jump."""
        r1 = get_interest_rate(2026)
        r2 = get_interest_rate(2027)
        assert abs(r2 - r1) < 0.02  # no more than 2pp jump per year


# ═══════════════════════════════════════════════════════════════════
# Depreciation / Residual Value
# ═══════════════════════════════════════════════════════════════════

class TestDepreciation:

    def test_new_vehicle_has_full_value(self) -> None:
        assert get_vehicle_depreciation_residual("ICE", 0) == 1.0

    def test_residual_declines_with_age(self) -> None:
        r1 = get_vehicle_depreciation_residual("ICE", 1)
        r5 = get_vehicle_depreciation_residual("ICE", 5)
        assert r5 < r1 < 1.0

    def test_floor_at_ten_percent(self) -> None:
        r = get_vehicle_depreciation_residual("ICE", 30)
        assert r >= 0.10

    def test_ev_depreciates_differently_from_ice(self) -> None:
        """EV and ICE should have different depreciation curves."""
        ev = get_vehicle_depreciation_residual("EV", 5)
        ice = get_vehicle_depreciation_residual("ICE", 5)
        assert ev != ice


# ═══════════════════════════════════════════════════════════════════
# Tooling
# ═══════════════════════════════════════════════════════════════════

class TestTooling:

    def test_ice_tooling_is_flat(self) -> None:
        t1 = get_legacy_tooling_per_unit("ICE", 0)
        t2 = get_legacy_tooling_per_unit("ICE", 1_000_000)
        assert t1 == t2

    def test_ev_legacy_tooling_declines_with_volume(self) -> None:
        t_low = get_legacy_tooling_per_unit("EV", 100_000)
        t_high = get_legacy_tooling_per_unit("EV", 1_000_000)
        assert t_high <= t_low

    def test_startup_tooling_declines_with_volume(self) -> None:
        t_low = get_startup_tooling_per_unit(100_000)
        t_high = get_startup_tooling_per_unit(1_000_000)
        assert t_high <= t_low


# ═══════════════════════════════════════════════════════════════════
# Producer Unit Costs
# ═══════════════════════════════════════════════════════════════════

class TestProducerUnitCosts:

    def test_legacy_ice_cost_positive(self) -> None:
        assert get_legacy_unit_cost("ICE", START_YEAR) > 0

    def test_legacy_ev_cost_positive(self) -> None:
        assert get_legacy_unit_cost("EV", START_YEAR) > 0

    def test_startup_cost_positive(self) -> None:
        assert get_startup_unit_cost(START_YEAR) > 0

    def test_startup_cheaper_than_legacy_ev(self) -> None:
        """Startup has DTC savings and no union premium."""
        legacy = get_legacy_unit_cost("EV", START_YEAR)
        startup = get_startup_unit_cost(START_YEAR)
        assert startup < legacy

    def test_rd_milestones_reduce_cost(self) -> None:
        c0 = get_legacy_unit_cost("EV", START_YEAR, rd_milestones=0)
        c3 = get_legacy_unit_cost("EV", START_YEAR, rd_milestones=3)
        assert c3 < c0


# ═══════════════════════════════════════════════════════════════════
# Consumer-Facing Annual Costs
# ═══════════════════════════════════════════════════════════════════

class TestAnnualCosts:

    def test_ev_fuel_cheaper_than_ice(self) -> None:
        ev = get_annual_fuel_cost("EV", START_YEAR, 12_000, kwh_per_mile=0.30)
        ice = get_annual_fuel_cost("ICE", START_YEAR, 12_000, mpg=30)
        assert ev < ice

    def test_public_charging_premium(self) -> None:
        home = get_annual_fuel_cost("EV", START_YEAR, 12_000, kwh_per_mile=0.30, can_charge_at_home=True)
        pub = get_annual_fuel_cost("EV", START_YEAR, 12_000, kwh_per_mile=0.30, can_charge_at_home=False)
        assert pub > home

    def test_insurance_ev_more_than_ice(self) -> None:
        assert get_annual_insurance("EV") > get_annual_insurance("ICE")

    def test_maintenance_escalates_with_age(self) -> None:
        m0 = get_annual_maintenance("ICE", 1200, vehicle_age=0)
        m5 = get_annual_maintenance("ICE", 1200, vehicle_age=5)
        assert m5 > m0

    def test_ev_maintenance_escalates_slowly(self) -> None:
        """EV maintenance should escalate much less than ICE."""
        ice_delta = get_annual_maintenance("ICE", 1200, 5) - get_annual_maintenance("ICE", 1200, 0)
        ev_delta = get_annual_maintenance("EV", 600, 5) - get_annual_maintenance("EV", 600, 0)
        assert ev_delta < ice_delta
