from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCharts import QBarCategoryAxis, QBarSet, QLineSeries, QStackedBarSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QToolTip, QWidget

from finance_app.application.dto import RowDTO
from finance_app.presentation import theme
from finance_app.presentation.formatting import money
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.charts import ChartView, attach_xy_tooltip, show_tooltip


class GrowthChart(ChartView):
    """Stacked bars (own capital vs interest) per year plus the inflation-adjusted value."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Growth: contributed capital vs. interest (year end)", parent)

    def show_rows(self, rows: tuple[RowDTO, ...]) -> None:
        chart = self.reset()
        contributed = QBarSet(tr("Contributed capital"))
        interest = QBarSet(tr("Interest"))
        contributed.setColor(theme.CONTRIBUTED)
        interest.setColor(theme.INTEREST)
        for row in rows:
            contributed.append(row.cost_basis)
            interest.append(row.gains)
        bars = QStackedBarSeries()
        bars.append([contributed, interest])
        bars.setBarWidth(0.8)
        bars.hovered.connect(_bar_hover(rows))

        categories = QBarCategoryAxis()
        categories.append([str(r.index) for r in rows])
        categories.setTitleText(tr("Year"))
        if len(rows) > 30:
            categories.setLabelsAngle(-90)
        values = QValueAxis()
        values.setLabelFormat("%.0f")
        values.setTitleText("€")
        chart.addAxis(categories, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(values, Qt.AlignmentFlag.AlignLeft)
        chart.addSeries(bars)
        bars.attachAxis(categories)
        bars.attachAxis(values)

        real = QLineSeries()
        real.setName(tr("Inflation-adjusted value"))
        pen = QPen(theme.REAL_VALUE)
        pen.setWidth(2)
        real.setPen(pen)
        for i, row in enumerate(rows):
            real.append(i, row.real_closing)
        chart.addSeries(real)
        real.attachAxis(categories)
        real.attachAxis(values)
        attach_xy_tooltip(
            real, lambda p: tr("Year {year}: {value}", year=round(p.x()) + 1, value=money(p.y()))
        )

        top = max((max(r.closing, r.cost_basis) for r in rows), default=0.0)
        bottom = min((min(r.gains, 0.0) for r in rows), default=0.0)
        values.setRange(bottom, top * 1.05 or 1.0)
        values.applyNiceNumbers()


def _bar_hover(rows: tuple[RowDTO, ...]) -> Callable[[bool, int, QBarSet], None]:
    def on_hover(status: bool, index: int, _barset: QBarSet) -> None:
        if not status or index >= len(rows):
            QToolTip.hideText()
            return
        r = rows[index]
        show_tooltip(
            tr(
                "Year {year}\nContributed: {contributed}\nInterest: {interest}\nBalance: {balance}",
                year=r.index,
                contributed=money(r.cost_basis),
                interest=money(r.gains),
                balance=money(r.closing),
            )
        )

    return on_hover
