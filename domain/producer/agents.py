"""
Producer agents — corporate entities that produce goods and adjust strategy.

Contains the abstract ProducerAgent contract and the auto-industry
LegacyAutomaker and PureEVStartup implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import math

from domain.environment.models import PolicySnapshot
from domain.market.models import ProductOffering, VehicleOffering, SalesRecord
from domain.producer.models import AnnualFinancials, CapitalLedger, RAndDPipeline
from domain.producer.strategy import StrategyEngine
from simulation.config import (
    INITIAL_CAPITAL,
    PRODUCTION_CAPACITY,
    CAPACITY_SHIFT_MAX_UNITS,
    COGS_PCT_BY_DRIVETRAIN,
    EV_COGS_MIN,
    EV_COGS_MAX,
    EV_COGS_LEARNING_RATE,
    EV_COGS_REFERENCE_UNITS,
    EV_BATTERY_DECLINE_TO_2030,
    EV_RND_COGS_REDUCTION,
    DEFAULT_VEHICLE_CATALOG,
    DRIVETRAINS,
    EV_RND_MILESTONE_COST,
    EV_RND_MSRP_REDUCTION_PCT,
    EV_RND_RANGE_BONUS_MI,
    HYBRID_RND_MILESTONE_COST,
    HYBRID_RND_MSRP_REDUCTION_PCT,
    RETOOLING_COST_PER_UNIT,
    R_AND_D_PCT_LEGACY,
    R_AND_D_PCT_STARTUP,
    R_AND_D_FLOOR_LEGACY,
    R_AND_D_FLOOR_STARTUP,
    SGA_FIXED_LEGACY,
    SGA_FIXED_STARTUP,
    SGA_VARIABLE_PCT,
    DEPRECIATION_RATE,
    CORPORATE_TAX_RATE,
    STARTUP_FUNDING_ROUNDS,
    START_YEAR,
)
from domain.environment.service import EnvironmentService


def _compute_dynamic_ev_cogs_pct(
    year: int,
    cumulative_ev_units: int,
    milestones: int,
    charging_infra_index: float,
) -> float:
    """
    Dynamic EV COGS ratio using:
      1) Battery learning over time (to 2030)
      2) Wright's Law volume effect from cumulative EV production
      3) Existing R&D milestone improvements
    """
    base = COGS_PCT_BY_DRIVETRAIN["EV"]

    # Time-based battery decline proxy toward 2030.
    denom = max(1, 2030 - START_YEAR)
    progress = max(0.0, min(1.0, (min(year, 2030) - START_YEAR) / denom))
    battery_factor = 1.0 - EV_BATTERY_DECLINE_TO_2030 * progress

    # Wright's Law: each cumulative doubling reduces cost by learning_rate.
    reference = max(1, EV_COGS_REFERENCE_UNITS)
    observed_units = max(cumulative_ev_units, reference)
    learning_exp = math.log2(max(1e-6, 1.0 - EV_COGS_LEARNING_RATE))
    volume_factor = (observed_units / reference) ** learning_exp

    # Better charging ecosystem modestly improves effective EV production economics.
    infra_factor = 1.0 - 0.08 * max(0.0, min(charging_infra_index, 1.0))

    cogs_pct = base * battery_factor * volume_factor * infra_factor
    cogs_pct -= milestones * EV_RND_COGS_REDUCTION
    return max(EV_COGS_MIN, min(EV_COGS_MAX, cogs_pct))


# ═══════════════════════════════════════════════════════════════════
# Abstract Contract
# ═══════════════════════════════════════════════════════════════════

class ProducerAgent(ABC):
    """
    Abstract producer agent. Any corporate entity in any domain
    must implement these methods.

    The simulation engine interacts only through this contract.
    """

    @abstractmethod
    def generate_offerings(
        self, env: PolicySnapshot
    ) -> list[ProductOffering]:
        ...

    @abstractmethod
    def process_sales(
        self, sales: dict[str, SalesRecord], env: PolicySnapshot
    ) -> None:
        ...

    @abstractmethod
    def get_state(self) -> dict:
        ...


# ═══════════════════════════════════════════════════════════════════
# Auto Industry Implementation — Legacy Automaker
# ═══════════════════════════════════════════════════════════════════

class LegacyAutomaker(ProducerAgent):
    """
    A legacy automaker transitioning from ICE to EV.

    Each tick:
      1. Generate catalog (apply R&D effects to base specs)
      2. Process sales → full P&L: revenue, per-dt COGS, SGA, R&D,
         penalties, depreciation, taxes → close_year()
      3. Adjust production capacity
    """

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        production_capacity: dict[str, int] | None = None,
        base_catalog: dict | None = None,
    ) -> None:
        self.ledger = CapitalLedger(capital=initial_capital)
        self.capacity = dict(production_capacity or PRODUCTION_CAPACITY)
        self.pipeline = RAndDPipeline()
        self.strategy = StrategyEngine()
        self._base_catalog = deepcopy(base_catalog or DEFAULT_VEHICLE_CATALOG)

        self._msrp_reductions: dict[str, float] = {dt: 0.0 for dt in DRIVETRAINS}
        self._range_bonuses: dict[str, float] = {dt: 0.0 for dt in DRIVETRAINS}
        self._last_sales: dict[str, SalesRecord] | None = None
        self._last_stmt: AnnualFinancials | None = None
        self._consecutive_negative_fcf: int = 0

    def generate_offerings(
        self, env: PolicySnapshot
    ) -> list[ProductOffering]:
        offerings: list[VehicleOffering] = []
        for dt in DRIVETRAINS:
            base = self._base_catalog[dt]
            msrp = base["msrp"] * (1.0 - self._msrp_reductions[dt])
            range_mi = base["range_mi"] + self._range_bonuses.get(dt, 0.0)
            offerings.append(VehicleOffering(
                drivetrain=dt,
                msrp=round(msrp, 2),
                mpg=base["mpg"],
                range_mi=round(range_mi, 1),
                annual_maintenance=base["annual_maintenance"],
                kwh_per_mile=base.get("kwh_per_mile"),
                _units_available=self.capacity.get(dt, 0),
            ))
        return offerings

    def process_sales(
        self, sales: dict[str, SalesRecord], env: PolicySnapshot
    ) -> None:
        self._last_sales = sales

        # ── 1. Per-drivetrain Revenue & COGS ──
        ev_milestones = self.pipeline.get_milestones("EV")
        ev_cogs_pct = _compute_dynamic_ev_cogs_pct(
            year=env.year,
            cumulative_ev_units=self.ledger.cumulative_units_by_dt.get("EV", 0),
            milestones=ev_milestones,
            charging_infra_index=env.charging_infrastructure_index,
        )
        total_revenue = 0.0
        for dt, record in sales.items():
            rev = record.revenue
            total_revenue += rev
            cogs_pct = COGS_PCT_BY_DRIVETRAIN.get(dt, 0.83)
            if dt == "EV":
                cogs_pct = ev_cogs_pct
            cogs = rev * cogs_pct
            self.ledger.record_sale(dt, rev, cogs, units_sold=record.units_sold)

        # ── 2. SG&A ──
        sga = SGA_FIXED_LEGACY + total_revenue * SGA_VARIABLE_PCT
        self.ledger.record_opex(sga, "sga")

        # ── 3. Emissions Penalties ──
        ice_sales = sales.get("ICE")
        if ice_sales and env.emissions_penalty_per_unit > 0:
            penalty = ice_sales.units_sold * env.emissions_penalty_per_unit
            self.ledger.record_opex(penalty, "penalty")

        # ── 4. R&D Allocation ──
        target_r_and_d = max(R_AND_D_FLOOR_LEGACY, total_revenue * R_AND_D_PCT_LEGACY)
        available_cash = max(0.0, self.ledger.capital)
        r_and_d_budget = min(target_r_and_d, available_cash)
        r_and_d_alloc = self.strategy.compute_r_and_d_allocation(
            r_and_d_budget, sales, DRIVETRAINS
        )
        for dt, amount in r_and_d_alloc.items():
            if amount > 0:
                self.pipeline.invest(dt, amount)
                self.ledger.record_opex(amount, "r_and_d")

        # ── 5. R&D Milestones ──
        self._apply_milestones()

        # ── 6. Capacity Reallocation ──
        shifts = self.strategy.compute_capacity_shifts(sales, self.capacity)
        retooling_cost = self.strategy.compute_retooling_cost(shifts)
        if retooling_cost > 0:
            self.ledger.record_capex(retooling_cost)
        for dt, shift in shifts.items():
            self.capacity[dt] = max(0, self.capacity[dt] + shift)

        # ── 7. Close the year ──
        stmt = self.ledger.close_year(env.year, CORPORATE_TAX_RATE, DEPRECIATION_RATE)
        self._last_stmt = stmt
        if stmt.free_cash_flow < 0:
            self._consecutive_negative_fcf += 1
        else:
            self._consecutive_negative_fcf = 0

    def _apply_milestones(self) -> None:
        new_ev = self.pipeline.check_and_award_milestones("EV", EV_RND_MILESTONE_COST)
        if new_ev > 0:
            self._msrp_reductions["EV"] += new_ev * EV_RND_MSRP_REDUCTION_PCT
            self._range_bonuses["EV"] += new_ev * EV_RND_RANGE_BONUS_MI
        new_hybrid = self.pipeline.check_and_award_milestones("HYBRID", HYBRID_RND_MILESTONE_COST)
        if new_hybrid > 0:
            self._msrp_reductions["HYBRID"] += new_hybrid * HYBRID_RND_MSRP_REDUCTION_PCT

    @property
    def ev_cogs_pct(self) -> float:
        milestones = self.pipeline.get_milestones("EV")
        return _compute_dynamic_ev_cogs_pct(
            year=START_YEAR + len(self.ledger.history),
            cumulative_ev_units=self.ledger.cumulative_units_by_dt.get("EV", 0),
            milestones=milestones,
            charging_infra_index=0.5,
        )

    def get_state(self) -> dict:
        stmt = self._last_stmt
        stmt_dict = stmt.to_dict() if stmt else {}
        rev = stmt.revenue if stmt else 0.0
        return {
            "firm": "LegacyAutomaker",
            "capital": self.ledger.capital,
            "is_bankrupt": False,
            "capacity": dict(self.capacity),
            "total_capacity": sum(self.capacity.values()),
            # ── Income Statement ──
            "revenue": stmt_dict.get("revenue", 0),
            "revenue_by_dt": stmt_dict.get("revenue_by_dt", {}),
            "cogs_by_dt": stmt_dict.get("cogs_by_dt", {}),
            "gross_profit": stmt_dict.get("gross_profit", 0),
            "gross_profit_by_dt": stmt_dict.get("gross_profit_by_dt", {}),
            "sga": stmt_dict.get("sga", 0),
            "r_and_d": stmt_dict.get("r_and_d", 0),
            "emissions_penalties": stmt_dict.get("emissions_penalties", 0),
            "ebitda": stmt_dict.get("ebitda", 0),
            "depreciation": stmt_dict.get("depreciation", 0),
            "ebit": stmt_dict.get("ebit", 0),
            "taxes": stmt_dict.get("taxes", 0),
            "net_income": stmt_dict.get("net_income", 0),
            # ── Cash Flow ──
            "capex": stmt_dict.get("capex", 0),
            "external_funding": stmt_dict.get("external_funding", 0),
            "fcf": stmt_dict.get("fcf", 0),
            # ── Ratios ──
            "gross_margin_pct": (stmt.gross_profit / rev) if stmt and rev else 0,
            "ev_cogs_pct": self.ev_cogs_pct,
            "ev_gross_margin_pct": (
                (stmt.gross_profit_by_dt.get("EV", 0) / stmt.revenue_by_dt.get("EV", 1))
                if stmt and stmt.revenue_by_dt.get("EV") else 0
            ),
            # ── R&D Pipeline ──
            "r_and_d_investments": dict(self.pipeline.investments),
            "milestones_achieved": dict(self.pipeline.milestones_achieved),
            "msrp_reductions": dict(self._msrp_reductions),
            "range_bonuses": dict(self._range_bonuses),
            # ── Backward-compat ──
            "financials": self.ledger.to_dict(),
        }


# ═══════════════════════════════════════════════════════════════════
# Pure EV Startup Implementation
# ═══════════════════════════════════════════════════════════════════

class PureEVStartup(ProducerAgent):
    """
    A pure-play EV startup. No legacy lines, no dealer overhead.
    Survives on external funding until EV margins turn positive.
    """

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        production_capacity: int = 0,
        base_ev_spec: dict | None = None,
    ) -> None:
        self.ledger = CapitalLedger(capital=initial_capital)
        self.capacity = {"EV": production_capacity}
        self.pipeline = RAndDPipeline()
        self.is_bankrupt: bool = False

        self._base_spec = deepcopy(base_ev_spec or DEFAULT_VEHICLE_CATALOG["EV"])
        if base_ev_spec is None:
            self._base_spec["msrp"] -= 3000
            self._base_spec["range_mi"] += 40

        self._msrp_reduction = 0.0
        self._range_bonus = 0.0
        self._last_sales: dict[str, SalesRecord] | None = None
        self._last_stmt: AnnualFinancials | None = None

    def generate_offerings(
        self, env: PolicySnapshot
    ) -> list[ProductOffering]:
        if self.is_bankrupt:
            return []
        msrp = self._base_spec["msrp"] * (1.0 - self._msrp_reduction)
        range_mi = self._base_spec["range_mi"] + self._range_bonus
        offering = VehicleOffering(
            drivetrain="EV",
            msrp=round(msrp, 2),
            mpg=None,
            range_mi=round(range_mi, 1),
            annual_maintenance=self._base_spec["annual_maintenance"],
            kwh_per_mile=self._base_spec.get("kwh_per_mile"),
            _producer_id="PureEVStartup",
            _units_available=self.capacity.get("EV", 0),
        )
        return [offering]

    def process_sales(
        self, sales: dict[str, SalesRecord], env: PolicySnapshot
    ) -> None:
        if self.is_bankrupt:
            return
        self._last_sales = sales

        # ── 0. External funding injection ──
        funding = self._get_funding(env.year)
        if funding > 0:
            self.ledger.record_funding(funding)

        ev_sales = sales.get("EV")

        # ── 1. Revenue & COGS ──
        ev_milestones = self.pipeline.get_milestones("EV")
        ev_cogs_pct = _compute_dynamic_ev_cogs_pct(
            year=env.year,
            cumulative_ev_units=self.ledger.cumulative_units_by_dt.get("EV", 0),
            milestones=ev_milestones,
            charging_infra_index=env.charging_infrastructure_index,
        )
        if ev_sales and ev_sales.revenue > 0:
            rev = ev_sales.revenue
            cogs = rev * ev_cogs_pct
            self.ledger.record_sale("EV", rev, cogs, units_sold=ev_sales.units_sold)
        else:
            rev = 0.0

        # ── 2. SG&A ──
        sga = SGA_FIXED_STARTUP + rev * SGA_VARIABLE_PCT
        self.ledger.record_opex(sga, "sga")

        # ── 3. R&D ──
        target_r_and_d = max(R_AND_D_FLOOR_STARTUP, rev * R_AND_D_PCT_STARTUP)
        r_and_d_total = min(max(0.0, self.ledger.capital), target_r_and_d)
        if r_and_d_total > 0:
            self.pipeline.invest("EV", r_and_d_total)
            self.ledger.record_opex(r_and_d_total, "r_and_d")

        # ── 4. R&D Milestones ──
        new_ev = self.pipeline.check_and_award_milestones("EV", EV_RND_MILESTONE_COST)
        if new_ev > 0:
            self._msrp_reduction += new_ev * EV_RND_MSRP_REDUCTION_PCT
            self._range_bonus += new_ev * EV_RND_RANGE_BONUS_MI

        # ── 5. Capacity expansion ──
        if ev_sales and ev_sales.units_sold > 0 and ev_sales.units_sold >= self.capacity["EV"] * 0.9:
            shift = CAPACITY_SHIFT_MAX_UNITS
            retooling_cost = shift * RETOOLING_COST_PER_UNIT
            if self.ledger.capital >= retooling_cost:
                self.capacity["EV"] += shift
                self.ledger.record_capex(retooling_cost)

        # ── 6. Close the year ──
        stmt = self.ledger.close_year(env.year, CORPORATE_TAX_RATE, DEPRECIATION_RATE)
        self._last_stmt = stmt

        # ── 7. Bankruptcy check ──
        has_future_funding = any(
            v > 0 for (s, e), v in STARTUP_FUNDING_ROUNDS.items() if e > env.year
        )
        if self.ledger.capital < 0 and not has_future_funding:
            self.is_bankrupt = True

    @staticmethod
    def _get_funding(year: int) -> float:
        return EnvironmentService._lookup_schedule(STARTUP_FUNDING_ROUNDS, year)

    @property
    def ev_cogs_pct(self) -> float:
        milestones = self.pipeline.get_milestones("EV")
        return _compute_dynamic_ev_cogs_pct(
            year=START_YEAR + len(self.ledger.history),
            cumulative_ev_units=self.ledger.cumulative_units_by_dt.get("EV", 0),
            milestones=milestones,
            charging_infra_index=0.5,
        )

    def get_state(self) -> dict:
        stmt = self._last_stmt
        stmt_dict = stmt.to_dict() if stmt else {}
        rev = stmt.revenue if stmt else 0.0
        return {
            "firm": "PureEVStartup",
            "capital": self.ledger.capital,
            "is_bankrupt": self.is_bankrupt,
            "capacity": dict(self.capacity),
            "total_capacity": sum(self.capacity.values()),
            "revenue": stmt_dict.get("revenue", 0),
            "revenue_by_dt": stmt_dict.get("revenue_by_dt", {}),
            "cogs_by_dt": stmt_dict.get("cogs_by_dt", {}),
            "gross_profit": stmt_dict.get("gross_profit", 0),
            "gross_profit_by_dt": stmt_dict.get("gross_profit_by_dt", {}),
            "sga": stmt_dict.get("sga", 0),
            "r_and_d": stmt_dict.get("r_and_d", 0),
            "emissions_penalties": stmt_dict.get("emissions_penalties", 0),
            "ebitda": stmt_dict.get("ebitda", 0),
            "depreciation": stmt_dict.get("depreciation", 0),
            "ebit": stmt_dict.get("ebit", 0),
            "taxes": stmt_dict.get("taxes", 0),
            "net_income": stmt_dict.get("net_income", 0),
            "capex": stmt_dict.get("capex", 0),
            "external_funding": stmt_dict.get("external_funding", 0),
            "fcf": stmt_dict.get("fcf", 0),
            "gross_margin_pct": (stmt.gross_profit / rev) if stmt and rev else 0,
            "ev_cogs_pct": self.ev_cogs_pct,
            "ev_gross_margin_pct": (
                (stmt.gross_profit_by_dt.get("EV", 0) / stmt.revenue_by_dt.get("EV", 1))
                if stmt and stmt.revenue_by_dt.get("EV") else 0
            ),
            "r_and_d_investments": dict(self.pipeline.investments),
            "milestones_achieved": dict(self.pipeline.milestones_achieved),
            "msrp_reductions": {"EV": self._msrp_reduction},
            "range_bonuses": {"EV": self._range_bonus},
            "financials": self.ledger.to_dict(),
        }
