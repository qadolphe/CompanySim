"""
Unit tests for the Environment bounded context.

Tests cover:
  - Clock mechanics (tick, boundaries, is_complete)
  - Policy schedule lookups (EV credit, emissions, CAFE, interest)
  - Compounding economic variables (gas price, electricity)
  - PolicySnapshot immutability and data contract
"""

import pytest

from domain.environment.service import EnvironmentService
from domain.environment.models import PolicySnapshot
from simulation.config import (
    START_YEAR,
    END_YEAR,
    GAS_PRICE_BASE,
    GAS_PRICE_ANNUAL_GROWTH,
    ELECTRICITY_PRICE_BASE,
    ELECTRICITY_PRICE_ANNUAL_GROWTH,
)


# ═══════════════════════════════════════════════════════════════════
# Clock Mechanics
# ═══════════════════════════════════════════════════════════════════

class TestClock:
    """Tests for the EnvironmentService clock."""

    def test_initial_year(self, env_service: EnvironmentService) -> None:
        assert env_service.year == START_YEAR

    def test_tick_advances_year(self, env_service: EnvironmentService) -> None:
        env_service.tick()
        assert env_service.year == START_YEAR + 1

    def test_tick_sequence(self, env_service: EnvironmentService) -> None:
        for i in range(1, 6):
            env_service.tick()
            assert env_service.year == START_YEAR + i

    def test_full_traversal(self, env_service: EnvironmentService) -> None:
        """Tick through the entire timeline and verify we get all valid years."""
        years_seen = [env_service.year]
        while not env_service.is_complete:
            env_service.tick()
            if not env_service.is_complete:
                years_seen.append(env_service.year)
        # Should have snapshots for every year from START to END inclusive
        assert years_seen == list(range(START_YEAR, END_YEAR + 1))
        assert env_service.is_complete

    def test_tick_past_end_raises(self, env_service: EnvironmentService) -> None:
        """Ticking past the end of the timeline raises StopIteration."""
        while not env_service.is_complete:
            env_service.tick()
        with pytest.raises(StopIteration):
            env_service.tick()

    def test_is_complete_false_initially(
        self, env_service: EnvironmentService
    ) -> None:
        assert not env_service.is_complete

    def test_invalid_year_range(self) -> None:
        with pytest.raises(ValueError):
            EnvironmentService(start_year=2035, end_year=2024)

    def test_single_year_range(self) -> None:
        """A single-year sim should work: start == end, one snapshot, one tick to complete."""
        svc = EnvironmentService(start_year=2024, end_year=2024)
        assert svc.year == 2024
        assert not svc.is_complete
        snap = svc.snapshot()
        assert snap.year == 2024
        svc.tick()
        assert svc.is_complete


# ═══════════════════════════════════════════════════════════════════
# Policy Schedule Lookups
# ═══════════════════════════════════════════════════════════════════

class TestPolicySchedules:
    """Verify that step-function policy schedules return correct values."""

    def test_ev_tax_credit_2024(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        assert env_snapshot_2024.ev_tax_credit == 7_500.0

    def test_ev_tax_credit_2026(self) -> None:
        svc = EnvironmentService(2024, 2035)
        for _ in range(2):
            svc.tick()
        snap = svc.snapshot()
        assert snap.year == 2026
        assert snap.ev_tax_credit == 7_500.0  # 2024-2026 bracket

    def test_ev_tax_credit_2027(self) -> None:
        svc = EnvironmentService(2024, 2035)
        for _ in range(3):
            svc.tick()
        snap = svc.snapshot()
        assert snap.year == 2027
        assert snap.ev_tax_credit == 5_000.0  # 2027-2029 bracket

    def test_ev_tax_credit_2030(
        self, env_snapshot_2030: PolicySnapshot
    ) -> None:
        assert env_snapshot_2030.ev_tax_credit == 2_500.0

    def test_emissions_penalty_starts_zero(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        assert env_snapshot_2024.emissions_penalty_per_unit == 0.0

    def test_emissions_penalty_ramps_up(
        self, env_snapshot_2030: PolicySnapshot
    ) -> None:
        assert env_snapshot_2030.emissions_penalty_per_unit == 1_000.0

    def test_cafe_mandate_increases(
        self, all_snapshots: list[PolicySnapshot]
    ) -> None:
        """CAFE EV mandate should be non-decreasing over time."""
        mandates = [s.cafe_ev_mandate_pct for s in all_snapshots]
        for i in range(1, len(mandates)):
            assert mandates[i] >= mandates[i - 1], (
                f"CAFE mandate decreased from year {all_snapshots[i-1].year} "
                f"to {all_snapshots[i].year}"
            )

    def test_interest_rate_decreases_over_time(
        self, all_snapshots: list[PolicySnapshot]
    ) -> None:
        """Interest rates should be non-increasing over the timeline."""
        rates = [s.interest_rate for s in all_snapshots]
        for i in range(1, len(rates)):
            assert rates[i] <= rates[i - 1], (
                f"Interest rate increased from year {all_snapshots[i-1].year} "
                f"to {all_snapshots[i].year}"
            )


# ═══════════════════════════════════════════════════════════════════
# Compounding Economic Variables
# ═══════════════════════════════════════════════════════════════════

class TestEconomicVariables:
    """Verify that compounding economic variables calculate correctly."""

    def test_gas_price_at_start(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        assert env_snapshot_2024.gas_price_per_gallon == pytest.approx(
            GAS_PRICE_BASE, rel=1e-6
        )

    def test_gas_price_compounds(self) -> None:
        """Gas price after N years should equal base × (1 + growth)^N."""
        svc = EnvironmentService(2024, 2035)
        for _ in range(5):
            svc.tick()
        snap = svc.snapshot()
        expected = GAS_PRICE_BASE * ((1 + GAS_PRICE_ANNUAL_GROWTH) ** 5)
        assert snap.gas_price_per_gallon == pytest.approx(expected, rel=1e-6)

    def test_gas_price_monotonically_increases(
        self, all_snapshots: list[PolicySnapshot]
    ) -> None:
        prices = [s.gas_price_per_gallon for s in all_snapshots]
        for i in range(1, len(prices)):
            assert prices[i] > prices[i - 1]

    def test_electricity_price_at_start(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        assert env_snapshot_2024.electricity_price_per_kwh == pytest.approx(
            ELECTRICITY_PRICE_BASE, rel=1e-6
        )

    def test_electricity_price_compounds(self) -> None:
        svc = EnvironmentService(2024, 2035)
        for _ in range(5):
            svc.tick()
        snap = svc.snapshot()
        expected = ELECTRICITY_PRICE_BASE * (
            (1 + ELECTRICITY_PRICE_ANNUAL_GROWTH) ** 5
        )
        assert snap.electricity_price_per_kwh == pytest.approx(
            expected, rel=1e-6
        )

    def test_electricity_price_monotonically_increases(
        self, all_snapshots: list[PolicySnapshot]
    ) -> None:
        prices = [s.electricity_price_per_kwh for s in all_snapshots]
        for i in range(1, len(prices)):
            assert prices[i] > prices[i - 1]


# ═══════════════════════════════════════════════════════════════════
# PolicySnapshot Data Contract
# ═══════════════════════════════════════════════════════════════════

class TestPolicySnapshot:
    """Verify the PolicySnapshot value object contract."""

    def test_snapshot_is_frozen(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        """PolicySnapshot should be immutable."""
        with pytest.raises(AttributeError):
            env_snapshot_2024.year = 9999  # type: ignore[misc]

    def test_snapshot_has_all_fields(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        required_fields = {
            "year",
            "ev_tax_credit",
            "gas_price_per_gallon",
            "electricity_price_per_kwh",
            "interest_rate",
            "emissions_penalty_per_unit",
            "cafe_ev_mandate_pct",
        }
        actual_fields = set(env_snapshot_2024.to_dict().keys())
        assert actual_fields == required_fields

    def test_to_dict_values_match_attributes(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        d = env_snapshot_2024.to_dict()
        assert d["year"] == env_snapshot_2024.year
        assert d["ev_tax_credit"] == env_snapshot_2024.ev_tax_credit
        assert d["gas_price_per_gallon"] == env_snapshot_2024.gas_price_per_gallon
        assert d["interest_rate"] == env_snapshot_2024.interest_rate

    def test_to_dict_returns_new_dict(
        self, env_snapshot_2024: PolicySnapshot
    ) -> None:
        """Modifying the dict should not affect the snapshot."""
        d = env_snapshot_2024.to_dict()
        d["year"] = 9999
        assert env_snapshot_2024.year != 9999

    def test_snapshots_are_independent(self) -> None:
        """Two snapshots from different years should have different values."""
        svc = EnvironmentService(2024, 2035)
        snap_a = svc.snapshot()
        svc.tick()
        snap_b = svc.snapshot()
        assert snap_a.year != snap_b.year
        assert snap_a.gas_price_per_gallon != snap_b.gas_price_per_gallon
