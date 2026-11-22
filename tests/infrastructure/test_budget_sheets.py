from __future__ import annotations

from datetime import date

import pytest

from finance_app.domain.budget.budget import BudgetLine, MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.domain.shared.money import Money
from finance_app.infrastructure.sheets.budget_repository import (
    GoogleSheetsBudgetRepository,
    GoogleSheetsCategoryRepository,
    GoogleSheetsTransactionRepository,
)
from finance_app.infrastructure.sheets.schema import (
    BUDGET_LINES_SHEET,
    BUDGETS_SHEET,
    CATEGORIES_SHEET,
    TRANSACTIONS_SHEET,
)
from tests.infrastructure.fakes import FakeSheetsGateway


def test_category_repository_roundtrip() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsCategoryRepository(gateway)
    assert repo.list() == []
    assert set(gateway.sheets) == {CATEGORIES_SHEET}
    assert gateway.sheets[CATEGORIES_SHEET][0][0] == "id"

    cat = Category.create("Food", "expense")
    repo.save(cat)
    fresh = GoogleSheetsCategoryRepository(gateway)
    loaded = fresh.get(cat.id)
    assert loaded.name == "Food" and not loaded.archived

    loaded.archive()
    fresh.save(loaded)
    assert fresh.get(cat.id).archived

    fresh.delete(cat.id)
    assert fresh.list() == []
    with pytest.raises(NotFoundError):
        fresh.delete(cat.id)


def test_budget_repository_diff_and_roundtrip() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsBudgetRepository(gateway)
    repo.list()  # triggers lazy schema creation
    assert set(gateway.sheets) == {BUDGETS_SHEET, BUDGET_LINES_SHEET}

    budget = MonthlyBudget.create(YearMonth(2025, 3), notes="month")
    line_a = BudgetLine("cat-a", Money.of(100), "a")
    line_b = BudgetLine("cat-b", Money.of(200), "b")
    budget.add_line(line_a)
    budget.add_line(line_b)
    repo.save(budget)
    assert len(gateway.sheets[BUDGET_LINES_SHEET]) == 3  # header + 2 lines

    fresh = GoogleSheetsBudgetRepository(gateway)
    loaded = fresh.find_by_period(YearMonth(2025, 3))
    assert loaded is not None and loaded.notes == "month"
    assert {line.amount for line in loaded.lines} == {Money.of(100), Money.of(200)}

    loaded.update_line(line_a.id, amount=Money.of(150))
    loaded.remove_line(line_b.id)
    loaded.add_line(BudgetLine("cat-c", Money.of(50)))
    fresh.save(loaded)

    reloaded = GoogleSheetsBudgetRepository(gateway).get(budget.id)
    amounts = {line.category_id: line.amount for line in reloaded.lines}
    assert amounts == {"cat-a": Money.of(150), "cat-c": Money.of(50)}
    assert len(gateway.sheets[BUDGET_LINES_SHEET]) == 3  # header + 2 lines

    assert [b.period for b in reloaded_repo_list(gateway)] == [YearMonth(2025, 3)]
    assert GoogleSheetsBudgetRepository(gateway).uses_category("cat-a")
    assert not GoogleSheetsBudgetRepository(gateway).uses_category("cat-z")

    repo.delete(budget.id)
    assert repo.list() == []
    assert len(gateway.sheets[BUDGET_LINES_SHEET]) == 1  # header only


def reloaded_repo_list(gateway: FakeSheetsGateway) -> list[MonthlyBudget]:
    return GoogleSheetsBudgetRepository(gateway).list_by_year(2025)


def test_budget_create_and_update_are_atomic() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsBudgetRepository(gateway)
    budget = MonthlyBudget.create(YearMonth(2025, 3))
    budget.add_line(BudgetLine("cat-a", Money.of(100), "a"))
    budget.add_line(BudgetLine("cat-b", Money.of(200), "b"))
    repo.create(budget)

    # Duplicate period is rejected without touching the sheet
    with pytest.raises(ValidationError):
        repo.create(MonthlyBudget.create(YearMonth(2025, 3)))
    assert len(gateway.sheets[BUDGETS_SHEET]) == 2  # header + 1 budget

    line_id, removed_id = budget.lines[0].id, budget.lines[1].id

    def mutate(b: MonthlyBudget) -> None:
        b.update_line(line_id, amount=Money.of(150))
        b.remove_line(removed_id)

    repo.update(budget.id, mutate)
    fresh = GoogleSheetsBudgetRepository(gateway).get(budget.id)
    assert [line.amount for line in fresh.lines] == [Money.of(150)]

    # update() must diff against the persisted state, not the mutated object:
    # the sheet row is updated in place and the removed line's row is deleted.
    amounts = sorted(r[4] for r in gateway.sheets[BUDGET_LINES_SHEET][1:])
    assert amounts == [150]
    with pytest.raises(NotFoundError):
        repo.update("missing", lambda b: None)


def test_transaction_repository_roundtrip_and_filters() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsTransactionRepository(gateway)
    repo.list()  # triggers lazy schema creation
    assert set(gateway.sheets) == {TRANSACTIONS_SHEET}

    tx = Transaction(date(2025, 3, 5), "cat-a", Money.of(10.5), " lunch ")
    repo.save(tx)
    repo.save(Transaction(date(2025, 4, 1), "cat-b", Money.of(20)))

    fresh = GoogleSheetsTransactionRepository(gateway)
    loaded = fresh.get(tx.id)
    assert loaded.amount == Money.of(10.5) and loaded.description == "lunch"
    assert [t.id for t in fresh.list_by_period(YearMonth(2025, 3))] == [tx.id]
    assert len(fresh.list_by_year(2025)) == 2
    assert fresh.uses_category("cat-a") and not fresh.uses_category("cat-z")

    edited = Transaction(date(2025, 3, 9), "cat-a", Money.of(11), "dinner", id=tx.id)
    fresh.save(edited)
    assert fresh.get(tx.id).amount == Money.of(11)

    fresh.delete(tx.id)
    assert not fresh.list_by_period(YearMonth(2025, 3))
    with pytest.raises(NotFoundError):
        fresh.get(tx.id)


def test_repositories_skip_corrupt_rows() -> None:
    gateway = FakeSheetsGateway()
    budgets = GoogleSheetsBudgetRepository(gateway)
    budgets.save(MonthlyBudget.create(YearMonth(2025, 3)))
    gateway.sheets[BUDGETS_SHEET].append(["bad-id", "not-a-year", "x"])
    budgets.refresh()
    assert len(budgets.list()) == 1

    transactions = GoogleSheetsTransactionRepository(gateway)
    transactions.list()  # creates the sheet
    gateway.sheets[TRANSACTIONS_SHEET].append(["bad-id", "not-a-date"])
    transactions.refresh()
    assert transactions.list() == []
