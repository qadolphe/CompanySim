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
)


class PopulationFactory:
    """
    Generates a population of AutoConsumer agents with realistic
    demographic distributions.

    Income: truncated normal (μ=65K, σ=25K, min=25K)
    Commute: truncated normal (μ=30mi, σ=15mi, min=5mi)
    Green preference: uniform [0, 1]
    Price sensitivity: uniform [0, 1]
    Homeownership: income-correlated probability (30% @ min → 85% @ high)
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
            )
            consumers.append(AutoConsumer(profile))

        return consumers
