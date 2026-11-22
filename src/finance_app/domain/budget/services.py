from __future__ import annotations

from finance_app.domain.budget.repository import BudgetRepository, TransactionRepository
from finance_app.domain.shared.errors import ValidationError


class CategoryUsage:
    """Checks whether a category is referenced by budgets or transactions."""

    def __init__(self, budgets: BudgetRepository, transactions: TransactionRepository) -> None:
        self._budgets = budgets
        self._transactions = transactions

    def is_used(self, category_id: str) -> bool:
        return self._budgets.uses_category(category_id) or self._transactions.uses_category(
            category_id
        )

    def ensure_unused(self, category_id: str) -> None:
        if self.is_used(category_id):
            raise ValidationError.single(
                "category", "Category is used by budgets or transactions and cannot be deleted."
            )
