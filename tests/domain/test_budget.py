from __future__ import annotations

from datetime import date

import pytest

from finance_app.domain.budget.budget import BudgetLine, MonthlyBudget
from finance_app.domain.budget.category import Category, CategoryKind
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.services import CategoryUsage
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.budget.variance import VarianceCalculator, VarianceStatus
from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money
from finance_app.infrastructure.memory.budget_repository import (
    InMemoryBudgetRepository,
    InMemoryTransactionRepository,
)


def make_category(kind: CategoryKind = CategoryKind.EXPENSE, name: str = "Food") -> Category:
    return Category.create(name, kind)


def test_year_month_validation_and_navigation() -> None:
    period = YearMonth(2025, 12)
    assert period.next() == YearMonth(2026, 1)
    assert period.previous() == YearMonth(2025, 11)
    assert YearMonth(2025, 1).previous() == YearMonth(2024, 12)
    assert period.contains(date(2025, 12, 31))
    assert not period.contains(date(2025, 11, 30))
    assert period.first_day == date(2025, 12, 1)
    assert len(YearMonth.months_of_year(2025)) == 12
    with pytest.raises(ValidationError):
        YearMonth(2025, 13)
    with pytest.raises(ValidationError):
        YearMonth(1899, 5)


def test_category_rules() -> None:
    category = Category.create("  Groceries  ", "expense")
    assert category.name == "Groceries"
    assert category.kind is CategoryKind.EXPENSE
    assert not category.archived
    category.archive()
    assert category.archived
    category.unarchive()
    assert not category.archived
    category.rename("Food")
    assert category.name == "Food"
    with pytest.raises(ValidationError):
        category.rename("   ")


def test_budget_lines_multiple_per_category_and_copy() -> None:
    food = make_category()
    budget = MonthlyBudget.create(YearMonth(2025, 3))
    budget.add_line(BudgetLine(food.id, Money.of(400), "weekly shop"))
    budget.add_line(BudgetLine(food.id, Money.of(50), "market"))
    line = budget.lines[0]
    budget.update_line(line.id, amount=Money.of(450))
    assert budget.planned_by_category()[food.id] == Money.of(500)
    with pytest.raises(ValidationError):
        BudgetLine(food.id, Money.of(0))

    copy = budget.copy_to(YearMonth(2025, 4))
    assert copy.period == YearMonth(2025, 4)
    assert copy.id != budget.id
    assert [line.id for line in copy.lines] != [line.id for line in budget.lines]
    assert copy.planned_by_category() == budget.planned_by_category()

    budget.remove_line(budget.lines[0].id)
    assert len(budget.lines) == 1


def test_transaction_validation() -> None:
    cat = make_category()
    tx = Transaction(date(2025, 3, 5), cat.id, Money.of(12.5), " lunch ")
    assert tx.description == "lunch"
    assert tx.period == YearMonth(2025, 3)
    with pytest.raises(ValidationError):
        Transaction(date(2025, 3, 5), cat.id, Money.of(0))
    with pytest.raises(ValidationError):
        Transaction(date(2025, 3, 5), " ", Money.of(12))


def _calculator() -> VarianceCalculator:
    return VarianceCalculator(tolerance=0.02)


def test_variance_status_is_kind_dependent() -> None:
    expense = make_category(CategoryKind.EXPENSE, "Food")
    income = make_category(CategoryKind.INCOME, "Salary")
    categories = {c.id: c for c in (expense, income)}
    period = YearMonth(2025, 3)
    budget = MonthlyBudget.create(period)
    budget.add_line(BudgetLine(expense.id, Money.of(1000)))
    budget.add_line(BudgetLine(income.id, Money.of(2000)))
    tx = [
        Transaction(date(2025, 3, 2), expense.id, Money.of(900)),  # under → favorable
        Transaction(date(2025, 3, 3), income.id, Money.of(1900)),  # under → unfavorable
    ]
    report = _calculator().monthly(period, budget, tx, categories)
    rows = {r.category_id: r for r in report.rows}
    assert rows[expense.id].status is VarianceStatus.FAVORABLE
    assert rows[income.id].status is VarianceStatus.UNFAVORABLE
    assert rows[expense.id].variance == Money.of(-100)
    assert report.totals.planned_expenses == Money.of(1000)
    assert report.totals.actual_net == Money.of(1000)
    assert report.has_budget


def test_variance_unbudgeted_and_no_budget() -> None:
    expense = make_category(CategoryKind.EXPENSE, "Food")
    income = make_category(CategoryKind.INCOME, "Salary")
    categories = {c.id: c for c in (expense, income)}
    period = YearMonth(2025, 3)
    tx = [
        Transaction(date(2025, 3, 2), expense.id, Money.of(10)),
        Transaction(date(2025, 3, 3), income.id, Money.of(10)),
    ]
    report = _calculator().monthly(period, None, tx, categories)
    assert not report.has_budget
    rows = {r.category_id: r for r in report.rows}
    assert rows[expense.id].status is VarianceStatus.UNFAVORABLE  # overspend
    assert rows[income.id].status is VarianceStatus.FAVORABLE  # extra income
    # transaction in another month is ignored
    other = Transaction(date(2025, 4, 1), expense.id, Money.of(50))
    report2 = _calculator().monthly(period, None, [*tx, other], categories)
    assert rows == {r.category_id: r for r in report2.rows}


def test_annual_rollup() -> None:
    expense = make_category(CategoryKind.EXPENSE, "Food")
    income = make_category(CategoryKind.INCOME, "Salary")
    categories = {c.id: c for c in (expense, income)}
    budgets = []
    for month in (1, 2):
        b = MonthlyBudget.create(YearMonth(2025, month))
        b.add_line(BudgetLine(expense.id, Money.of(1000)))
        b.add_line(BudgetLine(income.id, Money.of(3000)))
        budgets.append(b)
    tx = [
        Transaction(date(2025, 1, 15), expense.id, Money.of(800)),
        Transaction(date(2025, 2, 15), income.id, Money.of(3100)),
        Transaction(date(2024, 12, 15), expense.id, Money.of(999)),  # other year
    ]
    report = _calculator().annual(2025, budgets, tx, categories)
    assert len(report.months) == 12
    assert report.months[0].has_budget and report.months[1].has_budget
    assert not report.months[2].has_budget
    rows = {r.category_id: r for r in report.rows}
    assert rows[expense.id].planned == Money.of(2000)
    assert rows[expense.id].actual == Money.of(800)
    assert rows[income.id].actual == Money.of(3100)
    assert report.totals.planned_income == Money.of(6000)
    assert report.totals.actual_expenses == Money.of(800)
    assert report.months[1].totals.actual_net == Money.of(3100)


def test_category_usage() -> None:
    cat = make_category()
    budgets = InMemoryBudgetRepository()
    transactions = InMemoryTransactionRepository()
    usage = CategoryUsage(budgets, transactions)
    assert not usage.is_used(cat.id)
    budget = MonthlyBudget.create(YearMonth(2025, 3))
    budget.add_line(BudgetLine(cat.id, Money.of(100)))
    budgets.save(budget)
    assert usage.is_used(cat.id)
    with pytest.raises(ValidationError):
        usage.ensure_unused(cat.id)

    budgets.delete(budget.id)
    assert not usage.is_used(cat.id)
    transactions.save(Transaction(date(2025, 3, 1), cat.id, Money.of(5)))
    assert usage.is_used(cat.id)
