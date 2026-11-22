from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from finance_app.domain.simulation.value_objects import SimulationParameters


@dataclass(frozen=True, slots=True)
class PeriodRow:
    """One row of the breakdown (a month or an aggregated year)."""

    index: int
    opening: float
    contribution: float
    interest: float
    fees: float
    withdrawal: float
    taxes: float
    closing: float
    cost_basis: float
    real_closing: float

    @property
    def gains(self) -> float:
        """Part of the closing balance that is not own money (accumulated interest)."""
        return self.closing - self.cost_basis


@dataclass(frozen=True, slots=True)
class Summary:
    final_capital: float
    final_capital_net: float
    total_contributed: float
    total_withdrawn: float
    interest_earned: float
    total_fees: float
    total_taxes: float
    final_tax: float
    real_final_capital: float
    real_final_capital_net: float
    total_return: float
    irr: float | None
    irr_net: float | None
    depletion_month: int | None


@dataclass(frozen=True, slots=True)
class SimulationResult:
    parameters: SimulationParameters
    monthly: tuple[PeriodRow, ...]
    yearly: tuple[PeriodRow, ...]
    summary: Summary

    def balance_at(self, months: float) -> float:
        """Projected balance after ``months`` (fractional months are linearly interpolated)."""
        if months <= 0 or not self.monthly:
            return self.monthly[0].opening if self.monthly else 0.0
        if months >= len(self.monthly):
            return self.monthly[-1].closing
        whole = int(months)
        lower = self.monthly[whole - 1].closing if whole > 0 else self.monthly[0].opening
        upper = self.monthly[whole].closing
        return lower + (upper - lower) * (months - whole)


def aggregate_years(monthly: Sequence[PeriodRow]) -> tuple[PeriodRow, ...]:
    years: list[PeriodRow] = []
    for start in range(0, len(monthly), 12):
        chunk = monthly[start : start + 12]
        last = chunk[-1]
        years.append(
            PeriodRow(
                index=start // 12 + 1,
                opening=chunk[0].opening,
                contribution=sum(r.contribution for r in chunk),
                interest=sum(r.interest for r in chunk),
                fees=sum(r.fees for r in chunk),
                withdrawal=sum(r.withdrawal for r in chunk),
                taxes=sum(r.taxes for r in chunk),
                closing=last.closing,
                cost_basis=last.cost_basis,
                real_closing=last.real_closing,
            )
        )
    return tuple(years)
