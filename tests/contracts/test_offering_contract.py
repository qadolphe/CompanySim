"""
Contract tests for the ProductOffering ABC.

Any implementation of ProductOffering (VehicleOffering, EnergyPlanOffering, etc.)
must pass these tests.
"""

import pytest

from domain.market.models import ProductOffering, VehicleOffering


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(params=["vehicle_ice", "vehicle_ev"])
def product_offering(request) -> ProductOffering:
    """
    Parametrized fixture. Add new ProductOffering implementations here.
    """
    if request.param == "vehicle_ice":
        return VehicleOffering(
            drivetrain="ICE", msrp=32_000, mpg=30.0, range_mi=400,
            annual_maintenance=1200, kwh_per_mile=None, _units_available=100,
        )
    elif request.param == "vehicle_ev":
        return VehicleOffering(
            drivetrain="EV", msrp=42_000, mpg=None, range_mi=300,
            annual_maintenance=600, kwh_per_mile=0.3, _units_available=50,
        )
    raise ValueError(f"Unknown offering type: {request.param}")


# ═══════════════════════════════════════════════════════════════════
# Contract Tests
# ═══════════════════════════════════════════════════════════════════

class TestProductOfferingContract:

    def test_is_subclass_of_abc(
        self, product_offering: ProductOffering
    ) -> None:
        assert isinstance(product_offering, ProductOffering)

    def test_product_type_is_string(
        self, product_offering: ProductOffering
    ) -> None:
        assert isinstance(product_offering.product_type, str)
        assert len(product_offering.product_type) > 0

    def test_price_is_positive_float(
        self, product_offering: ProductOffering
    ) -> None:
        assert isinstance(product_offering.price, (int, float))
        assert product_offering.price > 0

    def test_units_available_is_non_negative_int(
        self, product_offering: ProductOffering
    ) -> None:
        assert isinstance(product_offering.units_available, int)
        assert product_offering.units_available >= 0

    def test_to_consumer_view_returns_dict(
        self, product_offering: ProductOffering
    ) -> None:
        view = product_offering.to_consumer_view()
        assert isinstance(view, dict)

    def test_consumer_view_contains_product_type(
        self, product_offering: ProductOffering
    ) -> None:
        view = product_offering.to_consumer_view()
        assert "product_type" in view

    def test_consumer_view_contains_price(
        self, product_offering: ProductOffering
    ) -> None:
        view = product_offering.to_consumer_view()
        assert "msrp" in view or "price" in view

    def test_decrement_inventory_reduces_count(
        self, product_offering: ProductOffering
    ) -> None:
        before = product_offering.units_available
        product_offering.decrement_inventory()
        assert product_offering.units_available == before - 1

    def test_decrement_past_zero_raises(self) -> None:
        offering = VehicleOffering(
            drivetrain="ICE", msrp=32_000, mpg=30.0, range_mi=400,
            annual_maintenance=1200, kwh_per_mile=None, _units_available=1,
        )
        offering.decrement_inventory()
        with pytest.raises(ValueError):
            offering.decrement_inventory()
