"""
Integration test: Consumer → Marketplace flow.

Tests the full loop of consumers shopping in a marketplace
with realistic population and inventory constraints.
"""

import pytest

from domain.consumer.factory import PopulationFactory
from domain.market.marketplace import Marketplace
from domain.market.models import VehicleOffering
from domain.environment.models import PolicySnapshot
from simulation.config import CONSUMER_MULTIPLIER


@pytest.fixture
def env_2024() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
    )


@pytest.fixture
def full_catalog() -> list[VehicleOffering]:
    return [
        VehicleOffering(
            drivetrain="ICE", msrp=32_000, mpg=30.0, range_mi=400,
            annual_maintenance=1200, kwh_per_mile=None, _units_available=600,
        ),
        VehicleOffering(
            drivetrain="HYBRID", msrp=35_000, mpg=50.0, range_mi=550,
            annual_maintenance=1000, kwh_per_mile=None, _units_available=250,
        ),
        VehicleOffering(
            drivetrain="EV", msrp=42_000, mpg=None, range_mi=300,
            annual_maintenance=600, kwh_per_mile=0.3, _units_available=150,
        ),
    ]


class TestConsumerMarketFlow:
    """
    Integration tests for the consumer → marketplace purchase flow.
    Uses a realistic population of 1,000 consumers.
    """

    def test_population_can_shop(
        self, env_2024: PolicySnapshot, full_catalog: list[VehicleOffering]
    ) -> None:
        """All 1000 consumers run through the marketplace without errors."""
        population = PopulationFactory.generate(n=1000, seed=42)
        marketplace = Marketplace()
        marketplace.set_catalog(full_catalog)

        catalog_view = marketplace.get_catalog_for_consumers()
        purchases = 0

        for consumer in population:
            if consumer.is_in_market():
                choice = consumer.evaluate_and_choose(catalog_view, env_2024)
                if choice:
                    success = marketplace.attempt_purchase(choice)
                    if success:
                        consumer.record_purchase(choice)
                        purchases += 1

        # At least some consumers should have bought
        assert purchases > 0

    def test_inventory_constraint_honored(
        self, env_2024: PolicySnapshot
    ) -> None:
        """When EV inventory is very limited, sales should be capped."""
        limited_catalog = [
            VehicleOffering(
                drivetrain="ICE", msrp=32_000, mpg=30.0, range_mi=400,
                annual_maintenance=1200, kwh_per_mile=None, _units_available=999,
            ),
            VehicleOffering(
                drivetrain="EV", msrp=42_000, mpg=None, range_mi=300,
                annual_maintenance=600, kwh_per_mile=0.3, _units_available=5,
            ),
        ]
        population = PopulationFactory.generate(n=500, seed=42)
        marketplace = Marketplace()
        marketplace.set_catalog(limited_catalog)

        catalog_view = marketplace.get_catalog_for_consumers()
        for consumer in population:
            if consumer.is_in_market():
                choice = consumer.evaluate_and_choose(catalog_view, env_2024)
                if choice:
                    marketplace.attempt_purchase(choice)

        summary = marketplace.get_sales_summary()
        assert summary["LegacyAutomaker_EV"].units_sold <= 5 * CONSUMER_MULTIPLIER

    def test_market_split_is_reasonable(
        self, env_2024: PolicySnapshot, full_catalog: list[VehicleOffering]
    ) -> None:
        """
        2024 baseline: no single drivetrain should capture 100% of sales.
        NOTE: Exact calibration (ICE ~80%) is a tuning task, not a
        structural test. This just verifies reasonable diversity.
        """
        population = PopulationFactory.generate(n=1000, seed=42)
        marketplace = Marketplace()
        marketplace.set_catalog(full_catalog)
        catalog_view = marketplace.get_catalog_for_consumers()

        for consumer in population:
            if consumer.is_in_market():
                choice = consumer.evaluate_and_choose(catalog_view, env_2024)
                if choice:
                    marketplace.attempt_purchase(choice)

        summary = marketplace.get_sales_summary()
        total = marketplace.get_total_units_sold()

        if total > 0:
            # At least 2 drivetrains should have non-zero sales
            nonzero = sum(1 for r in summary.values() if r.units_sold > 0)
            assert nonzero >= 2, (
                f"Only {nonzero} drivetrain(s) had sales — model lacks diversity"
            )

    def test_all_sales_are_accounted_for(
        self, env_2024: PolicySnapshot, full_catalog: list[VehicleOffering]
    ) -> None:
        """Total units in summary should equal sum of per-type sales."""
        population = PopulationFactory.generate(n=1000, seed=42)
        marketplace = Marketplace()
        marketplace.set_catalog(full_catalog)
        catalog_view = marketplace.get_catalog_for_consumers()

        for consumer in population:
            if consumer.is_in_market():
                choice = consumer.evaluate_and_choose(catalog_view, env_2024)
                if choice:
                    marketplace.attempt_purchase(choice)

        summary = marketplace.get_sales_summary()
        sum_sales = sum(r.units_sold for r in summary.values())
        assert sum_sales == marketplace.get_total_units_sold()
