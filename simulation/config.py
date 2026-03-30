"""
Simulation configuration — all constants and scenario knobs.

This is the single source of truth for tuning the simulation.
All values are for the "Legacy Automaker EV Transition" scenario.

Calibrated against real-world data:
  - Policy: IRA §30D, EPA Multi-Pollutant Standards, NEVI
  - Corporate: Ford/GM 10-K blended proxy, Tesla/Rivian startup proxy
  - Vehicles: KBB/Edmunds 2024 avg transaction prices
  - Demographics: US Census 2023, IHS Markit
  - Energy: EIA AEO 2024 reference case
"""

# ── Simulation Boundaries ──
START_YEAR: int = 2024
END_YEAR: int = 2035
NUM_CONSUMERS: int = 50_000

# ── Drivetrain Types ──
DRIVETRAINS: list[str] = ["ICE", "HYBRID", "EV"]

# ── Vehicle Defaults (MSRP in $, range in miles) ──
# Source: KBB/Edmunds 2024 avg transaction prices, EPA ratings
DEFAULT_VEHICLE_CATALOG: dict = {
    "ICE": {
        "msrp": 35_000,         # Avg new ICE sedan/CUV 2024
        "mpg": 28.0,            # EPA fleet avg light-duty
        "range_mi": 420.0,      # ~15 gal × 28 mpg
        "annual_maintenance": 1_400.0,  # AAA 2024 avg
        "kwh_per_mile": None,
    },
    "HYBRID": {
        "msrp": 38_500,         # Avg HEV transaction price 2024
        "mpg": 48.0,            # Typical HEV (Camry=52, RAV4=41)
        "range_mi": 600.0,      # ~12.5 gal × 48 mpg
        "annual_maintenance": 1_100.0,
        "kwh_per_mile": None,
    },
    "EV": {
        "msrp": 45_000,         # Avg BEV transaction price 2024 (excl. luxury)
        "mpg": None,
        "range_mi": 270.0,      # EPA avg BEV range 2024 (non-Tesla)
        "annual_maintenance": 700.0,   # AAA 2024 avg BEV
        "kwh_per_mile": 0.30,
    },
}

# ── Consumer Demographics ──
# Source: US Census 2023, IHS Markit new-car buyer profiles
INCOME_MEAN: float = 75_000.0       # Median HH ~$80K; new-car buyers skew higher
INCOME_STD: float = 30_000.0        # Wider distribution matches real inequality
INCOME_MIN: float = 28_000.0        # ~FPL for family of 4
COMMUTE_MEAN_MI: float = 30.0
COMMUTE_STD_MI: float = 15.0
COMMUTE_MIN_MI: float = 5.0
VEHICLE_OWNERSHIP_YEARS: int = 8    # IHS Markit avg new-car holding period

# ── Consumer Utility Weights ──
UTILITY_ALPHA_BASE: float = 1.0       # TCO weight base
UTILITY_ALPHA_SENSITIVITY: float = 2.0  # Additional TCO weight from price_sensitivity
UTILITY_BETA_MAX: float = 0.3         # Max green bonus
UTILITY_GAMMA_MAX: float = 0.5        # Max range anxiety penalty
UTILITY_RANGE_ANXIETY_THRESHOLD: float = 2.5  # Range must be > threshold × daily commute

# ── Ownership Hassle (EV charging difficulty) ──
UTILITY_DELTA_MAX: float = 0.4        # Max ownership hassle penalty
HOMEOWNER_INCOME_THRESHOLD: float = 75_000.0
HOMEOWNER_PROB_BASE: float = 0.30
HOMEOWNER_PROB_MAX: float = 0.85

# ── Automaker Defaults ──
# Scaled to NUM_CONSUMERS = 50,000
# Legacy proxy: Ford/GM blended 2023 10-K (cash ~$25B, US production ~2M)
INITIAL_CAPITAL: float = 2_500_000_000.0   # $2.5B
COGS_PCT: float = 0.83                     # Ford ~0.87, GM ~0.82 → blended
PRODUCTION_CAPACITY: dict[str, int] = {
    "ICE": 30_000,
    "HYBRID": 12_500,
    "EV": 7_500,
}
R_AND_D_BUDGET_PCT: float = 0.08           # ~5% of revenue, ~8% of capital
R_AND_D_EV_FLOOR_PCT: float = 0.30
RETOOLING_COST_PER_UNIT: float = 10_000.0  # Real retooling cost per unit
CAPACITY_SHIFT_MAX_UNITS: int = 1_000      # ~2% of total capacity
CAPACITY_SHIFT_PCT: float = 0.10

# R&D Milestone thresholds (scaled to 50K-consumer economy)
EV_RND_MILESTONE_COST: float = 1_000_000_000.0       # $1B per breakthrough
EV_RND_MSRP_REDUCTION_PCT: float = 0.05              # 5% MSRP drop per milestone
EV_RND_RANGE_BONUS_MI: float = 30.0                  # +30mi range per milestone
HYBRID_RND_MILESTONE_COST: float = 500_000_000.0     # $500M per milestone
HYBRID_RND_MSRP_REDUCTION_PCT: float = 0.03          # 3% MSRP drop per milestone

# ── Policy Schedules (year → value) ──
# EV Tax Credit: IRA §30D with battery sourcing erosion
# Credit splits into $3,750 halves (critical minerals + battery components)
# Compliance erodes as FEOC exclusions and domestic sourcing rules tighten
EV_TAX_CREDIT_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2026): 7_500.0,     # Both halves fully qualifying
    (2027, 2028): 5_625.0,     # Battery component half erodes (partial compliance)
    (2029, 2030): 3_750.0,     # Only critical minerals half remains
    (2031, 2032): 1_875.0,     # Critical minerals partial miss
    (2033, 2035): 0.0,         # Credit expired / fully phased out
}

# Emissions penalty: EPA Multi-Pollutant Standards proxy
# Translates fleet-wide avg requirements into per-ICE-unit shadow price
EMISSIONS_PENALTY_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.0,         # No enforcement yet
    (2026, 2027): 500.0,       # Phase-in, lenient
    (2028, 2029): 1_500.0,     # Standards tighten
    (2030, 2031): 3_500.0,     # Heavy enforcement
    (2032, 2035): 5_000.0,     # Full penalty (~EU CO₂ fine equivalent)
}

# CAFE EV mandate: EPA final rule ramp (56% EV target by 2032)
CAFE_EV_MANDATE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.12,
    (2026, 2027): 0.22,
    (2028, 2029): 0.35,
    (2030, 2031): 0.50,
    (2032, 2033): 0.56,
    (2034, 2035): 0.67,
}

# Interest rate schedule (Fed projected soft-landing path)
INTEREST_RATE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.072,
    (2026, 2027): 0.062,
    (2028, 2029): 0.055,
    (2030, 2031): 0.050,
    (2032, 2035): 0.048,
}

# Charging Infrastructure Index: NEVI rollout proxy
# $7.5B program targeting 500K public chargers by 2030 (from ~180K in 2024)
# Index = convenience parity with gas (1.0 = fully equivalent)
CHARGING_INFRASTRUCTURE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2024): 0.12,        # ~180K chargers, mostly urban
    (2025, 2026): 0.18,        # Early NEVI deployments
    (2027, 2028): 0.30,        # Interstate corridors filling in
    (2029, 2030): 0.50,        # NEVI build-out peak
    (2031, 2032): 0.65,        # Suburban coverage expanding
    (2033, 2035): 0.80,        # Rural gap persists → never reaches 1.0
}

# ── Exogenous Economic Baselines ──
# Source: EIA AEO 2024 reference case
GAS_PRICE_BASE: float = 3.45           # $/gallon 2024 avg regular (EIA)
GAS_PRICE_ANNUAL_GROWTH: float = 0.025 # 2.5% annual compound
ELECTRICITY_PRICE_BASE: float = 0.16   # $/kWh 2024 avg residential (EIA)
ELECTRICITY_PRICE_ANNUAL_GROWTH: float = 0.02  # 2.0% annual compound

# ── Randomness ──
SEED: int = 42
