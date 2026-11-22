from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from finance_app.domain.budget.period import YearMonth
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.domain.shared.money import Money

MAX_DESCRIPTION = 200
MAX_NOTES = 2_000


def _valid_amount(amount: Money, field: str, errors: dict[str, str]) -> None:
    if not amount.is_positive:
        errors[field] = "Amount must be greater than zero."


@dataclass(frozen=True, slots=True)
class BudgetLine:
    """An expected amount for a category inside a monthly budget."""

    category_id: str
    amount: Money
    description: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        _valid_amount(self.amount, "amount", errors)
        if not self.category_id.strip():
            errors["category"] = "Select a category."
        if len(self.description) > MAX_DESCRIPTION:
            errors["description"] = "Description must be at most 200 characters."
        if errors:
            raise ValidationError(errors)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(eq=False)
class MonthlyBudget:
    """Aggregate root: the plan (expected amounts per category) of one month."""

    id: str
    period: YearMonth
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0))
    _lines: list[BudgetLine] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.notes = self._valid_notes(self.notes)
        lines, self._lines = self._lines, []
        for line in lines:
            self.add_line(line)

    @classmethod
    def create(cls, period: YearMonth, notes: str = "") -> MonthlyBudget:
        return cls(uuid.uuid4().hex, period, notes=notes)

    @staticmethod
    def _valid_notes(notes: str) -> str:
        notes = notes.strip()
        if len(notes) > MAX_NOTES:
            raise ValidationError.single("notes", "Notes must be at most 2000 characters.")
        return notes

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MonthlyBudget) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def lines(self) -> tuple[BudgetLine, ...]:
        return tuple(self._lines)

    def set_notes(self, notes: str) -> None:
        self.notes = self._valid_notes(notes)

    def add_line(self, line: BudgetLine) -> None:
        self._lines = [li for li in self._lines if li.id != line.id] + [line]

    def update_line(self, line_id: str, **changes: object) -> BudgetLine:
        updated = replace(self.get_line(line_id), **changes)  # type: ignore[arg-type]
        self.add_line(updated)
        return updated

    def get_line(self, line_id: str) -> BudgetLine:
        for line in self._lines:
            if line.id == line_id:
                return line
        raise NotFoundError(f"Budget line {line_id} not found")

    def remove_line(self, line_id: str) -> None:
        self.get_line(line_id)
        self._lines = [li for li in self._lines if li.id != line_id]

    def planned_by_category(self) -> dict[str, Money]:
        planned: dict[str, Money] = {}
        for line in self._lines:
            planned[line.category_id] = planned.get(line.category_id, Money.zero()) + line.amount
        return planned

    def copy_to(self, period: YearMonth) -> MonthlyBudget:
        """A new budget for another month with the same lines (fresh ids)."""
        copy = MonthlyBudget.create(period, notes=self.notes)
        for line in self._lines:
            copy.add_line(BudgetLine(line.category_id, line.amount, line.description))
        return copy
