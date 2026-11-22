from __future__ import annotations

from collections.abc import Mapping

from finance_app.application.budget_assemblers import (
    budget_dto,
    month_totals_dto,
    monthly_report_rows,
    totals_dto,
    transaction_dto,
    variance_row_dto,
)
from finance_app.application.dto import AnnualReportDTO, MonthlyReportDTO
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.budget.variance import VarianceCalculator


class GetMonthlyReport:
    """Budget lines, variance rows, totals and transactions of one month."""

    def __init__(
        self,
        budgets: BudgetRepository,
        transactions: TransactionRepository,
        categories: CategoryRepository,
        calculator: VarianceCalculator,
    ) -> None:
        self._budgets = budgets
        self._transactions = transactions
        self._categories = categories
        self._calculator = calculator

    def _map(self) -> Mapping[str, Category]:
        return {c.id: c for c in self._categories.list()}

    def execute(self, year: int, month: int) -> MonthlyReportDTO:
        period = YearMonth(year, month)
        categories = self._map()
        budget = self._budgets.find_by_period(period)
        transactions: list[Transaction] = sorted(
            self._transactions.list_by_period(period), key=lambda t: (t.date, t.description)
        )
        report = self._calculator.monthly(period, budget, transactions, categories)
        return MonthlyReportDTO(
            year=year,
            month=month,
            budget=budget_dto(budget, categories) if budget else None,
            rows=monthly_report_rows(report),
            totals=totals_dto(report.totals),
            transactions=tuple(transaction_dto(tx, categories) for tx in transactions),
        )


class GetAnnualReport:
    """Roll-up of the year's monthly budgets and the year's transactions."""

    def __init__(
        self,
        budgets: BudgetRepository,
        transactions: TransactionRepository,
        categories: CategoryRepository,
        calculator: VarianceCalculator,
    ) -> None:
        self._budgets = budgets
        self._transactions = transactions
        self._categories = categories
        self._calculator = calculator

    def execute(self, year: int) -> AnnualReportDTO:
        categories = self._map()
        report = self._calculator.annual(
            year,
            self._budgets.list_by_year(year),
            self._transactions.list_by_year(year),
            categories,
        )
        return AnnualReportDTO(
            year=year,
            rows=tuple(variance_row_dto(r) for r in report.rows),
            months=tuple(month_totals_dto(m) for m in report.months),
            totals=totals_dto(report.totals),
        )

    def _map(self) -> Mapping[str, Category]:
        return {c.id: c for c in self._categories.list()}
