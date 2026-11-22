from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from PySide6.QtCore import Signal

from finance_app.application.dto import SimulationInput, SnapshotInput
from finance_app.application.use_cases.portfolio import (
    CreateInvestmentFromSimulation,
    DeleteInvestment,
    DeleteSnapshot,
    GetInvestmentDetail,
    ListInvestments,
    RecordSnapshot,
    UpdateInvestment,
)
from finance_app.domain.shared.errors import NotFoundError
from finance_app.presentation.base import BaseViewModel
from finance_app.presentation.i18n import tr
from finance_app.presentation.workers import TaskRunner


@dataclass(frozen=True, slots=True)
class PortfolioUseCases:
    create: CreateInvestmentFromSimulation
    list: ListInvestments
    detail: GetInvestmentDetail
    record_snapshot: RecordSnapshot
    delete_snapshot: DeleteSnapshot
    update: UpdateInvestment
    delete: DeleteInvestment


class PortfolioViewModel(BaseViewModel):
    investments_loaded = Signal(list)  # list[InvestmentSummaryDTO]
    detail_loaded = Signal(object)  # InvestmentDetailDTO | None
    created = Signal(str)  # investment id

    def __init__(self, use_cases: PortfolioUseCases, runner: TaskRunner) -> None:
        super().__init__(runner)
        self._uc = use_cases
        self.selected_id: str | None = None

    def load(self) -> None:
        self._run(self._uc.list.execute, self.investments_loaded.emit)

    def select(self, investment_id: str | None) -> None:
        self.selected_id = investment_id
        if investment_id is None:
            self.detail_loaded.emit(None)
            return

        def fetch() -> Any:
            try:
                return self._uc.detail.execute(investment_id)
            except NotFoundError:
                return None

        def deliver(detail: Any) -> None:
            if self.selected_id == investment_id:
                self.detail_loaded.emit(detail)

        self._run(fetch, deliver)

    def _refresh(self, _: Any = None) -> None:
        self.load()
        self.select(self.selected_id)

    def create_from_simulation(
        self, name: str, start: date, simulation: SimulationInput, notes: str = ""
    ) -> None:
        def done(investment_id: str) -> None:
            self.selected_id = investment_id
            self._refresh()
            self.created.emit(investment_id)

        self._run(
            lambda: self._uc.create.execute(name, start, simulation, notes),
            done,
            tr("Investment “{name}” saved.", name=name),
        )

    def record_snapshot(
        self, investment_id: str, data: SnapshotInput, snapshot_id: str | None = None
    ) -> None:
        self._run(
            lambda: self._uc.record_snapshot.execute(investment_id, data, snapshot_id),
            self._refresh,
            tr("Snapshot saved."),
        )

    def delete_snapshot(self, investment_id: str, snapshot_id: str) -> None:
        self._run(
            lambda: self._uc.delete_snapshot.execute(investment_id, snapshot_id),
            self._refresh,
            tr("Snapshot deleted."),
        )

    def update_investment(self, investment_id: str, **changes: Any) -> None:
        self._run(
            lambda: self._uc.update.execute(investment_id, **changes),
            self._refresh,
            tr("Investment updated."),
        )

    def delete_investment(self, investment_id: str) -> None:
        if self.selected_id == investment_id:
            self.selected_id = None
        self._run(
            lambda: self._uc.delete.execute(investment_id), self._refresh, tr("Investment deleted.")
        )
