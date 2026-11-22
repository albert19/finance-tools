"""Mapping between spreadsheet rows and domain objects."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from finance_app.domain.portfolio.investment import Investment, InvestmentStatus
from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import DomainError
from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.value_objects import (
    ContributionTiming,
    Frequency,
    SimulationParameters,
    TimeHorizon,
    WithdrawalPlan,
)
from finance_app.infrastructure.sheets.cells import (
    Row,
    RowMappingError,
    as_bool,
    as_date,
    as_dict,
    as_float,
    round_money,
)
from finance_app.infrastructure.sheets.schema import INVESTMENT_COLUMNS, SNAPSHOT_COLUMNS


def investment_to_row(investment: Investment) -> Row:
    p = investment.parameters
    w = p.withdrawal
    values: dict[str, Any] = {
        "id": investment.id,
        "name": investment.name,
        "created_at": investment.created_at.isoformat(timespec="seconds"),
        "start_date": investment.start_date.isoformat(),
        "status": investment.status.value,
        "initial_capital": round_money(p.initial_capital.to_float()),
        "contribution": round_money(p.contribution.to_float()),
        "contribution_frequency": p.contribution_frequency.value,
        "contribution_timing": p.contribution_timing.value,
        "annual_rate_pct": p.annual_rate.percent,
        "compounding_frequency": p.compounding_frequency.value,
        "horizon_months": p.horizon.months,
        "inflation_pct": p.inflation.percent,
        "ter_pct": p.ter.percent,
        "contribution_increase_pct": p.contribution_increase.percent,
        "withdrawal_amount": round_money(w.amount.to_float()) if w else 0,
        "withdrawal_frequency": w.frequency.value if w else "",
        "withdrawal_start_month": w.start_month if w else 0,
        "apply_taxes": p.apply_taxes,
        "notes": investment.notes,
    }
    return [values[c] for c in INVESTMENT_COLUMNS]


def snapshot_to_row(investment_id: str, snapshot: PerformanceSnapshot) -> Row:
    values: dict[str, Any] = {
        "id": snapshot.id,
        "investment_id": investment_id,
        "date": snapshot.date.isoformat(),
        "market_value": round_money(snapshot.market_value.to_float()),
        "contribution": round_money(snapshot.contribution.to_float()),
        "withdrawal": round_money(snapshot.withdrawal.to_float()),
        "note": snapshot.note,
    }
    return [values[c] for c in SNAPSHOT_COLUMNS]


def row_to_snapshot(row: Sequence[Any]) -> tuple[str, PerformanceSnapshot]:
    d = as_dict(row, SNAPSHOT_COLUMNS)
    try:
        snapshot = PerformanceSnapshot(
            id=str(d["id"]),
            date=as_date(d["date"]),
            market_value=Money.of(as_float(d["market_value"])),
            contribution=Money.of(as_float(d["contribution"])),
            withdrawal=Money.of(as_float(d["withdrawal"])),
            note=str(d["note"]),
        )
    except (ValueError, TypeError, DomainError) as exc:
        raise RowMappingError(f"Invalid snapshot row {row!r}: {exc}") from exc
    return str(d["investment_id"]), snapshot


def row_to_investment(
    row: Sequence[Any], snapshots: Sequence[PerformanceSnapshot] = ()
) -> Investment:
    d = as_dict(row, INVESTMENT_COLUMNS)
    try:
        withdrawal = None
        if as_float(d["withdrawal_amount"]) > 0:
            withdrawal = WithdrawalPlan(
                Money.of(as_float(d["withdrawal_amount"])),
                Frequency(d["withdrawal_frequency"] or Frequency.MONTHLY.value),
                int(as_float(d["withdrawal_start_month"])),
            )
        params = SimulationParameters(
            initial_capital=Money.of(as_float(d["initial_capital"])),
            contribution=Money.of(as_float(d["contribution"])),
            contribution_frequency=Frequency(d["contribution_frequency"]),
            annual_rate=Rate.from_percent(as_float(d["annual_rate_pct"])),
            compounding_frequency=Frequency(d["compounding_frequency"]),
            horizon=TimeHorizon(int(as_float(d["horizon_months"]))),
            contribution_timing=ContributionTiming(d["contribution_timing"]),
            inflation=Rate.from_percent(as_float(d["inflation_pct"])),
            ter=Rate.from_percent(as_float(d["ter_pct"])),
            contribution_increase=Rate.from_percent(as_float(d["contribution_increase_pct"])),
            withdrawal=withdrawal,
            apply_taxes=as_bool(d["apply_taxes"]),
        )
        return Investment(
            id=str(d["id"]),
            name=str(d["name"]),
            start_date=as_date(d["start_date"]),
            parameters=params,
            status=InvestmentStatus(d["status"] or InvestmentStatus.ACTIVE.value),
            created_at=datetime.fromisoformat(str(d["created_at"])),
            notes=str(d["notes"]),
            _snapshots=list(snapshots),
        )
    except (ValueError, TypeError, KeyError, DomainError) as exc:
        raise RowMappingError(f"Invalid investment row {row!r}: {exc}") from exc
