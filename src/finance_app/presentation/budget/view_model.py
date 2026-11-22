from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Signal

from finance_app.application.dto import (
    AnnualReportDTO,
    BudgetLineInput,
    CategoryDTO,
    MonthlyReportDTO,
    TransactionDTO,
    TransactionInput,
)
from finance_app.application.use_cases.budgets import (
    CreateMonthlyBudget,
    DeleteBudgetLine,
    DeleteMonthlyBudget,
    GetMonthlyBudget,
    ListBudgetPeriods,
    SaveBudgetLine,
    UpdateMonthlyBudget,
)
from finance_app.application.use_cases.categories import (
    CreateCategory,
    DeleteCategory,
    ListCategories,
    SeedDefaultCategories,
    UpdateCategory,
)
from finance_app.application.use_cases.reports import GetAnnualReport, GetMonthlyReport
from finance_app.application.use_cases.transactions import (
    DeleteTransaction,
    ListTransactions,
    RecordTransaction,
)
from finance_app.domain.budget.period import YearMonth
from finance_app.presentation.base import BaseViewModel
from finance_app.presentation.i18n import tr
from finance_app.presentation.workers import TaskRunner


@dataclass(frozen=True, slots=True)
class CategoriesUseCases:
    list: ListCategories
    create: CreateCategory
    update: UpdateCategory
    delete: DeleteCategory
    seed: SeedDefaultCategories


@dataclass(frozen=True, slots=True)
class BudgetUseCases:
    get: GetMonthlyBudget
    create: CreateMonthlyBudget
    update: UpdateMonthlyBudget
    delete: DeleteMonthlyBudget
    save_line: SaveBudgetLine
    delete_line: DeleteBudgetLine
    periods: ListBudgetPeriods
    monthly: GetMonthlyReport
    annual: GetAnnualReport


@dataclass(frozen=True, slots=True)
class TransactionsUseCases:
    list: ListTransactions
    record: RecordTransaction
    delete: DeleteTransaction


class CategoriesViewModel(BaseViewModel):
    categories_loaded = Signal(list)  # list[CategoryDTO]
    changed = Signal()  # emitted after a mutation; other views refresh

    def __init__(self, use_cases: CategoriesUseCases, runner: TaskRunner) -> None:
        super().__init__(runner)
        self._uc = use_cases
        self.categories: list[CategoryDTO] = []

    def load(self) -> None:
        def deliver(categories: list[CategoryDTO]) -> None:
            self.categories = categories
            self.categories_loaded.emit(categories)

        self._run(lambda: self._uc.list.execute(include_archived=True), deliver)

    def _changed(self, _: Any = None) -> None:
        self.load()
        self.changed.emit()

    def create(self, name: str, kind: str) -> None:
        self._run(
            lambda: self._uc.create.execute(name, kind),
            self._changed,
            tr("Category “{name}” created.", name=name),
        )

    def update(self, category_id: str, **changes: Any) -> None:
        self._run(
            lambda: self._uc.update.execute(category_id, **changes),
            self._changed,
            tr("Category updated."),
        )

    def delete(self, category_id: str) -> None:
        self._run(
            lambda: self._uc.delete.execute(category_id),
            self._changed,
            tr("Category deleted."),
        )

    def seed_defaults(self, income_names: list[str], expense_names: list[str]) -> None:
        self._run(
            lambda: self._uc.seed.execute(income_names, expense_names),
            self._changed,
            tr("Default categories created."),
        )


class BudgetViewModel(BaseViewModel):
    monthly_loaded = Signal(object)  # MonthlyReportDTO
    annual_loaded = Signal(object)  # AnnualReportDTO
    periods_loaded = Signal(list)  # list[tuple[int, int]]
    budget_changed = Signal()  # emitted after a mutation; other views refresh

    def __init__(self, use_cases: BudgetUseCases, runner: TaskRunner) -> None:
        super().__init__(runner)
        self._uc = use_cases
        self.period = YearMonth.current()
        self.year = self.period.year
        self._monthly_seq = 0
        self._annual_seq = 0

    def select_period(self, year: int, month: int) -> None:
        self.period = YearMonth(year, month)
        self.load_monthly()

    def select_year(self, year: int) -> None:
        self.year = year
        self.load_annual()

    def load_monthly(self) -> None:
        # In-flight loads can finish out of order: only the latest submission
        # may emit, otherwise an older snapshot could overwrite newer data.
        self._monthly_seq += 1
        seq, period = self._monthly_seq, self.period

        def deliver(report: MonthlyReportDTO) -> None:
            if self._monthly_seq == seq:
                self.monthly_loaded.emit(report)

        self._run(
            lambda: self._uc.monthly.execute(period.year, period.month),
            deliver,
        )

    def load_annual(self) -> None:
        self._annual_seq += 1
        seq, year = self._annual_seq, self.year

        def deliver(report: AnnualReportDTO) -> None:
            if self._annual_seq == seq:
                self.annual_loaded.emit(report)

        self._run(lambda: self._uc.annual.execute(year), deliver)

    def load_periods(self) -> None:
        self._run(self._uc.periods.execute, self.periods_loaded.emit)

    def reload(self) -> None:
        self.load_monthly()
        self.load_annual()
        self.load_periods()

    def _changed(self, _: Any = None) -> None:
        self.reload()
        self.budget_changed.emit()

    def create_budget(self, copy_from: tuple[int, int] | None = None) -> None:
        source = YearMonth(*copy_from) if copy_from else None
        self._run(
            lambda: self._uc.create.execute(self.period.year, self.period.month, copy_from=source),
            self._changed,
            tr("Budget created."),
        )

    def update_notes(self, budget_id: str, notes: str) -> None:
        self._run(
            lambda: self._uc.update.execute(budget_id, notes=notes),
            self._changed,
            tr("Budget updated."),
        )

    def delete_budget(self, budget_id: str) -> None:
        self._run(
            lambda: self._uc.delete.execute(budget_id),
            self._changed,
            tr("Budget deleted."),
        )

    def save_line(self, budget_id: str, data: BudgetLineInput, line_id: str | None = None) -> None:
        self._run(
            lambda: self._uc.save_line.execute(budget_id, data, line_id),
            self._changed,
            tr("Budget line saved."),
        )

    def delete_line(self, budget_id: str, line_id: str) -> None:
        self._run(
            lambda: self._uc.delete_line.execute(budget_id, line_id),
            self._changed,
            tr("Budget line deleted."),
        )


class TransactionsViewModel(BaseViewModel):
    transactions_loaded = Signal(list)  # list[TransactionDTO]
    changed = Signal()  # emitted after a mutation; reports refresh

    def __init__(self, use_cases: TransactionsUseCases, runner: TaskRunner) -> None:
        super().__init__(runner)
        self._uc = use_cases
        self.period = YearMonth.current()
        self._load_seq = 0

    def select_period(self, year: int, month: int) -> None:
        self.period = YearMonth(year, month)
        self.load()

    def load(self) -> None:
        # In-flight loads can finish out of order: only the latest submission
        # may emit, otherwise an older snapshot could overwrite newer data.
        self._load_seq += 1
        seq, period = self._load_seq, self.period

        def deliver(transactions: list[TransactionDTO]) -> None:
            if self._load_seq == seq:
                self.transactions_loaded.emit(transactions)

        self._run(
            lambda: self._uc.list.execute(period.year, period.month),
            deliver,
        )

    def _changed(self, _: Any = None) -> None:
        self.load()
        self.changed.emit()

    def record(self, data: TransactionInput, transaction_id: str | None = None) -> None:
        self._run(
            lambda: self._uc.record.execute(data, transaction_id),
            self._changed,
            tr("Transaction saved."),
        )

    def delete(self, transaction_id: str) -> None:
        self._run(
            lambda: self._uc.delete.execute(transaction_id),
            self._changed,
            tr("Transaction deleted."),
        )
