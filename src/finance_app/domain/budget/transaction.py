from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from finance_app.domain.budget.period import YearMonth
from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money

MAX_DESCRIPTION = 200


@dataclass(frozen=True, slots=True)
class Transaction:
    """A manually entered income or expense assigned to a category."""

    date: date
    category_id: str
    amount: Money
    description: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if not self.amount.is_positive:
            errors["amount"] = "Amount must be greater than zero."
        if not self.category_id.strip():
            errors["category"] = "Select a category."
        if len(self.description) > MAX_DESCRIPTION:
            errors["description"] = "Description must be at most 200 characters."
        if errors:
            raise ValidationError(errors)
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "category_id", self.category_id.strip())

    @property
    def period(self) -> YearMonth:
        return YearMonth.of(self.date)
