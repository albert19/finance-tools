"""Mapping between budget domain objects and spreadsheet rows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from finance_app.domain.budget.budget import BudgetLine, MonthlyBudget
from finance_app.domain.budget.category import Category, CategoryKind
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.errors import DomainError
from finance_app.domain.shared.money import Money
from finance_app.infrastructure.sheets.cells import (
    Row,
    RowMappingError,
    as_bool,
    as_date,
    as_dict,
    as_float,
    round_money,
)
from finance_app.infrastructure.sheets.schema import (
    BUDGET_COLUMNS,
    BUDGET_LINE_COLUMNS,
    CATEGORY_COLUMNS,
    TRANSACTION_COLUMNS,
)


def category_to_row(category: Category) -> Row:
    values: dict[str, Any] = {
        "id": category.id,
        "name": category.name,
        "kind": category.kind.value,
        "archived": category.archived,
    }
    return [values[c] for c in CATEGORY_COLUMNS]


def row_to_category(row: Sequence[Any]) -> Category:
    d = as_dict(row, CATEGORY_COLUMNS)
    try:
        return Category(
            id=str(d["id"]),
            name=str(d["name"]),
            kind=CategoryKind(d["kind"] or CategoryKind.EXPENSE.value),
            archived=as_bool(d["archived"]),
        )
    except (ValueError, TypeError, DomainError) as exc:
        raise RowMappingError(f"Invalid category row {row!r}: {exc}") from exc


def budget_to_row(budget: MonthlyBudget) -> Row:
    values: dict[str, Any] = {
        "id": budget.id,
        "year": budget.period.year,
        "month": budget.period.month,
        "notes": budget.notes,
        "created_at": budget.created_at.isoformat(timespec="seconds"),
    }
    return [values[c] for c in BUDGET_COLUMNS]


def budget_line_to_row(budget_id: str, line: BudgetLine) -> Row:
    values: dict[str, Any] = {
        "id": line.id,
        "budget_id": budget_id,
        "category_id": line.category_id,
        "description": line.description,
        "amount": round_money(line.amount.to_float()),
    }
    return [values[c] for c in BUDGET_LINE_COLUMNS]


def row_to_budget_line(row: Sequence[Any]) -> tuple[str, BudgetLine]:
    d = as_dict(row, BUDGET_LINE_COLUMNS)
    try:
        line = BudgetLine(
            id=str(d["id"]),
            category_id=str(d["category_id"]),
            description=str(d["description"]),
            amount=Money.of(as_float(d["amount"])),
        )
    except (ValueError, TypeError, DomainError) as exc:
        raise RowMappingError(f"Invalid budget line row {row!r}: {exc}") from exc
    return str(d["budget_id"]), line


def row_to_budget(row: Sequence[Any], lines: Sequence[BudgetLine] = ()) -> MonthlyBudget:
    d = as_dict(row, BUDGET_COLUMNS)
    try:
        created = str(d["created_at"])
        return MonthlyBudget(
            id=str(d["id"]),
            period=YearMonth(int(as_float(d["year"])), int(as_float(d["month"]))),
            notes=str(d["notes"]),
            created_at=datetime.fromisoformat(created) if created else datetime.min,
            _lines=list(lines),
        )
    except (ValueError, TypeError, KeyError, DomainError) as exc:
        raise RowMappingError(f"Invalid budget row {row!r}: {exc}") from exc


def transaction_to_row(transaction: Transaction) -> Row:
    values: dict[str, Any] = {
        "id": transaction.id,
        "date": transaction.date.isoformat(),
        "category_id": transaction.category_id,
        "amount": round_money(transaction.amount.to_float()),
        "description": transaction.description,
    }
    return [values[c] for c in TRANSACTION_COLUMNS]


def row_to_transaction(row: Sequence[Any]) -> Transaction:
    d = as_dict(row, TRANSACTION_COLUMNS)
    try:
        return Transaction(
            id=str(d["id"]),
            date=as_date(d["date"]),
            category_id=str(d["category_id"]),
            amount=Money.of(as_float(d["amount"])),
            description=str(d["description"]),
        )
    except (ValueError, TypeError, DomainError) as exc:
        raise RowMappingError(f"Invalid transaction row {row!r}: {exc}") from exc
