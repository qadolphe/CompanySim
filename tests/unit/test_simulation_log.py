"""
Unit tests for SimulationLog.
"""

import pytest
import pandas as pd

from simulation.log import SimulationLog
from domain.environment.models import PolicySnapshot
from domain.market.models import SalesRecord


@pytest.fixture
def log() -> SimulationLog:
    return SimulationLog()


@pytest.fixture
def sample_env() -> PolicySnapshot:
    return PolicySnapshot(
        year=2024, ev_tax_credit=7500, gas_price_per_gallon=3.50,
        electricity_price_per_kwh=0.14, interest_rate=0.07,
        emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
    )


@pytest.fixture
def sample_sales() -> dict[str, SalesRecord]:
    return {
        "ICE": SalesRecord("ICE", "ICE", 500, 16_000_000),
        "HYBRID": SalesRecord("HYBRID", "HYBRID", 200, 7_000_000),
        "EV": SalesRecord("EV", "EV", 100, 4_200_000),
    }


@pytest.fixture
def sample_producer_state() -> dict:
    return {
        "LegacyAutomaker": {
            "capital": 5_000_000_000,
            "total_capacity": 100_000,
            "capacity": {"ICE": 60000, "HYBRID": 25000, "EV": 15000},
            "msrp_reductions": {"ICE": 0.0, "HYBRID": 0.0, "EV": 0.0},
            "range_bonuses": {"ICE": 0.0, "HYBRID": 0.0, "EV": 0.0},
            "financials": {
                "capital": 5_000_000_000,
                "cumulative_revenue": 27_200_000,
            },
        }
    }


class TestSimulationLog:

    def test_empty_log_returns_empty_dataframe(self, log: SimulationLog) -> None:
        df = log.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_record_increases_tick_count(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(sample_env, sample_sales, sample_producer_state)
        assert log.tick_count == 1

    def test_dataframe_has_year_index(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(sample_env, sample_sales, sample_producer_state)
        df = log.to_dataframe()
        assert df.index.name == "year"
        assert 2024 in df.index

    def test_dataframe_has_environment_columns(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(sample_env, sample_sales, sample_producer_state)
        df = log.to_dataframe()
        assert "ev_tax_credit" in df.columns
        assert "gas_price_per_gallon" in df.columns

    def test_dataframe_has_sales_columns(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(sample_env, sample_sales, sample_producer_state)
        df = log.to_dataframe()
        assert "sales_ice_units" in df.columns
        assert "sales_ev_revenue" in df.columns
        assert "sales_total_units" in df.columns

    def test_market_share_sums_to_one(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(sample_env, sample_sales, sample_producer_state)
        df = log.to_dataframe()
        share_cols = [c for c in df.columns if c.startswith("share_type_")]
        total_share = df[share_cols].iloc[0].sum()
        assert total_share == pytest.approx(1.0, abs=0.001)

        share_cols_firm = [c for c in df.columns if c.startswith("share_firm_")]
        total_share_firm = df[share_cols_firm].iloc[0].sum()
        assert total_share_firm == pytest.approx(1.0, abs=0.001)

    def test_multi_tick_log(self, log, sample_sales, sample_producer_state) -> None:
        for yr in range(2024, 2027):
            env = PolicySnapshot(
                year=yr, ev_tax_credit=7500, gas_price_per_gallon=3.5,
                electricity_price_per_kwh=0.14, interest_rate=0.07,
                emissions_penalty_per_unit=0, cafe_ev_mandate_pct=0.1, charging_infrastructure_index=0.1,
            )
            log.record(env, sample_sales, sample_producer_state)
        df = log.to_dataframe()
        assert len(df) == 3
        assert list(df.index) == [2024, 2025, 2026]

    def test_consumer_stats_included(
        self, log, sample_env, sample_sales, sample_producer_state
    ) -> None:
        log.record(
            sample_env, sample_sales, sample_producer_state,
            consumer_stats={"consumers_shopping": 150, "consumers_bought": 120},
        )
        df = log.to_dataframe()
        assert "consumers_shopping" in df.columns
        assert df.iloc[0]["consumers_bought"] == 120

    def test_fleet_metrics_logged(self, log, sample_env, sample_sales, sample_producer_state) -> None:
        log.record(
            sample_env,
            sample_sales,
            sample_producer_state,
            consumer_stats={
                "consumers_shopping": 200,
                "consumers_bought": 150,
                "fleet_ice_pct": 0.62,
                "fleet_hybrid_pct": 0.23,
                "fleet_ev_pct": 0.15,
                "fleet_total_vehicles": 1_000,
            },
        )
        df = log.to_dataframe()
        assert df.iloc[0]["fleet_ice_pct"] == pytest.approx(0.62)
        assert df.iloc[0]["fleet_hybrid_pct"] == pytest.approx(0.23)
        assert df.iloc[0]["fleet_ev_pct"] == pytest.approx(0.15)
