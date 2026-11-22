from __future__ import annotations

from typing import Any

from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.value_objects import (
    ContributionTiming,
    Frequency,
    SimulationParameters,
    TimeHorizon,
)


def make_params(**overrides: Any) -> SimulationParameters:
    values: dict[str, Any] = {
        "initial_capital": Money.of(10_000),
        "contribution": Money.of(200),
        "contribution_frequency": Frequency.MONTHLY,
        "annual_rate": Rate.from_percent(6),
        "compounding_frequency": Frequency.MONTHLY,
        "horizon": TimeHorizon.from_years(10),
        "contribution_timing": ContributionTiming.END,
    }
    values.update(overrides)
    return SimulationParameters(**values)
