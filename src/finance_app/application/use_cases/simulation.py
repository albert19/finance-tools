from __future__ import annotations

from finance_app.application.assemblers import output_from_result, params_from_input
from finance_app.application.dto import ScenarioOutput, SimulationInput, SimulationOutput
from finance_app.domain.simulation.scenarios import ScenarioSet
from finance_app.domain.simulation.simulator import CompoundInterestSimulator


class RunSimulation:
    def __init__(self, simulator: CompoundInterestSimulator) -> None:
        self._simulator = simulator

    def execute(self, data: SimulationInput) -> SimulationOutput:
        return output_from_result(self._simulator.run(params_from_input(data)))


class CompareScenarios:
    def __init__(self, simulator: CompoundInterestSimulator, scenarios: ScenarioSet) -> None:
        self._simulator = simulator
        self._scenarios = scenarios

    @property
    def delta_pct(self) -> float:
        return self._scenarios.delta

    def execute(self, data: SimulationInput) -> tuple[ScenarioOutput, ...]:
        return tuple(
            ScenarioOutput(
                name=s.name,
                annual_rate_pct=s.parameters.annual_rate.percent,
                result=output_from_result(self._simulator.run(s.parameters)),
            )
            for s in self._scenarios.build(params_from_input(data))
        )
