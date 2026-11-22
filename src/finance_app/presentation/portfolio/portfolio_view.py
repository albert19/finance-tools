from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import InvestmentDetailDTO, InvestmentSummaryDTO, SnapshotDTO
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.portfolio.dialogs import SnapshotDialog
from finance_app.presentation.portfolio.investment_detail import InvestmentDetail
from finance_app.presentation.portfolio.investment_list import InvestmentList
from finance_app.presentation.portfolio.view_model import PortfolioViewModel
from finance_app.presentation.widgets import named

EMPTY_TEXT = N_(
    "No investments yet.\n\nConfigure a plan in the Simulator tab and click "
    "“Save as investment…” to start tracking it here."
)


class PortfolioView(QWidget):
    open_in_simulator = Signal(object)  # SimulationInput

    def __init__(self, view_model: PortfolioViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.list = InvestmentList()
        self.detail = InvestmentDetail()
        self.refresh_button = QPushButton(tr("Refresh"))
        self.delete_button = QPushButton(tr("Delete investment"))
        self.empty = named(QLabel(tr(EMPTY_TEXT)), "EmptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.no_selection = named(
            QLabel(tr("Select an investment to see its performance.")), "EmptyState"
        )
        self.no_selection.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left = QWidget()
        left.setMinimumWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(named(QLabel(tr("Investments")), "SectionTitle"))
        left_layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)
        buttons.addWidget(self.delete_button)
        left_layout.addLayout(buttons)

        self.right = QStackedWidget()
        self.right.addWidget(self.no_selection)
        self.right.addWidget(self.detail)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.right)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([520, 900])

        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(splitter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.list.selected.connect(self._vm.select)
        self.refresh_button.clicked.connect(self._vm.load)
        self.delete_button.clicked.connect(self._confirm_delete)
        self.detail.add_snapshot.connect(lambda: self._snapshot_dialog(None))
        self.detail.edit_snapshot.connect(self._snapshot_dialog)
        self.detail.delete_snapshot.connect(self._confirm_delete_snapshot)
        self.detail.open_in_simulator.connect(self.open_in_simulator)
        self.detail.toggle_status.connect(self._toggle_status)
        self._vm.investments_loaded.connect(self._on_investments)
        self._vm.detail_loaded.connect(self._on_detail)
        self._vm.busy_changed.connect(lambda busy: self.refresh_button.setDisabled(busy))
        self.delete_button.setEnabled(False)

    def _on_investments(self, items: list[InvestmentSummaryDTO]) -> None:
        self.stack.setCurrentIndex(1 if items else 0)
        self.list.set_investments(items, self._vm.selected_id)

    def _on_detail(self, detail: InvestmentDetailDTO | None) -> None:
        self.delete_button.setEnabled(detail is not None)
        if detail is None:
            self.right.setCurrentWidget(self.no_selection)
            return
        self.detail.show_detail(detail)
        self.right.setCurrentWidget(self.detail)

    def _current(self) -> InvestmentDetailDTO | None:
        return self.detail.detail if self.right.currentWidget() is self.detail else None

    def _snapshot_dialog(self, existing: SnapshotDTO | None) -> None:
        current = self._current()
        if current is None:
            return
        dialog = SnapshotDialog(current.summary.start_date, existing, self)
        if dialog.exec():
            self._vm.record_snapshot(
                current.summary.id, dialog.snapshot_input(), existing.id if existing else None
            )

    def _confirm_delete_snapshot(self, snapshot: SnapshotDTO) -> None:
        current = self._current()
        if current and self._confirm(
            tr("Delete the snapshot of {date}?", date=f"{snapshot.date:%d/%m/%Y}")
        ):
            self._vm.delete_snapshot(current.summary.id, snapshot.id)

    def _confirm_delete(self) -> None:
        current = self._current()
        if current and self._confirm(
            tr(
                "Delete “{name}” and all its snapshots? This cannot be undone.",
                name=current.summary.name,
            )
        ):
            self._vm.delete_investment(current.summary.id)

    def _toggle_status(self) -> None:
        current = self._current()
        if current:
            new = "active" if current.summary.status == "closed" else "closed"
            self._vm.update_investment(current.summary.id, status=new)

    def _confirm(self, text: str) -> bool:
        answer = QMessageBox.question(self, tr("Confirm"), text)
        return answer == QMessageBox.StandardButton.Yes
