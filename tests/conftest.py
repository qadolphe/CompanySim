"""
Shared test fixtures for the CompanySim test suite.

Organized by domain context. Each fixture is scoped appropriately
to balance isolation and performance.
"""

import pytest

from domain.environment.service import EnvironmentService
from domain.environment.models import PolicySnapshot
from simulation.config import START_YEAR, END_YEAR


# ═══════════════════════════════════════════════════════════════════
# Environment Context Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def env_service() -> EnvironmentService:
    """Fresh EnvironmentService with default config."""
    return EnvironmentService(start_year=START_YEAR, end_year=END_YEAR)


@pytest.fixture
def env_snapshot_2024(env_service: EnvironmentService) -> PolicySnapshot:
    """PolicySnapshot for the first year (2024)."""
    return env_service.snapshot()


@pytest.fixture
def env_snapshot_2030() -> PolicySnapshot:
    """PolicySnapshot for 2030 — mid-timeline, useful for testing policy shifts."""
    svc = EnvironmentService(start_year=START_YEAR, end_year=END_YEAR)
    for _ in range(2030 - START_YEAR):
        svc.tick()
    return svc.snapshot()


# ═══════════════════════════════════════════════════════════════════
# Convenience: all snapshots across the timeline
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def all_snapshots() -> list[PolicySnapshot]:
    """All PolicySnapshots from START_YEAR through END_YEAR (inclusive)."""
    svc = EnvironmentService(start_year=START_YEAR, end_year=END_YEAR)
    snapshots = [svc.snapshot()]
    while not svc.is_complete:
        svc.tick()
        if not svc.is_complete:
            snapshots.append(svc.snapshot())
    return snapshots
