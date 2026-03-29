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
        self._catalog = {o.offering_id: o for o in offerings}
        self._sales_count = {o.offering_id: 0 for o in offerings}
        self._sales_revenue = {o.offering_id: 0.0 for o in offerings}

    # ── Consumer Interface ──

    def get_catalog_for_consumers(self) -> list[dict]:
        """
        Returns the catalog as plain dicts (consumers don't see
        producer internals or inventory counts).
        """
        return [o.to_consumer_view() for o in self._catalog.values()]

    def attempt_purchase(self, offering_id: str) -> bool:
        """
        Consumer attempts to purchase a product by offering_id.
        Returns True if successful (units remain), False otherwise.
        Decrements inventory and records the sale.
        """
        offering = self._catalog.get(offering_id)
        if offering is None:
            return False
        if offering.units_available <= 0:
            return False

        offering.decrement_inventory()
        self._sales_count[offering_id] += 1
        self._sales_revenue[offering_id] += offering.price
        return True

    # ── Reporting Interface ──

    def get_sales_summary(self) -> dict[str, SalesRecord]:
        """
        Returns aggregate sales results keyed by offering_id.
        This is what the producer reads to adjust strategy.
        """
        return {
            off_id: SalesRecord(
                offering_id=off_id,
                product_type=self._catalog[off_id].product_type,
                units_sold=self._sales_count.get(off_id, 0),
                revenue=self._sales_revenue.get(off_id, 0.0),
            )
            for off_id in self._catalog
        }

    def get_firm_sales_summary(self, producer_id: str) -> dict[str, SalesRecord]:
        """
        Returns sales results for a specific firm, keyed by product_type.
        This allows Producer agents to remain ignorant of 'offering_id'
        and just look at their own 'EV' or 'ICE' sales.
        """
        firm_sales = {}
        for off_id, o in self._catalog.items():
            if o.producer_id == producer_id:
                sales_record = SalesRecord(
                    offering_id=off_id,
                    product_type=o.product_type,
                    units_sold=self._sales_count.get(off_id, 0),
                    revenue=self._sales_revenue.get(off_id, 0.0),
                )
                firm_sales[o.product_type] = sales_record
        return firm_sales

    def get_total_units_sold(self) -> int:
        """Total units sold across all product types this tick."""
        return sum(self._sales_count.values())

    def get_total_revenue(self) -> float:
        """Total revenue across all product types this tick."""
        return sum(self._sales_revenue.values())

    @property
    def product_types(self) -> list[str]:
        """List of unique product types currently in the catalog."""
        return list({o.product_type for o in self._catalog.values()})
