from __future__ import annotations

import builtins
import copy
import threading
from collections.abc import Callable

from finance_app.domain.budget.budget import MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.errors import NotFoundError, ValidationError


class InMemoryCategoryRepository(CategoryRepository):
    """Non-persistent repository used for tests and offline mode."""

    def __init__(self) -> None:
        self._items: dict[str, Category] = {}

    def list(self) -> builtins.list[Category]:
        return [copy.deepcopy(c) for c in self._items.values()]

    def get(self, category_id: str) -> Category:
        try:
            return copy.deepcopy(self._items[category_id])
        except KeyError:
            raise NotFoundError(f"Category {category_id} not found") from None

    def save(self, category: Category) -> None:
        self._items[category.id] = copy.deepcopy(category)

    def delete(self, category_id: str) -> None:
        if self._items.pop(category_id, None) is None:
            raise NotFoundError(f"Category {category_id} not found")


class InMemoryBudgetRepository(BudgetRepository):
    """Non-persistent repository used for tests and offline mode."""

    def __init__(self) -> None:
        self._items: dict[str, MonthlyBudget] = {}
        self._lock = threading.RLock()

    def list(self) -> builtins.list[MonthlyBudget]:
        return [copy.deepcopy(b) for b in self._items.values()]

    def get(self, budget_id: str) -> MonthlyBudget:
        try:
            return copy.deepcopy(self._items[budget_id])
        except KeyError:
            raise NotFoundError(f"Budget {budget_id} not found") from None

    def find_by_period(self, period: YearMonth) -> MonthlyBudget | None:
        for budget in self._items.values():
            if budget.period == period:
                return copy.deepcopy(budget)
        return None

    def list_by_year(self, year: int) -> builtins.list[MonthlyBudget]:
        return [copy.deepcopy(b) for b in self._items.values() if b.period.year == year]

    def uses_category(self, category_id: str) -> bool:
        return any(
            line.category_id == category_id
            for budget in self._items.values()
            for line in budget.lines
        )

    def save(self, budget: MonthlyBudget) -> None:
        with self._lock:
            self._items[budget.id] = copy.deepcopy(budget)

    def create(self, budget: MonthlyBudget) -> None:
        with self._lock:
            if any(b.period == budget.period for b in self._items.values()):
                raise ValidationError.single("period", "A budget already exists for that month.")
            self._items[budget.id] = copy.deepcopy(budget)

    def update(self, budget_id: str, mutate: Callable[[MonthlyBudget], None]) -> None:
        with self._lock:
            entity = self._items.get(budget_id)
            if entity is None:
                raise NotFoundError(f"Budget {budget_id} not found")
            mutate(entity)

    def delete(self, budget_id: str) -> None:
        with self._lock:
            if self._items.pop(budget_id, None) is None:
                raise NotFoundError(f"Budget {budget_id} not found")


class InMemoryTransactionRepository(TransactionRepository):
    """Non-persistent repository used for tests and offline mode."""

    def __init__(self) -> None:
        self._items: dict[str, Transaction] = {}

    def list(self) -> builtins.list[Transaction]:
        return [copy.deepcopy(t) for t in self._items.values()]

    def get(self, transaction_id: str) -> Transaction:
        try:
            return copy.deepcopy(self._items[transaction_id])
        except KeyError:
            raise NotFoundError(f"Transaction {transaction_id} not found") from None

    def list_by_period(self, period: YearMonth) -> builtins.list[Transaction]:
        return [copy.deepcopy(t) for t in self._items.values() if t.period == period]

    def list_by_year(self, year: int) -> builtins.list[Transaction]:
        return [copy.deepcopy(t) for t in self._items.values() if t.date.year == year]

    def uses_category(self, category_id: str) -> bool:
        return any(t.category_id == category_id for t in self._items.values())

    def save(self, transaction: Transaction) -> None:
        self._items[transaction.id] = copy.deepcopy(transaction)

    def delete(self, transaction_id: str) -> None:
        if self._items.pop(transaction_id, None) is None:
            raise NotFoundError(f"Transaction {transaction_id} not found")
