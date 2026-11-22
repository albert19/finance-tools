from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """Actual state of an investment at a given date.

    ``contribution`` / ``withdrawal`` are the cash flows made since the previous snapshot.
    """

    date: date
    market_value: Money
    contribution: Money = Money.zero()
    withdrawal: Money = Money.zero()
    note: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if self.market_value.is_negative:
            errors["market_value"] = "Market value cannot be negative."
        if self.contribution.is_negative:
            errors["contribution"] = "Contribution cannot be negative."
        if self.withdrawal.is_negative:
            errors["withdrawal"] = "Withdrawal cannot be negative."
        if errors:
            raise ValidationError(errors)
