"""
Simulation engine — master orchestrator for the game loop.

Wires together all bounded contexts and runs the year-by-year simulation.
"""

from __future__ import annotations

import pandas as pd

from domain.environment.service import EnvironmentService
from domain.consumer.factory import PopulationFactory
from domain.consumer.agents import AutoConsumer
from domain.producer.agents import LegacyAutomaker
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
        self.automaker = LegacyAutomaker(
            initial_capital=initial_capital,
            production_capacity=production_capacity or PRODUCTION_CAPACITY,
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

        # 2. Automaker posts catalog
        offerings = self.automaker.generate_offerings(env_snapshot)
        self.marketplace.set_catalog(offerings)

        # 3. Consumers shop
        catalog_view = self.marketplace.get_catalog_for_consumers()
        shoppers = 0
        buyers = 0

        for consumer in self.population:
            if consumer.is_in_market():
                shoppers += 1
                choice = consumer.evaluate_and_choose(catalog_view, env_snapshot)
                if choice:
                    success = self.marketplace.attempt_purchase(choice)
                    if success:
                        consumer.record_purchase(choice)
                        buyers += 1

        # 4. Get sales results
        sales = self.marketplace.get_sales_summary()

        # 5. Automaker processes sales and adjusts strategy
        self.automaker.process_sales(sales, env_snapshot)

        # 6. Age all consumers
        for consumer in self.population:
            consumer.age_one_tick()

        # 7. Log everything
        consumer_stats = {
            "consumers_shopping": shoppers,
            "consumers_bought": buyers,
        }
        self.log.record(
            env=env_snapshot,
            sales=sales,
            producer_state=self.automaker.get_state(),
            consumer_stats=consumer_stats,
        )
