"""
Producer domain models — value objects for corporate state tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# Annual Income Statement + Cash Flow
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AnnualFinancials:
    """One year's income statement and cash-flow summary."""
    year: int

    # ── Revenue & COGS by drivetrain ──
    revenue_by_dt: dict[str, float] = field(default_factory=dict)
    cogs_by_dt: dict[str, float] = field(default_factory=dict)

    # ── Operating Expenses ──
    sga: float = 0.0
    r_and_d: float = 0.0
    emissions_penalties: float = 0.0

    # ── Below the line ──
    depreciation: float = 0.0
    capex: float = 0.0
    taxes: float = 0.0
    external_funding: float = 0.0

    # ── Derived properties ──

    @property
    def revenue(self) -> float:
        return sum(self.revenue_by_dt.values())

    @property
    def cogs(self) -> float:
        return sum(self.cogs_by_dt.values())

    @property
    def gross_profit_by_dt(self) -> dict[str, float]:
        dts = set(self.revenue_by_dt) | set(self.cogs_by_dt)
        return {dt: self.revenue_by_dt.get(dt, 0) - self.cogs_by_dt.get(dt, 0)
                for dt in dts}

    @property
    def gross_profit(self) -> float:
        return self.revenue - self.cogs

    @property
    def total_opex(self) -> float:
        return self.sga + self.r_and_d + self.emissions_penalties

    @property
    def ebitda(self) -> float:
        return self.gross_profit - self.total_opex

    @property
    def ebit(self) -> float:
        return self.ebitda - self.depreciation

    @property
    def net_income(self) -> float:
        return self.ebit - self.taxes

    @property
    def free_cash_flow(self) -> float:
        return self.net_income + self.depreciation - self.capex + self.external_funding

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "revenue": self.revenue,
            "revenue_by_dt": dict(self.revenue_by_dt),
            "cogs_by_dt": dict(self.cogs_by_dt),
            "gross_profit": self.gross_profit,
            "gross_profit_by_dt": self.gross_profit_by_dt,
            "sga": self.sga,
            "r_and_d": self.r_and_d,
            "emissions_penalties": self.emissions_penalties,
            "ebitda": self.ebitda,
            "depreciation": self.depreciation,
            "ebit": self.ebit,
            "taxes": self.taxes,
            "net_income": self.net_income,
            "capex": self.capex,
            "external_funding": self.external_funding,
            "fcf": self.free_cash_flow,
        }


# ═══════════════════════════════════════════════════════════════════
# Capital Ledger — tick-level accumulator that produces AnnualFinancials
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CapitalLedger:
    """
    Tracks the financial state of a producer.

    Within a tick, callers use record_sale / record_opex / record_capex
    to accumulate line items.  At the end of the tick, close_year()
    freezes them into an AnnualFinancials, computes taxes, and resets.
    """
    capital: float
    cumulative_capex: float = 0.0
    history: list[AnnualFinancials] = field(default_factory=list)

    # ── Intra-tick accumulators ──
    _tick_revenue: dict[str, float] = field(default_factory=dict)
    _tick_cogs: dict[str, float] = field(default_factory=dict)
    _tick_sga: float = 0.0
    _tick_r_and_d: float = 0.0
    _tick_penalties: float = 0.0
    _tick_capex: float = 0.0
    _tick_external_funding: float = 0.0

    # ── Cumulative totals (kept for backward-compatible to_dict) ──
    cumulative_revenue: float = 0.0
    cumulative_cogs: float = 0.0
    cumulative_penalties: float = 0.0
    cumulative_r_and_d: float = 0.0
    cumulative_retooling: float = 0.0
    cumulative_units_by_dt: dict[str, int] = field(default_factory=dict)

    def record_sale(
        self,
        drivetrain: str,
        revenue: float,
        cogs: float,
        units_sold: int = 0,
    ) -> None:
        """Record per-drivetrain revenue and COGS; updates capital immediately."""
        self._tick_revenue[drivetrain] = self._tick_revenue.get(drivetrain, 0) + revenue
        self._tick_cogs[drivetrain] = self._tick_cogs.get(drivetrain, 0) + cogs
        if units_sold > 0:
            current = self.cumulative_units_by_dt.get(drivetrain, 0)
            self.cumulative_units_by_dt[drivetrain] = current + units_sold
        self.capital += (revenue - cogs)
        self.cumulative_revenue += revenue
        self.cumulative_cogs += cogs

    def record_opex(self, amount: float, category: str) -> None:
        """Record an operating expense (sga, r_and_d, or penalty)."""
        self.capital -= amount
        if category == "sga":
            self._tick_sga += amount
        elif category == "r_and_d":
            self._tick_r_and_d += amount
            self.cumulative_r_and_d += amount
        elif category == "penalty":
            self._tick_penalties += amount
            self.cumulative_penalties += amount

    def record_capex(self, amount: float) -> None:
        """Record capital expenditure (retooling)."""
        self.capital -= amount
        self._tick_capex += amount
        self.cumulative_capex += amount
        self.cumulative_retooling += amount

    def record_funding(self, amount: float) -> None:
        """Record external equity funding."""
        self.capital += amount
        self._tick_external_funding += amount

    def close_year(self, year: int, tax_rate: float, depreciation_rate: float) -> AnnualFinancials:
        """Freeze the tick into an AnnualFinancials, compute taxes, reset accumulators."""
        depreciation = self.cumulative_capex * depreciation_rate

        rev = sum(self._tick_revenue.values())
        cogs = sum(self._tick_cogs.values())
        pre_tax = (rev - cogs
                   - self._tick_sga - self._tick_r_and_d - self._tick_penalties
                   - depreciation)
        taxes = max(0.0, pre_tax * tax_rate)
        self.capital -= taxes

        stmt = AnnualFinancials(
            year=year,
            revenue_by_dt=dict(self._tick_revenue),
            cogs_by_dt=dict(self._tick_cogs),
            sga=self._tick_sga,
            r_and_d=self._tick_r_and_d,
            emissions_penalties=self._tick_penalties,
            depreciation=depreciation,
            capex=self._tick_capex,
            taxes=taxes,
            external_funding=self._tick_external_funding,
        )
        self.history.append(stmt)
        self._reset_accumulators()
        return stmt

    def _reset_accumulators(self) -> None:
        self._tick_revenue = {}
        self._tick_cogs = {}
        self._tick_sga = 0.0
        self._tick_r_and_d = 0.0
        self._tick_penalties = 0.0
        self._tick_capex = 0.0
        self._tick_external_funding = 0.0

    # ── Backward-compatible methods (used by old tests) ──

    def record_revenue(self, amount: float) -> None:
        self.capital += amount
        self.cumulative_revenue += amount

    def record_cost(self, amount: float, category: str = "cogs") -> None:
        self.capital -= amount
        if category == "cogs":
            self.cumulative_cogs += amount
        elif category == "penalty":
            self.cumulative_penalties += amount
        elif category == "r_and_d":
            self.cumulative_r_and_d += amount
        elif category == "retooling":
            self.cumulative_retooling += amount

    def to_dict(self) -> dict:
        return {
            "capital": self.capital,
            "cumulative_revenue": self.cumulative_revenue,
            "cumulative_cogs": self.cumulative_cogs,
            "cumulative_penalties": self.cumulative_penalties,
            "cumulative_r_and_d": self.cumulative_r_and_d,
            "cumulative_retooling": self.cumulative_retooling,
            "cumulative_units_by_dt": dict(self.cumulative_units_by_dt),
        }


@dataclass
class RAndDPipeline:
    """
    Tracks cumulative R&D investment by product category.
    When investment crosses a milestone threshold, effects are triggered.
    """
    investments: dict[str, float] = field(default_factory=dict)
    milestones_achieved: dict[str, int] = field(default_factory=dict)

    def invest(self, category: str, amount: float) -> None:
        """Add investment to a category."""
        self.investments[category] = self.investments.get(category, 0.0) + amount

    def get_investment(self, category: str) -> float:
        return self.investments.get(category, 0.0)

    def get_milestones(self, category: str) -> int:
        return self.milestones_achieved.get(category, 0)

    def check_and_award_milestones(
        self, category: str, threshold: float
    ) -> int:
        """
        Check if new milestones have been reached for a category.
        Returns the number of NEW milestones achieved this call.
        """
        total_invested = self.get_investment(category)
        total_milestones = int(total_invested // threshold)
        current = self.milestones_achieved.get(category, 0)
        new_milestones = total_milestones - current
        if new_milestones > 0:
            self.milestones_achieved[category] = total_milestones
        return max(0, new_milestones)

    def to_dict(self) -> dict:
        return {
            "investments": dict(self.investments),
            "milestones_achieved": dict(self.milestones_achieved),
        }
