from __future__ import annotations

from collections.abc import Mapping

from finance_app.application.budget_assemblers import budget_dto, line_from_input
from finance_app.application.dto import BudgetLineInput, MonthlyBudgetDTO
from finance_app.domain.budget.budget import MonthlyBudget
from finance_app.domain.budget.category import Category
from finance_app.domain.budget.period import YearMonth
from finance_app.domain.budget.repository import BudgetRepository, CategoryRepository
from finance_app.domain.shared.errors import NotFoundError


class GetMonthlyBudget:
    def __init__(self, budgets: BudgetRepository, categories: CategoryRepository) -> None:
        self._budgets = budgets
        self._categories = categories

    def _map(self) -> Mapping[str, Category]:
        return {c.id: c for c in self._categories.list()}

    def execute(self, year: int, month: int) -> MonthlyBudgetDTO | None:
        budget = self._budgets.find_by_period(YearMonth(year, month))
        return None if budget is None else budget_dto(budget, self._map())


class CreateMonthlyBudget:
    """Creates the budget of a month, optionally copying the lines of another month."""

    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    def execute(
        self,
        year: int,
        month: int,
        *,
        copy_from: YearMonth | None = None,
        notes: str = "",
    ) -> str:
        period = YearMonth(year, month)
        if copy_from is not None:
            source = self._budgets.find_by_period(copy_from)
            if source is None:
                raise NotFoundError(f"No budget exists for {copy_from}")
            budget = source.copy_to(period)
            if notes:
                budget.set_notes(notes)
        else:
            budget = MonthlyBudget.create(period, notes)
        # create() enforces the unique period atomically; a plain save could
        # let two concurrent creates both pass a separate existence check.
        self._budgets.create(budget)
        return budget.id


class UpdateMonthlyBudget:
    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    def execute(self, budget_id: str, *, notes: str | None = None) -> None:
        def apply(budget: MonthlyBudget) -> None:
            if notes is not None:
                budget.set_notes(notes)

        self._budgets.update(budget_id, apply)


class DeleteMonthlyBudget:
    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    def execute(self, budget_id: str) -> None:
        self._budgets.delete(budget_id)


class SaveBudgetLine:
    """Adds a new line, or replaces an existing one when ``line_id`` is given."""

    def __init__(self, budgets: BudgetRepository, categories: CategoryRepository) -> None:
        self._budgets = budgets
        self._categories = categories

    def execute(self, budget_id: str, data: BudgetLineInput, line_id: str | None = None) -> str:
        self._categories.get(data.category_id.strip())
        line = line_from_input(data, line_id)

        def apply(budget: MonthlyBudget) -> None:
            if line_id:
                budget.get_line(line_id)
            budget.add_line(line)

        self._budgets.update(budget_id, apply)
        return line.id


class DeleteBudgetLine:
    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    def execute(self, budget_id: str, line_id: str) -> None:
        self._budgets.update(budget_id, lambda budget: budget.remove_line(line_id))


class ListBudgetPeriods:
    """Periods that have a budget, for the copy dialog and navigation hints."""

    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    def execute(self) -> list[tuple[int, int]]:
        return sorted((b.period.year, b.period.month) for b in self._budgets.list())
