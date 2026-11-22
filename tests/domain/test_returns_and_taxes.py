from __future__ import annotations

from datetime import date

import pytest

from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.returns import cagr, irr, xirr
from finance_app.domain.simulation.scenarios import ScenarioSet
from finance_app.domain.simulation.tax_policy import (
    ProgressiveTaxPolicy,
    TaxBracket,
    spanish_savings_policy,
)
from tests.factories import make_params


def test_irr_simple() -> None:
    assert irr([(0, -100), (1, 110)]) == pytest.approx(0.10)
    assert irr([(0, -100), (2, 121)]) == pytest.approx(0.10)


def test_irr_negative_and_undefined() -> None:
    assert irr([(0, -100), (1, 80)]) == pytest.approx(-0.20)
    assert irr([(0, -100)]) is None


def test_xirr_dates() -> None:
    assert xirr([(date(2024, 1, 1), -1000), (date(2024, 12, 31), 1100)]) == pytest.approx(
        0.10, abs=1e-3
    )


def test_cagr() -> None:
    assert cagr(100, 121, 2) == pytest.approx(0.10)
    assert cagr(0, 100, 1) is None


@pytest.mark.parametrize(
    ("gain", "tax"),
    [
        (0, 0),
        (-500, 0),
        (6_000, 1_140),
        (10_000, 1_140 + 4_000 * 0.21),
        (400_000, 1_140 + 44_000 * 0.21 + 150_000 * 0.23 + 100_000 * 0.27 + 100_000 * 0.30),
    ],
)
def test_spanish_brackets(gain: float, tax: float) -> None:
    assert spanish_savings_policy().tax_for(gain) == pytest.approx(tax)


def test_invalid_brackets_rejected() -> None:
    with pytest.raises(ValidationError):
        ProgressiveTaxPolicy([TaxBracket(100, 0.1)])
    with pytest.raises(ValidationError):
        ProgressiveTaxPolicy([TaxBracket(100, 0.1), TaxBracket(50, 0.2), TaxBracket(None, 0.3)])


def test_scenarios_shift_rate() -> None:
    scenarios = ScenarioSet(2).build(make_params(annual_rate=Rate.from_percent(5)))
    assert [s.name for s in scenarios] == ["Pessimistic", "Baseline", "Optimistic"]
    assert [round(s.parameters.annual_rate.percent, 6) for s in scenarios] == [3, 5, 7]
