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
from simulation.events import EventDetector
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
        # Startup gets 20% of legacy capital and 5K EV capacity (Tesla/Rivian proxy)
        self.startup_maker = PureEVStartup(
            initial_capital=initial_capital * 0.20,
            production_capacity=5_000,
        )
        self.marketplace = Marketplace()
        self.log = SimulationLog()
        self.event_detector = EventDetector()

    def run(self) -> pd.DataFrame:
        """Execute the full simulation timeline. Returns the log DataFrame."""
        while not self.env.is_complete:
            self._tick()
            self.env.tick()
        self.log.to_micro_json("output/simulation_micro.json")
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

        # 7.5 Fleet composition (active cars on road)
        fleet_counts = {"ICE": 0, "HYBRID": 0, "EV": 0}
        for consumer in self.population:
            vehicle = consumer.profile.current_vehicle
            if vehicle in fleet_counts:
                fleet_counts[vehicle] += 1
        fleet_total = max(1, sum(fleet_counts.values()))
        fleet_pct = {
            "fleet_ice_pct": fleet_counts["ICE"] / fleet_total,
            "fleet_hybrid_pct": fleet_counts["HYBRID"] / fleet_total,
            "fleet_ev_pct": fleet_counts["EV"] / fleet_total,
            "fleet_total_vehicles": fleet_total,
        }

        # 7. Collect producer states
        legacy_state = self.legacy_maker.get_state()
        startup_state = self.startup_maker.get_state()
        producer_state = {
            "LegacyAutomaker": legacy_state,
            "PureEVStartup": startup_state,
        }

        # 8. Detect events
        env_dict = env_snapshot.to_dict()
        tick_events = self.event_detector.detect(
            env_snapshot.year, env_dict, producer_state
        )

        # 9. Log everything
        consumer_stats = {
            "consumers_shopping": shoppers,
            "consumers_bought": buyers,
            **fleet_pct,
        }
        sales = self.marketplace.get_sales_summary()

        self.log.record(
            env=env_snapshot,
            sales=sales,
            producer_state=producer_state,
            consumer_stats=consumer_stats,
        )

        # 10. Micro-state log for React web player
        macro_state = {
            # ── Environment ──
            "ev_tax_credit": env_snapshot.ev_tax_credit,
            "gas_price_per_gallon": env_snapshot.gas_price_per_gallon,
            "emissions_penalty_per_unit": env_snapshot.emissions_penalty_per_unit,
            "cafe_ev_mandate_pct": env_snapshot.cafe_ev_mandate_pct,
            "charging_infrastructure_index": env_snapshot.charging_infrastructure_index,
            "battery_cost_index": env_snapshot.battery_cost_index,
            # ── Legacy Automaker ──
            "legacy_capital": legacy_state.get("capital", 0),
            "legacy_revenue": legacy_state.get("revenue", 0),
            "legacy_net_income": legacy_state.get("net_income", 0),
            "legacy_fcf": legacy_state.get("fcf", 0),
            "legacy_ev_cogs_pct": legacy_state.get("ev_cogs_pct", 0),
            "legacy_gross_margin_pct": legacy_state.get("gross_margin_pct", 0),
            # ── Startup ──
            "startup_capital": startup_state.get("capital", 0),
            "startup_revenue": startup_state.get("revenue", 0),
            "startup_net_income": startup_state.get("net_income", 0),
            "startup_fcf": startup_state.get("fcf", 0),
            "startup_is_bankrupt": startup_state.get("is_bankrupt", False),
            "startup_ev_cogs_pct": startup_state.get("ev_cogs_pct", 0),
            "startup_gross_margin_pct": startup_state.get("gross_margin_pct", 0),
            "startup_vc_funding_raised": startup_state.get("vc_funding_raised", 0),
            "startup_total_dilution": startup_state.get("total_dilution", 0),
            # ── Fleet Composition ──
            "fleet_ice_pct": fleet_pct["fleet_ice_pct"],
            "fleet_hybrid_pct": fleet_pct["fleet_hybrid_pct"],
            "fleet_ev_pct": fleet_pct["fleet_ev_pct"],
            "fleet_total_vehicles": fleet_pct["fleet_total_vehicles"],
        }
        micro_state = [c.profile.to_micro_dict() for c in self.population]
        events_dicts = [e.to_dict() for e in tick_events]
        self.log.record_micro(env_snapshot.year, macro_state, micro_state, events_dicts)
