from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import AnnualReportDTO, VarianceRowDTO
from finance_app.presentation import theme
from finance_app.presentation.budget.charts import AnnualTrendChart
from finance_app.presentation.budget.period_picker import YearPicker, month_name
from finance_app.presentation.budget.view_model import BudgetViewModel
from finance_app.presentation.formatting import money, percent, signed_money
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.widgets import named
from finance_app.presentation.widgets.kpi import KpiGrid

_KPIS = [
    ("planned_income", N_("Planned income"), ""),
    ("actual_income", N_("Actual income"), ""),
    ("planned_expenses", N_("Planned expenses"), ""),
    ("actual_expenses", N_("Actual expenses"), ""),
    ("planned_net", N_("Planned net"), N_("Planned income minus planned expenses.")),
    ("actual_net", N_("Actual net"), N_("Actual income minus actual expenses.")),
]
_VARIANCE_HEADERS = [
    N_("Category"),
    N_("Type"),
    N_("Planned"),
    N_("Actual"),
    N_("Variance"),
    N_("Variance %"),
    N_("Status"),
]
_MONTH_HEADERS = [
    N_("Month"),
    N_("Planned income"),
    N_("Actual income"),
    N_("Planned expenses"),
    N_("Actual expenses"),
    N_("Actual net"),
]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_STATUS_COLORS = {
    "Favorable": theme.POSITIVE,
    "Unfavorable": theme.NEGATIVE,
}
_KIND_LABELS = {"income": N_("Income"), "expense": N_("Expense")}


class AnnualView(QWidget):
    """Roll-up of the year's monthly budgets and actuals."""

    open_month = Signal(int, int)  # year, month

    def __init__(self, view_model: BudgetViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.report: AnnualReportDTO | None = None

        self.picker = YearPicker()
        header = QHBoxLayout()
        header.addWidget(self.picker)
        header.addStretch(1)

        self.kpis = KpiGrid(_KPIS, columns=6)
        self.chart = AnnualTrendChart()
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
        self.months_table = QTableWidget(0, len(_MONTH_HEADERS))
        self.months_table.setHorizontalHeaderLabels([tr(h) for h in _MONTH_HEADERS])
        self.months_table.verticalHeader().hide()
        self.months_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.months_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.months_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        tables = QSplitter()
        tables.addWidget(self.variance_table)
        tables.addWidget(self.months_table)
        tables.setSizes([640, 760])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.kpis)
        layout.addWidget(self.chart, 1)
        hint = named(QLabel(tr("Double-click a month to open it in the Monthly tab.")), "KpiHint")
        layout.addWidget(hint)
        layout.addWidget(tables, 1)

        self.picker.year_changed.connect(self._vm.select_year)
        self.months_table.itemDoubleClicked.connect(self._open_month)
        self._vm.annual_loaded.connect(self.show_report)

    def set_year(self, year: int) -> None:
        self.picker.year.setValue(year)

    def year(self) -> int:
        return self.picker.year.value()

    def show_report(self, report: AnnualReportDTO) -> None:
        self.report = report
        t = report.totals
        self.kpis.cards["planned_income"].set_value(money(t.planned_income))
        self.kpis.cards["actual_income"].set_value(
            money(t.actual_income),
            tr("vs. plan: {diff}", diff=signed_money(t.actual_income - t.planned_income)),
        )
        self.kpis.cards["planned_expenses"].set_value(money(t.planned_expenses))
        self.kpis.cards["actual_expenses"].set_value(
            money(t.actual_expenses),
            tr("vs. plan: {diff}", diff=signed_money(t.actual_expenses - t.planned_expenses)),
        )
        self.kpis.cards["planned_net"].set_value(money(t.planned_net))
        self.kpis.cards["actual_net"].set_value(
            money(t.actual_net),
            tr("vs. plan: {diff}", diff=signed_money(t.actual_net - t.planned_net)),
            theme.POSITIVE if t.actual_net >= t.planned_net else theme.NEGATIVE,
        )
        self.chart.show_report(report)
        self._fill_variance(report.rows)
        self._fill_months(report)

    def _fill_variance(self, rows: tuple[VarianceRowDTO, ...]) -> None:
        self.variance_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            cells = [
                (item.name, None, None),
                (tr(_KIND_LABELS.get(item.kind, item.kind)), None, None),
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

    def _fill_months(self, report: AnnualReportDTO) -> None:
        self.months_table.setRowCount(len(report.months))
        for row, month in enumerate(report.months):
            t = month.totals
            label = f"{month_name(month.month)} {month.year}"
            if not month.has_budget:
                label += tr(" (no budget)")
            cells = [
                (label, None),
                (money(t.planned_income), _RIGHT),
                (money(t.actual_income), _RIGHT),
                (money(t.planned_expenses), _RIGHT),
                (money(t.actual_expenses), _RIGHT),
                (money(t.actual_net), _RIGHT),
            ]
            for col, (text, align) in enumerate(cells):
                cell = QTableWidgetItem(text)
                if align is not None:
                    cell.setTextAlignment(align)
                if col == 5:
                    cell.setForeground(
                        QColor(theme.POSITIVE if t.actual_net >= 0 else theme.NEGATIVE)
                    )
                if col == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, (month.year, month.month))
                self.months_table.setItem(row, col, cell)

    def _open_month(self, item: QTableWidgetItem) -> None:
        period = item.data(Qt.ItemDataRole.UserRole)
        if period:
            self.open_month.emit(*period)
