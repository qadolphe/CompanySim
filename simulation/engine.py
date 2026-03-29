"""
Simulation engine — master orchestrator for the game loop.

Wires together all bounded contexts and runs the year-by-year simulation.
"""

from __future__ import annotations

import pandas as pd

from domain.environment.service import EnvironmentService
from domain.consumer.factory import PopulationFactory
from domain.consumer.agents import AutoConsumer
from domain.producer.agents import LegacyAutomaker, PureEVStartup
from domain.market.marketplace import Marketplace
from simulation.log import SimulationLog
from simulation.config import (
    START_YEAR,
    END_YEAR,
    NUM_CONSUMERS,
    SEED,
    INITIAL_CAPITAL,
    PRODUCTION_CAPACITY,
)


class SimulationEngine:
    """
    Master orchestrator. Owns the game loop.

    Each tick (1 year):
      1. Environment advances (policy/prices update).
      2. Automaker posts catalog to Marketplace.
      3. Consumers who are in-market evaluate and purchase.
      4. Marketplace reports sales summary.
      5. Automaker ingests sales, adjusts strategy.
      6. All state is logged.
    """

    def __init__(
        self,
        start_year: int = START_YEAR,
        end_year: int = END_YEAR,
        num_consumers: int = NUM_CONSUMERS,
        seed: int = SEED,
        initial_capital: float = INITIAL_CAPITAL,
        production_capacity: dict[str, int] | None = None,
    ) -> None:
        self.env = EnvironmentService(start_year, end_year)
        self.population = PopulationFactory.generate(n=num_consumers, seed=seed)
        self.legacy_maker = LegacyAutomaker(
            initial_capital=initial_capital,
            production_capacity=production_capacity or PRODUCTION_CAPACITY,
        )
        # Give the startup 50% of the initial capital and 150 units of EV capacity
        self.startup_maker = PureEVStartup(
            initial_capital=initial_capital * 0.5,
            production_capacity=150,
        )
        self.marketplace = Marketplace()
        self.log = SimulationLog()

    def run(self) -> pd.DataFrame:
        """Execute the full simulation timeline. Returns the log DataFrame."""
        while not self.env.is_complete:
            self._tick()
            self.env.tick()
        return self.log.to_dataframe()

    def _tick(self) -> None:
        """Execute a single simulation year."""
        # 1. Get environment state
        env_snapshot = self.env.snapshot()

        # 2. Automakers post catalog
        offerings = []
        offerings.extend(self.legacy_maker.generate_offerings(env_snapshot))
        offerings.extend(self.startup_maker.generate_offerings(env_snapshot))
        self.marketplace.set_catalog(offerings)

        # 3. Consumers shop
        catalog_view = self.marketplace.get_catalog_for_consumers()
        shoppers = 0
        buyers = 0

        for consumer in self.population:
            if consumer.is_in_market():
                shoppers += 1
                choice_id = consumer.evaluate_and_choose(catalog_view, env_snapshot)
                if choice_id:
                    success = self.marketplace.attempt_purchase(choice_id)
                    if success:
                        # Extract product_type from choice_id (e.g. LegacyAutomaker_EV -> EV)
                        # More resilient: look it up in catalog_view
                        ptype = next(o["product_type"] for o in catalog_view if o["offering_id"] == choice_id)
                        consumer.record_purchase(ptype)
                        buyers += 1

        # 4. Get sales results by firm
        legacy_sales = self.marketplace.get_firm_sales_summary("LegacyAutomaker")
        startup_sales = self.marketplace.get_firm_sales_summary("PureEVStartup")

        # 5. Automakers process sales and adjust strategy
        self.legacy_maker.process_sales(legacy_sales, env_snapshot)
        self.startup_maker.process_sales(startup_sales, env_snapshot)

        # 6. Age all consumers
        for consumer in self.population:
            consumer.age_one_tick()

        # 7. Log everything
        consumer_stats = {
            "consumers_shopping": shoppers,
            "consumers_bought": buyers,
        }
        
        # Combine producer states for the log
        producer_state = {
            "LegacyAutomaker": self.legacy_maker.get_state(),
            "PureEVStartup": self.startup_maker.get_state(),
        }
        
        # Merge sales summaries
        sales = self.marketplace.get_sales_summary()
        
        self.log.record(
            env=env_snapshot,
            sales=sales,
            producer_state=producer_state,
            consumer_stats=consumer_stats,
        )
