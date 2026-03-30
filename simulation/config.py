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

Scenario Toggle:
  Set SCENARIO to "baseline" or "trump" to switch between policy regimes.
  "baseline" = IRA credits + EPA standards stay in place.
  "trump"    = EV tax credits zeroed from 2025, CAFE mandates frozen at 2024
               levels, EPA emissions penalties zeroed, NEVI funding stalls.
"""

from __future__ import annotations

from enum import Enum


# ═══════════════════════════════════════════════════════════════════
# Scenario System
# ═══════════════════════════════════════════════════════════════════

class Scenario(Enum):
    BASELINE = "baseline"
    TRUMP = "trump"


# ── Active scenario (change this to toggle) ──
SCENARIO: Scenario = Scenario.BASELINE


# ═══════════════════════════════════════════════════════════════════
# Simulation Boundaries
# ═══════════════════════════════════════════════════════════════════

START_YEAR: int = 2024
END_YEAR: int = 2035
NUM_CONSUMERS: int = 50_000

# ── Drivetrain Types ──
DRIVETRAINS: list[str] = ["ICE", "HYBRID", "EV"]


# ═══════════════════════════════════════════════════════════════════
# Vehicle Defaults (MSRP in $, range in miles)
# Source: KBB/Edmunds 2024 avg transaction prices, EPA ratings
# ═══════════════════════════════════════════════════════════════════

DEFAULT_VEHICLE_CATALOG: dict = {
    "ICE": {
        "msrp": 35_000,
        "mpg": 28.0,
        "range_mi": 420.0,
        "annual_maintenance": 1_400.0,
        "kwh_per_mile": None,
    },
    "HYBRID": {
        "msrp": 38_500,
        "mpg": 48.0,
        "range_mi": 600.0,
        "annual_maintenance": 1_100.0,
        "kwh_per_mile": None,
    },
    "EV": {
        "msrp": 45_000,
        "mpg": None,
        "range_mi": 270.0,
        "annual_maintenance": 700.0,
        "kwh_per_mile": 0.30,
    },
}


# ═══════════════════════════════════════════════════════════════════
# Consumer Demographics
# Source: US Census 2023, IHS Markit new-car buyer profiles
# ═══════════════════════════════════════════════════════════════════

INCOME_MEAN: float = 75_000.0
INCOME_STD: float = 30_000.0
INCOME_MIN: float = 28_000.0
COMMUTE_MEAN_MI: float = 30.0
COMMUTE_STD_MI: float = 15.0
COMMUTE_MIN_MI: float = 5.0
VEHICLE_OWNERSHIP_YEARS: int = 8

# ── Consumer Utility Weights ──
UTILITY_ALPHA_BASE: float = 1.0
UTILITY_ALPHA_SENSITIVITY: float = 2.0
UTILITY_BETA_MAX: float = 0.3
UTILITY_GAMMA_MAX: float = 0.5
UTILITY_RANGE_ANXIETY_THRESHOLD: float = 2.5

# ── Ownership Hassle (EV charging difficulty) ──
UTILITY_DELTA_MAX: float = 0.4
HOMEOWNER_INCOME_THRESHOLD: float = 75_000.0
HOMEOWNER_PROB_BASE: float = 0.30
HOMEOWNER_PROB_MAX: float = 0.85


# ═══════════════════════════════════════════════════════════════════
# Automaker Defaults — Corporate Finance
# Scaled to NUM_CONSUMERS = 50,000
# Legacy proxy: Ford/GM blended 2023 10-K
# ═══════════════════════════════════════════════════════════════════

INITIAL_CAPITAL: float = 2_500_000_000.0

# ── Per-Drivetrain COGS (% of revenue) ──
# ICE is the cash cow with mature supply chains.
# EV starts unprofitable (>1.0 = negative gross margin on every sale).
COGS_PCT_BY_DRIVETRAIN: dict[str, float] = {
    "ICE":    0.78,    # Mature, high-margin
    "HYBRID": 0.85,    # Dual powertrain complexity
    "EV":     1.10,    # Battery cost dominance → negative margin at launch
}
# Each EV R&D milestone reduces EV COGS_PCT by this amount
EV_RND_COGS_REDUCTION: float = 0.04   # 4pp per milestone

# Keep old flat COGS_PCT for backward compatibility in tests
COGS_PCT: float = 0.83

PRODUCTION_CAPACITY: dict[str, int] = {
    "ICE": 30_000,
    "HYBRID": 12_500,
    "EV": 7_500,
}

# ── SG&A (Selling, General & Administrative) ──
SGA_FIXED_LEGACY: float = 200_000_000.0    # $200M/yr (Ford ~$5B, scaled to 50K sim)
SGA_FIXED_STARTUP: float = 40_000_000.0    # $40M/yr (lean org)
SGA_VARIABLE_PCT: float = 0.03             # 3% of revenue (dealer/marketing)

# ── Depreciation & Amortization ──
DEPRECIATION_RATE: float = 0.10            # 10% of cumulative CapEx per year

# ── Tax ──
CORPORATE_TAX_RATE: float = 0.21           # US federal statutory rate

# ── R&D ──
R_AND_D_BUDGET_PCT: float = 0.08
R_AND_D_EV_FLOOR_PCT: float = 0.30
RETOOLING_COST_PER_UNIT: float = 10_000.0
CAPACITY_SHIFT_MAX_UNITS: int = 1_000
CAPACITY_SHIFT_PCT: float = 0.10

# R&D Milestone thresholds
EV_RND_MILESTONE_COST: float = 1_000_000_000.0
EV_RND_MSRP_REDUCTION_PCT: float = 0.05
EV_RND_RANGE_BONUS_MI: float = 30.0
HYBRID_RND_MILESTONE_COST: float = 500_000_000.0
HYBRID_RND_MSRP_REDUCTION_PCT: float = 0.03

# ── Startup External Funding Rounds ──
STARTUP_FUNDING_ROUNDS: dict[tuple[int, int], float] = {
    (2024, 2025): 300_000_000.0,    # Series D equivalent
    (2026, 2027): 200_000_000.0,    # Growth round
    (2028, 2029): 100_000_000.0,    # Bridge round (conditional on survival)
    (2030, 2035): 0.0,              # Must be self-sustaining
}


# ═══════════════════════════════════════════════════════════════════
# Policy Schedules — Scenario-Dependent
# ═══════════════════════════════════════════════════════════════════

# ── Baseline schedules (IRA + EPA intact) ──
_BASELINE_EV_TAX_CREDIT: dict[tuple[int, int], float] = {
    (2024, 2026): 7_500.0,
    (2027, 2028): 5_625.0,
    (2029, 2030): 3_750.0,
    (2031, 2032): 1_875.0,
    (2033, 2035): 0.0,
}

_BASELINE_EMISSIONS_PENALTY: dict[tuple[int, int], float] = {
    (2024, 2025): 0.0,
    (2026, 2027): 500.0,
    (2028, 2029): 1_500.0,
    (2030, 2031): 3_500.0,
    (2032, 2035): 5_000.0,
}

_BASELINE_CAFE_EV_MANDATE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.12,
    (2026, 2027): 0.22,
    (2028, 2029): 0.35,
    (2030, 2031): 0.50,
    (2032, 2033): 0.56,
    (2034, 2035): 0.67,
}

_BASELINE_CHARGING_INFRA: dict[tuple[int, int], float] = {
    (2024, 2024): 0.12,
    (2025, 2026): 0.18,
    (2027, 2028): 0.30,
    (2029, 2030): 0.50,
    (2031, 2032): 0.65,
    (2033, 2035): 0.80,
}

# ── Trump schedules (IRA repealed, EPA rolled back) ──
_TRUMP_EV_TAX_CREDIT: dict[tuple[int, int], float] = {
    (2024, 2024): 7_500.0,     # Credits honored for 2024 (already enacted)
    (2025, 2035): 0.0,         # Repealed
}

_TRUMP_EMISSIONS_PENALTY: dict[tuple[int, int], float] = {
    (2024, 2035): 0.0,         # EPA enforcement gutted
}

_TRUMP_CAFE_EV_MANDATE: dict[tuple[int, int], float] = {
    (2024, 2035): 0.12,        # Frozen at 2024 level — no ramp
}

_TRUMP_CHARGING_INFRA: dict[tuple[int, int], float] = {
    (2024, 2024): 0.12,
    (2025, 2026): 0.14,        # Minimal organic growth, NEVI stalled
    (2027, 2028): 0.16,
    (2029, 2030): 0.18,
    (2031, 2035): 0.20,        # Private buildout only — very slow
}

# ── Active policy schedules (resolved from SCENARIO) ──
def _pick(baseline: dict, trump: dict) -> dict:
    return baseline if SCENARIO == Scenario.BASELINE else trump

EV_TAX_CREDIT_SCHEDULE: dict[tuple[int, int], float] = _pick(
    _BASELINE_EV_TAX_CREDIT, _TRUMP_EV_TAX_CREDIT
)
EMISSIONS_PENALTY_SCHEDULE: dict[tuple[int, int], float] = _pick(
    _BASELINE_EMISSIONS_PENALTY, _TRUMP_EMISSIONS_PENALTY
)
CAFE_EV_MANDATE_SCHEDULE: dict[tuple[int, int], float] = _pick(
    _BASELINE_CAFE_EV_MANDATE, _TRUMP_CAFE_EV_MANDATE
)
CHARGING_INFRASTRUCTURE_SCHEDULE: dict[tuple[int, int], float] = _pick(
    _BASELINE_CHARGING_INFRA, _TRUMP_CHARGING_INFRA
)

# ── Scenario-independent schedules ──
INTEREST_RATE_SCHEDULE: dict[tuple[int, int], float] = {
    (2024, 2025): 0.072,
    (2026, 2027): 0.062,
    (2028, 2029): 0.055,
    (2030, 2031): 0.050,
    (2032, 2035): 0.048,
}


# ═══════════════════════════════════════════════════════════════════
# Exogenous Economic Baselines
# Source: EIA AEO 2024 reference case
# ═══════════════════════════════════════════════════════════════════

GAS_PRICE_BASE: float = 3.45
GAS_PRICE_ANNUAL_GROWTH: float = 0.025
ELECTRICITY_PRICE_BASE: float = 0.16
ELECTRICITY_PRICE_ANNUAL_GROWTH: float = 0.02

# ── Randomness ──
SEED: int = 42
