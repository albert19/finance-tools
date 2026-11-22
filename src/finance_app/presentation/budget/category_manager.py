from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from finance_app.application.dto import CategoryDTO
from finance_app.presentation.budget.dialogs import CategoryDialog
from finance_app.presentation.budget.view_model import CategoriesViewModel
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.widgets import named

DEFAULT_INCOME = (N_("Salary"), N_("Freelance work"), N_("Other income"))
DEFAULT_EXPENSES = (
    N_("Housing"),
    N_("Utilities"),
    N_("Groceries"),
    N_("Transport"),
    N_("Health"),
    N_("Leisure"),
    N_("Savings"),
    N_("Other expenses"),
)

_HEADERS = [N_("Name"), N_("State")]
_ID_ROLE = Qt.ItemDataRole.UserRole


class CategoryManagerView(QWidget):
    """Two lists (income / expenses) with add, rename, archive and delete actions."""

    def __init__(self, view_model: CategoriesViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.tables: dict[str, QTableWidget] = {
            "expense": self._table(),
            "income": self._table(),
        }
        self.empty = named(QLabel(tr("No categories yet.")), "EmptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seed_button = QPushButton(tr("Add default categories"))
        self.add_income = QPushButton(tr("Add income category"))
        self.add_expense = QPushButton(tr("Add expense category"))
        self.rename_button = QPushButton(tr("Rename"))
        self.archive_button = QPushButton(tr("Archive"))
        self.delete_button = QPushButton(tr("Delete"))

        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_income)
        buttons.addWidget(self.add_expense)
        buttons.addStretch(1)
        buttons.addWidget(self.rename_button)
        buttons.addWidget(self.archive_button)
        buttons.addWidget(self.delete_button)
        layout.addLayout(buttons)
        sections = (("income", N_("Income categories")), ("expense", N_("Expense categories")))
        for kind, title in sections:
            layout.addWidget(named(QLabel(tr(title)), "SectionTitle"))
            layout.addWidget(self.tables[kind], 1)
        hint = QHBoxLayout()
        hint.addWidget(self.seed_button)
        hint.addStretch(1)
        layout.addLayout(hint)

        self._vm.categories_loaded.connect(self._fill)
        self.add_income.clicked.connect(lambda: self._add("income"))
        self.add_expense.clicked.connect(lambda: self._add("expense"))
        self.rename_button.clicked.connect(self._rename)
        self.archive_button.clicked.connect(self._toggle_archive)
        self.delete_button.clicked.connect(self._delete)
        self.seed_button.clicked.connect(self._seed)
        for table in self.tables.values():
            table.itemSelectionChanged.connect(self._update_buttons)
            table.itemDoubleClicked.connect(lambda _item: self._rename())
        self._update_buttons()

    @staticmethod
    def _table() -> QTableWidget:
        table = QTableWidget(0, len(_HEADERS))
        table.setHorizontalHeaderLabels([tr(h) for h in _HEADERS])
        table.verticalHeader().hide()
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setMaximumHeight(300)
        return table

    def _fill(self, categories: list[CategoryDTO]) -> None:
        for kind, table in self.tables.items():
            items = [c for c in categories if c.kind == kind]
            with QSignalBlocker(table):
                table.setRowCount(len(items))
                for row, category in enumerate(items):
                    name = QTableWidgetItem(category.name)
                    name.setData(_ID_ROLE, category)
                    state = QTableWidgetItem(tr("Archived") if category.archived else "")
                    if category.archived:
                        name.setForeground(QColor("#94a3b8"))
                        state.setForeground(QColor("#94a3b8"))
                    table.setItem(row, 0, name)
                    table.setItem(row, 1, state)
                table.clearSelection()
        self.seed_button.setVisible(not categories)
        self._update_buttons()

    def _selected(self) -> CategoryDTO | None:
        for table in self.tables.values():
            rows = table.selectionModel().selectedRows()
            if rows:
                item = table.item(rows[0].row(), 0)
                return item.data(_ID_ROLE) if item else None
        return None

    def _update_buttons(self) -> None:
        category = self._selected()
        self.rename_button.setEnabled(category is not None)
        self.archive_button.setEnabled(category is not None)
        self.archive_button.setText(
            tr("Unarchive") if category and category.archived else tr("Archive")
        )
        self.delete_button.setEnabled(category is not None and not category.in_use)
        if category and category.in_use:
            self.delete_button.setToolTip(
                tr("Used by budgets or transactions; archive it instead.")
            )
        else:
            self.delete_button.setToolTip("")

    def _add(self, kind: str) -> None:
        dialog = CategoryDialog(parent=self)
        index = dialog.kind.findData(kind)
        if index >= 0:
            dialog.kind.setCurrentIndex(index)
        dialog.kind.setEnabled(False)
        if dialog.exec():
            name, selected_kind = dialog.values()
            self._vm.create(name, selected_kind)

    def _rename(self) -> None:
        category = self._selected()
        if category is None:
            return
        dialog = CategoryDialog(category, self)
        if dialog.exec():
            name, _kind = dialog.values()
            self._vm.update(category.id, name=name)

    def _toggle_archive(self) -> None:
        category = self._selected()
        if category is not None:
            self._vm.update(category.id, archived=not category.archived)

    def _delete(self) -> None:
        category = self._selected()
        if category is None:
            return
        answer = QMessageBox.question(
            self,
            tr("Confirm"),
            tr("Delete the category “{name}”?", name=category.name),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._vm.delete(category.id)

    def _seed(self) -> None:
        self._vm.seed_defaults(
            [tr(name) for name in DEFAULT_INCOME],
            [tr(name) for name in DEFAULT_EXPENSES],
        )
