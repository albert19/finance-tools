"""Google Sheets persistence for categories, monthly budgets and transactions.

Each repository caches its sheet(s) in memory and re-reads them after every
write so row numbers stay correct (and external edits are picked up).
"""

from __future__ import annotations

import builtins
import copy
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from finance_app.domain.budget.budget import BudgetLine, MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.infrastructure.sheets.budget_mappers import (
    budget_line_to_row,
    budget_to_row,
    category_to_row,
    row_to_budget,
    row_to_budget_line,
    row_to_category,
    row_to_transaction,
    transaction_to_row,
)
from finance_app.infrastructure.sheets.cells import Row, RowMappingError
from finance_app.infrastructure.sheets.client import SheetsGateway
from finance_app.infrastructure.sheets.schema import (
    BUDGET_LINES_SHEET,
    BUDGETS_SHEET,
    CATEGORIES_SHEET,
    TRANSACTIONS_SHEET,
    ensure_schema,
    row_range,
)
from finance_app.infrastructure.sheets.table import SheetTable

logger = logging.getLogger(__name__)


class _SheetRepository:
    """Shared plumbing: schema bootstrap plus a cached id -> entity map."""

    SHEETS: tuple[str, ...] = ()

    def __init__(self, gateway: SheetsGateway) -> None:
        self._gateway = gateway
        self._lock = threading.RLock()
        self._sheet_ids: dict[str, int] | None = None
        self._cache: dict[str, Any] | None = None

    def _ensure(self) -> None:
        if self._sheet_ids is None:
            self._sheet_ids = ensure_schema(self._gateway, self.SHEETS)


class GoogleSheetsCategoryRepository(_SheetRepository, CategoryRepository):
    SHEETS = (CATEGORIES_SHEET,)

    def __init__(self, gateway: SheetsGateway) -> None:
        super().__init__(gateway)
        self._table = SheetTable(gateway, CATEGORIES_SHEET)

    def refresh(self) -> None:
        with self._lock:
            self._ensure()
            assert self._sheet_ids is not None
            self._table.sheet_id = self._sheet_ids[CATEGORIES_SHEET]
            cache: dict[str, Category] = {}
            for number, row in self._table.read():
                try:
                    category = row_to_category(row)
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", CATEGORIES_SHEET, number, exc)
                    continue
                cache[category.id] = category
            self._cache = cache

    def _items(self) -> dict[str, Category]:
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache

    def list(self) -> builtins.list[Category]:
        with self._lock:
            return [copy.deepcopy(c) for c in self._items().values()]

    def get(self, category_id: str) -> Category:
        with self._lock:
            try:
                return copy.deepcopy(self._items()[category_id])
            except KeyError:
                raise NotFoundError(f"Category {category_id} not found") from None

    def save(self, category: Category) -> None:
        with self._lock:
            self._items()
            if category.id in self._table.rows:
                self._table.update(category.id, category_to_row(category))
            else:
                self._table.append([category_to_row(category)])
            self.refresh()

    def delete(self, category_id: str) -> None:
        with self._lock:
            if category_id not in self._items():
                raise NotFoundError(f"Category {category_id} not found")
            self._table.delete([category_id])
            self.refresh()


class GoogleSheetsBudgetRepository(_SheetRepository, BudgetRepository):
    """Stores budgets in ``Budgets`` and their lines in ``Budget lines``."""

    SHEETS = (BUDGETS_SHEET, BUDGET_LINES_SHEET)

    def __init__(self, gateway: SheetsGateway) -> None:
        super().__init__(gateway)
        self._budgets_table = SheetTable(gateway, BUDGETS_SHEET)
        self._lines_table = SheetTable(gateway, BUDGET_LINES_SHEET)

    def refresh(self) -> None:
        with self._lock:
            self._ensure()
            assert self._sheet_ids is not None
            self._budgets_table.sheet_id = self._sheet_ids[BUDGETS_SHEET]
            self._lines_table.sheet_id = self._sheet_ids[BUDGET_LINES_SHEET]
            lines: dict[str, list[BudgetLine]] = defaultdict(list)
            for number, row in self._lines_table.read():
                try:
                    budget_id, line = row_to_budget_line(row)
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", BUDGET_LINES_SHEET, number, exc)
                    continue
                lines[budget_id].append(line)
            cache: dict[str, MonthlyBudget] = {}
            for number, row in self._budgets_table.read():
                try:
                    budget = row_to_budget(row, lines.get(str(row[0]), []))
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", BUDGETS_SHEET, number, exc)
                    continue
                cache[budget.id] = budget
            self._cache = cache

    def _items(self) -> dict[str, MonthlyBudget]:
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache

    def list(self) -> builtins.list[MonthlyBudget]:
        with self._lock:
            return [copy.deepcopy(b) for b in self._items().values()]

    def get(self, budget_id: str) -> MonthlyBudget:
        with self._lock:
            try:
                return copy.deepcopy(self._items()[budget_id])
            except KeyError:
                raise NotFoundError(f"Budget {budget_id} not found") from None

    def find_by_period(self, period: YearMonth) -> MonthlyBudget | None:
        with self._lock:
            for budget in self._items().values():
                if budget.period == period:
                    return copy.deepcopy(budget)
            return None

    def list_by_year(self, year: int) -> builtins.list[MonthlyBudget]:
        with self._lock:
            return [copy.deepcopy(b) for b in self._items().values() if b.period.year == year]

    def uses_category(self, category_id: str) -> bool:
        with self._lock:
            return any(
                line.category_id == category_id
                for budget in self._items().values()
                for line in budget.lines
            )

    def save(self, budget: MonthlyBudget) -> None:
        with self._lock:
            existing = self._items().get(budget.id)
            updates: list[tuple[str, list[Row]]] = []
            if existing is not None:
                row = self._budgets_table.rows[budget.id]
                updates.append((row_range(BUDGETS_SHEET, row), [budget_to_row(budget)]))
            old = {line.id: line for line in existing.lines} if existing else {}
            new_rows: list[Row] = []
            for line in budget.lines:
                if line.id not in old:
                    new_rows.append(budget_line_to_row(budget.id, line))
                elif old[line.id] != line:
                    row = self._lines_table.rows[line.id]
                    updates.append(
                        (row_range(BUDGET_LINES_SHEET, row), [budget_line_to_row(budget.id, line)])
                    )
            removed = old.keys() - {line.id for line in budget.lines}

            self._gateway.update_values(updates)
            if existing is None:
                self._budgets_table.append([budget_to_row(budget)])
            self._lines_table.append(new_rows)
            self._lines_table.delete(removed)
            self.refresh()

    def create(self, budget: MonthlyBudget) -> None:
        with self._lock:
            if any(b.period == budget.period for b in self._items().values()):
                raise ValidationError.single("period", "A budget already exists for that month.")
            self.save(budget)

    def update(self, budget_id: str, mutate: Callable[[MonthlyBudget], None]) -> None:
        with self._lock:
            try:
                # Deep copy: save() diffs against the cached entity to decide
                # which line rows to write, so the cache must stay untouched.
                budget = copy.deepcopy(self._items()[budget_id])
            except KeyError:
                raise NotFoundError(f"Budget {budget_id} not found") from None
            mutate(budget)
            self.save(budget)

    def delete(self, budget_id: str) -> None:
        with self._lock:
            budget = self._items().get(budget_id)
            if budget is None:
                raise NotFoundError(f"Budget {budget_id} not found")
            assert self._sheet_ids is not None
            rows = [(self._sheet_ids[BUDGETS_SHEET], self._budgets_table.rows[budget_id])]
            rows += [
                (self._sheet_ids[BUDGET_LINES_SHEET], self._lines_table.rows[line.id])
                for line in budget.lines
            ]
            self._gateway.delete_rows(rows)
            self.refresh()


class GoogleSheetsTransactionRepository(_SheetRepository, TransactionRepository):
    SHEETS = (TRANSACTIONS_SHEET,)

    def __init__(self, gateway: SheetsGateway) -> None:
        super().__init__(gateway)
        self._table = SheetTable(gateway, TRANSACTIONS_SHEET)

    def refresh(self) -> None:
        with self._lock:
            self._ensure()
            assert self._sheet_ids is not None
            self._table.sheet_id = self._sheet_ids[TRANSACTIONS_SHEET]
            cache: dict[str, Transaction] = {}
            for number, row in self._table.read():
                try:
                    transaction = row_to_transaction(row)
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", TRANSACTIONS_SHEET, number, exc)
                    continue
                cache[transaction.id] = transaction
            self._cache = cache

    def _items(self) -> dict[str, Transaction]:
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache

    def list(self) -> builtins.list[Transaction]:
        with self._lock:
            return [copy.deepcopy(t) for t in self._items().values()]

    def get(self, transaction_id: str) -> Transaction:
        with self._lock:
            try:
                return copy.deepcopy(self._items()[transaction_id])
            except KeyError:
                raise NotFoundError(f"Transaction {transaction_id} not found") from None

    def list_by_period(self, period: YearMonth) -> builtins.list[Transaction]:
        with self._lock:
            return [copy.deepcopy(t) for t in self._items().values() if t.period == period]

    def list_by_year(self, year: int) -> builtins.list[Transaction]:
        with self._lock:
            return [copy.deepcopy(t) for t in self._items().values() if t.date.year == year]

    def uses_category(self, category_id: str) -> bool:
        with self._lock:
            return any(t.category_id == category_id for t in self._items().values())

    def save(self, transaction: Transaction) -> None:
        with self._lock:
            self._items()
            if transaction.id in self._table.rows:
                self._table.update(transaction.id, transaction_to_row(transaction))
            else:
                self._table.append([transaction_to_row(transaction)])
            self.refresh()

    def delete(self, transaction_id: str) -> None:
        with self._lock:
            if transaction_id not in self._items():
                raise NotFoundError(f"Transaction {transaction_id} not found")
            self._table.delete([transaction_id])
            self.refresh()
