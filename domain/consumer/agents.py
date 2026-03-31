"""
Consumer agents — the decision-making entities in the Consumer context.

Contains the abstract ConsumerAgent contract and the auto-industry
AutoConsumer implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import math
import random
from typing import Optional

from domain.consumer.models import ConsumerProfile
from domain.consumer.utility import UtilityCalculator, VehicleUtilityCalculator
from domain.environment.models import PolicySnapshot
from simulation.config import (
    INCOME_MEAN,
    INCOME_STD,
    SHOPPING_CYCLE_MID_YEARS,
    SHOPPING_INCOME_SLOPE,
    SHOPPING_MIN_CYCLE_YEARS,
    SHOPPING_MAX_CYCLE_YEARS,
    SHOPPING_LOGIT_INTERCEPT,
    SHOPPING_LOGIT_INCOME_WEIGHT,
    SHOPPING_LOGIT_OWNERSHIP_WEIGHT,
    SHOPPING_NOISE_SIGMA,
    AFFORDABILITY_MAX_DTI,
    LOAN_TERM_MONTHS,
)


# ═══════════════════════════════════════════════════════════════════
# Abstract Contract
# ═══════════════════════════════════════════════════════════════════

class ConsumerAgent(ABC):
    """
    Abstract consumer agent. Any domain (auto, housing, telecom)
    can implement its own consumer type. The simulation engine
    interacts only through this contract.
    """

    @abstractmethod
    def is_in_market(self) -> bool:
        """True if the consumer is actively shopping this tick."""
        ...

    @abstractmethod
    def evaluate_and_choose(
        self,
        offerings: list[dict],
        env: PolicySnapshot,
    ) -> Optional[str]:
        """
        Evaluate all available offerings and return the offering_id
        of the chosen one, or None if nothing is affordable/desirable.
        """
        ...

    @abstractmethod
    def record_purchase(self, product_type: str) -> None:
        """Update internal state after a successful purchase."""
        ...

    @abstractmethod
    def age_one_tick(self) -> None:
        """Advance the agent's internal clock by one tick."""
        ...

    @property
    @abstractmethod
    def profile(self) -> ConsumerProfile:
        """Access the agent's demographic profile."""
        ...


# ═══════════════════════════════════════════════════════════════════
# Auto Industry Implementation
# ═══════════════════════════════════════════════════════════════════

class AutoConsumer(ConsumerAgent):
    """
    An individual consumer in the auto market.

    Decision process each tick:
      1. Am I in the market? (vehicle age >= ownership cycle)
      2. If yes, compute utility for each available vehicle.
      3. Purchase the highest-utility option (if affordable).
    """

    def __init__(
        self,
        consumer_profile: ConsumerProfile,
        utility_calculator: UtilityCalculator | None = None,
    ) -> None:
        self._profile = consumer_profile
        self._utility = utility_calculator or VehicleUtilityCalculator()
        self._rng = random.Random(consumer_profile.id)

    @property
    def profile(self) -> ConsumerProfile:
        return self._profile

    def is_in_market(self) -> bool:
        """
        Consumer is shopping if:
          - They have no vehicle, OR
          - A probabilistic trigger fires based on income and years owned.
        """
        if self._profile.current_vehicle is None:
            return True
        return self._rng.random() < self._market_entry_probability()

    def _market_entry_probability(self) -> float:
        """Income-weighted market-entry probability with small random noise."""
        # Income z-score controls replacement-cycle target by cohort.
        income_z = (self._profile.annual_income - INCOME_MEAN) / max(1.0, INCOME_STD)
        target_cycle = SHOPPING_CYCLE_MID_YEARS - SHOPPING_INCOME_SLOPE * income_z
        target_cycle = max(SHOPPING_MIN_CYCLE_YEARS, min(SHOPPING_MAX_CYCLE_YEARS, target_cycle))

        ownership_pressure = self._profile.years_owned / max(1.0, target_cycle)
        noise = self._rng.gauss(0.0, SHOPPING_NOISE_SIGMA)
        logit = (
            SHOPPING_LOGIT_INTERCEPT
            + SHOPPING_LOGIT_INCOME_WEIGHT * income_z
            + SHOPPING_LOGIT_OWNERSHIP_WEIGHT * ownership_pressure
            + noise
        )
        probability = 1.0 / (1.0 + math.exp(-logit))
        return max(0.0, min(1.0, probability))

    def evaluate_and_choose(
        self,
        offerings: list[dict],
        env: PolicySnapshot,
    ) -> Optional[str]:
        """
        Evaluate all offerings, filter by affordability, return the
        offering_id with the highest utility. Returns None if nothing
        is affordable.
        """
        best_offering_id: Optional[str] = None
        best_utility: float = float("-inf")

        for offering in offerings:
            # Affordability gate
            if not self._is_affordable(offering):
                continue

            utility = self._utility.compute(self._profile, offering, env)

            if utility > best_utility:
                best_utility = utility
                best_offering_id = offering["offering_id"]

        return best_offering_id

    def record_purchase(self, product_type: str) -> None:
        """Update profile after buying a vehicle."""
        self._profile.current_vehicle = product_type
        self._profile.years_owned = 0

    def age_one_tick(self) -> None:
        """Increment vehicle ownership duration by one tick."""
        if self._profile.current_vehicle is not None:
            self._profile.years_owned += 1

    def _is_affordable(self, offering: dict) -> bool:
        """
        Can this consumer afford this vehicle?
        Monthly payment must be <= AFFORDABILITY_MAX_DTI × monthly income.
        """
        monthly_payment = offering["msrp"] / LOAN_TERM_MONTHS
        monthly_income = self._profile.annual_income / 12.0
        return monthly_payment <= (monthly_income * AFFORDABILITY_MAX_DTI)
