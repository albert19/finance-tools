"""Translation between DTOs and domain objects."""

from __future__ import annotations

from datetime import date

from finance_app.application.dto import (
    InvestmentSummaryDTO,
    RowDTO,
    SimulationInput,
    SimulationOutput,
    SnapshotDTO,
    SummaryDTO,
)
from finance_app.domain.portfolio.comparison import ComparisonPoint, ComparisonReport
from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import ValidationError
from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.result import PeriodRow, SimulationResult
from finance_app.domain.simulation.value_objects import (
    ContributionTiming,
    Frequency,
    SimulationParameters,
    TimeHorizon,
    WithdrawalPlan,
)


def _pct(value: float | None) -> float | None:
    return None if value is None else value * 100


def _enum[E: (Frequency, ContributionTiming)](
    kind: type[E], value: str, field: str, errors: dict[str, str]
) -> E | None:
    try:
        return kind(value)
    except ValueError:
        errors[field] = f"Invalid value '{value}'."
        return None


def params_from_input(data: SimulationInput) -> SimulationParameters:
    """Build validated domain parameters; raises ValidationError with all field errors."""
    errors: dict[str, str] = {}
    horizon: TimeHorizon | None = None
    try:
        horizon = TimeHorizon(int(data.horizon_months))
    except ValidationError as exc:
        errors.update(exc.errors)
    contribution_frequency = _enum(
        Frequency, data.contribution_frequency, "contribution_frequency", errors
    )
    compounding = _enum(Frequency, data.compounding_frequency, "compounding_frequency", errors)
    timing = _enum(ContributionTiming, data.contribution_timing, "contribution_timing", errors)
    withdrawal_frequency = _enum(
        Frequency, data.withdrawal_frequency, "withdrawal_frequency", errors
    )
    if data.withdrawal_amount < 0:
        errors["withdrawal_amount"] = "Withdrawal amount cannot be negative."
    if errors:
        try:
            _build(
                data,
                TimeHorizon(12),
                Frequency.MONTHLY,
                Frequency.MONTHLY,
                ContributionTiming.END,
                Frequency.MONTHLY,
            )
        except ValidationError as exc:
            errors = {**exc.errors, **errors}
        raise ValidationError(errors)
    assert horizon and contribution_frequency and compounding and timing and withdrawal_frequency
    return _build(data, horizon, contribution_frequency, compounding, timing, withdrawal_frequency)


def _build(
    data: SimulationInput,
    horizon: TimeHorizon,
    contribution_frequency: Frequency,
    compounding: Frequency,
    timing: ContributionTiming,
    withdrawal_frequency: Frequency,
) -> SimulationParameters:
    withdrawal = None
    if data.withdrawal_amount > 0:
        withdrawal = WithdrawalPlan(
            Money.of(data.withdrawal_amount), withdrawal_frequency, int(data.withdrawal_start_month)
        )
    return SimulationParameters(
        initial_capital=Money.of(data.initial_capital),
        contribution=Money.of(data.contribution),
        contribution_frequency=contribution_frequency,
        annual_rate=Rate.from_percent(data.annual_rate_pct),
        compounding_frequency=compounding,
        horizon=horizon,
        contribution_timing=timing,
        inflation=Rate.from_percent(data.inflation_pct),
        ter=Rate.from_percent(data.ter_pct),
        contribution_increase=Rate.from_percent(data.contribution_increase_pct),
        withdrawal=withdrawal,
        apply_taxes=data.apply_taxes,
    )


def input_from_params(params: SimulationParameters) -> SimulationInput:
    w = params.withdrawal
    return SimulationInput(
        initial_capital=params.initial_capital.to_float(),
        contribution=params.contribution.to_float(),
        contribution_frequency=params.contribution_frequency.value,
        annual_rate_pct=params.annual_rate.percent,
        compounding_frequency=params.compounding_frequency.value,
        horizon_months=params.horizon.months,
        contribution_timing=params.contribution_timing.value,
        inflation_pct=params.inflation.percent,
        ter_pct=params.ter.percent,
        contribution_increase_pct=params.contribution_increase.percent,
        withdrawal_amount=w.amount.to_float() if w else 0.0,
        withdrawal_frequency=w.frequency.value if w else Frequency.MONTHLY.value,
        withdrawal_start_month=w.start_month if w else 0,
        apply_taxes=params.apply_taxes,
    )


def _row(row: PeriodRow) -> RowDTO:
    return RowDTO(
        index=row.index,
        opening=row.opening,
        contribution=row.contribution,
        interest=row.interest,
        fees=row.fees,
        withdrawal=row.withdrawal,
        taxes=row.taxes,
        closing=row.closing,
        cost_basis=row.cost_basis,
        gains=row.gains,
        real_closing=row.real_closing,
    )


def output_from_result(result: SimulationResult) -> SimulationOutput:
    s = result.summary
    summary = SummaryDTO(
        final_capital=s.final_capital,
        final_capital_net=s.final_capital_net,
        total_contributed=s.total_contributed,
        total_withdrawn=s.total_withdrawn,
        interest_earned=s.interest_earned,
        total_fees=s.total_fees,
        total_taxes=s.total_taxes,
        real_final_capital=s.real_final_capital,
        real_final_capital_net=s.real_final_capital_net,
        total_return_pct=s.total_return * 100,
        irr_pct=_pct(s.irr),
        irr_net_pct=_pct(s.irr_net),
        depletion_month=s.depletion_month,
    )
    return SimulationOutput(
        summary,
        tuple(_row(r) for r in result.yearly),
        tuple(_row(r) for r in result.monthly),
    )


def snapshot_from_input(
    data_date: date,
    market_value: float,
    contribution: float,
    withdrawal: float,
    note: str,
    snapshot_id: str | None = None,
) -> PerformanceSnapshot:
    kwargs = {"id": snapshot_id} if snapshot_id else {}
    return PerformanceSnapshot(
        date=data_date,
        market_value=Money.of(market_value),
        contribution=Money.of(contribution),
        withdrawal=Money.of(withdrawal),
        note=note.strip(),
        **kwargs,
    )


def snapshot_dto(snapshot: PerformanceSnapshot, point: ComparisonPoint) -> SnapshotDTO:
    return SnapshotDTO(
        id=snapshot.id,
        date=snapshot.date,
        market_value=snapshot.market_value.to_float(),
        contribution=snapshot.contribution.to_float(),
        withdrawal=snapshot.withdrawal.to_float(),
        note=snapshot.note,
        projected=point.projected,
        deviation=point.deviation,
        deviation_pct=_pct(point.deviation_pct),
        contributed_actual=point.contributed_actual,
    )


def investment_summary(investment: Investment, report: ComparisonReport) -> InvestmentSummaryDTO:
    latest = report.latest
    return InvestmentSummaryDTO(
        id=investment.id,
        name=investment.name,
        start_date=investment.start_date,
        status=investment.status.value,
        expected_rate_pct=report.expected_rate * 100,
        initial_capital=investment.parameters.initial_capital.to_float(),
        latest_date=latest.date if latest else None,
        latest_value=latest.actual if latest else None,
        projected_at_latest=latest.projected if latest else None,
        deviation_pct=_pct(latest.deviation_pct) if latest else None,
        performance=report.status.value,
    )
