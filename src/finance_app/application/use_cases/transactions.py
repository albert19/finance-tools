from __future__ import annotations

from collections.abc import Mapping

from finance_app.application.budget_assemblers import transaction_dto, transaction_from_input
from finance_app.application.dto import TransactionDTO, TransactionInput
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.repository import CategoryRepository, TransactionRepository
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.errors import ValidationError


class RecordTransaction:
    """Adds a new transaction, or replaces an existing one when ``transaction_id`` is given."""

    def __init__(self, transactions: TransactionRepository, categories: CategoryRepository) -> None:
        self._transactions = transactions
        self._categories = categories

    def execute(self, data: TransactionInput, transaction_id: str | None = None) -> str:
        if transaction_id:
            self._transactions.get(transaction_id)
        category = self._categories.get(data.category_id.strip())
        if category.archived:
            raise ValidationError.single("category", "This category is archived.")
        transaction = transaction_from_input(data, transaction_id)
        self._transactions.save(transaction)
        return transaction.id


class DeleteTransaction:
    def __init__(self, transactions: TransactionRepository) -> None:
        self._transactions = transactions

    def execute(self, transaction_id: str) -> None:
        self._transactions.delete(transaction_id)


class ListTransactions:
    def __init__(self, transactions: TransactionRepository, categories: CategoryRepository) -> None:
        self._transactions = transactions
        self._categories = categories

    def _map(self) -> Mapping[str, Category]:
        return {c.id: c for c in self._categories.list()}

    def execute(self, year: int, month: int) -> list[TransactionDTO]:
        period = YearMonth(year, month)
        transactions: list[Transaction] = sorted(
            self._transactions.list_by_period(period), key=lambda t: (t.date, t.description)
        )
        categories = self._map()
        return [transaction_dto(tx, categories) for tx in transactions]
