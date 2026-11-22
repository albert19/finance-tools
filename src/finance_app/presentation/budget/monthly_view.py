from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import (
    BudgetLineDTO,
    MonthlyReportDTO,
    VarianceRowDTO,
)
from finance_app.presentation import theme
from finance_app.presentation.budget.charts import BudgetVsActualChart, ExpenseDonutChart
from finance_app.presentation.budget.dialogs import BudgetLineDialog, CopyBudgetDialog
from finance_app.presentation.budget.period_picker import PeriodPicker, month_name
from finance_app.presentation.budget.view_model import BudgetViewModel, CategoriesViewModel
from finance_app.presentation.formatting import money, percent, signed_money
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.widgets import named
from finance_app.presentation.widgets.kpi import KpiGrid

_LINE_HEADERS = [N_("Category"), N_("Description"), N_("Amount")]
_VARIANCE_HEADERS = [
    N_("Category"),
    N_("Type"),
    N_("Planned"),
    N_("Actual"),
    N_("Variance"),
    N_("Variance %"),
    N_("Status"),
]
_KPIS = [
    ("planned_income", N_("Planned income"), ""),
    ("actual_income", N_("Actual income"), ""),
    ("planned_expenses", N_("Planned expenses"), ""),
    ("actual_expenses", N_("Actual expenses"), ""),
    ("planned_net", N_("Planned net"), N_("Planned income minus planned expenses.")),
    ("actual_net", N_("Actual net"), N_("Actual income minus actual expenses.")),
]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_ID_ROLE = Qt.ItemDataRole.UserRole
_KIND_LABELS = {"income": N_("Income"), "expense": N_("Expense")}

_STATUS_COLORS = {
    "Favorable": theme.POSITIVE,
    "Unfavorable": theme.NEGATIVE,
}


def _lines_table() -> QTableWidget:
    table = QTableWidget(0, len(_LINE_HEADERS))
    table.setHorizontalHeaderLabels([tr(h) for h in _LINE_HEADERS])
    table.verticalHeader().hide()
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    return table


class MonthlyView(QWidget):
    """Plan editor (lines) plus the variance report of the selected month."""

    def __init__(
        self,
        view_model: BudgetViewModel,
        categories_vm: CategoriesViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._categories_vm = categories_vm
        self.report: MonthlyReportDTO | None = None
        self._periods: list[tuple[int, int]] = []

        self.picker = PeriodPicker()
        self.create_button = named(QPushButton(tr("Create budget")), "Primary")
        self.copy_button = QPushButton(tr("Copy from another month…"))
        self.delete_budget_button = QPushButton(tr("Delete budget"))
        header = QHBoxLayout()
        header.addWidget(self.picker)
        header.addStretch(1)
        header.addWidget(self.create_button)
        header.addWidget(self.copy_button)
        header.addWidget(self.delete_budget_button)

        self.empty = named(QLabel(), "EmptyState")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)

        self.income_table = _lines_table()
        self.expense_table = _lines_table()
        self.income_subtotal = named(QLabel(), "KpiHint")
        self.expense_subtotal = named(QLabel(), "KpiHint")
        self.add_line_button = QPushButton(tr("Add line"))
        self.edit_line_button = QPushButton(tr("Edit line"))
        self.delete_line_button = QPushButton(tr("Delete line"))
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(60)
        self.notes.setPlaceholderText(tr("Notes for this month's budget"))
        self.save_notes_button = QPushButton(tr("Save notes"))

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(named(QLabel(tr("Planned expenses")), "SectionTitle"))
        editor_layout.addWidget(self.expense_table, 1)
        editor_layout.addWidget(self.expense_subtotal)
        editor_layout.addWidget(named(QLabel(tr("Planned income")), "SectionTitle"))
        editor_layout.addWidget(self.income_table, 1)
        editor_layout.addWidget(self.income_subtotal)
        line_buttons = QHBoxLayout()
        line_buttons.addWidget(self.add_line_button)
        line_buttons.addWidget(self.edit_line_button)
        line_buttons.addWidget(self.delete_line_button)
        line_buttons.addStretch(1)
        editor_layout.addLayout(line_buttons)
        notes_row = QHBoxLayout()
        notes_row.addWidget(self.notes, 1)
        notes_row.addWidget(self.save_notes_button)
        editor_layout.addLayout(notes_row)

        self.kpis = KpiGrid(_KPIS, columns=3)
        self.variance_table = QTableWidget(0, len(_VARIANCE_HEADERS))
        self.variance_table.setHorizontalHeaderLabels([tr(h) for h in _VARIANCE_HEADERS])
        self.variance_table.verticalHeader().hide()
        self.variance_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.variance_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.variance_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.variance_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.budget_chart = BudgetVsActualChart()
        self.expense_chart = ExpenseDonutChart()
        chart_tabs = QTabWidget()
        chart_tabs.addTab(self.budget_chart, tr("Planned vs. actual"))
        chart_tabs.addTab(self.expense_chart, tr("Expense breakdown"))

        report_panel = QWidget()
        report_layout = QVBoxLayout(report_panel)
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.addWidget(self.kpis)
        report_layout.addWidget(named(QLabel(tr("Variance by category")), "SectionTitle"))
        report_layout.addWidget(self.variance_table, 1)
        report_layout.addWidget(chart_tabs, 1)

        splitter = QSplitter()
        splitter.addWidget(editor)
        splitter.addWidget(report_panel)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([520, 860])

        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(splitter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.stack, 1)

        self.picker.period_changed.connect(self._vm.select_period)
        self.create_button.clicked.connect(lambda: self._vm.create_budget())
        self.copy_button.clicked.connect(self._copy)
        self.delete_budget_button.clicked.connect(self._confirm_delete_budget)
        self.add_line_button.clicked.connect(lambda: self._line_dialog(None))
        self.edit_line_button.clicked.connect(lambda: self._line_dialog(self._selected_line()))
        self.delete_line_button.clicked.connect(self._confirm_delete_line)
        for table in (self.income_table, self.expense_table):
            table.itemDoubleClicked.connect(lambda _item: self._line_dialog(self._selected_line()))
            table.itemSelectionChanged.connect(self._update_buttons)
        self.save_notes_button.clicked.connect(self._save_notes)
        self._vm.monthly_loaded.connect(self.show_report)
        self._vm.periods_loaded.connect(self._on_periods)
        self._update_buttons()

    # --- state -----------------------------------------------------------

    def set_period(self, year: int, month: int) -> None:
        self.picker.set_period(year, month, emit=True)

    def period(self) -> tuple[int, int]:
        return self.picker.period()

    # --- rendering ---------------------------------------------------------

    def _on_periods(self, periods: list[tuple[int, int]]) -> None:
        self._periods = periods

    def show_report(self, report: MonthlyReportDTO) -> None:
        self.report = report
        budget = report.budget
        self.stack.setCurrentIndex(1 if budget else 0)
        if budget is None:
            self.empty.setText(
                tr(
                    "No budget for {month} {year}.\n\n"
                    "Create one or copy an existing month's budget.",
                    month=month_name(report.month),
                    year=report.year,
                )
            )
        self.delete_budget_button.setEnabled(budget is not None)
        self._fill_lines(budget.lines if budget else ())
        self.notes.setPlainText(budget.notes if budget else "")
        self._fill_totals(report)
        self._fill_variance(report.rows)
        self.budget_chart.show_rows(report.rows)
        self.expense_chart.show_rows(report.rows)
        self._update_buttons()

    def _fill_lines(self, lines: tuple[BudgetLineDTO, ...]) -> None:
        income_total = expense_total = 0.0
        for kind, table in (("expense", self.expense_table), ("income", self.income_table)):
            items = [line for line in lines if line.kind == kind]
            with QSignalBlocker(table):
                table.setRowCount(len(items))
                for row, line in enumerate(items):
                    cells = [
                        (line.category_name, None),
                        (line.description, None),
                        (money(line.amount), _RIGHT),
                    ]
                    for col, (text, align) in enumerate(cells):
                        item = QTableWidgetItem(text)
                        item.setData(_ID_ROLE, line.id)
                        if align is not None:
                            item.setTextAlignment(align)
                        table.setItem(row, col, item)
            if kind == "expense":
                expense_total = sum(line.amount for line in items)
            else:
                income_total = sum(line.amount for line in items)
        self.expense_subtotal.setText(tr("Total expenses: {total}", total=money(expense_total)))
        self.income_subtotal.setText(tr("Total income: {total}", total=money(income_total)))

    def _fill_totals(self, report: MonthlyReportDTO) -> None:
        t = report.totals
        self.kpis.cards["planned_income"].set_value(money(t.planned_income))
        self.kpis.cards["actual_income"].set_value(
            money(t.actual_income), self._hint(t.actual_income - t.planned_income)
        )
        self.kpis.cards["planned_expenses"].set_value(money(t.planned_expenses))
        self.kpis.cards["actual_expenses"].set_value(
            money(t.actual_expenses), self._hint(t.planned_expenses - t.actual_expenses)
        )
        self.kpis.cards["planned_net"].set_value(money(t.planned_net))
        self.kpis.cards["actual_net"].set_value(
            money(t.actual_net),
            self._hint(t.actual_net - t.planned_net),
            theme.POSITIVE if t.actual_net >= t.planned_net else theme.NEGATIVE,
        )

    @staticmethod
    def _hint(difference: float) -> str:
        return tr("vs. plan: {diff}", diff=signed_money(difference)) if difference else ""

    def _fill_variance(self, rows: tuple[VarianceRowDTO, ...]) -> None:
        self.variance_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            cells = [
                (item.name, None, None),
                (
                    tr(_KIND_LABELS.get(item.kind, item.kind)),
                    None,
                    None,
                ),
                (money(item.planned), _RIGHT, None),
                (money(item.actual), _RIGHT, None),
                (signed_money(item.variance), _RIGHT, _STATUS_COLORS.get(item.status)),
                (percent(item.variance_pct, signed=True), _RIGHT, _STATUS_COLORS.get(item.status)),
                (tr(item.status), None, _STATUS_COLORS.get(item.status)),
            ]
            for col, (text, align, color) in enumerate(cells):
                cell = QTableWidgetItem(text)
                if align is not None:
                    cell.setTextAlignment(align)
                if color is not None:
                    cell.setForeground(QColor(color))
                self.variance_table.setItem(row, col, cell)

    # --- actions -----------------------------------------------------------

    def _selected_line(self) -> str | None:
        for table in (self.expense_table, self.income_table):
            rows = table.selectionModel().selectedRows()
            if rows:
                item = table.item(rows[0].row(), 0)
                return str(item.data(_ID_ROLE)) if item else None
        return None

    def _update_buttons(self) -> None:
        has_budget = self.report is not None and self.report.budget is not None
        self.add_line_button.setEnabled(has_budget)
        self.save_notes_button.setEnabled(has_budget)
        selected = self._selected_line()
        self.edit_line_button.setEnabled(selected is not None)
        self.delete_line_button.setEnabled(selected is not None)

    def _line_dialog(self, line_id: str | None) -> None:
        if not self.report or not self.report.budget:
            return
        existing = None
        if line_id:
            existing = next((line for line in self.report.budget.lines if line.id == line_id), None)
        dialog = BudgetLineDialog(self._categories_vm.categories, existing, self)
        if dialog.exec():
            self._vm.save_line(self.report.budget.id, dialog.line_input(), line_id)

    def _save_notes(self) -> None:
        if self.report and self.report.budget:
            self._vm.update_notes(self.report.budget.id, self.notes.toPlainText())

    def _copy(self) -> None:
        dialog = CopyBudgetDialog(self._periods, self.period(), self)
        if dialog.exec() and dialog.selected_period():
            self._vm.create_budget(copy_from=dialog.selected_period())

    def _confirm_delete_budget(self) -> None:
        if not self.report or not self.report.budget:
            return
        answer = QMessageBox.question(
            self,
            tr("Confirm"),
            tr(
                "Delete the budget of {month} {year} and all its lines? This cannot be undone.",
                month=month_name(self.report.month),
                year=self.report.year,
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._vm.delete_budget(self.report.budget.id)

    def _confirm_delete_line(self) -> None:
        line_id = self._selected_line()
        if not self.report or not self.report.budget or line_id is None:
            return
        answer = QMessageBox.question(self, tr("Confirm"), tr("Delete this budget line?"))
        if answer == QMessageBox.StandardButton.Yes:
            self._vm.delete_line(self.report.budget.id, line_id)
