from __future__ import annotations

from datetime import date

from finance_app.application.assemblers import (
    input_from_params,
    investment_summary,
    params_from_input,
    snapshot_dto,
    snapshot_from_input,
)
from finance_app.application.dates import add_months
from finance_app.application.dto import (
    InvestmentDetailDTO,
    InvestmentSummaryDTO,
    SimulationInput,
    SnapshotInput,
)
from finance_app.domain.portfolio.comparison import PerformanceComparator
from finance_app.domain.portfolio.investment import Investment, InvestmentStatus
from finance_app.domain.portfolio.repository import InvestmentRepository
from finance_app.domain.shared.errors import ValidationError


class CreateInvestmentFromSimulation:
    def __init__(self, repository: InvestmentRepository) -> None:
        self._repository = repository

    def execute(
        self, name: str, start_date: date, simulation: SimulationInput, notes: str = ""
    ) -> str:
        investment = Investment.create(name, start_date, params_from_input(simulation), notes)
        self._repository.save(investment)
        return investment.id


class ListInvestments:
    def __init__(self, repository: InvestmentRepository, comparator: PerformanceComparator):
        self._repository = repository
        self._comparator = comparator

    def execute(self) -> list[InvestmentSummaryDTO]:
        investments = sorted(self._repository.list(), key=lambda i: (i.start_date, i.name))
        return [investment_summary(i, self._comparator.compare(i)) for i in investments]


class GetInvestmentDetail:
    def __init__(self, repository: InvestmentRepository, comparator: PerformanceComparator):
        self._repository = repository
        self._comparator = comparator

    def execute(self, investment_id: str) -> InvestmentDetailDTO:
        investment = self._repository.get(investment_id)
        report = self._comparator.compare(investment)
        start = investment.start_date
        monthly = report.projection.monthly
        initial = investment.parameters.initial_capital.to_float()
        projection = ((start, initial), *((add_months(start, r.index), r.closing) for r in monthly))
        contributed = (
            (start, initial),
            *((add_months(start, r.index), r.cost_basis) for r in monthly),
        )
        xirr = report.actual_xirr
        return InvestmentDetailDTO(
            summary=investment_summary(investment, report),
            notes=investment.notes,
            parameters=input_from_params(investment.parameters),
            projection=projection,
            projection_contributed=contributed,
            projected_final=report.projection.summary.final_capital,
            snapshots=tuple(
                snapshot_dto(s, p) for s, p in zip(investment.snapshots, report.points, strict=True)
            ),
            actual_xirr_pct=None if xirr is None else xirr * 100,
        )


class RecordSnapshot:
    """Adds a new snapshot, or replaces an existing one when ``snapshot_id`` is given."""

    def __init__(self, repository: InvestmentRepository) -> None:
        self._repository = repository

    def execute(
        self, investment_id: str, data: SnapshotInput, snapshot_id: str | None = None
    ) -> str:
        investment = self._repository.get(investment_id)
        if snapshot_id:
            investment.get_snapshot(snapshot_id)
        snapshot = snapshot_from_input(
            data.date, data.market_value, data.contribution, data.withdrawal, data.note, snapshot_id
        )
        investment.record_snapshot(snapshot)
        self._repository.save(investment)
        return snapshot.id


class DeleteSnapshot:
    def __init__(self, repository: InvestmentRepository) -> None:
        self._repository = repository

    def execute(self, investment_id: str, snapshot_id: str) -> None:
        investment = self._repository.get(investment_id)
        investment.remove_snapshot(snapshot_id)
        self._repository.save(investment)


class UpdateInvestment:
    def __init__(self, repository: InvestmentRepository) -> None:
        self._repository = repository

    def execute(
        self,
        investment_id: str,
        *,
        name: str | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> None:
        investment = self._repository.get(investment_id)
        if name is not None:
            investment.rename(name)
        if notes is not None:
            investment.notes = notes.strip()
        if status is not None:
            try:
                new_status = InvestmentStatus(status)
            except ValueError as exc:
                raise ValidationError.single("status", f"Invalid status '{status}'.") from exc
            investment.close() if new_status is InvestmentStatus.CLOSED else investment.reopen()
        self._repository.save(investment)


class DeleteInvestment:
    def __init__(self, repository: InvestmentRepository) -> None:
        self._repository = repository

    def execute(self, investment_id: str) -> None:
        self._repository.delete(investment_id)
