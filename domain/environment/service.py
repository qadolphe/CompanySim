"""
Environment service — aggregate root for the Environment bounded context.

Owns the world clock and produces PolicySnapshot instances.
This is a read-only timeline: nothing in the simulation mutates it.
"""

from __future__ import annotations

from domain.environment.models import PolicySnapshot
import simulation.config as cfg


class EnvironmentService:
    """
    Aggregate root for the Environment context.

    Manages a deterministic, exogenous timeline of policy and economic
    conditions. Each call to tick() advances the clock by one year.
    The snapshot() method returns an immutable PolicySnapshot for the
    current year.

    This service is intentionally stateless beyond the clock position —
    all values are computed from schedules and formulas, not stored.
    """

    def __init__(
        self,
        start_year: int = cfg.START_YEAR,
        end_year: int = cfg.END_YEAR,
    ) -> None:
        if start_year > end_year:
            raise ValueError(
                f"start_year ({start_year}) must be <= end_year ({end_year})"
            )
        self._start_year = start_year
        self._end_year = end_year
        self._current_year = start_year

    # ── Clock ──

    @property
    def year(self) -> int:
        """Current simulation year."""
        return self._current_year

    @property
    def is_complete(self) -> bool:
        """True if the timeline has been fully traversed."""
        return self._current_year > self._end_year

    def tick(self) -> None:
        """Advance the clock by one year."""
        if self.is_complete:
            raise StopIteration(
                f"Environment has reached end of timeline ({self._end_year})"
            )
        self._current_year += 1

    # ── Snapshot ──

    def snapshot(self) -> PolicySnapshot:
        """
        Produce an immutable snapshot of all exogenous conditions
        for the current year.
        """
        return PolicySnapshot(
            year=self._current_year,
            ev_tax_credit=self._ev_tax_credit(),
            gas_price_per_gallon=self._gas_price(),
            electricity_price_per_kwh=self._electricity_price(),
            interest_rate=self._interest_rate(),
            emissions_penalty_per_unit=self._emissions_penalty(),
            cafe_ev_mandate_pct=self._cafe_ev_mandate(),
            charging_infrastructure_index=self._charging_infrastructure_index(),
        )

    # ── Private: Schedule Lookups ──

    @staticmethod
    def _lookup_schedule(schedule: dict[tuple[int, int], float], year: int) -> float:
        """
        Generic schedule lookup. Searches for the year range that
        contains the given year regardless of dict ordering.
        Falls back to the last bracket if year exceeds all ranges.
        """
        # Find exact match first
        for (start, end), value in schedule.items():
            if start <= year <= end:
                return value

        # Fallback: use the bracket with the highest end year
        max_range = max(schedule.keys(), key=lambda r: r[1])
        return schedule[max_range]

    def _ev_tax_credit(self) -> float:
        return self._lookup_schedule(cfg.EV_TAX_CREDIT_SCHEDULE, self._current_year)

    def _emissions_penalty(self) -> float:
        return self._lookup_schedule(cfg.EMISSIONS_PENALTY_SCHEDULE, self._current_year)

    def _cafe_ev_mandate(self) -> float:
        return self._lookup_schedule(cfg.CAFE_EV_MANDATE_SCHEDULE, self._current_year)

    def _interest_rate(self) -> float:
        return self._lookup_schedule(cfg.INTEREST_RATE_SCHEDULE, self._current_year)

    def _charging_infrastructure_index(self) -> float:
        return self._lookup_schedule(cfg.CHARGING_INFRASTRUCTURE_SCHEDULE, self._current_year)

    # ── Private: Compounding Economic Variables ──

    def _gas_price(self) -> float:
        """Gas price compounds annually from a base value."""
        years_elapsed = self._current_year - self._start_year
        return cfg.GAS_PRICE_BASE * ((1.0 + cfg.GAS_PRICE_ANNUAL_GROWTH) ** years_elapsed)

    def _electricity_price(self) -> float:
        """Electricity price compounds annually from a base value."""
        years_elapsed = self._current_year - self._start_year
        return cfg.ELECTRICITY_PRICE_BASE * (
            (1.0 + cfg.ELECTRICITY_PRICE_ANNUAL_GROWTH) ** years_elapsed
        )
