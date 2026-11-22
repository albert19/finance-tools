from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCharts import QAbstractSeries, QChart, QChartView, QXYSeries
from PySide6.QtCore import QMargins, QPointF, Qt
from PySide6.QtGui import QCursor, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets import spanish_locale


class ChartView(QChartView):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        chart = QChart()
        chart.setTitle(tr(title))
        chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setMargins(QMargins(4, 4, 4, 4))
        chart.setLocale(spanish_locale())
        chart.setLocalizeNumbers(True)
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(280)

    def reset(self) -> QChart:
        chart = self.chart()
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)
        return chart


def show_tooltip(text: str) -> None:
    QToolTip.showText(QCursor.pos(), text)


def attach_xy_tooltip(series: QXYSeries, describe: Callable[[QPointF], str]) -> None:
    def on_hover(point: QPointF, state: bool) -> None:
        if state:
            show_tooltip(f"{series.name()}\n{describe(point)}")
        else:
            QToolTip.hideText()

    series.hovered.connect(on_hover)


def attach(chart: QChart, series: QAbstractSeries, *axes: object) -> None:
    chart.addSeries(series)
    for axis in axes:
        series.attachAxis(axis)  # type: ignore[arg-type]
