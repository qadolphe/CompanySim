"""
Full integration tests — end-to-end simulation runs.

Tests the complete game loop: environment → consumers → marketplace →
automaker → logging.
"""

import pytest
import pandas as pd

from simulation.engine import SimulationEngine
from simulation.config import START_YEAR, END_YEAR
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Single Tick Tests
# ═══════════════════════════════════════════════════════════════════

class TestSingleTick:
    """Verify that a single tick produces valid state."""

    def test_single_tick_runs(self) -> None:
        """A single-year simulation should complete without error."""
        sim = SimulationEngine(
            start_year=2024, end_year=2024, num_consumers=100, seed=42,
        )
        df = sim.run()
        assert len(df) == 1
        assert 2024 in df.index

    def test_single_tick_has_sales(self) -> None:
        sim = SimulationEngine(
            start_year=2024, end_year=2024, num_consumers=500, seed=42,
        )
        df = sim.run()
        assert df.iloc[0]["sales_total_units"] > 0


# ═══════════════════════════════════════════════════════════════════
# Full Simulation Tests
# ═══════════════════════════════════════════════════════════════════

class TestFullSimulation:
    """End-to-end simulation over the complete 2024–2035 timeline."""

    @pytest.fixture
    def full_results(self) -> pd.DataFrame:
        """Run the full 12-year simulation with 1000 consumers."""
        sim = SimulationEngine(
            start_year=START_YEAR, end_year=END_YEAR,
            num_consumers=1000, seed=42,
        )
        return sim.run()

    def test_correct_number_of_years(self, full_results: pd.DataFrame) -> None:
        expected_years = END_YEAR - START_YEAR + 1
        assert len(full_results) == expected_years

    def test_all_years_present(self, full_results: pd.DataFrame) -> None:
        expected = list(range(START_YEAR, END_YEAR + 1))
        assert list(full_results.index) == expected

    def test_ev_has_sales_at_some_point(
        self, full_results: pd.DataFrame
    ) -> None:
        """EV should have non-zero sales in at least some years."""
        if "sales_ev_units" in full_results.columns:
            ev_total = full_results["sales_ev_units"].sum()
            assert ev_total > 0, "EV had zero sales across entire simulation"

    def test_multiple_drivetrain_types_sell(
        self, full_results: pd.DataFrame
    ) -> None:
        """All three drivetrains should have at least some sales."""
        for dt in ["ice", "hybrid", "ev"]:
            col = f"sales_{dt}_units"
            if col in full_results.columns:
                total = full_results[col].sum()
                assert total > 0, f"{dt.upper()} had zero total sales"

    def test_capital_stays_reasonable(self, full_results: pd.DataFrame) -> None:
        """Legacy automaker capital should not collapse catastrophically.

        Under the full P&L model (per-drivetrain COGS, SGA, taxes),
        the EV transition can push capital negative in later years —
        that's the Innovator's Dilemma. We just check it doesn't
        spiral to an unreasonable floor.
        """
        min_cap = full_results["legacyautomaker_capital"].min()
        assert min_cap > -5_000_000_000, (
            f"Capital collapsed to ${min_cap / 1e9:.2f}B — check cost model"
        )

    def test_total_capacity_stable(self, full_results: pd.DataFrame) -> None:
        """Total production capacity should remain roughly constant (zero-sum)."""
        if "total_capacity" in full_results.columns:
            caps = full_results["total_capacity"]
            # Allow some variance from retooling rounding
            assert caps.max() / caps.min() < 1.5, (
                "Total capacity swung too wildly"
            )

    def test_market_shares_sum_to_one(self, full_results: pd.DataFrame) -> None:
        share_cols = [c for c in full_results.columns if c.startswith("share_type_")]
        if share_cols:
            totals = full_results[share_cols].sum(axis=1)
            for year, total in totals.items():
                assert total == pytest.approx(1.0, abs=0.01), (
                    f"Shares don't sum to 1.0 in year {year}: {total}"
                )

    def test_dataframe_has_no_nan(self, full_results: pd.DataFrame) -> None:
        """No NaN values should appear in the core columns."""
        core_cols = ["legacyautomaker_capital", "sales_total_units", "sales_total_revenue"]
        for col in core_cols:
            if col in full_results.columns:
                assert not full_results[col].isna().any(), (
                    f"NaN found in column {col}"
                )


# ═══════════════════════════════════════════════════════════════════
# Policy Sensitivity Tests
# ═══════════════════════════════════════════════════════════════════

class TestPolicySensitivity:
    """
    Verify the model is sensitive to policy changes.
    If changing policy inputs doesn't change outputs, the model is broken.
    """

    def test_ev_credit_affects_utility(self) -> None:
        """
        A higher EV tax credit should make EVs more attractive.
        We test this at the utility level since module-level config
        mutation doesn't propagate cleanly through EnvironmentService.
        """
        from domain.consumer.utility import VehicleUtilityCalculator
        from domain.consumer.models import ConsumerProfile

        calc = VehicleUtilityCalculator()
        profile = ConsumerProfile(
            id=0, annual_income=70_000, annual_commute_miles=10_000,
            green_preference=0.5, price_sensitivity=0.5,
            is_homeowner=True,
            current_vehicle="ICE", years_owned=7,
        )
        ev = {"offering_id": "LegacyAutomaker_EV", "product_type": "EV", "msrp": 42_000, "mpg": None,
              "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3}

        env_high_credit = PolicySnapshot(
            year=2024, ev_tax_credit=7_500, gas_price_per_gallon=3.5,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        env_no_credit = PolicySnapshot(
            year=2024, ev_tax_credit=0, gas_price_per_gallon=3.5,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )

        u_high = calc.compute(profile, ev, env_high_credit)
        u_low = calc.compute(profile, ev, env_no_credit)

        assert u_high > u_low, (
            f"Higher EV credit should increase utility: "
            f"with credit={u_high:.4f}, without={u_low:.4f}"
        )
