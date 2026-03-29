"""
Contract tests for the ConsumerAgent ABC.

Any implementation of ConsumerAgent (AutoConsumer, HousingConsumer, etc.)
must pass these tests. They verify the behavioral contract, not the
specific economic logic.
"""

import pytest

from domain.consumer.agents import ConsumerAgent, AutoConsumer
from domain.consumer.models import ConsumerProfile
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Fixtures — implementations to test against the contract
# ═══════════════════════════════════════════════════════════════════

def _make_auto_consumer(**overrides) -> AutoConsumer:
    defaults = dict(
        id=0, annual_income=65_000, annual_commute_miles=7_500,
        green_preference=0.5, price_sensitivity=0.5,
        is_homeowner=True,
        current_vehicle="ICE", years_owned=7,
    )
    defaults.update(overrides)
    return AutoConsumer(ConsumerProfile(**defaults))


@pytest.fixture(params=["auto"])
def consumer_agent(request) -> ConsumerAgent:
    """
    Parametrized fixture — add new implementations here as they're built.
    Each implementation will run through every contract test below.
    """
    if request.param == "auto":
        return _make_auto_consumer()
    raise ValueError(f"Unknown consumer type: {request.param}")


@pytest.fixture
def sample_env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1,
    )


@pytest.fixture
def sample_offerings() -> list[dict]:
    return [
        {"product_type": "ICE", "msrp": 32_000, "mpg": 30,
         "range_mi": 400, "annual_maintenance": 1200, "kwh_per_mile": None},
        {"product_type": "EV", "msrp": 42_000, "mpg": None,
         "range_mi": 300, "annual_maintenance": 600, "kwh_per_mile": 0.3},
    ]


# ═══════════════════════════════════════════════════════════════════
# Contract Tests — any ConsumerAgent must satisfy these
# ═══════════════════════════════════════════════════════════════════

class TestConsumerAgentContract:
    """
    Behavioral contract for ConsumerAgent. These test the interface,
    not the implementation details.
    """

    def test_is_subclass_of_abc(self, consumer_agent: ConsumerAgent) -> None:
        assert isinstance(consumer_agent, ConsumerAgent)

    def test_is_in_market_returns_bool(
        self, consumer_agent: ConsumerAgent
    ) -> None:
        result = consumer_agent.is_in_market()
        assert isinstance(result, bool)

    def test_evaluate_and_choose_returns_str_or_none(
        self,
        consumer_agent: ConsumerAgent,
        sample_offerings: list[dict],
        sample_env: PolicySnapshot,
    ) -> None:
        result = consumer_agent.evaluate_and_choose(sample_offerings, sample_env)
        assert result is None or isinstance(result, str)

    def test_evaluate_and_choose_empty_catalog_returns_none(
        self,
        consumer_agent: ConsumerAgent,
        sample_env: PolicySnapshot,
    ) -> None:
        result = consumer_agent.evaluate_and_choose([], sample_env)
        assert result is None

    def test_record_purchase_does_not_raise(
        self, consumer_agent: ConsumerAgent
    ) -> None:
        """record_purchase should not raise for a valid product type."""
        consumer_agent.record_purchase("ICE")

    def test_age_one_tick_does_not_raise(
        self, consumer_agent: ConsumerAgent
    ) -> None:
        consumer_agent.age_one_tick()

    def test_has_profile(self, consumer_agent: ConsumerAgent) -> None:
        profile = consumer_agent.profile
        assert isinstance(profile, ConsumerProfile)
        assert hasattr(profile, "id")
        assert hasattr(profile, "annual_income")

    def test_purchase_affects_market_eligibility(
        self, consumer_agent: ConsumerAgent
    ) -> None:
        """After purchasing, the agent should NOT be in market immediately."""
        consumer_agent.record_purchase("ICE")
        assert not consumer_agent.is_in_market()
