from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import RowDTO
from finance_app.presentation.formatting import money
from finance_app.presentation.i18n import N_, tr

_Index = QModelIndex | QPersistentModelIndex
_COLUMNS: list[tuple[str, Callable[[RowDTO], float]]] = [
    (N_("Opening balance"), lambda r: r.opening),
    (N_("Contributions"), lambda r: r.contribution),
    (N_("Interest"), lambda r: r.interest),
    (N_("Fees"), lambda r: -r.fees),
    (N_("Withdrawals"), lambda r: -r.withdrawal),
    (N_("Taxes"), lambda r: -r.taxes),
    (N_("Closing balance"), lambda r: r.closing),
    (N_("Real value"), lambda r: r.real_closing),
]


class BreakdownModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._rows: tuple[RowDTO, ...] = ()
        self._period = N_("Year")

    def set_rows(self, rows: tuple[RowDTO, ...], period: str) -> None:
        self.beginResetModel()
        self._rows, self._period = rows, period
        self.endResetModel()

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: N802, B008
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: N802, B008
        return 0 if parent.isValid() else len(_COLUMNS) + 1

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return tr(self._period if section == 0 else _COLUMNS[section - 1][0])

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return str(row.index)
            return money(_COLUMNS[index.column() - 1][1](row))
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None


class BreakdownTable(QWidget):
    """Year-by-year or month-by-month breakdown."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.granularity = QComboBox()
        self.granularity.addItem(tr("Yearly"), "yearly")
        self.granularity.addItem(tr("Monthly"), "monthly")
        self.model = BreakdownModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("View:")))
        top.addWidget(self.granularity)
        top.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.view)
        self._yearly: tuple[RowDTO, ...] = ()
        self._monthly: tuple[RowDTO, ...] = ()
        self.granularity.currentIndexChanged.connect(self._refresh)

    def set_rows(self, yearly: tuple[RowDTO, ...], monthly: tuple[RowDTO, ...]) -> None:
        self._yearly, self._monthly = yearly, monthly
        self._refresh()

    def _refresh(self) -> None:
        if self.granularity.currentData() == "monthly":
            self.model.set_rows(self._monthly, N_("Month"))
        else:
            self.model.set_rows(self._yearly, N_("Year"))
