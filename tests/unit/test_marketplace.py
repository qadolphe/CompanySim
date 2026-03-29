"""
Unit tests for the Marketplace aggregate root.

Tests cover:
  - Catalog management (set, get)
  - Purchase mechanics (inventory, sellout)
  - Sales summary reporting
"""

import pytest

from domain.market.marketplace import Marketplace
from domain.market.models import VehicleOffering, SalesRecord


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def marketplace() -> Marketplace:
    return Marketplace()


@pytest.fixture
def sample_offerings() -> list[VehicleOffering]:
    return [
        VehicleOffering(
            drivetrain="ICE", msrp=32_000, mpg=30.0, range_mi=400,
            annual_maintenance=1200, kwh_per_mile=None, _units_available=100,
        ),
        VehicleOffering(
            drivetrain="EV", msrp=42_000, mpg=None, range_mi=300,
            annual_maintenance=600, kwh_per_mile=0.3, _units_available=50,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════
# Catalog Tests
# ═══════════════════════════════════════════════════════════════════

class TestCatalog:

    def test_set_catalog(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        assert set(marketplace.product_types) == {"ICE", "EV"}

    def test_consumer_view_hides_inventory(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        """Consumer catalog should not expose units_available."""
        marketplace.set_catalog(sample_offerings)
        views = marketplace.get_catalog_for_consumers()
        for view in views:
            assert "units_available" not in view
            assert "_units_available" not in view

    def test_consumer_view_has_required_fields(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        views = marketplace.get_catalog_for_consumers()
        for view in views:
            assert "product_type" in view
            assert "msrp" in view

    def test_set_catalog_resets_sales(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        """Setting a new catalog should reset all sales counters."""
        marketplace.set_catalog(sample_offerings)
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        # Reset
        marketplace.set_catalog(sample_offerings)
        summary = marketplace.get_sales_summary()
        assert summary["LegacyAutomaker_ICE"].units_sold == 0


# ═══════════════════════════════════════════════════════════════════
# Purchase Tests
# ═══════════════════════════════════════════════════════════════════

class TestPurchases:

    def test_successful_purchase(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        assert marketplace.attempt_purchase("LegacyAutomaker_ICE") is True

    def test_purchase_decrements_inventory(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        summary = marketplace.get_sales_summary()
        assert summary["LegacyAutomaker_ICE"].units_sold == 1

    def test_purchase_unknown_type_fails(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        assert marketplace.attempt_purchase("HELICOPTER") is False

    def test_purchase_empty_catalog_fails(
        self, marketplace: Marketplace
    ) -> None:
        assert marketplace.attempt_purchase("LegacyAutomaker_ICE") is False

    def test_sellout_blocks_further_purchases(
        self, marketplace: Marketplace
    ) -> None:
        """Once inventory hits 0, no more purchases are possible."""
        offerings = [
            VehicleOffering(
                drivetrain="EV", msrp=42_000, mpg=None, range_mi=300,
                annual_maintenance=600, kwh_per_mile=0.3, _units_available=3,
            ),
        ]
        marketplace.set_catalog(offerings)
        assert marketplace.attempt_purchase("LegacyAutomaker_EV") is True
        assert marketplace.attempt_purchase("LegacyAutomaker_EV") is True
        assert marketplace.attempt_purchase("LegacyAutomaker_EV") is True
        assert marketplace.attempt_purchase("LegacyAutomaker_EV") is False  # sold out

    def test_purchase_tracks_revenue(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        marketplace.attempt_purchase("LegacyAutomaker_EV")
        marketplace.attempt_purchase("LegacyAutomaker_EV")
        summary = marketplace.get_sales_summary()
        assert summary["LegacyAutomaker_EV"].revenue == pytest.approx(84_000.0)


# ═══════════════════════════════════════════════════════════════════
# Sales Summary Tests
# ═══════════════════════════════════════════════════════════════════

class TestSalesSummary:

    def test_summary_has_all_product_types(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        summary = marketplace.get_sales_summary()
        expected_keys = {o.offering_id for o in sample_offerings}
        assert set(summary.keys()) == expected_keys

    def test_summary_returns_sales_records(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        summary = marketplace.get_sales_summary()
        for record in summary.values():
            assert isinstance(record, SalesRecord)

    def test_total_units_sold(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        marketplace.attempt_purchase("LegacyAutomaker_EV")
        assert marketplace.get_total_units_sold() == 3

    def test_total_revenue(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        marketplace.attempt_purchase("LegacyAutomaker_ICE")
        marketplace.attempt_purchase("LegacyAutomaker_EV")
        expected = 32_000 + 42_000
        assert marketplace.get_total_revenue() == pytest.approx(expected)

    def test_zero_sales_summary(
        self, marketplace: Marketplace, sample_offerings: list[VehicleOffering]
    ) -> None:
        marketplace.set_catalog(sample_offerings)
        summary = marketplace.get_sales_summary()
        for record in summary.values():
            assert record.units_sold == 0
            assert record.revenue == 0.0
