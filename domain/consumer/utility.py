"""
Utility calculator — the economic decision engine for consumer agents.

Contains the abstract UtilityCalculator contract and the auto-industry
VehicleUtilityCalculator implementation.

V2: 5-Year TCO model with:
  - Financed MSRP, fuel, maintenance, insurance, resale value
  - Behavioral multipliers: charging access penalty, inertia discount,
    family size factor, maintenance sensitivity
  - Demographic depth: can_charge_at_home, fast_chargers_nearby, family_size
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import math

from domain.consumer.models import ConsumerProfile
from domain.economics import (
    get_annual_fuel_cost,
    get_annual_insurance,
    get_annual_maintenance,
    get_vehicle_depreciation_residual,
)
from domain.environment.models import PolicySnapshot
from simulation.config import (
    UTILITY_ALPHA_BASE,
    UTILITY_ALPHA_SENSITIVITY,
    UTILITY_BETA_MAX,
    UTILITY_GAMMA_MAX,
    UTILITY_DELTA_MAX,
    UTILITY_RANGE_ANXIETY_THRESHOLD,
    HOMEOWNER_INCOME_THRESHOLD,
    INCOME_MEAN,
    INCOME_STD,
    START_YEAR,
    TCO_HORIZON_YEARS,
    UTILITY_INFRA_CONVEXITY,
    UTILITY_INFRA_CRITICAL_THRESHOLD,
    UTILITY_INFRA_CRITICAL_MULTIPLIER,
    UTILITY_EARLY_YEARS_AMPLIFIER,
    UTILITY_EARLY_DECAY_YEARS,
    UTILITY_DEMOGRAPHIC_SHIELD_MAX,
    TECH_INERTIA_BONUS,
    UTILITY_SWITCHING_PENALTY_BASE,
    UTILITY_SWITCH_TO_EV_EXTRA,
    UTILITY_SAME_DRIVETRAIN_BONUS,
    UTILITY_RENTER_PUBLIC_CHARGING_BASE,
    UTILITY_RENTER_PUBLIC_CHARGING_INCOME_RELIEF,
    INERTIA_DISCOUNT_PCT,
    CHARGING_INCONVENIENCE_COST,
    FAST_CHARGER_RELIEF_THRESHOLD,
    FAMILY_RANGE_MULTIPLIER,
    CHARGING_TIME_COST_PER_YEAR,
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
    Vehicle-specific utility function using 5-Year TCO.

    utility = -α · TCO_normalized + β · green_bonus + tech_inertia
              - γ · range_anxiety - δ · ownership_hassle - switching_penalty

    Where TCO is a 5-year total cost of ownership:
      TCO = financed_MSRP + 5yr_fuel + 5yr_maintenance + 5yr_insurance
            - resale_value + charging_penalty + time_cost
    """

    def compute(
        self,
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        # ── 5-Year TCO Calculation ──
        tco = self._compute_tco(profile, offering, env)

        # ── Inertia discount (same drivetrain familiarity) ──
        if profile.current_vehicle == offering["product_type"]:
            tco *= (1.0 - INERTIA_DISCOUNT_PCT)

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

        # Technology inertia captures incumbent familiarity/servicing convenience.
        tech_inertia = 0.0
        if offering["product_type"] in ("ICE", "HYBRID"):
            tech_inertia = TECH_INERTIA_BONUS * (1.0 - 0.5 * profile.green_preference)

        # ── Range anxiety (only for EVs) ──
        range_anxiety = 0.0
        if offering["product_type"] == "EV":
            range_anxiety = self._compute_range_anxiety(profile, offering, env)

        # ── Ownership hassle (only for EVs) ──
        ownership_hassle = 0.0
        if offering["product_type"] == "EV":
            ownership_hassle = self._compute_ownership_hassle(profile, env)

        # Switching between drivetrains carries behavioral and practical friction.
        switching_penalty = self._compute_switching_penalty(profile, offering, env)

        return (
            -alpha * tco_normalized
            + green_bonus
            + tech_inertia
            - range_anxiety
            - ownership_hassle
            - switching_penalty
        )

    @staticmethod
    def _compute_switching_penalty(
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        current = profile.current_vehicle
        target = offering["product_type"]
        if current is None:
            return 0.0

        if current == target:
            return -UTILITY_SAME_DRIVETRAIN_BONUS

        penalty = UTILITY_SWITCHING_PENALTY_BASE
        if current in ("ICE", "HYBRID") and target == "EV":
            infra_relief = max(0.0, min(1.0, env.charging_infrastructure_index))
            green_relief = max(0.0, min(1.0, profile.green_preference))
            transition_extra = (
                UTILITY_SWITCH_TO_EV_EXTRA
                * (1.0 - 0.55 * infra_relief)
                * (1.0 - 0.45 * green_relief)
            )
            penalty += max(0.0, transition_extra)
        elif current == "EV" and target in ("ICE", "HYBRID"):
            penalty += 0.04

        return penalty

    def _compute_tco(
        self,
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        """
        5-Year Total Cost of Ownership.

        TCO = financed_purchase + fuel_5yr + maintenance_5yr + insurance_5yr
              - resale_value + charging_access_penalty + time_cost_penalty
        """
        years = TCO_HORIZON_YEARS
        dt = offering["product_type"]
        msrp = offering["msrp"]

        # ── Purchase cost (minus tax credit for EVs) ──
        purchase_cost = msrp
        if dt == "EV":
            purchase_cost -= env.ev_tax_credit

        # ── Financing (simplified half-interest over loan term) ──
        financed_purchase = purchase_cost * (1.0 + env.interest_rate * years * 0.5)

        # ── 5-Year Fuel Cost (year-aware via economics module) ──
        annual_fuel = get_annual_fuel_cost(
            drivetrain=dt,
            year=env.year,
            annual_miles=profile.annual_commute_miles,
            mpg=offering.get("mpg"),
            kwh_per_mile=offering.get("kwh_per_mile"),
            can_charge_at_home=profile.can_charge_at_home,
        )
        fuel_5yr = annual_fuel * years

        # ── 5-Year Maintenance (escalating with vehicle age) ──
        base_maintenance = offering["annual_maintenance"]
        # Weight by maintenance sensitivity (budget-conscious families care more)
        sensitivity_weight = 1.0 + 0.3 * profile.maintenance_cost_sensitivity
        maintenance_5yr = sum(
            get_annual_maintenance(dt, base_maintenance, vehicle_age=y)
            for y in range(years)
        ) * sensitivity_weight

        # ── 5-Year Insurance ──
        insurance_5yr = get_annual_insurance(dt) * years

        # ── Resale Value (depreciation at end of holding period) ──
        residual_fraction = get_vehicle_depreciation_residual(dt, vehicle_age=years)
        resale_value = msrp * residual_fraction

        # ── Charging Access Penalty (EVs only) ──
        charging_penalty = 0.0
        if dt == "EV" and not profile.can_charge_at_home:
            # Relief scales with local fast-charger availability
            charger_relief = max(0.0, min(1.0,
                (profile.fast_chargers_nearby - FAST_CHARGER_RELIEF_THRESHOLD)
                / (1.0 - FAST_CHARGER_RELIEF_THRESHOLD)
            )) if profile.fast_chargers_nearby > FAST_CHARGER_RELIEF_THRESHOLD else 0.0
            charging_penalty = CHARGING_INCONVENIENCE_COST * (1.0 - 0.7 * charger_relief)
            # Add implicit time cost of public charging
            charging_penalty += CHARGING_TIME_COST_PER_YEAR * years

        return (
            financed_purchase
            + fuel_5yr
            + maintenance_5yr
            + insurance_5yr
            - resale_value
            + charging_penalty
        )

    @staticmethod
    def _compute_range_anxiety(
        profile: ConsumerProfile,
        offering: dict,
        env: PolicySnapshot,
    ) -> float:
        """
        Range anxiety penalty for EVs.
        Penalty scales with shortfall below required range.
        Family size > 3 increases range requirement (road trips).
        """
        range_mi = offering.get("range_mi", 0.0)
        daily_commute = profile.daily_commute_miles
        infra_shortfall = max(0.0, 1.0 - env.charging_infrastructure_index)
        required_range = daily_commute * UTILITY_RANGE_ANXIETY_THRESHOLD * (1.0 + 1.8 * infra_shortfall)

        # Family size factor: larger families need more range for road trips
        if profile.family_size > 3:
            required_range *= FAMILY_RANGE_MULTIPLIER

        if required_range <= 0:
            return 0.0

        ratio = range_mi / required_range
        if ratio >= 1.0:
            return 0.0

        shortfall = 1.0 - ratio
        years_elapsed = max(0, env.year - START_YEAR)
        early_multiplier = 1.0 + UTILITY_EARLY_YEARS_AMPLIFIER * math.exp(
            -years_elapsed / max(1.0, UTILITY_EARLY_DECAY_YEARS)
        )

        income_z = (profile.annual_income - INCOME_MEAN) / max(1.0, INCOME_STD)
        homeowner_boost = 1.2 if profile.is_homeowner else -0.3
        # can_charge_at_home provides additional relief beyond homeownership
        if profile.can_charge_at_home:
            homeowner_boost += 0.3
        shield_raw = 1.0 / (1.0 + math.exp(-(1.1 * income_z + homeowner_boost)))
        shield = min(UTILITY_DEMOGRAPHIC_SHIELD_MAX, shield_raw)

        penalty = shortfall * UTILITY_GAMMA_MAX * early_multiplier * (1.0 - shield)
        return max(0.0, penalty)

    @staticmethod
    def _compute_ownership_hassle(
        profile: ConsumerProfile,
        env: PolicySnapshot,
    ) -> float:
        """
        Ownership hassle penalty for EVs based on charging access and demographics.

        Now uses can_charge_at_home directly instead of is_homeowner proxy.
        """
        # Base hassle score before infrastructure scaling.
        if profile.can_charge_at_home:
            income_factor = min(
                profile.annual_income / HOMEOWNER_INCOME_THRESHOLD, 1.0
            )
            base_hassle = 0.16 * (1.0 - income_factor)
        else:
            income_factor = min(
                profile.annual_income / HOMEOWNER_INCOME_THRESHOLD, 1.0
            )
            base_hassle = 1.2 - 0.5 * income_factor

        commute_avg = 30.0  # miles
        commute_factor = min(
            profile.daily_commute_miles / commute_avg, 2.0
        )
        intensity = 0.6 + 0.8 * commute_factor  # range: 0.6 – 2.2

        infra_shortfall = max(0.0, 1.0 - env.charging_infrastructure_index)
        infrastructure_multiplier = infra_shortfall ** UTILITY_INFRA_CONVEXITY
        if env.charging_infrastructure_index < UTILITY_INFRA_CRITICAL_THRESHOLD:
            gap = (UTILITY_INFRA_CRITICAL_THRESHOLD - env.charging_infrastructure_index)
            cliff = 1.0 + UTILITY_INFRA_CRITICAL_MULTIPLIER * (gap ** 2)
            infrastructure_multiplier *= cliff

        # Consumers without home charging retain persistent public-charging
        # inconvenience even when infrastructure is widespread.
        if not profile.can_charge_at_home:
            renter_income_factor = min(
                profile.annual_income / HOMEOWNER_INCOME_THRESHOLD,
                1.0,
            )
            persistent_public_inconvenience = (
                UTILITY_RENTER_PUBLIC_CHARGING_BASE
                - UTILITY_RENTER_PUBLIC_CHARGING_INCOME_RELIEF * renter_income_factor
            )
            persistent_public_inconvenience = max(
                0.0,
                min(0.85, persistent_public_inconvenience),
            )
            # Fast chargers nearby provide partial relief
            charger_relief = profile.fast_chargers_nearby * 0.3
            persistent_public_inconvenience *= (1.0 - charger_relief)
            infrastructure_multiplier = (
                persistent_public_inconvenience
                + (1.0 - persistent_public_inconvenience) * infrastructure_multiplier
            )

        years_elapsed = max(0, env.year - START_YEAR)
        early_multiplier = 1.0 + UTILITY_EARLY_YEARS_AMPLIFIER * math.exp(
            -years_elapsed / max(1.0, UTILITY_EARLY_DECAY_YEARS)
        )

        income_z = (profile.annual_income - INCOME_MEAN) / max(1.0, INCOME_STD)
        homeowner_boost = 1.3 if profile.can_charge_at_home else -0.4
        relief_raw = 1.0 / (1.0 + math.exp(-(1.1 * income_z + homeowner_boost)))
        relief = min(UTILITY_DEMOGRAPHIC_SHIELD_MAX, relief_raw)

        raw = min(base_hassle * intensity, 1.8) * infrastructure_multiplier
        return raw * UTILITY_DELTA_MAX * early_multiplier * (1.0 - relief)
