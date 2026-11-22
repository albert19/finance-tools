from __future__ import annotations

from finance_app.presentation.formatting import duration, money, number, percent, signed_money


def test_money_uses_spanish_separators() -> None:
    assert money(1234.5) == "1.234,50 €"
    assert money(1234567.891) == "1.234.567,89 €"
    assert money(-0.001) == "0,00 €"
    assert money(-1500) == "-1.500,00 €"
    assert money(None) == "—"


def test_percent_and_misc() -> None:
    assert percent(6.1749) == "6,17 %"
    assert percent(2.5, signed=True) == "+2,50 %"
    assert signed_money(10) == "+10,00 €"
    assert number(1000, 0) == "1.000"
    assert duration(30) == "2 years 6 months"
