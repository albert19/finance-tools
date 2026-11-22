from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from finance_app.application.dto import InvestmentSummaryDTO
from finance_app.presentation import theme
from finance_app.presentation.formatting import money, percent, short_date
from finance_app.presentation.i18n import N_, tr

_HEADERS = [
    N_("Name"),
    N_("Start"),
    N_("Expected"),
    N_("Latest value"),
    N_("Deviation"),
    N_("Performance"),
]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class InvestmentList(QTableWidget):
    selected = Signal(object)  # investment id or None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(_HEADERS), parent)
        self.setHorizontalHeaderLabels([tr(h) for h in _HEADERS])
        self.verticalHeader().hide()
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._ids: list[str] = []
        self.itemSelectionChanged.connect(self._emit_selection)

    def current_id(self) -> str | None:
        rows = self.selectionModel().selectedRows()
        return self._ids[rows[0].row()] if rows else None

    def set_investments(self, items: list[InvestmentSummaryDTO], select_id: str | None) -> None:
        with QSignalBlocker(self):
            self.setRowCount(len(items))
            self._ids = [i.id for i in items]
            for row, inv in enumerate(items):
                name = inv.name + (tr(" (closed)") if inv.status == "closed" else "")
                cells = [
                    (name, None),
                    (short_date(inv.start_date), None),
                    (percent(inv.expected_rate_pct), _RIGHT),
                    (money(inv.latest_value), _RIGHT),
                    (percent(inv.deviation_pct, signed=True), _RIGHT),
                    (tr(inv.performance), None),
                ]
                for col, (text, align) in enumerate(cells):
                    item = QTableWidgetItem(text)
                    if align is not None:
                        item.setTextAlignment(align)
                    if col == 4 and inv.deviation_pct is not None:
                        item.setForeground(
                            QColor(theme.POSITIVE if inv.deviation_pct >= 0 else theme.NEGATIVE)
                        )
                    self.setItem(row, col, item)
            self.clearSelection()
            if select_id in self._ids:
                self.selectRow(self._ids.index(select_id))
        self._emit_selection()

    def _emit_selection(self) -> None:
        self.selected.emit(self.current_id())
