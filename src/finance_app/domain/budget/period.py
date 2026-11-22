from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from finance_app.domain.shared.errors import ValidationError

MIN_YEAR = 1900
MAX_YEAR = 2200


@dataclass(frozen=True, slots=True, order=True)
class YearMonth:
    """A calendar month, the period a monthly budget belongs to."""

    year: int
    month: int

    def __post_init__(self) -> None:
        errors: dict[str, str] = {}
        if not MIN_YEAR <= self.year <= MAX_YEAR:
            errors["year"] = "Year must be between 1900 and 2200."
        if not 1 <= self.month <= 12:
            errors["month"] = "Month must be between 1 and 12."
        if errors:
            raise ValidationError(errors)

    @classmethod
    def of(cls, day: date) -> YearMonth:
        return cls(day.year, day.month)

    @classmethod
    def current(cls, today: date | None = None) -> YearMonth:
        return cls.of(today or date.today())

    @classmethod
    def months_of_year(cls, year: int) -> tuple[YearMonth, ...]:
        return tuple(cls(year, month) for month in range(1, 13))

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def next(self) -> YearMonth:
        return YearMonth(self.year + (self.month == 12), self.month % 12 + 1)

    def previous(self) -> YearMonth:
        return YearMonth(self.year - (self.month == 1), (self.month - 2) % 12 + 1)

    def contains(self, day: date) -> bool:
        return day.year == self.year and day.month == self.month

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
