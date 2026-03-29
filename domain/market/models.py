"""
Market domain models — product offerings and sales records.

Contains the abstract ProductOffering base class (generalization contract)
and the auto-industry-specific VehicleOffering implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# Abstract Contract — any industry can implement this
# ═══════════════════════════════════════════════════════════════════

class ProductOffering(ABC):
    """
    Abstract base for any product offered in a marketplace.

    Subclasses define industry-specific attributes (e.g., MPG for vehicles,
    data caps for telecom plans). The marketplace and consumers interact
    only through this contract.
    """

    @abstractmethod
    def to_consumer_view(self) -> dict:
        """
        Return a plain dict of attributes visible to consumers.
        This is the decoupling boundary — consumers never see
        producer internals, only this dict.
        """
        ...

    @property
    @abstractmethod
    def product_type(self) -> str:
        """Category identifier (e.g., 'ICE', 'HYBRID', 'EV')."""
        ...

    @property
    @abstractmethod
    def price(self) -> float:
        """Consumer-facing price."""
        ...

    @property
    @abstractmethod
    def units_available(self) -> int:
        """Number of units available for purchase this tick."""
        ...

    @abstractmethod
    def decrement_inventory(self) -> None:
        """Remove one unit from available inventory."""
        ...


# ═══════════════════════════════════════════════════════════════════
# Auto Industry Implementation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class VehicleOffering(ProductOffering):
    """
    A specific vehicle the automaker is offering this tick.

    This is the auto-industry implementation of ProductOffering.
    """
    drivetrain: str          # "ICE", "HYBRID", "EV"
    msrp: float
    mpg: float | None        # None for pure EVs
    range_mi: float
    annual_maintenance: float
    kwh_per_mile: float | None  # Only for EVs
    _units_available: int = field(default=0, repr=False)

    @property
    def product_type(self) -> str:
        return self.drivetrain

    @property
    def price(self) -> float:
        return self.msrp

    @property
    def units_available(self) -> int:
        return self._units_available

    def decrement_inventory(self) -> None:
        if self._units_available <= 0:
            raise ValueError(
                f"No inventory remaining for {self.drivetrain}"
            )
        self._units_available -= 1

    def to_consumer_view(self) -> dict:
        """
        What consumers see when shopping. Excludes producer-internal
        data like cost structure, margin, etc.
        """
        return {
            "product_type": self.drivetrain,
            "msrp": self.msrp,
            "mpg": self.mpg,
            "range_mi": self.range_mi,
            "annual_maintenance": self.annual_maintenance,
            "kwh_per_mile": self.kwh_per_mile,
        }


# ═══════════════════════════════════════════════════════════════════
# Sales Record Value Object
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SalesRecord:
    """
    Immutable record of sales for a single product type in a single tick.
    """
    product_type: str
    units_sold: int
    revenue: float
