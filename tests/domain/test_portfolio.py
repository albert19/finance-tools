from __future__ import annotations

from datetime import date

import pytest

from finance_app.domain.portfolio.comparison import PerformanceComparator, PerformanceStatus
from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.domain.shared.money import Money
from finance_app.domain.simulation.simulator import CompoundInterestSimulator
from tests.factories import make_params

START = date(2024, 1, 1)


def make_investment() -> Investment:
    return Investment.create("ETF World", START, make_params(contribution=Money.zero()))


def test_snapshots_are_sorted_and_validated() -> None:
    inv = make_investment()
    inv.record_snapshot(PerformanceSnapshot(date(2024, 6, 1), Money.of(10_300)))
    inv.record_snapshot(PerformanceSnapshot(date(2024, 3, 1), Money.of(10_100)))
    assert [s.date.month for s in inv.snapshots] == [3, 6]
    with pytest.raises(ValidationError):
        inv.record_snapshot(PerformanceSnapshot(date(2023, 12, 1), Money.of(1)))
    with pytest.raises(ValidationError):
        inv.record_snapshot(PerformanceSnapshot(date(2024, 3, 1), Money.of(1)))


def test_update_and_remove_snapshot() -> None:
    inv = make_investment()
    snap = PerformanceSnapshot(date(2024, 3, 1), Money.of(10_100))
    inv.record_snapshot(snap)
    inv.update_snapshot(snap.id, market_value=Money.of(9_000))
    assert inv.snapshots[0].market_value == Money.of(9_000)
    inv.remove_snapshot(snap.id)
    assert inv.snapshots == ()
    with pytest.raises(NotFoundError):
        inv.remove_snapshot(snap.id)


def test_invalid_name_and_negative_snapshot() -> None:
    with pytest.raises(ValidationError):
        Investment.create("  ", START, make_params())
    with pytest.raises(ValidationError):
        PerformanceSnapshot(START, Money.of(-1))


def test_comparison_against_projection() -> None:
    inv = make_investment()
    comparator = PerformanceComparator(CompoundInterestSimulator())
    assert comparator.compare(inv).status is PerformanceStatus.NO_DATA

    one_year = date(2025, 1, 1)
    projected = comparator.compare(inv).projection.balance_at(12 * 366 / 365.25)
    inv.record_snapshot(PerformanceSnapshot(one_year, Money.of(projected * 0.9)))
    report = comparator.compare(inv)
    latest = report.latest
    assert latest is not None
    assert latest.projected == pytest.approx(projected)
    assert latest.deviation_pct == pytest.approx(-0.10, abs=1e-5)
    assert report.status is PerformanceStatus.BEHIND
    assert report.actual_xirr is not None
    assert report.actual_xirr < report.expected_rate


def test_comparison_ahead_with_contributions() -> None:
    inv = make_investment()
    inv.record_snapshot(
        PerformanceSnapshot(date(2024, 7, 1), Money.of(12_500), contribution=Money.of(1_000))
    )
    report = PerformanceComparator(CompoundInterestSimulator()).compare(inv)
    assert report.status is PerformanceStatus.AHEAD
    assert report.points[0].contributed_actual == pytest.approx(11_000)
