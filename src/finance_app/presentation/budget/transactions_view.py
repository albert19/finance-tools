from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import TransactionDTO
from finance_app.presentation import theme
from finance_app.presentation.budget.dialogs import TransactionDialog
from finance_app.presentation.budget.period_picker import PeriodPicker
from finance_app.presentation.budget.view_model import (
    CategoriesViewModel,
    TransactionsViewModel,
)
from finance_app.presentation.formatting import money, short_date
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.widgets import named

_HEADERS = [N_("Date"), N_("Type"), N_("Category"), N_("Description"), N_("Amount")]
_KIND_LABELS = {"income": N_("Income"), "expense": N_("Expense")}
_FILTERS = [
    ("", N_("All")),
    ("income", N_("Income")),
    ("expense", N_("Expense")),
]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_ID_ROLE = Qt.ItemDataRole.UserRole


class TransactionsView(QWidget):
    """Manual income and expense entries for the selected month."""

    def __init__(
        self,
        view_model: TransactionsViewModel,
        categories_vm: CategoriesViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._categories_vm = categories_vm
        self._transactions: list[TransactionDTO] = []

        self.picker = PeriodPicker()
        self.filter = QComboBox()
        for value, label in _FILTERS:
            self.filter.addItem(tr(label), value)
        self.add_button = named(QPushButton(tr("Add entry")), "Primary")
        self.edit_button = QPushButton(tr("Edit"))
        self.delete_button = QPushButton(tr("Delete"))
        header = QHBoxLayout()
        header.addWidget(self.picker)
        header.addStretch(1)
        header.addWidget(QLabel(tr("Show:")))
        header.addWidget(self.filter)
        header.addWidget(self.add_button)
        header.addWidget(self.edit_button)
        header.addWidget(self.delete_button)

        self.empty = named(QLabel(tr("No entries for this month.")), "EmptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table = QTableWidget(0, len(_HEADERS))
        self.table.setHorizontalHeaderLabels([tr(h) for h in _HEADERS])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.totals = named(QLabel(""), "KpiHint")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.empty)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.totals)
        self.empty.hide()

        self.picker.period_changed.connect(self._vm.select_period)
        self.filter.currentIndexChanged.connect(self._fill)
        self.add_button.clicked.connect(lambda: self._dialog(None))
        self.edit_button.clicked.connect(lambda: self._dialog(self._selected()))
        self.delete_button.clicked.connect(self._confirm_delete)
        self.table.itemDoubleClicked.connect(lambda _item: self._dialog(self._selected()))
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self._vm.transactions_loaded.connect(self._on_loaded)
        self._update_buttons()

    def set_period(self, year: int, month: int) -> None:
        self.picker.set_period(year, month, emit=True)

    def period(self) -> tuple[int, int]:
        return self.picker.period()

    def filter_kind(self) -> int:
        return self.filter.currentIndex()

    def set_filter_kind(self, index: int) -> None:
        self.filter.setCurrentIndex(index)

    def _on_loaded(self, transactions: list[TransactionDTO]) -> None:
        self._transactions = transactions
        self._fill()

    def _fill(self, *_args: object) -> None:
        kind = str(self.filter.currentData())
        items = [t for t in self._transactions if not kind or t.kind == kind]
        self.table.setRowCount(len(items))
        self.empty.setVisible(not items)
        income_total = expense_total = 0.0
        for row, tx in enumerate(items):
            cells = [
                (short_date(tx.date), None, None),
                (tr(_KIND_LABELS.get(tx.kind, tx.kind)), None, None),
                (tx.category_name, None, None),
                (tx.description, None, None),
                (
                    money(tx.amount),
                    _RIGHT,
                    theme.POSITIVE if tx.kind == "income" else theme.NEGATIVE,
                ),
            ]
            for col, (text, align, color) in enumerate(cells):
                cell = QTableWidgetItem(text)
                cell.setData(_ID_ROLE, tx.id)
                if align is not None:
                    cell.setTextAlignment(align)
                if color is not None:
                    cell.setForeground(QColor(color))
                self.table.setItem(row, col, cell)
            if tx.kind == "income":
                income_total += tx.amount
            else:
                expense_total += tx.amount
        self.totals.setText(
            tr(
                "Income: {income} · Expenses: {expenses} · Net: {net}",
                income=money(income_total),
                expenses=money(expense_total),
                net=money(income_total - expense_total),
            )
        )
        self._update_buttons()

    def _selected(self) -> TransactionDTO | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        tx_id = str(item.data(_ID_ROLE)) if item else None
        return next((t for t in self._transactions if t.id == tx_id), None)

    def _update_buttons(self) -> None:
        has_categories = bool(self._categories_vm.categories)
        selected = self._selected() is not None
        self.add_button.setEnabled(has_categories)
        if not has_categories:
            self.add_button.setToolTip(tr("Create a category first (Budget → Categories tab)."))
        else:
            self.add_button.setToolTip("")
        self.edit_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    def _dialog(self, existing: TransactionDTO | None) -> None:
        year, month = self.period()
        dialog = TransactionDialog(
            self._categories_vm.categories,
            existing,
            default_date=self._default_day(year, month),
            parent=self,
        )
        if dialog.exec():
            self._vm.record(dialog.transaction_input(), existing.id if existing else None)

    @staticmethod
    def _default_day(year: int, month: int) -> date:
        today = date.today()
        return today if (today.year, today.month) == (year, month) else date(year, month, 1)

    def _confirm_delete(self) -> None:
        tx = self._selected()
        if tx is None:
            return
        answer = QMessageBox.question(
            self,
            tr("Confirm"),
            tr(
                "Delete the {kind} of {amount} on {date}?",
                kind=tr(_KIND_LABELS.get(tx.kind, tx.kind)),
                amount=money(tx.amount),
                date=short_date(tx.date),
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._vm.delete(tx.id)
