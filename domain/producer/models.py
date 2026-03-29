"""
Producer domain models — value objects for corporate state tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CapitalLedger:
    """
    Tracks the financial state of a producer.
    Mutable — updated each tick after processing sales.
    """
    capital: float
    cumulative_revenue: float = 0.0
    cumulative_cogs: float = 0.0
    cumulative_penalties: float = 0.0
    cumulative_r_and_d: float = 0.0
    cumulative_retooling: float = 0.0

    def record_revenue(self, amount: float) -> None:
        self.capital += amount
        self.cumulative_revenue += amount

    def record_cost(self, amount: float, category: str = "cogs") -> None:
        self.capital -= amount
        if category == "cogs":
            self.cumulative_cogs += amount
        elif category == "penalty":
            self.cumulative_penalties += amount
        elif category == "r_and_d":
            self.cumulative_r_and_d += amount
        elif category == "retooling":
            self.cumulative_retooling += amount

    def to_dict(self) -> dict:
        return {
            "capital": self.capital,
            "cumulative_revenue": self.cumulative_revenue,
            "cumulative_cogs": self.cumulative_cogs,
            "cumulative_penalties": self.cumulative_penalties,
            "cumulative_r_and_d": self.cumulative_r_and_d,
            "cumulative_retooling": self.cumulative_retooling,
        }


@dataclass
class RAndDPipeline:
    """
    Tracks cumulative R&D investment by product category.
    When investment crosses a milestone threshold, effects are triggered.
    """
    investments: dict[str, float] = field(default_factory=dict)
    milestones_achieved: dict[str, int] = field(default_factory=dict)

    def invest(self, category: str, amount: float) -> None:
        """Add investment to a category."""
        self.investments[category] = self.investments.get(category, 0.0) + amount

    def get_investment(self, category: str) -> float:
        return self.investments.get(category, 0.0)

    def get_milestones(self, category: str) -> int:
        return self.milestones_achieved.get(category, 0)

    def check_and_award_milestones(
        self, category: str, threshold: float
    ) -> int:
        """
        Check if new milestones have been reached for a category.
        Returns the number of NEW milestones achieved this call.
        """
        total_invested = self.get_investment(category)
        total_milestones = int(total_invested // threshold)
        current = self.milestones_achieved.get(category, 0)
        new_milestones = total_milestones - current
        if new_milestones > 0:
            self.milestones_achieved[category] = total_milestones
        return max(0, new_milestones)

    def to_dict(self) -> dict:
        return {
            "investments": dict(self.investments),
            "milestones_achieved": dict(self.milestones_achieved),
        }
