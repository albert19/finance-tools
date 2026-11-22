from __future__ import annotations

from datetime import date

import pytest

from finance_app.application.assemblers import input_from_params, params_from_input
from finance_app.application.dates import add_months
from finance_app.application.dto import SimulationInput, SnapshotInput
from finance_app.application.use_cases.portfolio import (
    CreateInvestmentFromSimulation,
    DeleteInvestment,
    DeleteSnapshot,
    GetInvestmentDetail,
    ListInvestments,
    RecordSnapshot,
    UpdateInvestment,
)
from finance_app.application.use_cases.simulation import CompareScenarios, RunSimulation
from finance_app.domain.portfolio.comparison import PerformanceComparator
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.domain.simulation.scenarios import ScenarioSet
from finance_app.domain.simulation.simulator import CompoundInterestSimulator
from finance_app.domain.simulation.tax_policy import spanish_savings_policy
from finance_app.infrastructure.memory.repository import InMemoryInvestmentRepository

SIM = CompoundInterestSimulator(spanish_savings_policy())


@pytest.fixture
def repo() -> InMemoryInvestmentRepository:
    return InMemoryInvestmentRepository()


def test_run_simulation_returns_percentages() -> None:
    out = RunSimulation(SIM).execute(SimulationInput(horizon_months=120))
    assert len(out.yearly) == 10 and len(out.monthly) == 120
    assert out.summary.irr_pct == pytest.approx(6.17, abs=0.01)


def test_validation_collects_all_errors() -> None:
    data = SimulationInput(
        initial_capital=-1, ter_pct=-2, horizon_months=0, compounding_frequency="weekly"
    )
    with pytest.raises(ValidationError) as exc:
        RunSimulation(SIM).execute(data)
    assert {"initial_capital", "ter", "horizon_months", "compounding_frequency"} <= set(
        exc.value.errors
    )


def test_input_roundtrip() -> None:
    data = SimulationInput(
        withdrawal_amount=500,
        withdrawal_start_month=60,
        apply_taxes=True,
        ter_pct=0.2,
        inflation_pct=2,
    )
    back = input_from_params(params_from_input(data))
    assert back.withdrawal_amount == 500 and back.withdrawal_start_month == 60
    assert back.ter_pct == pytest.approx(0.2) and back.apply_taxes


def test_compare_scenarios_ordered() -> None:
    outs = CompareScenarios(SIM, ScenarioSet(2)).execute(SimulationInput())
    finals = [o.result.summary.final_capital for o in outs]
    assert finals == sorted(finals)
    assert [o.annual_rate_pct for o in outs] == pytest.approx([4, 6, 8])


def test_portfolio_lifecycle(repo: InMemoryInvestmentRepository) -> None:
    comparator = PerformanceComparator(SIM)
    inv_id = CreateInvestmentFromSimulation(repo).execute(
        "Index fund", date(2024, 1, 15), SimulationInput(horizon_months=120)
    )
    snap_id = RecordSnapshot(repo).execute(
        inv_id, SnapshotInput(date(2024, 7, 15), 11_500, contribution=1_200)
    )
    RecordSnapshot(repo).execute(inv_id, SnapshotInput(date(2025, 1, 15), 12_900, 1_200))

    [summary] = ListInvestments(repo, comparator).execute()
    assert summary.latest_value == 12_900 and summary.deviation_pct is not None

    detail = GetInvestmentDetail(repo, comparator).execute(inv_id)
    assert len(detail.projection) == 121
    assert detail.projection[12][0] == date(2025, 1, 15)
    assert len(detail.snapshots) == 2 and detail.actual_xirr_pct is not None

    RecordSnapshot(repo).execute(inv_id, SnapshotInput(date(2024, 7, 15), 11_000, 1_200), snap_id)
    detail = GetInvestmentDetail(repo, comparator).execute(inv_id)
    assert detail.snapshots[0].market_value == 11_000

    DeleteSnapshot(repo).execute(inv_id, snap_id)
    UpdateInvestment(repo).execute(inv_id, name="Renamed", status="closed")
    detail = GetInvestmentDetail(repo, comparator).execute(inv_id)
    assert detail.summary.name == "Renamed" and detail.summary.status == "closed"
    assert len(detail.snapshots) == 1

    DeleteInvestment(repo).execute(inv_id)
    with pytest.raises(NotFoundError):
        GetInvestmentDetail(repo, comparator).execute(inv_id)


def test_add_months_clamps_day() -> None:
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2024, 11, 30), 14) == date(2026, 1, 30)
