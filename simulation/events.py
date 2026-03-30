"""
Event detection — emits discrete events for React chart annotations.

Compares adjacent-year snapshots and financial statements to detect
policy shifts and corporate milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class SimulationEvent:
    """An annotatable event for the visualization layer."""
    year: int
    category: str  # "policy" | "corporate"
    severity: str  # "info" | "warning" | "critical"
    label: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


class EventDetector:
    """
    Stateful detector that compares the current tick's data
    against the previous tick's to emit events.
    """

    def __init__(self) -> None:
        self._prev_env: dict | None = None
        self._prev_states: dict[str, dict] | None = None

    def detect(
        self,
        year: int,
        env: dict,
        producer_states: dict[str, dict],
    ) -> list[SimulationEvent]:
        events: list[SimulationEvent] = []

        # ── Policy events ──
        if self._prev_env is not None:
            events.extend(self._detect_policy(year, env))

        # ── Corporate events ──
        for firm, state in producer_states.items():
            events.extend(self._detect_corporate(year, firm, state))

        self._prev_env = dict(env)
        self._prev_states = {k: dict(v) for k, v in producer_states.items()}
        return events

    # ── Private ──

    def _detect_policy(self, year: int, env: dict) -> list[SimulationEvent]:
        events: list[SimulationEvent] = []
        prev = self._prev_env
        assert prev is not None

        # EV tax credit changed
        curr_credit = env.get("ev_tax_credit", 0)
        prev_credit = prev.get("ev_tax_credit", 0)
        if curr_credit != prev_credit:
            direction = "increased" if curr_credit > prev_credit else "decreased"
            if curr_credit == 0:
                events.append(SimulationEvent(
                    year, "policy", "critical",
                    "EV Tax Credit Eliminated",
                    f"Federal EV credit dropped from ${prev_credit:,.0f} to $0",
                ))
            else:
                events.append(SimulationEvent(
                    year, "policy", "info",
                    f"EV Credit {direction.title()}",
                    f"${prev_credit:,.0f} → ${curr_credit:,.0f}",
                ))

        # Emissions penalty activated or changed
        curr_penalty = env.get("emissions_penalty_per_unit", 0)
        prev_penalty = prev.get("emissions_penalty_per_unit", 0)
        if curr_penalty > 0 and prev_penalty == 0:
            events.append(SimulationEvent(
                year, "policy", "warning",
                "Emissions Penalties Activated",
                f"${curr_penalty:,.0f} per ICE unit sold",
            ))
        elif curr_penalty != prev_penalty and curr_penalty > 0:
            events.append(SimulationEvent(
                year, "policy", "info",
                "Emissions Penalty Changed",
                f"${prev_penalty:,.0f} → ${curr_penalty:,.0f} per unit",
            ))

        return events

    def _detect_corporate(self, year: int, firm: str, state: dict) -> list[SimulationEvent]:
        events: list[SimulationEvent] = []
        prev = self._prev_states.get(firm, {}) if self._prev_states else {}

        # Startup bankruptcy
        if state.get("is_bankrupt") and not prev.get("is_bankrupt"):
            events.append(SimulationEvent(
                year, "corporate", "critical",
                f"{firm} Bankrupt",
                f"Capital exhausted with no future funding rounds",
            ))

        # External funding
        funding = state.get("external_funding", 0)
        if funding > 0:
            events.append(SimulationEvent(
                year, "corporate", "info",
                f"{firm} Funding Round",
                f"Received ${funding / 1e6:.0f}M external funding",
            ))

        # Negative net income (first occurrence)
        net_income = state.get("net_income", 0)
        prev_net_income = prev.get("net_income", 0)
        if net_income < 0 and prev_net_income >= 0:
            events.append(SimulationEvent(
                year, "corporate", "warning",
                f"{firm} Net Loss",
                f"First unprofitable year: ${net_income / 1e6:.0f}M",
            ))

        # EV breakeven (gross margin turns positive)
        ev_gp = state.get("gross_profit_by_dt", {}).get("EV", 0)
        prev_ev_gp = prev.get("gross_profit_by_dt", {}).get("EV", 0)
        if ev_gp > 0 and prev_ev_gp <= 0 and prev:
            events.append(SimulationEvent(
                year, "corporate", "info",
                f"{firm} EV Breakeven",
                f"EV gross margin turned positive",
            ))

        return events
