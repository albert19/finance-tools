from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import ScenarioOutput, SimulationInput, SimulationOutput
from finance_app.presentation.i18n import tr
from finance_app.presentation.simulator.breakdown_table import BreakdownTable
from finance_app.presentation.simulator.growth_chart import GrowthChart
from finance_app.presentation.simulator.input_panel import InputPanel
from finance_app.presentation.simulator.results_panel import ResultsPanel
from finance_app.presentation.simulator.scenario_chart import ScenarioView
from finance_app.presentation.simulator.view_model import SimulatorViewModel
from finance_app.presentation.widgets import named

DEBOUNCE_MS = 150


class SimulatorView(QWidget):
    save_requested = Signal(object)  # SimulationInput

    def __init__(self, view_model: SimulatorViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = view_model
        self.inputs = InputPanel()
        self.results = ResultsPanel()
        self.growth = GrowthChart()
        self.breakdown = BreakdownTable()
        self.scenarios = ScenarioView()
        self.status = named(QLabel(), "ErrorLabel")
        self.save_button = named(QPushButton(tr("Save as investment…")), "Primary")
        self.save_button.setToolTip(tr("Track this plan in the Portfolio tab"))

        scroll = QScrollArea()
        scroll.setWidget(self.inputs)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(430)
        scroll.setMaximumWidth(520)

        tabs = QTabWidget()
        tabs.addTab(self.growth, tr("Growth chart"))
        tabs.addTab(self.breakdown, tr("Breakdown table"))
        tabs.addTab(self.scenarios, tr("Scenarios"))

        actions = QHBoxLayout()
        actions.addWidget(self.status, 1)
        actions.addWidget(self.save_button)

        right = QVBoxLayout()
        right.addWidget(self.results)
        right.addWidget(tabs, 1)
        right.addLayout(actions)

        layout = QHBoxLayout(self)
        layout.addWidget(scroll)
        layout.addLayout(right, 1)

        self._timer = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self._timer.timeout.connect(self.run_now)
        self.inputs.changed.connect(self._timer.start)
        self._vm.simulated.connect(self._on_simulated)
        self._vm.invalid.connect(self._on_invalid)
        self.save_button.clicked.connect(self._on_save)
        self.run_now()

    def run_now(self) -> None:
        self._vm.simulate(self.inputs.to_input())

    def load(self, data: SimulationInput, advanced: bool | None = None) -> None:
        self.inputs.load_input(data, advanced)

    def _on_simulated(
        self, output: SimulationOutput, scenarios: tuple[ScenarioOutput, ...]
    ) -> None:
        self.inputs.clear_errors()
        self.status.clear()
        self.results.setEnabled(True)
        self.save_button.setEnabled(True)
        self.results.show_summary(output.summary)
        self.growth.show_rows(output.yearly)
        self.breakdown.set_rows(output.yearly, output.monthly)
        self.scenarios.show_scenarios(scenarios)

    def _on_invalid(self, errors: dict[str, str]) -> None:
        self.inputs.show_errors(errors)
        self.status.setText(tr("Fix the highlighted inputs to update the results."))
        self.results.setEnabled(False)
        self.save_button.setEnabled(False)

    def _on_save(self) -> None:
        if self._vm.last_valid_input is not None:
            self.save_requested.emit(self._vm.last_valid_input)
