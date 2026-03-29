"""
Simulation configuration — all constants and scenario knobs.

This is the single source of truth for tuning the simulation.
All values are for the "Legacy Automaker EV Transition" scenario.
"""

# ── Simulation Boundaries ──
START_YEAR: int = 2024
END_YEAR: int = 2035
NUM_CONSUMERS: int = 1_000

# ── Drivetrain Types ──
DRIVETRAINS: list[str] = ["ICE", "HYBRID", "EV"]

# ── Vehicle Defaults (MSRP in $, range in miles) ──
DEFAULT_VEHICLE_CATALOG: dict = {
    "ICE": {
        "msrp": 32_000,
        "mpg": 30.0,
        "range_mi": 400.0,
        "annual_maintenance": 1_200.0,
        "kwh_per_mile": None,
    },
    "HYBRID": {
        "msrp": 35_000,
        "mpg": 50.0,
        "range_mi": 550.0,
        "annual_maintenance": 1_000.0,
        "kwh_per_mile": None,
    },
    "EV": {
        "msrp": 42_000,
        "mpg": None,
        "range_mi": 300.0,
        "annual_maintenance": 600.0,
        "kwh_per_mile": 0.30,
    },
}

# ── Consumer Demographics ──
INCOME_MEAN: float = 65_000.0
INCOME_STD: float = 25_000.0
INCOME_MIN: float = 25_000.0
COMMUTE_MEAN_MI: float = 30.0
COMMUTE_STD_MI: float = 15.0
COMMUTE_MIN_MI: float = 5.0
VEHICLE_OWNERSHIP_YEARS: int = 7  # Average holding period for TCO calc

# ── Consumer Utility Weights (initial — will be tuned after Phase 2) ──
UTILITY_ALPHA_BASE: float = 1.0       # TCO weight base
UTILITY_ALPHA_SENSITIVITY: float = 2.0  # Additional TCO weight from price_sensitivity
UTILITY_BETA_MAX: float = 0.3         # Max green bonus
UTILITY_GAMMA_MAX: float = 0.5        # Max range anxiety penalty
UTILITY_RANGE_ANXIETY_THRESHOLD: float = 2.5  # Range must be > threshold × daily commute

# ── Ownership Hassle (EV charging difficulty) ──
# Models the real-world friction of EV ownership for non-homeowners:
#   - No home charger → reliance on public charging infrastructure
#   - Time cost of charging sessions (30+ min vs. 5 min gas station)
#   - Accessibility issues (apartment dwellers, street parkers)
# Hassle is modulated by income (proxy for housing situation) and commute distance.
UTILITY_DELTA_MAX: float = 0.4        # Max ownership hassle penalty
HOMEOWNER_INCOME_THRESHOLD: float = 75_000.0  # Income above which homeownership is likely
HOMEOWNER_PROB_BASE: float = 0.30     # Base homeownership probability at min income
HOMEOWNER_PROB_MAX: float = 0.85      # Max homeownership probability at high income

# ── Automaker Defaults ──
# NOTE: Scaled to match NUM_CONSUMERS = 1,000 (~100 purchases/year)
# For a real-scale sim (100K consumers), multiply these by 100.
INITIAL_CAPITAL: float = 50_000_000.0     # $50M (scaled from $5B)
COGS_PCT: float = 0.70                    # Cost of goods sold as % of revenue
PRODUCTION_CAPACITY: dict[str, int] = {
    "ICE": 600,          # Scaled to NUM_CONSUMERS (1K → ~140 shoppers/yr)
    "HYBRID": 250,
    "EV": 150,
}
R_AND_D_BUDGET_PCT: float = 0.15          # % of capital allocated to R&D
R_AND_D_EV_FLOOR_PCT: float = 0.30        # Minimum % of R&D going to EV
RETOOLING_COST_PER_UNIT: float = 1_000.0  # Scaled down from $10K
CAPACITY_SHIFT_MAX_UNITS: int = 50
CAPACITY_SHIFT_PCT: float = 0.05

# R&D Milestone thresholds (scaled to 1K-consumer economy)
EV_RND_MILESTONE_COST: float = 20_000_000.0       # Every $20M → milestone
EV_RND_MSRP_REDUCTION_PCT: float = 0.05           # 5% MSRP drop per milestone
EV_RND_RANGE_BONUS_MI: float = 30.0               # +30mi range per milestone
HYBRID_RND_MILESTONE_COST: float = 10_000_000.0
HYBRID_RND_MSRP_REDUCTION_PCT: float = 0.03       # 3% MSRP drop per milestone

# ── Policy Schedules (year → value) ──
# EV Tax Credit: steps down over time
EV_TAX_CREDIT_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2026): 7_500.0,
    (2027, 2029): 5_000.0,
    (2030, 2035): 2_500.0,
}

# Emissions penalty: ramps up ($ per ICE unit sold)
EMISSIONS_PENALTY_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.0,
    (2026, 2027): 200.0,
    (2028, 2029): 500.0,
    (2030, 2031): 1_000.0,
    (2032, 2035): 2_000.0,
}

# CAFE EV mandate: minimum % of fleet that must be EV/Hybrid
CAFE_EV_MANDATE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.10,
    (2026, 2027): 0.15,
    (2028, 2029): 0.25,
    (2030, 2031): 0.35,
    (2032, 2033): 0.50,
    (2034, 2035): 0.67,
}

# Interest rate schedule
INTEREST_RATE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.070,
    (2026, 2027): 0.065,
    (2028, 2029): 0.055,
    (2030, 2031): 0.050,
    (2032, 2035): 0.045,
}

# ── Exogenous Economic Baselines ──
GAS_PRICE_BASE: float = 3.50           # $/gallon in START_YEAR
GAS_PRICE_ANNUAL_GROWTH: float = 0.03  # 3% annual compound
ELECTRICITY_PRICE_BASE: float = 0.14   # $/kWh in START_YEAR
ELECTRICITY_PRICE_ANNUAL_GROWTH: float = 0.015  # 1.5% annual compound

# ── Randomness ──
SEED: int = 42
