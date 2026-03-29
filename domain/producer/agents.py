"""
Producer agents — corporate entities that produce goods and adjust strategy.

Contains the abstract ProducerAgent contract and the auto-industry
LegacyAutomaker implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy

from domain.environment.models import PolicySnapshot
from domain.market.models import ProductOffering, VehicleOffering, SalesRecord
from domain.producer.models import CapitalLedger, RAndDPipeline
from domain.producer.strategy import StrategyEngine
from simulation.config import (
    INITIAL_CAPITAL,
    PRODUCTION_CAPACITY,
    COGS_PCT,
    DEFAULT_VEHICLE_CATALOG,
    DRIVETRAINS,
    EV_RND_MILESTONE_COST,
    EV_RND_MSRP_REDUCTION_PCT,
    EV_RND_RANGE_BONUS_MI,
    HYBRID_RND_MILESTONE_COST,
    HYBRID_RND_MSRP_REDUCTION_PCT,
)


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
        """Produce the catalog of products for this tick."""
        ...

    @abstractmethod
    def process_sales(
        self, sales: dict[str, SalesRecord], env: PolicySnapshot
    ) -> None:
        """
        Ingest sales results and update internal state:
        revenue, costs, strategy adjustments.
        """
        ...

    @abstractmethod
    def get_state(self) -> dict:
        """Return a snapshot of internal state for logging."""
        ...


# ═══════════════════════════════════════════════════════════════════
# Auto Industry Implementation
# ═══════════════════════════════════════════════════════════════════

class LegacyAutomaker(ProducerAgent):
    """
    A legacy automaker transitioning from ICE to EV.

    Each tick:
      1. Generate catalog (apply R&D effects to base specs)
      2. Process sales (revenue, COGS, penalties)
      3. Allocate R&D budget
      4. Adjust production capacity
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

        # Track R&D-driven modifications to base specs
        self._msrp_reductions: dict[str, float] = {dt: 0.0 for dt in DRIVETRAINS}
        self._range_bonuses: dict[str, float] = {dt: 0.0 for dt in DRIVETRAINS}

        # History for logging
        self._last_sales: dict[str, SalesRecord] | None = None

    # ── ProducerAgent Interface ──

    def generate_offerings(
        self, env: PolicySnapshot
    ) -> list[ProductOffering]:
        """
        Build the vehicle catalog for this tick.
        Apply R&D-driven price reductions and range improvements.
        """
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
        """
        Full end-of-tick processing:
          1. Revenue from sales
          2. COGS
          3. Emissions penalties (per ICE unit)
          4. R&D allocation
          5. Apply R&D milestones
          6. Production capacity adjustment
        """
        self._last_sales = sales

        # ── 1. Revenue ──
        total_revenue = sum(s.revenue for s in sales.values())
        self.ledger.record_revenue(total_revenue)

        # ── 2. COGS ──
        cogs = total_revenue * COGS_PCT
        self.ledger.record_cost(cogs, "cogs")

        # ── 3. Emissions Penalties ──
        ice_sales = sales.get("ICE")
        if ice_sales and env.emissions_penalty_per_unit > 0:
            penalty = ice_sales.units_sold * env.emissions_penalty_per_unit
            self.ledger.record_cost(penalty, "penalty")

        # ── 4. R&D Allocation ──
        r_and_d_alloc = self.strategy.compute_r_and_d_allocation(
            self.ledger.capital, sales, DRIVETRAINS
        )
        for dt, amount in r_and_d_alloc.items():
            if amount > 0:
                self.pipeline.invest(dt, amount)
                self.ledger.record_cost(amount, "r_and_d")

        # ── 5. R&D Milestones ──
        self._apply_milestones()

        # ── 6. Capacity Reallocation ──
        shifts = self.strategy.compute_capacity_shifts(sales, self.capacity)
        retooling_cost = self.strategy.compute_retooling_cost(shifts)
        if retooling_cost > 0:
            self.ledger.record_cost(retooling_cost, "retooling")
        for dt, shift in shifts.items():
            self.capacity[dt] = max(0, self.capacity[dt] + shift)

    def _apply_milestones(self) -> None:
        """Check and apply R&D milestone effects."""
        # EV milestones
        new_ev = self.pipeline.check_and_award_milestones(
            "EV", EV_RND_MILESTONE_COST
        )
        if new_ev > 0:
            self._msrp_reductions["EV"] += new_ev * EV_RND_MSRP_REDUCTION_PCT
            self._range_bonuses["EV"] += new_ev * EV_RND_RANGE_BONUS_MI

        # Hybrid milestones
        new_hybrid = self.pipeline.check_and_award_milestones(
            "HYBRID", HYBRID_RND_MILESTONE_COST
        )
        if new_hybrid > 0:
            self._msrp_reductions["HYBRID"] += (
                new_hybrid * HYBRID_RND_MSRP_REDUCTION_PCT
            )

    def get_state(self) -> dict:
        """Snapshot for logging."""
        return {
            "capital": self.ledger.capital,
            "capacity": dict(self.capacity),
            "total_capacity": sum(self.capacity.values()),
            "msrp_reductions": dict(self._msrp_reductions),
            "range_bonuses": dict(self._range_bonuses),
            "r_and_d": self.pipeline.to_dict(),
            "financials": self.ledger.to_dict(),
        }
