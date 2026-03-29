"""
Contract tests for the ProducerAgent ABC.

Any implementation of ProducerAgent (LegacyAutomaker, EnergyCompany, etc.)
must pass these tests.
"""

import pytest

from domain.producer.agents import ProducerAgent, LegacyAutomaker
from domain.market.models import ProductOffering, SalesRecord
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(params=["legacy_automaker"])
def producer_agent(request) -> ProducerAgent:
    """
    Parametrized fixture. Add new ProducerAgent implementations here.
    """
    if request.param == "legacy_automaker":
        return LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )
    raise ValueError(f"Unknown producer type: {request.param}")


@pytest.fixture
def env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1,
    )


@pytest.fixture
def sample_sales() -> dict[str, SalesRecord]:
    return {
        "ICE": SalesRecord("ICE", units_sold=400, revenue=12_800_000),
        "HYBRID": SalesRecord("HYBRID", units_sold=180, revenue=6_300_000),
        "EV": SalesRecord("EV", units_sold=100, revenue=4_200_000),
    }


# ═══════════════════════════════════════════════════════════════════
# Contract Tests
# ═══════════════════════════════════════════════════════════════════

class TestProducerAgentContract:

    def test_is_subclass_of_abc(
        self, producer_agent: ProducerAgent
    ) -> None:
        assert isinstance(producer_agent, ProducerAgent)

    def test_generate_offerings_returns_list(
        self, producer_agent: ProducerAgent, env: PolicySnapshot
    ) -> None:
        offerings = producer_agent.generate_offerings(env)
        assert isinstance(offerings, list)
        assert len(offerings) > 0

    def test_offerings_are_product_offerings(
        self, producer_agent: ProducerAgent, env: PolicySnapshot
    ) -> None:
        offerings = producer_agent.generate_offerings(env)
        for o in offerings:
            assert isinstance(o, ProductOffering)

    def test_process_sales_does_not_raise(
        self,
        producer_agent: ProducerAgent,
        sample_sales: dict,
        env: PolicySnapshot,
    ) -> None:
        producer_agent.process_sales(sample_sales, env)

    def test_get_state_returns_dict(
        self, producer_agent: ProducerAgent
    ) -> None:
        state = producer_agent.get_state()
        assert isinstance(state, dict)

    def test_get_state_has_capital(
        self, producer_agent: ProducerAgent
    ) -> None:
        state = producer_agent.get_state()
        assert "capital" in state

    def test_process_sales_then_generate_offerings(
        self,
        producer_agent: ProducerAgent,
        sample_sales: dict,
        env: PolicySnapshot,
    ) -> None:
        """The full cycle should work: process sales, then generate new offerings."""
        producer_agent.process_sales(sample_sales, env)
        offerings = producer_agent.generate_offerings(env)
        assert isinstance(offerings, list)
        assert len(offerings) > 0
