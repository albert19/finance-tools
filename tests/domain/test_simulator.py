from __future__ import annotations

import pytest

from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.simulator import CompoundInterestSimulator
from finance_app.domain.simulation.tax_policy import spanish_savings_policy
from finance_app.domain.simulation.value_objects import (
    ContributionTiming,
    Frequency,
    TimeHorizon,
    WithdrawalPlan,
)
from tests.factories import make_params


def closed_formula(p: float, pmt: float, r: float, n: int, t: float) -> float:
    growth = (1 + r / n) ** (n * t)
    return p * growth + pmt * (growth - 1) / (r / n)


@pytest.mark.parametrize("freq", [Frequency.MONTHLY, Frequency.QUARTERLY, Frequency.ANNUAL])
def test_matches_closed_formula_end_of_period(freq: Frequency) -> None:
    params = make_params(contribution_frequency=freq, compounding_frequency=freq)
    result = CompoundInterestSimulator().run(params)
    expected = closed_formula(10_000, 200, 0.06, freq.periods_per_year, 10)
    assert result.summary.final_capital == pytest.approx(expected, rel=1e-9)


def test_matches_annuity_due_for_beginning_timing() -> None:
    params = make_params(contribution_timing=ContributionTiming.BEGINNING)
    result = CompoundInterestSimulator().run(params)
    g = (1 + 0.06 / 12) ** 120
    expected = 10_000 * g + 200 * (g - 1) / (0.06 / 12) * (1 + 0.06 / 12)
    assert result.summary.final_capital == pytest.approx(expected, rel=1e-9)


def test_daily_compounding_without_contributions() -> None:
    params = make_params(contribution=Money.zero(), compounding_frequency=Frequency.DAILY)
    result = CompoundInterestSimulator().run(params)
    assert result.summary.final_capital == pytest.approx(10_000 * (1 + 0.06 / 365) ** 3650)


def test_totals_and_rows_are_consistent() -> None:
    result = CompoundInterestSimulator().run(make_params())
    s = result.summary
    assert s.total_contributed == pytest.approx(10_000 + 200 * 120)
    assert s.interest_earned == pytest.approx(s.final_capital - s.total_contributed)
    assert len(result.monthly) == 120 and len(result.yearly) == 10
    assert result.yearly[-1].closing == pytest.approx(s.final_capital)
    assert result.yearly[0].contribution == pytest.approx(2_400)
    assert s.irr == pytest.approx((1 + 0.06 / 12) ** 12 - 1, rel=1e-6)


def test_fees_reduce_final_capital_by_ter() -> None:
    no_fee = CompoundInterestSimulator().run(make_params(contribution=Money.zero()))
    fee = CompoundInterestSimulator().run(
        make_params(contribution=Money.zero(), ter=Rate.from_percent(1))
    )
    assert fee.summary.final_capital == pytest.approx(no_fee.summary.final_capital / 1.01**10)
    assert fee.summary.total_fees > 0


def test_inflation_adjusted_value() -> None:
    result = CompoundInterestSimulator().run(make_params(inflation=Rate.from_percent(2)))
    s = result.summary
    assert s.real_final_capital == pytest.approx(s.final_capital / 1.02**10)


def test_contribution_increase_applies_per_year() -> None:
    result = CompoundInterestSimulator().run(
        make_params(contribution_increase=Rate.from_percent(3))
    )
    assert result.yearly[1].contribution == pytest.approx(2_400 * 1.03)
    assert result.yearly[2].contribution == pytest.approx(2_400 * 1.03**2)


def test_taxes_on_final_gains_use_spanish_brackets() -> None:
    params = make_params(contribution=Money.zero(), apply_taxes=True)
    result = CompoundInterestSimulator(spanish_savings_policy()).run(params)
    gain = result.summary.final_capital - 10_000
    expected_tax = 6_000 * 0.19 + (gain - 6_000) * 0.21
    assert result.summary.final_tax == pytest.approx(expected_tax)
    assert result.summary.final_capital_net == pytest.approx(
        result.summary.final_capital - expected_tax
    )
    assert result.summary.irr_net is not None and result.summary.irr is not None
    assert result.summary.irr_net < result.summary.irr


def test_taxes_ignored_when_disabled() -> None:
    result = CompoundInterestSimulator(spanish_savings_policy()).run(make_params())
    assert result.summary.total_taxes == 0


def test_withdrawals_stop_contributions_and_deplete() -> None:
    plan = WithdrawalPlan(Money.of(1_000), Frequency.MONTHLY, start_month=24)
    params = make_params(withdrawal=plan, horizon=TimeHorizon.from_years(10), apply_taxes=True)
    result = CompoundInterestSimulator(spanish_savings_policy()).run(params)
    assert all(r.contribution == 0 for r in result.monthly[24:])
    assert result.summary.depletion_month is not None
    assert result.summary.final_capital == 0
    assert result.monthly[-1].withdrawal == 0
    assert result.summary.total_taxes > 0


def test_withdrawals_tax_only_gain_portion() -> None:
    plan = WithdrawalPlan(Money.of(100), Frequency.ANNUAL, start_month=0)
    params = make_params(
        initial_capital=Money.of(1_000),
        contribution=Money.zero(),
        annual_rate=Rate(0.0),
        withdrawal=plan,
        apply_taxes=True,
    )
    result = CompoundInterestSimulator(spanish_savings_policy()).run(params)
    assert result.summary.total_taxes == 0
    assert result.summary.total_withdrawn == pytest.approx(1_000)


def test_balance_at_interpolates() -> None:
    result = CompoundInterestSimulator().run(make_params())
    assert result.balance_at(0) == pytest.approx(10_000)
    mid = result.balance_at(1.5)
    assert result.monthly[0].closing < mid < result.monthly[1].closing
    assert result.balance_at(10_000) == result.summary.final_capital


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"initial_capital": Money.of(-1)}, "initial_capital"),
        ({"contribution": Money.of(-5)}, "contribution"),
        ({"ter": Rate.from_percent(-1)}, "ter"),
        ({"initial_capital": Money.zero(), "contribution": Money.zero()}, "initial_capital"),
        (
            {"withdrawal": WithdrawalPlan(Money.of(100), Frequency.MONTHLY, start_month=500)},
            "withdrawal_start_month",
        ),
    ],
)
def test_validation_errors(override: dict[str, object], field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        make_params(**override)
    assert field in exc.value.errors


def test_horizon_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        TimeHorizon(0)
