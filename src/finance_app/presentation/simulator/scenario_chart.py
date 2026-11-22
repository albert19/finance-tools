from __future__ import annotations

from PySide6.QtCharts import QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import ScenarioOutput
from finance_app.presentation import theme
from finance_app.presentation.formatting import money, number, percent
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.widgets.charts import ChartView, attach_xy_tooltip

_HEADERS = [
    N_("Scenario"),
    N_("Annual return"),
    N_("Final capital"),
    N_("After tax"),
    N_("Interest earned"),
    N_("Real value"),
    N_("IRR"),
]


class ScenarioView(QWidget):
    """Pessimistic / baseline / optimistic projections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.chart_view = ChartView("Scenario comparison (balance at year end)")
        self.table = QTableWidget(0, len(_HEADERS))
        self.table.setHorizontalHeaderLabels([tr(h) for h in _HEADERS])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(130)
        layout = QVBoxLayout(self)
        layout.addWidget(self.chart_view, 1)
        layout.addWidget(self.table)

    def show_scenarios(self, scenarios: tuple[ScenarioOutput, ...]) -> None:
        chart = self.chart_view.reset()
        x_axis = QValueAxis()
        x_axis.setTitleText(tr("Year"))
        x_axis.setLabelFormat("%.0f")
        y_axis = QValueAxis()
        y_axis.setLabelFormat("%.0f")
        y_axis.setTitleText("€")
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        top = 0.0
        for scenario, color in zip(scenarios, theme.SCENARIOS, strict=False):
            series = QLineSeries()
            series.setName(f"{tr(scenario.name)} ({percent(scenario.annual_rate_pct)})")
            pen = QPen(color)
            pen.setWidth(2)
            series.setPen(pen)
            rows = scenario.result.monthly
            series.append(0, rows[0].opening if rows else 0)
            for row in rows:
                series.append(row.index / 12, row.closing)
                top = max(top, row.closing)
            chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
            attach_xy_tooltip(
                series,
                lambda p: tr("Year {year}: {value}", year=number(p.x(), 1), value=money(p.y())),
            )
        horizon = len(scenarios[0].result.monthly) / 12 if scenarios else 1
        x_axis.setRange(0, horizon)
        y_axis.setRange(0, top * 1.05 or 1.0)
        y_axis.applyNiceNumbers()

        self.table.setRowCount(len(scenarios))
        for i, sc in enumerate(scenarios):
            s = sc.result.summary
            values = [
                tr(sc.name),
                percent(sc.annual_rate_pct),
                money(s.final_capital),
                money(s.final_capital_net),
                money(s.interest_earned),
                money(s.real_final_capital),
                percent(s.irr_pct),
            ]
            for j, text in enumerate(values):
                item = QTableWidgetItem(text)
                if j:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(i, j, item)
