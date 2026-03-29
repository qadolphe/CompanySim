"""
Environment domain models — immutable value objects representing
the exogenous state of the world at a point in time.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicySnapshot:
    """
    Immutable snapshot of all exogenous policy and economic conditions
    for a single simulation tick.

    This is the data contract between the Environment context and all
    other bounded contexts. Consumers and producers read this; nobody
    writes to it.
    """
    year: int
    ev_tax_credit: float
    gas_price_per_gallon: float
    electricity_price_per_kwh: float
    interest_rate: float
    emissions_penalty_per_unit: float
    cafe_ev_mandate_pct: float
    charging_infrastructure_index: float

    def to_dict(self) -> dict:
        """Convert to plain dict for logging and serialization."""
        return {
            "year": self.year,
            "ev_tax_credit": self.ev_tax_credit,
            "gas_price_per_gallon": self.gas_price_per_gallon,
            "electricity_price_per_kwh": self.electricity_price_per_kwh,
            "interest_rate": self.interest_rate,
            "emissions_penalty_per_unit": self.emissions_penalty_per_unit,
            "cafe_ev_mandate_pct": self.cafe_ev_mandate_pct,
            "charging_infrastructure_index": self.charging_infrastructure_index,
        }
