from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from finance_app.application.dto import SimulationInput
from finance_app.application.use_cases.simulation import CompareScenarios, RunSimulation
from finance_app.domain.shared.errors import ValidationError


class SimulatorViewModel(QObject):
    """Runs simulations and exposes results / validation errors as signals."""

    simulated = Signal(object, object)  # SimulationOutput, tuple[ScenarioOutput, ...]
    invalid = Signal(dict)

    def __init__(self, run: RunSimulation, compare: CompareScenarios) -> None:
        super().__init__()
        self._run = run
        self._compare = compare
        self.last_valid_input: SimulationInput | None = None

    def simulate(self, data: SimulationInput) -> None:
        try:
            output = self._run.execute(data)
            scenarios = self._compare.execute(data)
        except ValidationError as exc:
            self.last_valid_input = None
            self.invalid.emit(exc.errors)
            return
        self.last_valid_input = data
        self.simulated.emit(output, scenarios)
