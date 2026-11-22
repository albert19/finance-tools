from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from finance_app.domain.budget.budget import MonthlyBudget
from finance_app.domain.budget.category import Category, CategoryKind
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.money import Money


class VarianceStatus(StrEnum):
    FAVORABLE = "Favorable"
    ON_BUDGET = "On budget"
    UNFAVORABLE = "Unfavorable"


@dataclass(frozen=True, slots=True)
class CategoryVariance:
    """Planned vs. actual amounts for one category in a period."""

    category_id: str
    name: str
    kind: CategoryKind
    planned: Money
    actual: Money
    status: VarianceStatus

    @property
    def variance(self) -> Money:
        """Actual minus planned; positive means over (expense) or extra (income)."""
        return self.actual - self.planned

    @property
    def variance_pct(self) -> float | None:
        return (
            float(self.variance.amount / self.planned.amount) if not self.planned.is_zero else None
        )


@dataclass(frozen=True, slots=True)
class PeriodTotals:
    """Aggregated planned and actual amounts of a period."""

    planned_income: Money
    actual_income: Money
    planned_expenses: Money
    actual_expenses: Money

    @classmethod
    def of(cls, rows: Sequence[CategoryVariance]) -> PeriodTotals:
        income = [r for r in rows if r.kind is CategoryKind.INCOME]
        expenses = [r for r in rows if r.kind is CategoryKind.EXPENSE]
        return cls(
            planned_income=Money.sum(r.planned for r in income),
            actual_income=Money.sum(r.actual for r in income),
            planned_expenses=Money.sum(r.planned for r in expenses),
            actual_expenses=Money.sum(r.actual for r in expenses),
        )

    @property
    def planned_net(self) -> Money:
        return self.planned_income - self.planned_expenses

    @property
    def actual_net(self) -> Money:
        return self.actual_income - self.actual_expenses


@dataclass(frozen=True, slots=True)
class BudgetReport:
    period: YearMonth
    has_budget: bool
    rows: tuple[CategoryVariance, ...]
    totals: PeriodTotals


@dataclass(frozen=True, slots=True)
class MonthTotals:
    period: YearMonth
    has_budget: bool
    totals: PeriodTotals


@dataclass(frozen=True, slots=True)
class AnnualReport:
    """Roll-up of the twelve monthly budgets and the actuals of one year."""

    year: int
    rows: tuple[CategoryVariance, ...]
    months: tuple[MonthTotals, ...]
    totals: PeriodTotals


def _status(kind: CategoryKind, planned: Money, actual: Money, tolerance: float) -> VarianceStatus:
    if actual == planned:
        return VarianceStatus.ON_BUDGET
    if planned.is_zero:
        return (
            VarianceStatus.FAVORABLE if kind is CategoryKind.INCOME else VarianceStatus.UNFAVORABLE
        )
    # Directional deviation: positive is always "better than planned".
    directional = actual - planned if kind is CategoryKind.INCOME else planned - actual
    deviation = float(directional.amount / planned.amount)
    if deviation > tolerance:
        return VarianceStatus.FAVORABLE
    if deviation < -tolerance:
        return VarianceStatus.UNFAVORABLE
    return VarianceStatus.ON_BUDGET


class VarianceCalculator:
    """Compares monthly budgets with the transactions recorded in the same period."""

    def __init__(self, tolerance: float = 0.02) -> None:
        self._tolerance = tolerance

    def monthly(
        self,
        period: YearMonth,
        budget: MonthlyBudget | None,
        transactions: Sequence[Transaction],
        categories: Mapping[str, Category],
    ) -> BudgetReport:
        planned = budget.planned_by_category() if budget else {}
        actual: dict[str, Money] = {}
        for tx in transactions:
            if tx.period == period:
                actual[tx.category_id] = actual.get(tx.category_id, Money.zero()) + tx.amount
        rows = tuple(
            self._row(cat, planned.get(cat.id, Money.zero()), actual.get(cat.id, Money.zero()))
            for cat in self._categories(categories, planned, actual)
        )
        return BudgetReport(period, budget is not None, rows, PeriodTotals.of(rows))

    def annual(
        self,
        year: int,
        budgets: Sequence[MonthlyBudget],
        transactions: Sequence[Transaction],
        categories: Mapping[str, Category],
    ) -> AnnualReport:
        by_period = {b.period: b for b in budgets if b.period.year == year}
        months: list[MonthTotals] = []
        planned: dict[str, Money] = {}
        actual: dict[str, Money] = {}
        for period in YearMonth.months_of_year(year):
            budget = by_period.get(period)
            month_planned = budget.planned_by_category() if budget else {}
            month_actual: dict[str, Money] = {}
            for tx in transactions:
                if tx.period == period:
                    month_actual[tx.category_id] = (
                        month_actual.get(tx.category_id, Money.zero()) + tx.amount
                    )
            for cat_id, amount in month_planned.items():
                planned[cat_id] = planned.get(cat_id, Money.zero()) + amount
            for cat_id, amount in month_actual.items():
                actual[cat_id] = actual.get(cat_id, Money.zero()) + amount
            rows = tuple(
                self._row(
                    cat,
                    month_planned.get(cat.id, Money.zero()),
                    month_actual.get(cat.id, Money.zero()),
                )
                for cat in self._categories(categories, month_planned, month_actual)
            )
            months.append(MonthTotals(period, budget is not None, PeriodTotals.of(rows)))
        rows = tuple(
            self._row(cat, planned.get(cat.id, Money.zero()), actual.get(cat.id, Money.zero()))
            for cat in self._categories(categories, planned, actual)
        )
        return AnnualReport(year, rows, tuple(months), PeriodTotals.of(rows))

    def _row(self, category: Category, planned: Money, actual: Money) -> CategoryVariance:
        return CategoryVariance(
            category_id=category.id,
            name=category.name,
            kind=category.kind,
            planned=planned,
            actual=actual,
            status=_status(category.kind, planned, actual, self._tolerance),
        )

    @staticmethod
    def _categories(
        categories: Mapping[str, Category],
        planned: Mapping[str, Money],
        actual: Mapping[str, Money],
    ) -> list[Category]:
        """Categories referenced by the period, expenses first, then income, alphabetically."""
        referenced = planned.keys() | actual.keys()
        found = [categories[c] for c in referenced if c in categories]
        return sorted(found, key=lambda c: (c.kind is CategoryKind.INCOME, c.name.lower()))
