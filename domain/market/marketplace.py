"""
Marketplace — aggregate root for the Market bounded context.

The marketplace is the decoupling seam between consumers and producers.
Each tick:
  1. Producer posts offerings (set_catalog)
  2. Consumers shop (attempt_purchase)
  3. Simulation reads results (get_sales_summary)
"""

from __future__ import annotations

from domain.market.models import ProductOffering, SalesRecord


class Marketplace:
    """
    Aggregate root for the Market context.

    Holds the current product catalog, tracks sales, and enforces
    inventory constraints. Neither consumers nor producers hold
    a reference to each other — they interact only through this class.
    """

    def __init__(self) -> None:
        self._catalog: dict[str, ProductOffering] = {}
        self._sales_count: dict[str, int] = {}
        self._sales_revenue: dict[str, float] = {}

    # ── Producer Interface ──

    def set_catalog(self, offerings: list[ProductOffering]) -> None:
        """
        Replace the catalog with new offerings for this tick.
        Resets all sales counters.
        """
        self._catalog = {o.product_type: o for o in offerings}
        self._sales_count = {o.product_type: 0 for o in offerings}
        self._sales_revenue = {o.product_type: 0.0 for o in offerings}

    # ── Consumer Interface ──

    def get_catalog_for_consumers(self) -> list[dict]:
        """
        Returns the catalog as plain dicts (consumers don't see
        producer internals or inventory counts).
        """
        return [o.to_consumer_view() for o in self._catalog.values()]

    def attempt_purchase(self, product_type: str) -> bool:
        """
        Consumer attempts to purchase a product by type.
        Returns True if successful (units remain), False otherwise.
        Decrements inventory and records the sale.
        """
        offering = self._catalog.get(product_type)
        if offering is None:
            return False
        if offering.units_available <= 0:
            return False

        offering.decrement_inventory()
        self._sales_count[product_type] += 1
        self._sales_revenue[product_type] += offering.price
        return True

    # ── Reporting Interface ──

    def get_sales_summary(self) -> dict[str, SalesRecord]:
        """
        Returns aggregate sales results keyed by product type.
        This is what the producer reads to adjust strategy.
        """
        return {
            ptype: SalesRecord(
                product_type=ptype,
                units_sold=self._sales_count.get(ptype, 0),
                revenue=self._sales_revenue.get(ptype, 0.0),
            )
            for ptype in self._catalog
        }

    def get_total_units_sold(self) -> int:
        """Total units sold across all product types this tick."""
        return sum(self._sales_count.values())

    def get_total_revenue(self) -> float:
        """Total revenue across all product types this tick."""
        return sum(self._sales_revenue.values())

    @property
    def product_types(self) -> list[str]:
        """List of product types currently in the catalog."""
        return list(self._catalog.keys())
