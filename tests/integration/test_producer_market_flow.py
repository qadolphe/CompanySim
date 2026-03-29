"""
Integration test: Producer → Marketplace → Producer feedback loop.

Tests the full cycle of the automaker posting catalog, receiving
synthetic sales, and adjusting strategy.
"""

import pytest

from domain.producer.agents import LegacyAutomaker
from domain.market.marketplace import Marketplace
from domain.market.models import SalesRecord
from domain.environment.models import PolicySnapshot


@pytest.fixture
def env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2026, ev_tax_credit=7500, gas_price_per_gallon=3.71,
        electricity_price_per_kwh=0.144, interest_rate=0.065,
        emissions_penalty_per_unit=200, cafe_ev_mandate_pct=0.15, charging_infrastructure_index=0.1,
    )


class TestProducerMarketFlow:

    def test_automaker_posts_and_reads_sales(
        self, env: PolicySnapshot
    ) -> None:
        """Full round-trip: automaker → marketplace → sales → automaker."""
        automaker = LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )
        marketplace = Marketplace()

        # 1. Automaker posts catalog
        offerings = automaker.generate_offerings(env)
        marketplace.set_catalog(offerings)

        # 2. Simulate some purchases
        for _ in range(400):
            marketplace.attempt_purchase("LegacyAutomaker_ICE")
        for _ in range(180):
            marketplace.attempt_purchase("LegacyAutomaker_HYBRID")
        for _ in range(100):
            marketplace.attempt_purchase("LegacyAutomaker_EV")

        # 3. Get sales summary
        sales = marketplace.get_firm_sales_summary("LegacyAutomaker")

        # 4. Automaker processes
        automaker.process_sales(sales, env)

        # Verify automaker state updated
        state = automaker.get_state()
        assert state["capital"] != 5_000_000_000
        assert automaker.ledger.cumulative_revenue > 0

    def test_ev_sellout_triggers_capacity_increase(
        self, env: PolicySnapshot
    ) -> None:
        """When EV sells out and ICE underperforms, capacity should shift toward EV."""
        automaker = LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )
        initial_ev_cap = automaker.capacity["EV"]

        # ICE underperforms (<50%), EV sells out (>90%) → capacity shifts
        sales = {
            "ICE": SalesRecord("ICE", "ICE", 150, 4_800_000),    # 25% of 600
            "HYBRID": SalesRecord("HYBRID", "HYBRID", 180, 6_300_000),  # 72%
            "EV": SalesRecord("EV", "EV", 145, 6_090_000),       # 97% of 150
        }
        automaker.process_sales(sales, env)

        assert automaker.capacity["EV"] > initial_ev_cap, (
            "EV capacity should increase when selling out"
        )

    def test_ice_underperformance_triggers_decrease(
        self, env: PolicySnapshot
    ) -> None:
        """When ICE sells at <50%, capacity should shift away."""
        automaker = LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )
        initial_ice_cap = automaker.capacity["ICE"]

        # ICE barely sells, EV sells out
        sales = {
            "ICE": SalesRecord("ICE", "ICE", 150, 4_800_000),  # 25% of 600
            "HYBRID": SalesRecord("HYBRID", "HYBRID", 180, 6_300_000),
            "EV": SalesRecord("EV", "EV", 148, 6_216_000),  # 98.7%
        }
        automaker.process_sales(sales, env)

        assert automaker.capacity["ICE"] < initial_ice_cap, (
            "ICE capacity should decrease when underperforming"
        )

    def test_multi_tick_stability(self, env: PolicySnapshot) -> None:
        """Running 5 ticks shouldn't crash or produce degenerate values."""
        automaker = LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )

        for i in range(5):
            sales = {
                "ICE": SalesRecord("ICE", "ICE", 400, 400 * 32_000),
                "HYBRID": SalesRecord("HYBRID", "HYBRID", 200, 200 * 35_000),
                "EV": SalesRecord("EV", "EV", 140, 140 * 42_000),
            }
            automaker.process_sales(sales, env)

        state = automaker.get_state()
        # Capital should still be a real number (not inf, nan, or zero)
        assert state["capital"] > 0, "Capital went to zero or negative"
        assert state["total_capacity"] > 0, "Total capacity should be positive"
