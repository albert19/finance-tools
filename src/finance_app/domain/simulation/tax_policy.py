from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from finance_app.domain.shared.errors import ValidationError


class TaxPolicy(Protocol):
    """Computes the tax due on realised capital gains for one tax year."""

    name: str

    def tax_for(self, gain: float) -> float: ...


@dataclass(frozen=True, slots=True)
class TaxBracket:
    """Bracket applying ``rate`` to the slice of gains up to ``upper`` (None = no limit)."""

    upper: float | None
    rate: float


#: Spanish "base imponible del ahorro" brackets (2025+). Verify before relying on them.
SPANISH_SAVINGS_BRACKETS: tuple[TaxBracket, ...] = (
    TaxBracket(6_000, 0.19),
    TaxBracket(50_000, 0.21),
    TaxBracket(200_000, 0.23),
    TaxBracket(300_000, 0.27),
    TaxBracket(None, 0.30),
)


class ProgressiveTaxPolicy:
    def __init__(self, brackets: Sequence[TaxBracket], name: str = "Progressive") -> None:
        self._validate(brackets)
        self._brackets = tuple(brackets)
        self.name = name

    @staticmethod
    def _validate(brackets: Sequence[TaxBracket]) -> None:
        if not brackets or brackets[-1].upper is not None:
            raise ValidationError.single("tax_brackets", "Last bracket must have no upper limit.")
        uppers = [b.upper for b in brackets[:-1] if b.upper is not None]
        if len(uppers) != len(brackets) - 1 or uppers != sorted(set(uppers)):
            raise ValidationError.single("tax_brackets", "Bracket limits must be ascending.")
        if any(not 0 <= b.rate <= 1 for b in brackets):
            raise ValidationError.single("tax_brackets", "Tax rates must be between 0 and 1.")

    @property
    def brackets(self) -> tuple[TaxBracket, ...]:
        return self._brackets

    def tax_for(self, gain: float) -> float:
        if gain <= 0:
            return 0.0
        tax, lower = 0.0, 0.0
        for bracket in self._brackets:
            upper = bracket.upper if bracket.upper is not None else float("inf")
            if gain <= lower:
                break
            tax += (min(gain, upper) - lower) * bracket.rate
            lower = upper
        return tax


class NoTaxPolicy:
    name = "No taxes"

    def tax_for(self, gain: float) -> float:
        return 0.0


def spanish_savings_policy(brackets: Sequence[TaxBracket] | None = None) -> ProgressiveTaxPolicy:
    return ProgressiveTaxPolicy(brackets or SPANISH_SAVINGS_BRACKETS, "Spain – savings income")
