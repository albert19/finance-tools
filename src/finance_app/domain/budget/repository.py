from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from collections.abc import Callable

from finance_app.domain.budget.budget import MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.transaction import Transaction


class CategoryRepository(ABC):
    """Persistence port for categories."""

    @abstractmethod
    def list(self) -> list[Category]: ...

    @abstractmethod
    def get(self, category_id: str) -> Category:
        """Return the category or raise ``NotFoundError``."""

    @abstractmethod
    def save(self, category: Category) -> None: ...

    @abstractmethod
    def delete(self, category_id: str) -> None:
        """Delete the category or raise ``NotFoundError``."""


class BudgetRepository(ABC):
    """Persistence port for the MonthlyBudget aggregate (lines included)."""

    @abstractmethod
    def list(self) -> builtins.list[MonthlyBudget]: ...

    @abstractmethod
    def get(self, budget_id: str) -> MonthlyBudget:
        """Return the budget or raise ``NotFoundError``."""

    @abstractmethod
    def find_by_period(self, period: YearMonth) -> MonthlyBudget | None: ...

    @abstractmethod
    def list_by_year(self, year: int) -> builtins.list[MonthlyBudget]: ...

    @abstractmethod
    def uses_category(self, category_id: str) -> bool:
        """True when any budget line references the category."""

    @abstractmethod
    def save(self, budget: MonthlyBudget) -> None:
        """Insert or update the aggregate, including its lines."""

    @abstractmethod
    def create(self, budget: MonthlyBudget) -> None:
        """Insert a new aggregate.

        Raise ``ValidationError`` when a budget already exists for its period.
        """

    @abstractmethod
    def update(self, budget_id: str, mutate: Callable[[MonthlyBudget], None]) -> None:
        """Load, mutate and persist the aggregate atomically.

        Raise ``NotFoundError`` when the budget does not exist.
        """

    @abstractmethod
    def delete(self, budget_id: str) -> None:
        """Delete the aggregate or raise ``NotFoundError``."""


class TransactionRepository(ABC):
    """Persistence port for manually entered transactions."""

    @abstractmethod
    def list(self) -> builtins.list[Transaction]: ...

    @abstractmethod
    def get(self, transaction_id: str) -> Transaction:
        """Return the transaction or raise ``NotFoundError``."""

    @abstractmethod
    def list_by_period(self, period: YearMonth) -> builtins.list[Transaction]: ...

    @abstractmethod
    def list_by_year(self, year: int) -> builtins.list[Transaction]: ...

    @abstractmethod
    def uses_category(self, category_id: str) -> bool: ...

    @abstractmethod
    def save(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def delete(self, transaction_id: str) -> None:
        """Delete the transaction or raise ``NotFoundError``."""
