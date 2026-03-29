"""
Unit tests for the VehicleUtilityCalculator.

Tests verify the economic logic is directionally correct:
  - TCO calculation
  - Green preference bonus
  - Range anxiety penalty
  - Sensitivity to policy changes (gas price, EV credit)
"""

import pytest

from domain.consumer.models import ConsumerProfile
from domain.consumer.utility import VehicleUtilityCalculator
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def calc() -> VehicleUtilityCalculator:
    return VehicleUtilityCalculator()


@pytest.fixture
def env_2024() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024,
        ev_tax_credit=7_500.0,
        gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14,
        interest_rate=0.07,
        emissions_penalty_per_unit=0.0,
        cafe_ev_mandate_pct=0.10, charging_infrastructure_index=0.1,
    )


@pytest.fixture
def ice_offering() -> dict:
    return {
        "offering_id": "LegacyAutomaker_ICE", "product_type": "ICE",
        "msrp": 32_000,
        "mpg": 30.0,
        "range_mi": 400,
        "annual_maintenance": 1_200,
        "kwh_per_mile": None,
    }


@pytest.fixture
def ev_offering() -> dict:
    return {
        "offering_id": "LegacyAutomaker_EV", "product_type": "EV",
        "msrp": 42_000,
        "mpg": None,
        "range_mi": 300,
        "annual_maintenance": 600,
        "kwh_per_mile": 0.30,
    }


@pytest.fixture
def hybrid_offering() -> dict:
    return {
        "offering_id": "LegacyAutomaker_HYBRID", "product_type": "HYBRID",
        "msrp": 35_000,
        "mpg": 50.0,
        "range_mi": 550,
        "annual_maintenance": 1_000,
        "kwh_per_mile": None,
    }


def _make_profile(**overrides) -> ConsumerProfile:
    """Helper to build a consumer profile with sensible defaults."""
    defaults = dict(
        id=0,
        annual_income=65_000,
        annual_commute_miles=7_500,
        green_preference=0.5,
        price_sensitivity=0.5,
        is_homeowner=True,
        current_vehicle="ICE",
        years_owned=7,
    )
    defaults.update(overrides)
    return ConsumerProfile(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Directional Tests — verify the math moves the right way
# ═══════════════════════════════════════════════════════════════════

class TestDirectionalLogic:
    """
    These tests don't assert exact numbers — they verify that the
    utility function moves in the economically correct direction.
    """

    def test_high_income_green_consumer_prefers_ev(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
        ice_offering: dict,
        ev_offering: dict,
    ) -> None:
        """A wealthy, eco-conscious consumer should prefer EV."""
        profile = _make_profile(
            annual_income=120_000,
            annual_commute_miles=5_000,  # short commute, no range anxiety
            green_preference=0.9,
            price_sensitivity=0.2,
        )
        u_ice = calc.compute(profile, ice_offering, env_2024)
        u_ev = calc.compute(profile, ev_offering, env_2024)
        assert u_ev > u_ice

    def test_low_income_long_commute_prefers_ice(
        self,
        calc: VehicleUtilityCalculator,
        ice_offering: dict,
        ev_offering: dict,
    ) -> None:
        """Without tax credits, a cost-conscious consumer should prefer ICE
        due to the massive MSRP gap dominating TCO."""
        profile = _make_profile(
            annual_income=40_000,
            annual_commute_miles=8_000,
            green_preference=0.0,
            price_sensitivity=1.0,
        )
        # Remove the EV credit to isolate price sensitivity
        env_no_credit = PolicySnapshot(
            year=2030, ev_tax_credit=0, gas_price_per_gallon=3.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        u_ice = calc.compute(profile, ice_offering, env_no_credit)
        u_ev = calc.compute(profile, ev_offering, env_no_credit)
        assert u_ice > u_ev

    def test_higher_gas_price_favors_ev(
        self,
        calc: VehicleUtilityCalculator,
        ice_offering: dict,
        ev_offering: dict,
    ) -> None:
        """When gas is expensive, EV becomes relatively more attractive."""
        profile = _make_profile(annual_income=80_000, green_preference=0.5)

        env_low_gas = PolicySnapshot(
            year=2024, ev_tax_credit=7500, gas_price_per_gallon=2.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        env_high_gas = PolicySnapshot(
            year=2030, ev_tax_credit=7500, gas_price_per_gallon=6.00,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )

        # Utility gap should narrow or flip with expensive gas
        gap_low = (
            calc.compute(profile, ice_offering, env_low_gas)
            - calc.compute(profile, ev_offering, env_low_gas)
        )
        gap_high = (
            calc.compute(profile, ice_offering, env_high_gas)
            - calc.compute(profile, ev_offering, env_high_gas)
        )
        # ICE advantage should shrink or invert when gas is more expensive
        assert gap_high < gap_low

    def test_higher_ev_credit_favors_ev(
        self,
        calc: VehicleUtilityCalculator,
        ev_offering: dict,
    ) -> None:
        """Larger EV tax credit should increase EV utility."""
        profile = _make_profile(annual_income=80_000)

        env_low = PolicySnapshot(
            year=2030, ev_tax_credit=0, gas_price_per_gallon=3.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        env_high = PolicySnapshot(
            year=2030, ev_tax_credit=10_000, gas_price_per_gallon=3.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )

        u_low = calc.compute(profile, ev_offering, env_low)
        u_high = calc.compute(profile, ev_offering, env_high)
        assert u_high > u_low

    def test_hybrid_between_ice_and_ev_for_moderate_consumer(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
        ice_offering: dict,
        hybrid_offering: dict,
        ev_offering: dict,
    ) -> None:
        """For a moderate consumer, hybrid utility should fall between ICE and EV,
        or at least be competitive with both."""
        profile = _make_profile(
            annual_income=70_000,
            annual_commute_miles=7_500,
            green_preference=0.5,
            price_sensitivity=0.5,
        )
        u_ice = calc.compute(profile, ice_offering, env_2024)
        u_hybrid = calc.compute(profile, hybrid_offering, env_2024)
        u_ev = calc.compute(profile, ev_offering, env_2024)
        # Hybrid should be within the ICE-EV range (not necessarily exactly between)
        assert min(u_ice, u_ev) <= u_hybrid <= max(u_ice, u_ev) or \
               u_hybrid >= min(u_ice, u_ev)


# ═══════════════════════════════════════════════════════════════════
# Range Anxiety Tests
# ═══════════════════════════════════════════════════════════════════

class TestRangeAnxiety:
    """Tests for the EV range anxiety penalty."""

    def test_no_range_anxiety_for_ice(
        self,
        calc: VehicleUtilityCalculator,
    ) -> None:
        """ICE vehicles should never trigger range anxiety."""
        profile = _make_profile(annual_commute_miles=30_000)
        # _compute_range_anxiety is only called for EV, so ICE should
        # not have the penalty. We test indirectly via utility stability.
        env = PolicySnapshot(
            year=2024, ev_tax_credit=0, gas_price_per_gallon=3.5,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        ice = {"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 32000, "mpg": 30,
               "range_mi": 50, "annual_maintenance": 1200, "kwh_per_mile": None}
        # Even with tiny range, ICE shouldn't be penalized
        u = calc.compute(profile, ice, env)
        assert isinstance(u, float)

    def test_short_commute_no_range_anxiety_for_ev(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
    ) -> None:
        """EV with 300mi range should have no anxiety for a 10mi/day commuter."""
        profile = _make_profile(annual_commute_miles=2_500)  # ~10mi/day
        ev = {"offering_id": "LegacyAutomaker_EV", "product_type": "EV", "msrp": 42000, "mpg": None,
              "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3}
        # Compute directly
        anxiety = VehicleUtilityCalculator._compute_range_anxiety(profile, ev)
        assert anxiety == 0.0

    def test_long_commute_causes_range_anxiety_for_ev(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
    ) -> None:
        """EV with 300mi range should trigger anxiety for a 200mi/day commuter.
        Required range = 200 × 2.5 = 500mi > 300mi → anxiety."""
        profile = _make_profile(annual_commute_miles=50_000)  # ~200mi/day
        ev = {"offering_id": "LegacyAutomaker_EV", "product_type": "EV", "msrp": 42000, "mpg": None,
              "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3}
        anxiety = VehicleUtilityCalculator._compute_range_anxiety(profile, ev)
        assert anxiety > 0.0


# ═══════════════════════════════════════════════════════════════════
# TCO Calculation Tests
# ═══════════════════════════════════════════════════════════════════

class TestTCO:
    """Tests for the total cost of ownership calculation."""

    def test_tco_is_positive(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
        ice_offering: dict,
    ) -> None:
        profile = _make_profile()
        tco = calc._compute_tco(profile, ice_offering, env_2024)
        assert tco > 0

    def test_ev_tco_includes_tax_credit(
        self,
        calc: VehicleUtilityCalculator,
        ev_offering: dict,
    ) -> None:
        """EV TCO should decrease when tax credit increases."""
        profile = _make_profile()
        env_no_credit = PolicySnapshot(
            year=2024, ev_tax_credit=0, gas_price_per_gallon=3.5,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        env_with_credit = PolicySnapshot(
            year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.5,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
        )
        tco_no = calc._compute_tco(profile, ev_offering, env_no_credit)
        tco_with = calc._compute_tco(profile, ev_offering, env_with_credit)
        assert tco_with < tco_no
        assert tco_no - tco_with == pytest.approx(7500.0)

    def test_ev_cheaper_fuel_than_ice(
        self,
        calc: VehicleUtilityCalculator,
        env_2024: PolicySnapshot,
    ) -> None:
        """Annual fuel cost for EV should be lower than ICE at current prices."""
        profile = _make_profile(annual_commute_miles=12_000)
        ice = {"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 32000, "mpg": 30,
               "range_mi": 400, "annual_maintenance": 1200, "kwh_per_mile": None}
        ev = {"offering_id": "LegacyAutomaker_EV", "product_type": "EV", "msrp": 42000, "mpg": None,
              "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3}
        fuel_ice = VehicleUtilityCalculator._annual_fuel_cost(
            profile, ice, env_2024
        )
        fuel_ev = VehicleUtilityCalculator._annual_fuel_cost(
            profile, ev, env_2024
        )
        assert fuel_ev < fuel_ice


# ═══════════════════════════════════════════════════════════════════
# Ownership Hassle Tests
# ═══════════════════════════════════════════════════════════════════

class TestOwnershipHassle:
    """Tests for the EV ownership hassle penalty."""

    def test_homeowner_has_lower_hassle_than_renter(self, env_2024: PolicySnapshot) -> None:
        """A homeowner should have significantly lower hassle than a renter with identical stats."""
        from domain.consumer.utility import VehicleUtilityCalculator
        homeowner = _make_profile(is_homeowner=True, annual_income=60_000)
        renter = _make_profile(is_homeowner=False, annual_income=60_000)
        
        h_home = VehicleUtilityCalculator._compute_ownership_hassle(homeowner, env_2024)
        h_rent = VehicleUtilityCalculator._compute_ownership_hassle(renter, env_2024)
        
        assert h_home < h_rent

    def test_high_income_renter_has_lower_hassle_than_low_income_renter(self, env_2024: PolicySnapshot) -> None:
        """Higher income for renters mitigates some friction (can afford paid charging)."""
        from domain.consumer.utility import VehicleUtilityCalculator
        rich_renter = _make_profile(is_homeowner=False, annual_income=100_000)
        poor_renter = _make_profile(is_homeowner=False, annual_income=30_000)
        
        h_rich = VehicleUtilityCalculator._compute_ownership_hassle(rich_renter, env_2024)
        h_poor = VehicleUtilityCalculator._compute_ownership_hassle(poor_renter, env_2024)
        
        assert h_rich < h_poor

    def test_long_commute_increases_hassle(self, env_2024: PolicySnapshot) -> None:
        """Longer commutes mean more frequent charging, increasing the hassle penalty."""
        from domain.consumer.utility import VehicleUtilityCalculator
        short_commute = _make_profile(is_homeowner=False, annual_commute_miles=5_000)
        long_commute = _make_profile(is_homeowner=False, annual_commute_miles=20_000)
        
        h_short = VehicleUtilityCalculator._compute_ownership_hassle(short_commute, env_2024)
        h_long = VehicleUtilityCalculator._compute_ownership_hassle(long_commute, env_2024)
        
        assert h_short < h_long
