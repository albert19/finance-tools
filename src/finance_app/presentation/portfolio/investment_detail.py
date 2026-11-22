from __future__ import annotations

from PySide6.QtCore import Qt, Signal, SignalInstance
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import InvestmentDetailDTO, SnapshotDTO
from finance_app.presentation import theme
from finance_app.presentation.formatting import (
    duration,
    money,
    percent,
    short_date,
    signed_money,
)
from finance_app.presentation.i18n import N_, tr
from finance_app.presentation.portfolio.comparison_chart import ComparisonChart
from finance_app.presentation.widgets import named
from finance_app.presentation.widgets.kpi import KpiGrid

_KPIS = [
    ("expected", N_("Expected annual rate"), N_("Money-weighted rate of the original projection.")),
    (
        "actual_rate",
        N_("Actual annual rate (XIRR)"),
        N_("Money-weighted return of your real cash flows."),
    ),
    ("projected", N_("Projected at last snapshot"), ""),
    ("actual", N_("Actual value"), ""),
    ("deviation", N_("Deviation"), N_("Actual − projected at the latest snapshot.")),
    ("status", N_("Status"), N_("Within ±tolerance of the plan counts as on track.")),
    ("final", N_("Projected final capital"), ""),
    ("plan", N_("Plan"), ""),
]
_SNAP_HEADERS = [
    N_("Date"),
    N_("Market value"),
    N_("Contributed"),
    N_("Withdrawn"),
    N_("Projected"),
    N_("Deviation"),
    N_("Deviation %"),
    N_("Note"),
]
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class InvestmentDetail(QWidget):
    add_snapshot = Signal()
    edit_snapshot = Signal(object)  # SnapshotDTO
    delete_snapshot = Signal(object)  # SnapshotDTO
    open_in_simulator = Signal(object)  # SimulationInput
    toggle_status = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.detail: InvestmentDetailDTO | None = None
        self.title = named(QLabel(), "SectionTitle")
        self.subtitle = named(QLabel(), "KpiHint")
        self.kpis = KpiGrid(_KPIS, columns=4)
        self.chart = ComparisonChart()
        self.full_horizon = QCheckBox(tr("Show full horizon"))
        self.table = QTableWidget(0, len(_SNAP_HEADERS))
        self.table.setHorizontalHeaderLabels([tr(h) for h in _SNAP_HEADERS])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.add_button = named(QPushButton(tr("Add snapshot…")), "Primary")
        self.edit_button = QPushButton(tr("Edit"))
        self.delete_button = QPushButton(tr("Delete"))
        self.simulate_button = QPushButton(tr("Open in simulator"))
        self.status_button = QPushButton(tr("Close investment"))

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        header.addWidget(self.simulate_button)
        header.addWidget(self.status_button)

        chart_bar = QHBoxLayout()
        chart_bar.addStretch(1)
        chart_bar.addWidget(self.full_horizon)

        actions = QHBoxLayout()
        actions.addWidget(QLabel(tr("<b>Performance snapshots</b>")))
        actions.addStretch(1)
        actions.addWidget(self.add_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.kpis)
        layout.addLayout(chart_bar)
        layout.addWidget(self.chart, 3)
        layout.addLayout(actions)
        layout.addWidget(self.table, 2)

        self.add_button.clicked.connect(self.add_snapshot)
        self.edit_button.clicked.connect(lambda: self._emit_selected(self.edit_snapshot))
        self.delete_button.clicked.connect(lambda: self._emit_selected(self.delete_snapshot))
        self.table.doubleClicked.connect(lambda _: self._emit_selected(self.edit_snapshot))
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.simulate_button.clicked.connect(
            lambda: self.detail and self.open_in_simulator.emit(self.detail.parameters)
        )
        self.status_button.clicked.connect(self.toggle_status)
        self.full_horizon.toggled.connect(self._redraw_chart)
        self._update_buttons()

    def selected_snapshot(self) -> SnapshotDTO | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or self.detail is None:
            return None
        return self.detail.snapshots[rows[0].row()]

    def _emit_selected(self, signal: SignalInstance) -> None:
        snapshot = self.selected_snapshot()
        if snapshot is not None:
            signal.emit(snapshot)

    def _update_buttons(self) -> None:
        has = self.selected_snapshot() is not None
        self.edit_button.setEnabled(has)
        self.delete_button.setEnabled(has)

    def _redraw_chart(self) -> None:
        if self.detail is not None:
            self.chart.show_detail(self.detail, self.full_horizon.isChecked())

    def show_detail(self, detail: InvestmentDetailDTO) -> None:
        self.detail = detail
        s, p = detail.summary, detail.parameters
        self.title.setText(s.name)
        self.subtitle.setText(
            tr(
                "Started {start} · {initial} initial · {contribution} {frequency} · "
                "{rate} expected · {horizon}",
                start=short_date(s.start_date),
                initial=money(p.initial_capital),
                contribution=money(p.contribution),
                frequency=tr(p.contribution_frequency.capitalize()).lower(),
                rate=percent(p.annual_rate_pct),
                horizon=duration(p.horizon_months),
            )
            + (f" · {detail.notes}" if detail.notes else "")
        )
        self.status_button.setText(
            tr("Reopen investment") if s.status == "closed" else tr("Close investment")
        )
        k = self.kpis.cards
        k["expected"].set_value(percent(s.expected_rate_pct))
        rate_color = None
        if detail.actual_xirr_pct is not None:
            rate_color = (
                theme.POSITIVE if detail.actual_xirr_pct >= s.expected_rate_pct else theme.NEGATIVE
            )
        k["actual_rate"].set_value(percent(detail.actual_xirr_pct), color=rate_color)
        k["projected"].set_value(money(s.projected_at_latest), short_date(s.latest_date))
        k["actual"].set_value(money(s.latest_value))
        latest = detail.snapshots[-1] if detail.snapshots else None
        color = None
        if latest is not None:
            color = theme.POSITIVE if latest.deviation >= 0 else theme.NEGATIVE
        k["deviation"].set_value(
            signed_money(latest.deviation) if latest else "—",
            percent(s.deviation_pct, signed=True) if latest else "",
            color,
        )
        status_colors = {"Ahead of plan": theme.POSITIVE, "Behind plan": theme.NEGATIVE}
        k["status"].set_value(tr(s.performance), color=status_colors.get(s.performance))
        k["final"].set_value(money(detail.projected_final), duration(p.horizon_months))
        k["plan"].set_value(
            tr(s.status.capitalize()), tr("{n} snapshot(s)", n=len(detail.snapshots))
        )

        self.table.setRowCount(len(detail.snapshots))
        for row, snap in enumerate(detail.snapshots):
            cells = [
                short_date(snap.date),
                money(snap.market_value),
                money(snap.contribution),
                money(snap.withdrawal),
                money(snap.projected),
                signed_money(snap.deviation),
                percent(snap.deviation_pct, signed=True),
                snap.note,
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if 0 < col < 7:
                    item.setTextAlignment(_RIGHT)
                if col in (5, 6):
                    item.setForeground(
                        QColor(theme.POSITIVE if snap.deviation >= 0 else theme.NEGATIVE)
                    )
                self.table.setItem(row, col, item)
        self._update_buttons()
        self._redraw_chart()
