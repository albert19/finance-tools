from __future__ import annotations

from dataclasses import dataclass

from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.value_objects import SimulationParameters

_MIN_RATE, _MAX_RATE = -0.5, 1.0


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    parameters: SimulationParameters


class ScenarioSet:
    """Builds pessimistic / baseline / optimistic variants by shifting the return rate."""

    NAMES = ("Pessimistic", "Baseline", "Optimistic")

    def __init__(self, delta_percentage_points: float = 2.0) -> None:
        if delta_percentage_points <= 0:
            raise ValueError("Scenario delta must be positive")
        self._delta = delta_percentage_points

    @property
    def delta(self) -> float:
        return self._delta

    def build(self, base: SimulationParameters) -> tuple[Scenario, ...]:
        def shifted(sign: int) -> SimulationParameters:
            fraction = base.annual_rate.shifted(sign * self._delta).fraction
            return base.with_rate(Rate(min(max(fraction, _MIN_RATE), _MAX_RATE)))

        return (
            Scenario(self.NAMES[0], shifted(-1)),
            Scenario(self.NAMES[1], base),
            Scenario(self.NAMES[2], shifted(+1)),
        )
