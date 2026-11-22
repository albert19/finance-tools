from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.simulation.result import SimulationResult
from finance_app.domain.simulation.returns import xirr
from finance_app.domain.simulation.simulator import CompoundInterestSimulator

_DAYS_PER_MONTH = 365.25 / 12


class PerformanceStatus(StrEnum):
    NO_DATA = "No data yet"
    AHEAD = "Ahead of plan"
    ON_TRACK = "On track"
    BEHIND = "Behind plan"


def months_between(start: date, end: date) -> float:
    return (end - start).days / _DAYS_PER_MONTH


@dataclass(frozen=True, slots=True)
class ComparisonPoint:
    date: date
    months_elapsed: float
    projected: float
    actual: float
    contributed_actual: float

    @property
    def deviation(self) -> float:
        return self.actual - self.projected

    @property
    def deviation_pct(self) -> float | None:
        return self.deviation / self.projected if self.projected else None


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    projection: SimulationResult
    points: tuple[ComparisonPoint, ...]
    expected_rate: float
    actual_xirr: float | None
    status: PerformanceStatus

    @property
    def latest(self) -> ComparisonPoint | None:
        return self.points[-1] if self.points else None


class PerformanceComparator:
    """Compares actual snapshots with the projection made when the investment was created."""

    def __init__(self, simulator: CompoundInterestSimulator, tolerance: float = 0.02) -> None:
        self._simulator = simulator
        self._tolerance = tolerance

    def compare(self, investment: Investment) -> ComparisonReport:
        projection = self._simulator.run(investment.parameters)
        initial = investment.parameters.initial_capital.to_float()
        contributed = initial
        flows: list[tuple[date, float]] = [(investment.start_date, -initial)]
        points: list[ComparisonPoint] = []
        for snap in investment.snapshots:
            contributed += snap.contribution.to_float() - snap.withdrawal.to_float()
            flows.append((snap.date, snap.withdrawal.to_float() - snap.contribution.to_float()))
            months = months_between(investment.start_date, snap.date)
            points.append(
                ComparisonPoint(
                    date=snap.date,
                    months_elapsed=months,
                    projected=projection.balance_at(months),
                    actual=snap.market_value.to_float(),
                    contributed_actual=contributed,
                )
            )
        actual_xirr = None
        if points and points[-1].date > investment.start_date:
            actual_xirr = xirr([*flows, (points[-1].date, points[-1].actual)])
        return ComparisonReport(
            projection=projection,
            points=tuple(points),
            expected_rate=projection.summary.irr or investment.parameters.annual_rate.fraction,
            actual_xirr=actual_xirr,
            status=self._status(points[-1] if points else None),
        )

    def _status(self, latest: ComparisonPoint | None) -> PerformanceStatus:
        if latest is None or latest.deviation_pct is None:
            return PerformanceStatus.NO_DATA
        if latest.deviation_pct > self._tolerance:
            return PerformanceStatus.AHEAD
        if latest.deviation_pct < -self._tolerance:
            return PerformanceStatus.BEHIND
        return PerformanceStatus.ON_TRACK
