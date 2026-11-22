from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable monetary amount, rounded to cents (EUR by default)."""

    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", Decimal(self.amount).quantize(_CENT, ROUND_HALF_UP))

    @classmethod
    def of(cls, value: float | int | str | Decimal, currency: str = "EUR") -> Money:
        return cls(Decimal(str(value)), currency)

    @classmethod
    def zero(cls, currency: str = "EUR") -> Money:
        return cls(Decimal(0), currency)

    @classmethod
    def sum(cls, amounts: Iterable[Money], currency: str = "EUR") -> Money:
        total = cls.zero(currency)
        for amount in amounts:
            total = total + amount
        return total

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def to_float(self) -> float:
        return float(self.amount)

    def _check(self, other: Money) -> None:
        if other.currency != self.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._check(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._check(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._check(other)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"
