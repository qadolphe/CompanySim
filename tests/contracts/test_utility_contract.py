"""
Contract tests for the UtilityCalculator ABC.

Any implementation must pass these tests to be valid for use
in a consumer agent.
"""

import pytest

from domain.consumer.utility import UtilityCalculator, VehicleUtilityCalculator
from domain.consumer.models import ConsumerProfile
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(params=["vehicle"])
def utility_calc(request) -> UtilityCalculator:
    """Add new UtilityCalculator implementations here."""
    if request.param == "vehicle":
        return VehicleUtilityCalculator()
    raise ValueError(f"Unknown calc type: {request.param}")


@pytest.fixture
def sample_profile() -> ConsumerProfile:
    return ConsumerProfile(
        id=0, annual_income=65_000, annual_commute_miles=7_500,
        green_preference=0.5, price_sensitivity=0.5,
        is_homeowner=True,
        current_vehicle="ICE", years_owned=7,
    )


@pytest.fixture
def sample_env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
    )


@pytest.fixture
def sample_offering() -> dict:
    return {
        "offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 32_000, "mpg": 30,
        "range_mi": 400, "annual_maintenance": 1200, "kwh_per_mile": None,
    }


# ═══════════════════════════════════════════════════════════════════
# Contract Tests
# ═══════════════════════════════════════════════════════════════════

class TestUtilityCalculatorContract:

    def test_is_subclass_of_abc(
        self, utility_calc: UtilityCalculator
    ) -> None:
        assert isinstance(utility_calc, UtilityCalculator)

    def test_compute_returns_float(
        self,
        utility_calc: UtilityCalculator,
        sample_profile: ConsumerProfile,
        sample_offering: dict,
        sample_env: PolicySnapshot,
    ) -> None:
        result = utility_calc.compute(sample_profile, sample_offering, sample_env)
        assert isinstance(result, (int, float))

    def test_compute_is_deterministic(
        self,
        utility_calc: UtilityCalculator,
        sample_profile: ConsumerProfile,
        sample_offering: dict,
        sample_env: PolicySnapshot,
    ) -> None:
        """Same inputs → same output."""
        r1 = utility_calc.compute(sample_profile, sample_offering, sample_env)
        r2 = utility_calc.compute(sample_profile, sample_offering, sample_env)
        assert r1 == r2

    def test_different_offerings_can_produce_different_utilities(
        self,
        utility_calc: UtilityCalculator,
        sample_profile: ConsumerProfile,
        sample_env: PolicySnapshot,
    ) -> None:
        """Two meaningfully different offerings should yield different scores."""
        cheap = {"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 20_000, "mpg": 35,
                 "range_mi": 500, "annual_maintenance": 800, "kwh_per_mile": None}
        expensive = {"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 80_000, "mpg": 15,
                     "range_mi": 300, "annual_maintenance": 2500, "kwh_per_mile": None}
        u_cheap = utility_calc.compute(sample_profile, cheap, sample_env)
        u_expensive = utility_calc.compute(sample_profile, expensive, sample_env)
        assert u_cheap != u_expensive
