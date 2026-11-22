from __future__ import annotations

from datetime import date

import pytest

from finance_app.application.dto import BudgetLineInput, TransactionInput
from finance_app.application.use_cases.budgets import (
    CreateMonthlyBudget,
    DeleteBudgetLine,
    DeleteMonthlyBudget,
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
from finance_app.domain.budget.services import CategoryUsage
from finance_app.domain.budget.variance import VarianceCalculator
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.infrastructure.memory.budget_repository import (
    InMemoryBudgetRepository,
    InMemoryCategoryRepository,
    InMemoryTransactionRepository,
)


@pytest.fixture
def repos() -> tuple[
    InMemoryCategoryRepository, InMemoryBudgetRepository, InMemoryTransactionRepository
]:
    return (
        InMemoryCategoryRepository(),
        InMemoryBudgetRepository(),
        InMemoryTransactionRepository(),
    )


@pytest.fixture
def categories(repos) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    cats, _, _ = repos
    create = CreateCategory(cats)
    return create.execute("Salary", "income"), create.execute("Groceries", "expense")


def test_category_lifecycle(repos) -> None:  # type: ignore[no-untyped-def]
    cats, budgets, transactions = repos
    usage = CategoryUsage(budgets, transactions)
    create, update = CreateCategory(cats), UpdateCategory(cats)
    cat_id = create.execute("Salary", "income")
    with pytest.raises(ValidationError):
        create.execute(" salary ", "income")  # duplicate (case-insensitive)
    other = create.execute("Bonus", "income")

    items = ListCategories(cats, usage).execute()
    assert [c.name for c in items] == ["Bonus", "Salary"]
    update.execute(cat_id, name="Wage")
    update.execute(other, archived=True)
    items = {c.id: c for c in ListCategories(cats, usage).execute()}
    assert items[cat_id].name == "Wage"
    assert items[other].archived
    active = ListCategories(cats, usage).execute(include_archived=False)
    assert [c.id for c in active] == [cat_id]

    DeleteCategory(cats, usage).execute(other)
    assert len(cats.list()) == 1


def test_category_delete_blocked_when_in_use(repos, categories) -> None:  # type: ignore[no-untyped-def]
    cats, budgets, transactions = repos
    income, _ = categories
    usage = CategoryUsage(budgets, transactions)
    budget_id = CreateMonthlyBudget(budgets).execute(2025, 3)
    SaveBudgetLine(budgets, cats).execute(budget_id, BudgetLineInput(income, 3000, "main"))
    with pytest.raises(ValidationError):
        DeleteCategory(cats, usage).execute(income)

    items = {c.id: c for c in ListCategories(cats, usage).execute()}
    assert items[income].in_use


def test_seed_categories_is_idempotent(repos) -> None:  # type: ignore[no-untyped-def]
    cats, _, _ = repos
    seed = SeedDefaultCategories(cats)
    first = seed.execute(["Salary"], ["Rent", "Food"])
    second = seed.execute(["salary"], ["RENT", "Transport"])
    assert len(first) == 3
    assert len(second) == 1  # only "Transport" is new
    names = [c.name for c in cats.list()]
    assert "Transport" in names and names.count("Salary") == 1


def test_budget_create_copy_and_uniqueness(repos, categories) -> None:  # type: ignore[no-untyped-def]
    cats, budgets, _ = repos
    income, expense = categories
    create = CreateMonthlyBudget(budgets)
    budget_id = create.execute(2025, 3)
    SaveBudgetLine(budgets, cats).execute(budget_id, BudgetLineInput(expense, 500, "weekly"))
    SaveBudgetLine(budgets, cats).execute(budget_id, BudgetLineInput(income, 3000))

    with pytest.raises(ValidationError):
        create.execute(2025, 3)  # duplicate period

    copied_id = create.execute(2025, 4, copy_from=YearMonth(2025, 3))
    copied = budgets.get(copied_id)
    assert len(copied.lines) == 2
    assert copied.id != budget_id

    assert ListBudgetPeriods(budgets).execute() == [(2025, 3), (2025, 4)]

    UpdateMonthlyBudget(budgets).execute(budget_id, notes=" tight month ")
    assert budgets.get(budget_id).notes == "tight month"

    DeleteMonthlyBudget(budgets).execute(budget_id)
    assert ListBudgetPeriods(budgets).execute() == [(2025, 4)]
    with pytest.raises(NotFoundError):
        DeleteMonthlyBudget(budgets).execute(budget_id)


def test_budget_line_crud(repos, categories) -> None:  # type: ignore[no-untyped-def]
    cats, budgets, _ = repos
    _, expense = categories
    budget_id = CreateMonthlyBudget(budgets).execute(2025, 3)
    save = SaveBudgetLine(budgets, cats)
    line_id = save.execute(budget_id, BudgetLineInput(expense, 500, "a"))
    save.execute(budget_id, BudgetLineInput(expense, 50, "b"), line_id)  # replace
    budget = budgets.get(budget_id)
    assert len(budget.lines) == 1
    assert budget.lines[0].amount.to_float() == 50

    with pytest.raises(NotFoundError):
        save.execute(budget_id, BudgetLineInput("missing", 10))
    with pytest.raises(ValidationError):
        save.execute(budget_id, BudgetLineInput(expense, 0))

    DeleteBudgetLine(budgets).execute(budget_id, line_id)
    assert not budgets.get(budget_id).lines


def test_transaction_crud(repos, categories) -> None:  # type: ignore[no-untyped-def]
    cats, _, transactions = repos
    income, _ = categories
    record = RecordTransaction(transactions, cats)
    tx_id = record.execute(TransactionInput(date(2025, 3, 5), income, 2500, "paycheck"))
    listed = ListTransactions(transactions, cats).execute(2025, 3)
    assert [t.amount for t in listed] == [2500]
    assert listed[0].category_name == "Salary"

    record.execute(TransactionInput(date(2025, 3, 6), income, 2600), tx_id)
    assert transactions.get(tx_id).amount.to_float() == 2600

    with pytest.raises(NotFoundError):
        record.execute(TransactionInput(date(2025, 3, 6), "missing", 1))
    UpdateCategory(cats).execute(income, archived=True)
    with pytest.raises(ValidationError):
        record.execute(TransactionInput(date(2025, 3, 7), income, 1))

    DeleteTransaction(transactions).execute(tx_id)
    assert ListTransactions(transactions, cats).execute(2025, 3) == []


def test_monthly_and_annual_reports(repos, categories) -> None:  # type: ignore[no-untyped-def]
    cats, budgets, transactions = repos
    income, expense = categories
    calculator = VarianceCalculator(0.02)
    budget_id = CreateMonthlyBudget(budgets).execute(2025, 3)
    SaveBudgetLine(budgets, cats).execute(budget_id, BudgetLineInput(income, 3000))
    SaveBudgetLine(budgets, cats).execute(budget_id, BudgetLineInput(expense, 1000))
    record = RecordTransaction(transactions, cats)
    record.execute(TransactionInput(date(2025, 3, 5), income, 3200))
    record.execute(TransactionInput(date(2025, 3, 6), expense, 700))
    record.execute(TransactionInput(date(2025, 4, 6), expense, 900))  # another month

    report = GetMonthlyReport(budgets, transactions, cats, calculator).execute(2025, 3)
    assert report.budget is not None and len(report.budget.lines) == 2
    rows = {r.category_id: r for r in report.rows}
    assert rows[income].status == "Favorable"
    assert rows[expense].status == "Favorable"
    assert rows[expense].variance == -300
    assert len(report.transactions) == 2

    empty = GetMonthlyReport(budgets, transactions, cats, calculator).execute(2025, 4)
    assert empty.budget is None
    assert empty.totals.actual_expenses == 900

    annual = GetAnnualReport(budgets, transactions, cats, calculator).execute(2025)
    assert len(annual.months) == 12
    arows = {r.category_id: r for r in annual.rows}
    assert arows[expense].planned == 1000 and arows[expense].actual == 1600
    assert annual.months[3].totals.actual_expenses == 900
