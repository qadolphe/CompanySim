"""
Economics module — pure-function library for all time-varying macro curves.

This is the single source of truth for:
  - Fuel costs (gasoline, electricity)
  - Bill of Materials (BOM) by drivetrain with Wright's Law battery curves
  - EV battery cost per kWh
  - Interest rates (smooth interpolation)
  - Vehicle depreciation / residual value
  - Material cost index (shared supplier pressure)
  - Plant tooling amortization (with manufacturing learning curves)

All functions are stateless: they take (year, scenario, ...) and return a float.
Both producers and consumers call these functions via the same interface.

Sources:
  - BNEF Battery Price Survey 2024
  - UBS Evidence Lab teardowns
  - EIA AEO 2024 reference case
  - iSeeCars / Black Book residual value studies
"""

from __future__ import annotations

import math

import simulation.config as cfg


# ═══════════════════════════════════════════════════════════════════
# Fuel Costs
# ═══════════════════════════════════════════════════════════════════

def get_fuel_cost(fuel_type: str, year: int) -> float:
    """
    Return the per-unit fuel cost for the given year.

    fuel_type:
      "gasoline"    → $/gallon  (compounds at GAS_PRICE_ANNUAL_GROWTH)
      "electricity" → $/kWh     (compounds at ELECTRICITY_PRICE_ANNUAL_GROWTH)
    """
    years_elapsed = max(0, year - cfg.START_YEAR)
    if fuel_type == "gasoline":
        return cfg.GAS_PRICE_BASE * (
            (1.0 + cfg.GAS_PRICE_ANNUAL_GROWTH) ** years_elapsed
        )
    if fuel_type == "electricity":
        return cfg.ELECTRICITY_PRICE_BASE * (
            (1.0 + cfg.ELECTRICITY_PRICE_ANNUAL_GROWTH) ** years_elapsed
        )
    raise ValueError(f"Unknown fuel_type: {fuel_type!r}")


# ═══════════════════════════════════════════════════════════════════
# Battery Cost (Wright's Law)
# ═══════════════════════════════════════════════════════════════════

def get_ev_battery_cost_per_kwh(year: int) -> float:
    """
    EV battery pack cost in $/kWh for the given year.

    Uses a secular annual decline rate as a time proxy for global
    cumulative production doublings (Wright's Law).

    $140/kWh (2024) → ~$80/kWh (2030) → floor $60/kWh.
    """
    years_elapsed = max(0, year - cfg.START_YEAR)
    start = cfg.BATTERY_COST_PER_KWH_2024
    floor = cfg.BATTERY_COST_FLOOR_PER_KWH
    decay = cfg.BATTERY_ANNUAL_DECLINE_RATE
    return floor + (start - floor) * ((1.0 - decay) ** years_elapsed)


# ═══════════════════════════════════════════════════════════════════
# Material Cost Index (shared supplier pressure)
# ═══════════════════════════════════════════════════════════════════

def get_material_cost_index(year: int) -> float:
    """
    Shared material cost pressure index (CPI-linked).
    Affects both Legacy and Startup equally via common suppliers.
    Returns a multiplier relative to 2024 baseline (1.0 at START_YEAR).
    """
    years_elapsed = max(0, year - cfg.START_YEAR)
    return cfg.MATERIAL_COST_INDEX_BASE * (
        (1.0 + cfg.MATERIAL_COST_INFLATION) ** years_elapsed
    )


# ═══════════════════════════════════════════════════════════════════
# Bill of Materials (BOM) — Absolute Unit Cost by Drivetrain
# ═══════════════════════════════════════════════════════════════════

def get_bom_cost(
    drivetrain: str,
    year: int,
    cumulative_ev_units: int = 0,
    manufacturer_credit_per_kwh: float = 0.0,
) -> float:
    """
    Return the Bill of Materials cost for one vehicle of the given
    drivetrain type, in absolute dollars.

    ICE:    Base inflates with material costs (~1.5%/yr CPI).
    HYBRID: ICE powertrain portion (discounted via shared platform) +
            small battery portion declining.
    EV:     Battery portion follows Wright's Law decline;
            non-battery portion inflates slowly.
            Manufacturer credit (§45X) directly reduces battery cost.

    Parameters
    ----------
    drivetrain : "ICE", "HYBRID", or "EV"
    year : simulation year
    cumulative_ev_units : total EV units produced (for Wright's Law volume)
    manufacturer_credit_per_kwh : IRA §45X production credit, $/kWh
    """
    mat_index = get_material_cost_index(year)

    if drivetrain == "ICE":
        return cfg.BOM_BASE_ICE * mat_index

    if drivetrain == "HYBRID":
        # ICE powertrain portion (discounted for shared platform)
        ice_portion = cfg.BOM_BASE_ICE * cfg.BOM_HYBRID_ICE_PLATFORM_DISCOUNT * mat_index
        # Small battery portion (~15kWh typical PHEV)
        hybrid_battery_kwh = 15.0
        battery_cost = get_ev_battery_cost_per_kwh(year) * hybrid_battery_kwh
        # Remaining hybrid-specific components (electric motor, power electronics)
        hybrid_electronics = (
            cfg.BOM_BASE_HYBRID - cfg.BOM_BASE_ICE * cfg.BOM_HYBRID_ICE_PLATFORM_DISCOUNT - 15.0 * cfg.BATTERY_COST_PER_KWH_2024
        ) * mat_index
        return ice_portion + battery_cost + max(0.0, hybrid_electronics)

    if drivetrain == "EV":
        # Battery portion: pack_kwh × $/kWh, minus manufacturer credit
        battery_per_kwh = get_ev_battery_cost_per_kwh(year)
        effective_battery_per_kwh = max(
            0.0, battery_per_kwh - manufacturer_credit_per_kwh
        )
        battery_cost = effective_battery_per_kwh * cfg.EV_BATTERY_CAPACITY_KWH

        # Volume learning (Wright's Law on manufacturing efficiency)
        volume_discount = _wrights_law_factor(
            cumulative_ev_units,
            reference_units=cfg.EV_COGS_REFERENCE_UNITS,
            learning_rate=cfg.BATTERY_WRIGHTS_LEARNING_RATE,
        )
        battery_cost *= volume_discount

        # Non-battery portion inflates slowly
        non_battery_base = cfg.BOM_BASE_EV * (1.0 - cfg.EV_BOM_BATTERY_FRACTION)
        years_elapsed = max(0, year - cfg.START_YEAR)
        non_battery_cost = non_battery_base * (
            (1.0 + cfg.EV_BOM_NON_BATTERY_INFLATION) ** years_elapsed
        )

        return battery_cost + non_battery_cost

    raise ValueError(f"Unknown drivetrain: {drivetrain!r}")


def _wrights_law_factor(
    cumulative_units: int,
    reference_units: int,
    learning_rate: float,
) -> float:
    """
    Wright's Law: cost decreases by `learning_rate` fraction for each
    cumulative doubling of production volume.

    Returns a multiplier in (0, 1] where 1.0 = no volume benefit.
    """
    ref = max(1, reference_units)
    observed = max(cumulative_units, ref)
    if observed <= ref:
        return 1.0
    log_ratio = math.log2(observed / ref)
    exponent = math.log2(1.0 - learning_rate)
    return max(0.3, observed / ref * 0.0 + (observed / ref) ** exponent)


# ═══════════════════════════════════════════════════════════════════
# Interest Rate (smooth interpolation)
# ═══════════════════════════════════════════════════════════════════

def get_interest_rate(year: int) -> float:
    """
    Return the macro interest rate for the given year.

    Uses piecewise-linear interpolation between the bracket midpoints
    defined in INTEREST_RATE_SCHEDULE for smooth transitions instead
    of step functions.
    """
    schedule = cfg.INTEREST_RATE_SCHEDULE

    # Build sorted list of (midpoint_year, rate) pairs
    points: list[tuple[float, float]] = []
    for (start, end), rate in sorted(schedule.items()):
        midpoint = (start + end) / 2.0
        points.append((midpoint, rate))
    points.sort()

    if not points:
        return 0.05  # fallback

    # Clamp to endpoints
    if year <= points[0][0]:
        return points[0][1]
    if year >= points[-1][0]:
        return points[-1][1]

    # Linear interpolation between surrounding midpoints
    for i in range(len(points) - 1):
        y0, r0 = points[i]
        y1, r1 = points[i + 1]
        if y0 <= year <= y1:
            t = (year - y0) / (y1 - y0)
            return r0 + t * (r1 - r0)

    return points[-1][1]


# ═══════════════════════════════════════════════════════════════════
# Vehicle Depreciation / Residual Value
# ═══════════════════════════════════════════════════════════════════

def get_vehicle_depreciation_residual(drivetrain: str, vehicle_age: int) -> float:
    """
    Return the residual value as a fraction of original MSRP.

    Uses the appropriate depreciation curve for the drivetrain.
    Linearly interpolates between defined age points.
    For ages beyond the curve, extrapolates from the last two points
    (floored at 0.10).
    """
    curves = {
        "ICE": cfg.DEPRECIATION_CURVE_ICE,
        "HYBRID": cfg.DEPRECIATION_CURVE_HYBRID,
        "EV": cfg.DEPRECIATION_CURVE_EV,
    }
    curve = curves.get(drivetrain, cfg.DEPRECIATION_CURVE_ICE)

    if vehicle_age <= 0:
        return 1.0

    max_age = max(curve.keys())
    if vehicle_age >= max_age:
        # Extrapolate: ~3% annual decline beyond last point
        last_val = curve[max_age]
        extra_years = vehicle_age - max_age
        return max(0.10, last_val * (0.97 ** extra_years))

    # Exact match
    if vehicle_age in curve:
        return curve[vehicle_age]

    # Linear interpolation between surrounding points
    ages = sorted(curve.keys())
    for i in range(len(ages) - 1):
        if ages[i] <= vehicle_age <= ages[i + 1]:
            a0, a1 = ages[i], ages[i + 1]
            v0, v1 = curve[a0], curve[a1]
            t = (vehicle_age - a0) / (a1 - a0)
            return v0 + t * (v1 - v0)

    return curve[max_age]


# ═══════════════════════════════════════════════════════════════════
# Plant Tooling Amortization (Manufacturing Learning Curves)
# ═══════════════════════════════════════════════════════════════════

def get_legacy_tooling_per_unit(drivetrain: str, cumulative_ev_units: int = 0) -> float:
    """
    Return per-unit plant tooling amortization for Legacy Automaker.

    ICE/HYBRID: fixed (mature, fully amortized lines).
    EV: declines with cumulative volume via manufacturing learning curve.
    """
    base = cfg.PLANT_TOOLING_PER_UNIT.get(drivetrain, 800.0)
    if drivetrain != "EV":
        return base
    # EV tooling declines with manufacturing learning
    factor = _wrights_law_factor(
        cumulative_ev_units,
        reference_units=cfg.EV_COGS_REFERENCE_UNITS,
        learning_rate=cfg.LEGACY_EV_TOOLING_LEARNING_RATE,
    )
    return max(cfg.LEGACY_EV_TOOLING_FLOOR, base * factor)


def get_startup_tooling_per_unit(cumulative_ev_units: int = 0) -> float:
    """
    Return per-unit plant tooling amortization for Pure-EV Startup.

    Starts higher than Legacy EV (fully burdened new skateboard platform)
    but declines faster (clean-sheet manufacturing, faster iteration).
    """
    base = cfg.STARTUP_PLANT_TOOLING_BASE
    factor = _wrights_law_factor(
        cumulative_ev_units,
        reference_units=cfg.EV_COGS_REFERENCE_UNITS,
        learning_rate=cfg.STARTUP_TOOLING_LEARNING_RATE,
    )
    return max(cfg.STARTUP_TOOLING_FLOOR, base * factor)


# ═══════════════════════════════════════════════════════════════════
# Producer Unit Cost (composed from building blocks above)
# ═══════════════════════════════════════════════════════════════════

def get_legacy_unit_cost(
    drivetrain: str,
    year: int,
    cumulative_ev_units: int = 0,
    rd_milestones: int = 0,
    manufacturer_credit_per_kwh: float = 0.0,
) -> float:
    """
    All-in unit cost for one vehicle produced by the Legacy Automaker.

    unit_cost = BOM × union_labor_premium + dealer_distribution + tooling - rd_savings

    The union premium applies only to the labor fraction of BOM.
    """
    bom = get_bom_cost(drivetrain, year, cumulative_ev_units, manufacturer_credit_per_kwh)

    # Union labor premium on the labor portion of BOM
    labor_cost = bom * cfg.BOM_LABOR_FRACTION
    union_adder = labor_cost * (cfg.UNION_LABOR_PREMIUM - 1.0)

    # Dealer distribution
    distribution = cfg.DEALER_DISTRIBUTION_MARKUP

    # Tooling
    tooling = get_legacy_tooling_per_unit(drivetrain, cumulative_ev_units)

    # R&D milestone savings (only for EV)
    rd_savings = 0.0
    if drivetrain == "EV" and rd_milestones > 0:
        rd_savings = rd_milestones * cfg.EV_RND_COGS_REDUCTION_DOLLARS

    return bom + union_adder + distribution + tooling - rd_savings


def get_startup_unit_cost(
    year: int,
    cumulative_ev_units: int = 0,
    rd_milestones: int = 0,
    manufacturer_credit_per_kwh: float = 0.0,
) -> float:
    """
    All-in unit cost for one EV produced by the Pure-EV Startup.

    unit_cost = BOM - dtc_savings + tooling - rd_savings

    No union premium, no dealer markup. DTC savings from direct distribution.
    """
    bom = get_bom_cost("EV", year, cumulative_ev_units, manufacturer_credit_per_kwh)

    # DTC distribution savings (no dealer network)
    dtc_savings = cfg.DTC_DISTRIBUTION_SAVINGS

    # Tooling (fully burdened skateboard platform, declining with learning)
    tooling = get_startup_tooling_per_unit(cumulative_ev_units)

    # R&D milestone savings
    rd_savings = 0.0
    if rd_milestones > 0:
        rd_savings = rd_milestones * cfg.EV_RND_COGS_REDUCTION_DOLLARS

    return bom - dtc_savings + tooling - rd_savings


# ═══════════════════════════════════════════════════════════════════
# Consumer-Facing: Annual Costs & Insurance
# ═══════════════════════════════════════════════════════════════════

def get_annual_fuel_cost(
    drivetrain: str,
    year: int,
    annual_miles: float,
    mpg: float | None = None,
    kwh_per_mile: float | None = None,
    can_charge_at_home: bool = True,
) -> float:
    """
    Annual fuel/energy cost for a consumer based on drivetrain and commute.

    EV owners who can't charge at home pay a public-charging premium (~30%).
    """
    if drivetrain == "EV":
        kpm = kwh_per_mile or 0.30
        price = get_fuel_cost("electricity", year)
        if not can_charge_at_home:
            price *= 1.30  # Public charging premium
        return annual_miles * kpm * price
    else:
        effective_mpg = mpg or (28.0 if drivetrain == "ICE" else 48.0)
        return (annual_miles / effective_mpg) * get_fuel_cost("gasoline", year)


def get_annual_insurance(drivetrain: str) -> float:
    """Return annual insurance cost by drivetrain."""
    return {
        "ICE": cfg.ANNUAL_INSURANCE_ICE,
        "HYBRID": cfg.ANNUAL_INSURANCE_HYBRID,
        "EV": cfg.ANNUAL_INSURANCE_EV,
    }.get(drivetrain, cfg.ANNUAL_INSURANCE_ICE)


def get_annual_maintenance(
    drivetrain: str,
    base_maintenance: float,
    vehicle_age: int = 0,
) -> float:
    """
    Annual maintenance cost, escalating with vehicle age.

    ICE: escalates ~3%/yr (wear-sensitive parts).
    HYBRID: escalates ~2.5%/yr (dual system complexity).
    EV: near-flat escalation (fewer moving parts).
    """
    escalation = {
        "ICE": cfg.MAINTENANCE_ESCALATION_ICE,
        "HYBRID": cfg.MAINTENANCE_ESCALATION_HYBRID,
        "EV": cfg.MAINTENANCE_ESCALATION_EV,
    }.get(drivetrain, 0.02)
    return base_maintenance * ((1.0 + escalation) ** vehicle_age)
