"""
Utility calculator — the economic decision engine for consumer agents.

Contains the abstract UtilityCalculator contract and the auto-industry
VehicleUtilityCalculator implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.consumer.models import ConsumerProfile
from domain.environment.models import PolicySnapshot
from simulation.config import (
    VEHICLE_OWNERSHIP_YEARS,
    UTILITY_ALPHA_BASE,
    UTILITY_ALPHA_SENSITIVITY,
    UTILITY_BETA_MAX,
    UTILITY_GAMMA_MAX,
    UTILITY_DELTA_MAX,
    UTILITY_RANGE_ANXIETY_THRESHOLD,
    HOMEOWNER_INCOME_THRESHOLD,
)


# ═══════════════════════════════════════════════════════════════════
# Abstract Contract
# ═══════════════════════════════════════════════════════════════════

class UtilityCalculator(ABC):
    """
    Abstract utility calculator. Any domain (auto, housing, telecom)
    can implement its own version. The consumer agent delegates
    all evaluation logic to this.
    """

    @abstractmethod
    def compute(
        self,
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        """
        Compute the utility score for a consumer considering an offering.

        Higher utility = more desirable. Sign convention:
          - Costs contribute negatively
          - Benefits contribute positively

        Returns a float score that is comparable across offerings
        for the same consumer.
        """
        ...


# ═══════════════════════════════════════════════════════════════════
# Auto Industry Implementation
# ═══════════════════════════════════════════════════════════════════

class VehicleUtilityCalculator(UtilityCalculator):
    """
    Vehicle-specific utility function.

    utility = -α · TCO_normalized + β · green_bonus - γ · range_anxiety - δ · ownership_hassle

    Where:
      TCO = (MSRP - tax_credit) + fuel_cost + maintenance + financing
      α = 1.0 + (price_sensitivity × 2.0)       # 1.0 – 3.0
      β = green_preference × 0.3                 # 0.0 – 0.3
      γ = penalty if EV range < threshold × daily commute
      δ = EV ownership friction (charging access, time cost)
    """

    def compute(
        self,
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        # ── TCO Calculation ──
        tco = self._compute_tco(profile, offering, env)

        # Normalize TCO by income (makes price sensitivity relative)
        tco_normalized = tco / max(profile.annual_income, 1.0)

        # ── Weight: price sensitivity ──
        alpha = UTILITY_ALPHA_BASE + (
            profile.price_sensitivity * UTILITY_ALPHA_SENSITIVITY
        )

        # ── Green bonus (only for EV and Hybrid) ──
        green_bonus = 0.0
        if offering["product_type"] in ("EV", "HYBRID"):
            green_bonus = profile.green_preference * UTILITY_BETA_MAX

        # ── Range anxiety (only for EVs) ──
        range_anxiety = 0.0
        if offering["product_type"] == "EV":
            range_anxiety = self._compute_range_anxiety(profile, offering)

        # ── Ownership hassle (only for EVs) ──
        ownership_hassle = 0.0
        if offering["product_type"] == "EV":
            ownership_hassle = self._compute_ownership_hassle(profile)

        return (
            -alpha * tco_normalized
            + green_bonus
            - range_anxiety
            - ownership_hassle
        )

    def _compute_tco(
        self,
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        """
        Total Cost of Ownership over the holding period.

        TCO = purchase_cost + fuel_cost + maintenance + financing
        """
        years = VEHICLE_OWNERSHIP_YEARS

        # Purchase cost (minus tax credit for EVs)
        purchase_cost = offering["msrp"]
        if offering["product_type"] == "EV":
            purchase_cost -= env.ev_tax_credit

        # Annual fuel cost
        annual_fuel = self._annual_fuel_cost(profile, offering, env)

        # Maintenance
        annual_maintenance = offering["annual_maintenance"]

        # Financing (simplified linear approximation)
        financing = offering["msrp"] * env.interest_rate * years * 0.5

        return purchase_cost + (annual_fuel * years) + (
            annual_maintenance * years
        ) + financing

    @staticmethod
    def _annual_fuel_cost(
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        """Compute annual fuel/energy cost based on drivetrain type."""
        miles = profile.annual_commute_miles

        if offering["product_type"] == "EV":
            # EV: cost = miles × kWh/mile × $/kWh
            kwh_per_mile = offering.get("kwh_per_mile") or 0.30
            return miles * kwh_per_mile * env.electricity_price_per_kwh
        else:
            # ICE / Hybrid: cost = (miles / MPG) × $/gallon
            mpg = offering.get("mpg") or 30.0
            return (miles / mpg) * env.gas_price_per_gallon

    @staticmethod
    def _compute_range_anxiety(
        profile: ConsumerProfile,
        offering: dict,
    ) -> float:
        """
        Range anxiety penalty for EVs.
        Penalty = max(0, 1 - range / (daily_commute × threshold)) × γ_max

        No penalty if range exceeds threshold × daily commute.
        """
        range_mi = offering.get("range_mi", 0.0)
        daily_commute = profile.daily_commute_miles
        required_range = daily_commute * UTILITY_RANGE_ANXIETY_THRESHOLD

        if required_range <= 0:
            return 0.0

        ratio = range_mi / required_range
        if ratio >= 1.0:
            return 0.0

        return (1.0 - ratio) * UTILITY_GAMMA_MAX

    @staticmethod
    def _compute_ownership_hassle(
        profile: ConsumerProfile,
    ) -> float:
        """
        Ownership hassle penalty for EVs based on housing and income.

        Models the real-world difficulty of EV ownership:
          - Homeowners: can install L2 charger → minimal hassle
          - Non-homeowners: must rely on public charging → high hassle
          - Higher income reduces hassle (access to paid charging services,
            premium apartments with chargers, workplace charging)
          - Longer commutes amplify the hassle (more charging sessions/week)

        Returns a float penalty in [0, DELTA_MAX].
        """
        # Base hassle score: 0.0 (no friction) to 1.0 (maximum friction)
        if profile.is_homeowner:
            # Homeowners have a charger — minimal hassle
            # But lower income homeowners may have older electrical panels,
            # so give them a small residual hassle.
            income_factor = min(
                profile.annual_income / HOMEOWNER_INCOME_THRESHOLD, 1.0
            )
            base_hassle = 0.1 * (1.0 - income_factor)  # 0.0 – 0.1
        else:
            # Non-homeowners: significant friction
            # Higher income somewhat mitigates (premium apartments with
            # chargers, can afford paid fast-charging memberships)
            income_factor = min(
                profile.annual_income / HOMEOWNER_INCOME_THRESHOLD, 1.0
            )
            base_hassle = 0.9 - 0.4 * income_factor  # 0.5 – 0.9

        # Commute intensity amplifier: longer commutes → more charging
        # sessions → more friction. Normalized around 30mi (average).
        commute_avg = 30.0  # miles
        commute_factor = min(
            profile.daily_commute_miles / commute_avg, 2.0
        )
        # Short commuters (<30mi) care less; long commuters care more
        intensity = 0.5 + 0.5 * commute_factor  # range: 0.5 – 1.5

        return min(base_hassle * intensity, 1.0) * UTILITY_DELTA_MAX
