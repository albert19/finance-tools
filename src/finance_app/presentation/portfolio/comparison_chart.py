from __future__ import annotations

from datetime import date

from PySide6.QtCharts import QDateTimeAxis, QLineSeries, QScatterSeries, QValueAxis
from PySide6.QtCore import QDate, QDateTime, QPointF, Qt, QTime
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QWidget

from finance_app.application.dates import add_months
from finance_app.application.dto import InvestmentDetailDTO
from finance_app.presentation import theme
from finance_app.presentation.formatting import money
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.charts import ChartView, attach_xy_tooltip


def _msecs(value: date) -> float:
    return float(
        QDateTime(QDate(value.year, value.month, value.day), QTime(0, 0)).toMSecsSinceEpoch()
    )


def _date_label(point: QPointF) -> str:
    return QDateTime.fromMSecsSinceEpoch(int(point.x())).toString("dd/MM/yyyy")


def _line(name: str, color: QColor, dashed: bool = False, width: int = 2) -> QLineSeries:
    series = QLineSeries()
    series.setName(name)
    pen = QPen(color)
    pen.setWidth(width)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    series.setPen(pen)
    return series


class ComparisonChart(ChartView):
    """Projected balance (from the original simulation) vs. actual snapshots."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Projected vs. actual performance", parent)

    def show_detail(self, detail: InvestmentDetailDTO, full_horizon: bool) -> None:
        chart = self.reset()
        end = detail.projection[-1][0]
        if not full_horizon:
            last = detail.snapshots[-1].date if detail.snapshots else detail.summary.start_date
            end = min(end, max(add_months(last, 6), add_months(detail.summary.start_date, 12)))

        projected = _line(tr("Projected balance"), theme.CONTRIBUTED)
        contributed = _line(tr("Projected contributions"), theme.CONTRIBUTED, dashed=True, width=1)
        for (day, value), (_, basis) in zip(
            detail.projection, detail.projection_contributed, strict=True
        ):
            if day <= end:
                projected.append(_msecs(day), value)
                contributed.append(_msecs(day), basis)

        actual = _line(tr("Actual value"), theme.ACTUAL, width=3)
        actual_contrib = _line(tr("Actual contributions"), theme.ACTUAL, dashed=True, width=1)
        markers = QScatterSeries()
        markers.setName(tr("Snapshots"))
        markers.setColor(theme.ACTUAL)
        markers.setMarkerSize(9)
        start = detail.summary.start_date
        actual.append(_msecs(start), detail.parameters.initial_capital)
        actual_contrib.append(_msecs(start), detail.parameters.initial_capital)
        for snap in detail.snapshots:
            actual.append(_msecs(snap.date), snap.market_value)
            actual_contrib.append(_msecs(snap.date), snap.contributed_actual)
            markers.append(_msecs(snap.date), snap.market_value)

        x_axis = QDateTimeAxis()
        x_axis.setFormat("MM/yyyy")
        x_axis.setTitleText(tr("Date"))
        y_axis = QValueAxis()
        y_axis.setLabelFormat("%.0f")
        y_axis.setTitleText("€")
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        all_series = (projected, contributed, actual, actual_contrib, markers)
        for series in all_series:
            chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
            attach_xy_tooltip(series, lambda p: f"{_date_label(p)}: {money(p.y())}")

        values = [p.y() for s in all_series for p in s.points()]
        x_axis.setRange(
            QDateTime.fromMSecsSinceEpoch(int(_msecs(start))),
            QDateTime.fromMSecsSinceEpoch(int(_msecs(end))),
        )
        y_axis.setRange(min(0.0, *values) if values else 0.0, max(values, default=1.0) * 1.05)
        y_axis.applyNiceNumbers()
