"""
Consumer domain models — entities and value objects for consumer agents.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConsumerProfile:
    """
    Demographic identity of a consumer. Generated once at initialization
    by the PopulationFactory.

    This is an entity — it has a unique ID and mutable state (vehicle
    ownership changes over time).
    """
    id: int
    annual_income: float
    annual_commute_miles: float
    green_preference: float       # 0.0 – 1.0, higher = values EV/green more
    price_sensitivity: float      # 0.0 – 1.0, higher = more cost-conscious
    is_homeowner: bool            # Homeowners can install chargers → low EV hassle
    current_vehicle: str | None   # "ICE", "HYBRID", "EV", or None (no car)
    years_owned: int              # Ticks since last purchase (0 = just bought)

    # ── New demographic & charging fields ──
    family_size: int = 2                    # 1–5, correlated with income
    can_charge_at_home: bool = True         # True if home charger access (garage, driveway, etc.)
    fast_chargers_nearby: float = 0.5       # 0.0–1.0, localized charging access
    maintenance_cost_sensitivity: float = 0.5  # 0.0–1.0, inversely correlated with income

    @property
    def daily_commute_miles(self) -> float:
        """Approximate daily commute assuming 250 working days."""
        return self.annual_commute_miles / 250.0

    def to_micro_dict(self) -> dict:
        """Serialize to a compact dict for the React micro-state log."""
        return {
            "id": self.id,
            "income": self.annual_income,
            "vehicle": self.current_vehicle,
            "just_bought": self.years_owned == 0 and self.current_vehicle is not None,
            "family_size": self.family_size,
            "can_charge": self.can_charge_at_home,
        }
