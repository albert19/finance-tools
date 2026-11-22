"""Translation between budget domain objects and DTOs."""

from __future__ import annotations

from collections.abc import Mapping

from finance_app.application.dto import (
    BudgetLineDTO,
    BudgetLineInput,
    CategoryDTO,
    MonthlyBudgetDTO,
    MonthTotalsDTO,
    TotalsDTO,
    TransactionDTO,
    TransactionInput,
    VarianceRowDTO,
)
from finance_app.domain.budget.budget import BudgetLine, MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.transaction import Transaction
from finance_app.domain.budget.variance import (
    AnnualReport,
    BudgetReport,
    CategoryVariance,
    MonthTotals,
    PeriodTotals,
)
from finance_app.domain.shared.money import Money


def line_from_input(data: BudgetLineInput, line_id: str | None = None) -> BudgetLine:
    kwargs = {"id": line_id} if line_id else {}
    return BudgetLine(
        category_id=data.category_id.strip(),
        amount=Money.of(data.amount),
        description=data.description,
        **kwargs,
    )


def transaction_from_input(
    data: TransactionInput, transaction_id: str | None = None
) -> Transaction:
    kwargs = {"id": transaction_id} if transaction_id else {}
    return Transaction(
        date=data.date,
        category_id=data.category_id.strip(),
        amount=Money.of(data.amount),
        description=data.description,
        **kwargs,
    )


def category_dto(category: Category, in_use: bool = False) -> CategoryDTO:
    return CategoryDTO(
        id=category.id,
        name=category.name,
        kind=category.kind.value,
        archived=category.archived,
        in_use=in_use,
    )


def line_dto(line: BudgetLine, categories: Mapping[str, Category]) -> BudgetLineDTO:
    category = categories.get(line.category_id)
    return BudgetLineDTO(
        id=line.id,
        category_id=line.category_id,
        category_name=category.name if category else "?",
        kind=category.kind.value if category else "",
        description=line.description,
        amount=line.amount.to_float(),
    )


def _line_sort(line: BudgetLine, categories: Mapping[str, Category]) -> tuple[int, str]:
    category = categories.get(line.category_id)
    kind_order = 1 if category is not None and category.kind.value == "income" else 0
    return (kind_order, category.name.lower() if category else "?")


def budget_dto(budget: MonthlyBudget, categories: Mapping[str, Category]) -> MonthlyBudgetDTO:
    planned = budget.planned_by_category()
    income = expenses = 0.0
    for cat_id, amount in planned.items():
        category = categories.get(cat_id)
        if category is None:
            continue
        if category.kind.value == "income":
            income += amount.to_float()
        else:
            expenses += amount.to_float()
    return MonthlyBudgetDTO(
        id=budget.id,
        year=budget.period.year,
        month=budget.period.month,
        notes=budget.notes,
        lines=tuple(
            line_dto(line, categories)
            for line in sorted(budget.lines, key=lambda line: _line_sort(line, categories))
        ),
        planned_income=income,
        planned_expenses=expenses,
    )


def transaction_dto(tx: Transaction, categories: Mapping[str, Category]) -> TransactionDTO:
    category = categories.get(tx.category_id)
    return TransactionDTO(
        id=tx.id,
        date=tx.date,
        category_id=tx.category_id,
        category_name=category.name if category else "?",
        kind=category.kind.value if category else "",
        amount=tx.amount.to_float(),
        description=tx.description,
    )


def variance_row_dto(row: CategoryVariance) -> VarianceRowDTO:
    return VarianceRowDTO(
        category_id=row.category_id,
        name=row.name,
        kind=row.kind.value,
        planned=row.planned.to_float(),
        actual=row.actual.to_float(),
        variance=row.variance.to_float(),
        variance_pct=None if row.variance_pct is None else row.variance_pct * 100,
        status=row.status.value,
    )


def totals_dto(totals: PeriodTotals) -> TotalsDTO:
    return TotalsDTO(
        planned_income=totals.planned_income.to_float(),
        actual_income=totals.actual_income.to_float(),
        planned_expenses=totals.planned_expenses.to_float(),
        actual_expenses=totals.actual_expenses.to_float(),
        planned_net=totals.planned_net.to_float(),
        actual_net=totals.actual_net.to_float(),
    )


def month_totals_dto(month: MonthTotals) -> MonthTotalsDTO:
    return MonthTotalsDTO(
        year=month.period.year,
        month=month.period.month,
        has_budget=month.has_budget,
        totals=totals_dto(month.totals),
    )


def monthly_report_rows(report: BudgetReport) -> tuple[VarianceRowDTO, ...]:
    return tuple(variance_row_dto(r) for r in report.rows)


def annual_report_rows(report: AnnualReport) -> tuple[VarianceRowDTO, ...]:
    return tuple(variance_row_dto(r) for r in report.rows)
