"""
Population factory — generates realistic consumer populations
with statistically distributed demographics.
"""

from __future__ import annotations

import numpy as np

from domain.consumer.agents import AutoConsumer
from domain.consumer.models import ConsumerProfile
from simulation.config import (
    NUM_CONSUMERS,
    INCOME_MEAN,
    INCOME_STD,
    INCOME_MIN,
    COMMUTE_MEAN_MI,
    COMMUTE_STD_MI,
    COMMUTE_MIN_MI,
    DRIVETRAINS,
    SEED,
    VEHICLE_OWNERSHIP_YEARS,
    HOMEOWNER_INCOME_THRESHOLD,
    HOMEOWNER_PROB_BASE,
    HOMEOWNER_PROB_MAX,
    HOMEOWNER_CAN_CHARGE_PROB,
    RENTER_CAN_CHARGE_PROB,
)


class PopulationFactory:
    """
    Generates a population of AutoConsumer agents with realistic
    demographic distributions.

    Income: truncated normal (μ=75K, σ=30K, min=28K)
    Commute: truncated normal (μ=30mi, σ=15mi, min=5mi)
    Green preference: uniform [0, 1]
    Price sensitivity: uniform [0, 1]
    Homeownership: income-correlated probability (30% @ min → 85% @ high)
    Family size: income-correlated truncated Poisson (1–5)
    Can charge at home: homeowner 90% True, renter 15% True
    Fast chargers nearby: infra_index × (0.5 + 0.5 × random) geographic noise
    Maintenance sensitivity: inversely correlated with income
    Current vehicle: random assignment (weighted toward ICE)
    Years owned: uniform [0, ownership_cycle]
    """

    @staticmethod
    def generate(
        n: int = NUM_CONSUMERS,
        seed: int = SEED,
    ) -> list[AutoConsumer]:
        """Generate n consumers with reproducible random demographics."""
        rng = np.random.default_rng(seed)

        consumers: list[AutoConsumer] = []

        # ── Generate demographic arrays ──
        incomes = np.clip(
            rng.normal(INCOME_MEAN, INCOME_STD, size=n),
            INCOME_MIN,
            None,
        )

        commutes = np.clip(
            rng.normal(COMMUTE_MEAN_MI, COMMUTE_STD_MI, size=n),
            COMMUTE_MIN_MI,
            None,
        )

        green_prefs = rng.uniform(0.0, 1.0, size=n)
        price_sensitivities = rng.uniform(0.0, 1.0, size=n)

        # Starting vehicle ownership — weighted toward ICE (realistic 2024)
        vehicle_weights = [0.75, 0.15, 0.10]  # ICE, HYBRID, EV (2024 US stock)
        starting_vehicles = rng.choice(
            DRIVETRAINS,
            size=n,
            p=vehicle_weights,
        )

        # Randomize how old their current vehicle is
        starting_years = rng.integers(
            0, VEHICLE_OWNERSHIP_YEARS + 1, size=n
        )

        # ── Homeownership (correlated with income) ──
        # P(homeowner) scales linearly from PROB_BASE at min income
        # to PROB_MAX at the threshold, clamped on both ends.
        income_ratio = np.clip(
            (incomes - INCOME_MIN) / (HOMEOWNER_INCOME_THRESHOLD - INCOME_MIN),
            0.0,
            1.0,
        )
        homeowner_probs = (
            HOMEOWNER_PROB_BASE
            + income_ratio * (HOMEOWNER_PROB_MAX - HOMEOWNER_PROB_BASE)
        )
        is_homeowner_flags = rng.random(size=n) < homeowner_probs

        # ── Family size (income-correlated truncated Poisson, 1–5) ──
        # Higher income → slightly larger family (μ scales 1.5–3.0)
        family_lambda = 1.5 + 1.5 * income_ratio  # λ ∈ [1.5, 3.0]
        family_sizes = np.clip(
            rng.poisson(lam=family_lambda) + 1,  # +1 so minimum is 1
            1,
            5,
        ).astype(int)

        # ── Can charge at home (homeowners ~90%, renters ~15%) ──
        can_charge_probs = np.where(
            is_homeowner_flags,
            HOMEOWNER_CAN_CHARGE_PROB,
            RENTER_CAN_CHARGE_PROB,
        )
        can_charge_flags = rng.random(size=n) < can_charge_probs

        # ── Fast chargers nearby (geographic noise around infra baseline) ──
        # At sim start, infra_index ~0.12; per-consumer noise creates variance
        infra_baseline = 0.12  # Will be updated each tick via env snapshot
        fast_charger_scores = np.clip(
            infra_baseline * (0.5 + 0.5 * rng.random(size=n))
            + 0.3 * rng.random(size=n),  # Some areas have private chargers
            0.0,
            1.0,
        )

        # ── Maintenance cost sensitivity (inversely correlated with income) ──
        # Low income → high sensitivity; high income → low sensitivity
        income_pctl = np.clip(
            (incomes - INCOME_MIN) / (INCOME_MEAN * 2.0 - INCOME_MIN),
            0.0,
            1.0,
        )
        maintenance_sensitivities = np.clip(
            1.0 - income_pctl + rng.normal(0.0, 0.1, size=n),
            0.0,
            1.0,
        )

        # ── Build agents ──
        for i in range(n):
            profile = ConsumerProfile(
                id=i,
                annual_income=float(incomes[i]),
                annual_commute_miles=float(commutes[i]),
                green_preference=float(green_prefs[i]),
                price_sensitivity=float(price_sensitivities[i]),
                is_homeowner=bool(is_homeowner_flags[i]),
                current_vehicle=str(starting_vehicles[i]),
                years_owned=int(starting_years[i]),
                family_size=int(family_sizes[i]),
                can_charge_at_home=bool(can_charge_flags[i]),
                fast_chargers_nearby=float(fast_charger_scores[i]),
                maintenance_cost_sensitivity=float(maintenance_sensitivities[i]),
            )
            consumers.append(AutoConsumer(profile))

        return consumers
