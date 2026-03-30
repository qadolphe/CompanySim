"""
Unit tests for AutoConsumer agent behavior.

Tests cover:
    - is_in_market logic (probabilistic, income-weighted, no vehicle)
  - evaluate_and_choose (selection, affordability gate)
  - record_purchase (state update)
  - age_one_tick (clock advancement)
"""

import pytest

from domain.consumer.agents import AutoConsumer
from domain.consumer.models import ConsumerProfile
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
    )


@pytest.fixture
def catalog() -> list[dict]:
    return [
        {"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 32_000, "mpg": 30,
         "range_mi": 400, "annual_maintenance": 1200, "kwh_per_mile": None},
        {"offering_id": "LegacyAutomaker_HYBRID", "product_type": "HYBRID", "msrp": 35_000, "mpg": 50,
         "range_mi": 550, "annual_maintenance": 1000, "kwh_per_mile": None},
        {"offering_id": "LegacyAutomaker_EV", "product_type": "EV", "msrp": 42_000, "mpg": None,
         "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3},
    ]


def _make_agent(**overrides) -> AutoConsumer:
    defaults = dict(
        id=0, annual_income=65_000, annual_commute_miles=7_500,
        green_preference=0.5, price_sensitivity=0.5,
        is_homeowner=True,
        current_vehicle="ICE", years_owned=7,
    )
    defaults.update(overrides)
    return AutoConsumer(ConsumerProfile(**defaults))


# ═══════════════════════════════════════════════════════════════════
# Market Entry Tests
# ═══════════════════════════════════════════════════════════════════

class TestIsInMarket:

    def test_in_market_when_no_vehicle(self) -> None:
        agent = _make_agent(current_vehicle=None, years_owned=0)
        assert agent.is_in_market()

    def test_higher_income_increases_entry_probability(self) -> None:
        low = _make_agent(annual_income=35_000, years_owned=4)
        high = _make_agent(annual_income=180_000, years_owned=4)
        assert high._market_entry_probability() > low._market_entry_probability()

    def test_more_years_owned_increases_entry_probability(self) -> None:
        newer = _make_agent(annual_income=70_000, years_owned=1)
        older = _make_agent(annual_income=70_000, years_owned=9)
        assert older._market_entry_probability() > newer._market_entry_probability()

    def test_market_entry_draw_gate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = _make_agent(annual_income=70_000, years_owned=5)
        monkeypatch.setattr(agent, "_market_entry_probability", lambda: 0.25)
        monkeypatch.setattr(agent._rng, "random", lambda: 0.90)
        assert not agent.is_in_market()

        monkeypatch.setattr(agent._rng, "random", lambda: 0.10)
        assert agent.is_in_market()


# ═══════════════════════════════════════════════════════════════════
# Choice & Affordability Tests
# ═══════════════════════════════════════════════════════════════════

class TestEvaluateAndChoose:

    def test_returns_a_valid_product_type(
        self, env: PolicySnapshot, catalog: list[dict]
    ) -> None:
        agent = _make_agent(annual_income=80_000)
        choice = agent.evaluate_and_choose(catalog, env)
        assert choice in ("LegacyAutomaker_ICE", "LegacyAutomaker_HYBRID", "LegacyAutomaker_EV")

    def test_returns_none_when_nothing_affordable(
        self, env: PolicySnapshot, catalog: list[dict]
    ) -> None:
        """A very low income consumer can't afford anything (max = $16K)."""
        agent = _make_agent(annual_income=20_000)  # max affordable = $16K
        choice = agent.evaluate_and_choose(catalog, env)
        assert choice is None

    def test_empty_catalog_returns_none(
        self, env: PolicySnapshot
    ) -> None:
        agent = _make_agent()
        choice = agent.evaluate_and_choose([], env)
        assert choice is None

    def test_single_offering_returns_it_if_affordable(
        self, env: PolicySnapshot
    ) -> None:
        agent = _make_agent(annual_income=80_000)
        catalog = [{"offering_id": "LegacyAutomaker_ICE", "product_type": "ICE", "msrp": 32_000, "mpg": 30,
                     "range_mi": 400, "annual_maintenance": 1200,
                     "kwh_per_mile": None}]
        assert agent.evaluate_and_choose(catalog, env) == "LegacyAutomaker_ICE"


# ═══════════════════════════════════════════════════════════════════
# State Mutation Tests
# ═══════════════════════════════════════════════════════════════════

class TestStateMutations:

    def test_record_purchase_updates_vehicle(self) -> None:
        agent = _make_agent(current_vehicle="ICE", years_owned=7)
        agent.record_purchase("EV")
        assert agent.profile.current_vehicle == "EV"
        assert agent.profile.years_owned == 0

    def test_age_one_tick_increments_years(self) -> None:
        agent = _make_agent(years_owned=3)
        agent.age_one_tick()
        assert agent.profile.years_owned == 4

    def test_age_one_tick_no_vehicle(self) -> None:
        """Aging does nothing if consumer has no vehicle."""
        agent = _make_agent(current_vehicle=None, years_owned=0)
        agent.age_one_tick()
        assert agent.profile.years_owned == 0

    def test_purchase_then_age_cycle(self) -> None:
        """Full lifecycle: buy → age → can eventually re-enter market."""
        agent = _make_agent(current_vehicle=None, years_owned=0)
        agent.record_purchase("HYBRID")
        assert agent.profile.current_vehicle == "HYBRID"

        for _ in range(10):
            agent.age_one_tick()
        assert agent.profile.years_owned == 10
