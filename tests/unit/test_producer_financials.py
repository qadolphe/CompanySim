"""
Unit tests for producer financial mechanics.

Tests cover:
  - CapitalLedger operations
  - RAndDPipeline milestones
  - LegacyAutomaker financial flow (revenue → costs → capital)
"""

import pytest

from domain.producer.models import CapitalLedger, RAndDPipeline
from domain.producer.agents import LegacyAutomaker
from domain.market.models import SalesRecord
from domain.environment.models import PolicySnapshot


# ═══════════════════════════════════════════════════════════════════
# CapitalLedger
# ═══════════════════════════════════════════════════════════════════

class TestCapitalLedger:

    def test_initial_state(self) -> None:
        ledger = CapitalLedger(capital=1_000_000)
        assert ledger.capital == 1_000_000
        assert ledger.cumulative_revenue == 0

    def test_record_revenue(self) -> None:
        ledger = CapitalLedger(capital=1_000)
        ledger.record_revenue(500)
        assert ledger.capital == 1_500
        assert ledger.cumulative_revenue == 500

    def test_record_cost_reduces_capital(self) -> None:
        ledger = CapitalLedger(capital=1_000)
        ledger.record_cost(300, "cogs")
        assert ledger.capital == 700
        assert ledger.cumulative_cogs == 300

    def test_penalty_tracking(self) -> None:
        ledger = CapitalLedger(capital=1_000)
        ledger.record_cost(200, "penalty")
        assert ledger.cumulative_penalties == 200

    def test_to_dict(self) -> None:
        ledger = CapitalLedger(capital=5000)
        d = ledger.to_dict()
        assert "capital" in d
        assert d["capital"] == 5000


# ═══════════════════════════════════════════════════════════════════
# RAndDPipeline
# ═══════════════════════════════════════════════════════════════════

class TestRAndDPipeline:

    def test_invest_accumulates(self) -> None:
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 1_000_000)
        pipeline.invest("EV", 500_000)
        assert pipeline.get_investment("EV") == 1_500_000

    def test_milestone_not_reached(self) -> None:
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 500_000)
        new = pipeline.check_and_award_milestones("EV", 2_000_000_000)
        assert new == 0

    def test_milestone_reached(self) -> None:
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 2_000_000_000)
        new = pipeline.check_and_award_milestones("EV", 2_000_000_000)
        assert new == 1

    def test_multiple_milestones(self) -> None:
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 5_000_000_000)
        new = pipeline.check_and_award_milestones("EV", 2_000_000_000)
        assert new == 2  # 5B / 2B = 2 milestones

    def test_milestones_not_re_awarded(self) -> None:
        """Milestones should only fire once."""
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 2_000_000_000)
        first = pipeline.check_and_award_milestones("EV", 2_000_000_000)
        assert first == 1
        # Same check again — no new investment
        second = pipeline.check_and_award_milestones("EV", 2_000_000_000)
        assert second == 0

    def test_to_dict(self) -> None:
        pipeline = RAndDPipeline()
        pipeline.invest("EV", 100)
        d = pipeline.to_dict()
        assert "investments" in d
        assert d["investments"]["EV"] == 100


# ═══════════════════════════════════════════════════════════════════
# LegacyAutomaker Financial Flow
# ═══════════════════════════════════════════════════════════════════

class TestAutomakerFinancials:

    @pytest.fixture
    def env(self) -> PolicySnapshot:
        return PolicySnapshot(
            year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=500, cafe_ev_mandate_pct=0.1,
        )

    @pytest.fixture
    def automaker(self) -> LegacyAutomaker:
        return LegacyAutomaker(
            initial_capital=5_000_000_000,
            production_capacity={"ICE": 600, "HYBRID": 250, "EV": 150},
        )

    def test_process_sales_updates_capital(
        self, automaker: LegacyAutomaker, env: PolicySnapshot
    ) -> None:
        """Capital should change after processing sales."""
        initial = automaker.ledger.capital
        sales = {
            "ICE": SalesRecord("ICE", 500, 16_000_000),
            "HYBRID": SalesRecord("HYBRID", 200, 7_000_000),
            "EV": SalesRecord("EV", 100, 4_200_000),
        }
        automaker.process_sales(sales, env)
        assert automaker.ledger.capital != initial

    def test_emissions_penalty_applied(
        self, automaker: LegacyAutomaker, env: PolicySnapshot
    ) -> None:
        """Penalties should be deducted for ICE sales."""
        sales = {
            "ICE": SalesRecord("ICE", 100, 3_200_000),
            "HYBRID": SalesRecord("HYBRID", 0, 0),
            "EV": SalesRecord("EV", 0, 0),
        }
        automaker.process_sales(sales, env)
        # Penalty = 100 units × $500 = $50,000
        assert automaker.ledger.cumulative_penalties == pytest.approx(
            50_000, rel=0.01
        )

    def test_no_penalty_when_rate_is_zero(
        self, automaker: LegacyAutomaker
    ) -> None:
        env_no_penalty = PolicySnapshot(
            year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
            electricity_price_per_kwh=0.14, interest_rate=0.07,
            emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1,
        )
        sales = {"ICE": SalesRecord("ICE", 500, 16_000_000)}
        automaker.process_sales(sales, env_no_penalty)
        assert automaker.ledger.cumulative_penalties == 0.0

    def test_generate_catalog_returns_offerings(
        self, automaker: LegacyAutomaker, env: PolicySnapshot
    ) -> None:
        offerings = automaker.generate_offerings(env)
        assert len(offerings) == 3
        types = {o.product_type for o in offerings}
        assert types == {"ICE", "HYBRID", "EV"}

    def test_catalog_reflects_capacity(
        self, automaker: LegacyAutomaker, env: PolicySnapshot
    ) -> None:
        """Each offering's units_available should match production capacity."""
        offerings = automaker.generate_offerings(env)
        for o in offerings:
            assert o.units_available == automaker.capacity[o.product_type]

    def test_state_snapshot(
        self, automaker: LegacyAutomaker
    ) -> None:
        state = automaker.get_state()
        assert "capital" in state
        assert "capacity" in state
        assert "r_and_d" in state
        assert "financials" in state
