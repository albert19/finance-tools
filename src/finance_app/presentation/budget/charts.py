from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QHorizontalBarSeries,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QToolTip, QWidget

from finance_app.application.dto import AnnualReportDTO, MonthTotalsDTO, VarianceRowDTO
from finance_app.presentation import theme
from finance_app.presentation.budget.period_picker import MONTH_NAMES
from finance_app.presentation.formatting import money, percent
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.charts import ChartView, attach_xy_tooltip, show_tooltip


def _slice_hover(state: bool, text: str) -> None:
    if state:
        show_tooltip(text)
    else:
        QToolTip.hideText()


class BudgetVsActualChart(ChartView):
    """Horizontal grouped bars per category: planned vs. actual."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Planned vs. actual by category", parent)

    def show_rows(self, rows: tuple[VarianceRowDTO, ...]) -> None:
        chart = self.reset()
        rows = tuple(r for r in reversed(rows) if r.planned or r.actual)
        planned = QBarSet(tr("Planned"))
        actual = QBarSet(tr("Actual"))
        planned.setColor(theme.CONTRIBUTED)
        actual.setColor(theme.REAL_VALUE)
        for row in rows:
            planned.append(row.planned)
            actual.append(row.actual)
        series = QHorizontalBarSeries()
        series.append([planned, actual])
        series.hovered.connect(self._hover(rows))
        categories = QBarCategoryAxis()
        categories.append([r.name for r in rows])
        values = QValueAxis()
        values.setLabelFormat("%.0f")
        values.setTitleText("€")
        chart.addAxis(categories, Qt.AlignmentFlag.AlignLeft)
        chart.addAxis(values, Qt.AlignmentFlag.AlignBottom)
        chart.addSeries(series)
        series.attachAxis(categories)
        series.attachAxis(values)
        top = max((max(r.planned, r.actual) for r in rows), default=0.0)
        values.setRange(0.0, top * 1.05 or 1.0)
        values.applyNiceNumbers()

    @staticmethod
    def _hover(rows: tuple[VarianceRowDTO, ...]) -> Callable[[bool, int, QBarSet], None]:
        def on_hover(status: bool, index: int, barset: QBarSet) -> None:
            if not status or index >= len(rows):
                QToolTip.hideText()
                return
            row = rows[index]
            show_tooltip(
                tr(
                    "{name}\nPlanned: {planned}\nActual: {actual}\nVariance: {variance}",
                    name=row.name,
                    planned=money(row.planned),
                    actual=money(row.actual),
                    variance=money(row.variance),
                )
            )

        return on_hover


class ExpenseDonutChart(ChartView):
    """Donut of the month's actual expenses by category."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Actual expenses by category", parent)

    def show_rows(self, rows: tuple[VarianceRowDTO, ...]) -> None:
        chart = self.reset()
        series = QPieSeries()
        series.setHoleSize(0.45)
        expenses = [r for r in rows if r.kind == "expense" and r.actual > 0]
        total = sum(r.actual for r in expenses)
        for row in expenses:
            slice_ = series.append(row.name, row.actual)
            slice_.setLabelVisible(False)
            share = row.actual / total if total else 0.0
            text = f"{row.name}\n{money(row.actual)} · {percent(share * 100)}"
            slice_.hovered.connect(lambda state, t=text: _slice_hover(state, t))
        chart.addSeries(series)


class AnnualTrendChart(ChartView):
    """Grouped planned vs. actual bars per month plus the actual net line."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Year overview: planned vs. actual per month", parent)

    def show_report(self, report: AnnualReportDTO) -> None:
        chart = self.reset()
        months = report.months
        income_planned = QBarSet(tr("Planned income"))
        income_actual = QBarSet(tr("Actual income"))
        expense_planned = QBarSet(tr("Planned expenses"))
        expense_actual = QBarSet(tr("Actual expenses"))
        income_planned.setColor(theme.PLANNED_INCOME)
        income_actual.setColor(theme.INCOME)
        expense_planned.setColor(theme.PLANNED_EXPENSE)
        expense_actual.setColor(theme.EXPENSE)
        net = QLineSeries()
        net.setName(tr("Actual net"))
        net.setPen(QPen(theme.NET, 2))
        for i, month in enumerate(months):
            t = month.totals
            income_planned.append(t.planned_income)
            income_actual.append(t.actual_income)
            expense_planned.append(-t.planned_expenses)
            expense_actual.append(-t.actual_expenses)
            net.append(i, t.actual_net)
        series = QBarSeries()
        series.append([income_planned, income_actual, expense_planned, expense_actual])
        series.hovered.connect(self._hover(months))
        categories = QBarCategoryAxis()
        categories.append([tr(MONTH_NAMES[m.month - 1])[:3] for m in months])
        categories.setTitleText(tr("Month"))
        values = QValueAxis()
        values.setLabelFormat("%.0f")
        values.setTitleText("€")
        chart.addAxis(categories, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(values, Qt.AlignmentFlag.AlignLeft)
        chart.addSeries(series)
        series.attachAxis(categories)
        series.attachAxis(values)
        chart.addSeries(net)
        net.attachAxis(categories)
        net.attachAxis(values)
        attach_xy_tooltip(
            net,
            lambda p: tr(
                "{month}: {value}",
                month=tr(MONTH_NAMES[round(p.x())]),
                value=money(p.y()),
            ),
        )
        top = max(
            (
                max(
                    m.totals.planned_income,
                    m.totals.actual_income,
                    m.totals.actual_net,
                )
                for m in months
            ),
            default=0.0,
        )
        bottom = min(
            (
                min(-m.totals.planned_expenses, -m.totals.actual_expenses, m.totals.actual_net)
                for m in months
            ),
            default=0.0,
        )
        values.setRange(bottom * 1.05, top * 1.05 or 1.0)
        values.applyNiceNumbers()

    @staticmethod
    def _hover(months: tuple[MonthTotalsDTO, ...]) -> Callable[[bool, int, QBarSet], None]:
        def on_hover(status: bool, index: int, barset: QBarSet) -> None:
            if not status or index >= len(months):
                QToolTip.hideText()
                return
            show_tooltip(
                f"{tr(MONTH_NAMES[months[index].month - 1])} {months[index].year}\n"
                f"{barset.label()}: {money(abs(barset.at(index)))}"
            )

        return on_hover
