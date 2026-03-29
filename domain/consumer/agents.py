"""
Consumer agents — the decision-making entities in the Consumer context.

Contains the abstract ConsumerAgent contract and the auto-industry
AutoConsumer implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.consumer.models import ConsumerProfile
from domain.consumer.utility import UtilityCalculator, VehicleUtilityCalculator
from domain.environment.models import PolicySnapshot
from simulation.config import VEHICLE_OWNERSHIP_YEARS


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

    # Maximum portion of annual income willing to spend on a vehicle
    # (realistic for financed purchases spread over 5-7 years)
    AFFORDABILITY_THRESHOLD: float = 0.80

    def __init__(
        self,
        consumer_profile: ConsumerProfile,
        utility_calculator: UtilityCalculator | None = None,
    ) -> None:
        self._profile = consumer_profile
        self._utility = utility_calculator or VehicleUtilityCalculator()

    @property
    def profile(self) -> ConsumerProfile:
        return self._profile

    def is_in_market(self) -> bool:
        """
        Consumer is shopping if:
          - They have no vehicle, OR
          - Their vehicle is older than the ownership cycle
        """
        if self._profile.current_vehicle is None:
            return True
        return self._profile.years_owned >= VEHICLE_OWNERSHIP_YEARS

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
        MSRP must be <= AFFORDABILITY_THRESHOLD × annual income.
        """
        return offering["msrp"] <= (
            self._profile.annual_income * self.AFFORDABILITY_THRESHOLD
        )
