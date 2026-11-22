"""EUR / percent formatting (Spanish conventions: 1.234.567,89 €)."""

from __future__ import annotations

from datetime import date

from finance_app.presentation.i18n import tr

PLACEHOLDER = "—"


def number(value: float, decimals: int = 2) -> str:
    text = f"{abs(value):,.{decimals}f}".replace(",", "\x00").replace(".", ",")
    text = text.replace("\x00", ".")
    return f"-{text}" if value < 0 and text.strip("0,.") else text


def money(value: float | None, decimals: int = 2) -> str:
    return PLACEHOLDER if value is None else f"{number(value, decimals)} €"


def percent(value_pct: float | None, decimals: int = 2, signed: bool = False) -> str:
    if value_pct is None:
        return PLACEHOLDER
    sign = "+" if signed and value_pct > 0 else ""
    return f"{sign}{number(value_pct, decimals)} %"


def signed_money(value: float | None) -> str:
    if value is None:
        return PLACEHOLDER
    return f"+{money(value)}" if value > 0 else money(value)


def short_date(value: date | None) -> str:
    return PLACEHOLDER if value is None else value.strftime("%d/%m/%Y")


def duration(months: int) -> str:
    years, rest = divmod(months, 12)
    parts = [tr("{n} year" if years == 1 else "{n} years", n=years)] if years else []
    if rest:
        parts.append(tr("{n} month" if rest == 1 else "{n} months", n=rest))
    return " ".join(parts) or tr("{n} months", n=0)
