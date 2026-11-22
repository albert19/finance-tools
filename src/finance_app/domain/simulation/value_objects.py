from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate

MAX_HORIZON_MONTHS = 100 * 12


class Frequency(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"

    @property
    def periods_per_year(self) -> int:
        return _PERIODS_PER_YEAR[self]

    @property
    def months_per_period(self) -> int:
        if self is Frequency.DAILY:
            raise ValueError("Daily frequency has no whole number of months per period")
        return 12 // self.periods_per_year

    @property
    def label(self) -> str:
        return self.value.capitalize()


_PERIODS_PER_YEAR = {
    Frequency.DAILY: 365,
    Frequency.MONTHLY: 12,
    Frequency.QUARTERLY: 4,
    Frequency.SEMIANNUAL: 2,
    Frequency.ANNUAL: 1,
}

#: Frequencies usable for cash flows (contributions / withdrawals) in the monthly engine.
CASH_FLOW_FREQUENCIES: tuple[Frequency, ...] = (
    Frequency.MONTHLY,
    Frequency.QUARTERLY,
    Frequency.SEMIANNUAL,
    Frequency.ANNUAL,
)
COMPOUNDING_FREQUENCIES: tuple[Frequency, ...] = tuple(Frequency)


class ContributionTiming(StrEnum):
    BEGINNING = "beginning"
    END = "end"

    @property
    def label(self) -> str:
        return f"{self.value.capitalize()} of period"


@dataclass(frozen=True, slots=True)
class TimeHorizon:
    months: int

    def __post_init__(self) -> None:
        if not 1 <= self.months <= MAX_HORIZON_MONTHS:
            raise ValidationError.single(
                "horizon_months",
                f"Time horizon must be between 1 month and {MAX_HORIZON_MONTHS // 12} years.",
            )

    @classmethod
    def from_years(cls, years: int) -> TimeHorizon:
        return cls(years * 12)

    @property
    def years(self) -> float:
        return self.months / 12


@dataclass(frozen=True, slots=True)
class WithdrawalPlan:
    """Periodic withdrawals (e.g. retirement phase) starting after ``start_month`` months."""

    amount: Money
    frequency: Frequency = Frequency.MONTHLY
    start_month: int = 0

    def validation_errors(self) -> dict[str, str]:
        errors: dict[str, str] = {}
        if self.amount.amount <= 0:
            errors["withdrawal_amount"] = "Withdrawal amount must be greater than zero."
        if self.frequency not in CASH_FLOW_FREQUENCIES:
            errors["withdrawal_frequency"] = "Unsupported withdrawal frequency."
        if self.start_month < 0:
            errors["withdrawal_start_month"] = "Withdrawal start cannot be negative."
        return errors


@dataclass(frozen=True, slots=True)
class SimulationParameters:
    """All inputs of a simulation. Self-validating and immutable."""

    initial_capital: Money
    contribution: Money
    contribution_frequency: Frequency
    annual_rate: Rate
    compounding_frequency: Frequency
    horizon: TimeHorizon
    contribution_timing: ContributionTiming = ContributionTiming.END
    inflation: Rate = Rate(0.0)
    ter: Rate = Rate(0.0)
    contribution_increase: Rate = Rate(0.0)
    withdrawal: WithdrawalPlan | None = None
    apply_taxes: bool = False

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if self.initial_capital.is_negative:
            errors["initial_capital"] = "Initial capital cannot be negative."
        if self.contribution.is_negative:
            errors["contribution"] = "Periodic contribution cannot be negative."
        if self.contribution_frequency not in CASH_FLOW_FREQUENCIES:
            errors["contribution_frequency"] = "Unsupported contribution frequency."
        if not -0.5 <= self.annual_rate.fraction <= 1.0:
            errors["annual_rate"] = "Annual return must be between -50 % and 100 %."
        if not 0 <= self.inflation.fraction <= 0.5:
            errors["inflation"] = "Inflation must be between 0 % and 50 %."
        if not 0 <= self.ter.fraction <= 0.1:
            errors["ter"] = "Fees (TER) must be between 0 % and 10 %."
        if not 0 <= self.contribution_increase.fraction <= 0.5:
            errors["contribution_increase"] = "Contribution increase must be between 0 % and 50 %."
        if self.initial_capital.amount == 0 and self.contribution.amount == 0:
            errors["initial_capital"] = "Enter an initial capital or a periodic contribution."
        if self.withdrawal is not None:
            errors.update(self.withdrawal.validation_errors())
            if self.withdrawal.start_month >= self.horizon.months:
                errors["withdrawal_start_month"] = (
                    "Withdrawals must start before the end of the time horizon."
                )
        if errors:
            raise ValidationError(errors)

    def with_rate(self, rate: Rate) -> SimulationParameters:
        return replace(self, annual_rate=rate)
