from __future__ import annotations

from datetime import date

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from finance_app.application.dto import SimulationInput, SnapshotInput
from finance_app.bootstrap import Container, build_container
from finance_app.infrastructure.config import Settings
from finance_app.infrastructure.memory.repository import InMemoryInvestmentRepository
from finance_app.presentation.app import MainWindow


@pytest.fixture
def window(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> tuple[MainWindow, Container]:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    container = build_container(Settings(), InMemoryInvestmentRepository())
    win = MainWindow(container)
    qtbot.addWidget(win)
    return win, container


def test_slider_change_updates_results(qtbot: QtBot, window: tuple[MainWindow, Container]) -> None:
    win, _ = window
    card = win.simulator.results.cards["final_capital"]
    before = card.value_text
    win.simulator.inputs.annual_rate.slider.setValue(1000)  # 10.00 %
    qtbot.waitUntil(lambda: card.value_text != before, timeout=2000)
    assert win.simulator.inputs.annual_rate.spin.value() == pytest.approx(10.0)
    assert win.simulator.save_button.isEnabled()


def test_invalid_input_shows_error(qtbot: QtBot, window: tuple[MainWindow, Container]) -> None:
    win, _ = window
    inputs = win.simulator.inputs
    inputs.initial_capital.setValue(0)
    inputs.contribution.setValue(0)
    qtbot.waitUntil(lambda: not win.simulator.save_button.isEnabled(), timeout=2000)
    assert "initial_capital" in inputs.error_messages()


def test_advanced_inputs_reach_simulation(window: tuple[MainWindow, Container]) -> None:
    win, _ = window
    inputs = win.simulator.inputs
    assert inputs.to_input().ter_pct == 0
    inputs.advanced.setChecked(True)
    inputs.ter.setValue(0.5)
    inputs.horizon_unit.setCurrentIndex(1)
    data = inputs.to_input()
    assert data.ter_pct == pytest.approx(0.5) and data.apply_taxes
    assert data.horizon_months == 240 and inputs.horizon.value() == 240


def test_load_input_roundtrip(window: tuple[MainWindow, Container]) -> None:
    win, _ = window
    data = SimulationInput(
        initial_capital=5_000,
        horizon_months=18,
        ter_pct=0.3,
        withdrawal_amount=0,
        apply_taxes=True,
        compounding_frequency="daily",
    )
    win.simulator.load(data)
    assert win.simulator.inputs.to_input() == data


def test_portfolio_flow(qtbot: QtBot, window: tuple[MainWindow, Container]) -> None:
    win, container = window
    vm = container.portfolio_vm
    assert win.portfolio.stack.currentIndex() == 0  # empty state before load
    vm.create_from_simulation("Test fund", date(2024, 1, 1), SimulationInput())
    qtbot.waitUntil(lambda: win.portfolio.list.rowCount() == 1, timeout=3000)
    qtbot.waitUntil(lambda: win.portfolio.detail.detail is not None, timeout=3000)
    assert win.portfolio.stack.currentIndex() == 1
    inv_id = win.portfolio.detail.detail.summary.id  # type: ignore[union-attr]

    vm.record_snapshot(inv_id, SnapshotInput(date(2024, 12, 31), 13_000, 2_400))
    qtbot.waitUntil(
        lambda: bool(win.portfolio.detail.detail and win.portfolio.detail.detail.snapshots),
        timeout=3000,
    )
    assert win.portfolio.detail.table.rowCount() == 1
    assert win.portfolio.detail.kpis.cards["actual"].value_text == "13.000,00 €"
    assert win.portfolio.list.item(0, 3).text() == "13.000,00 €"

    errors: list[str] = []
    vm.error.connect(errors.append)
    vm.record_snapshot(inv_id, SnapshotInput(date(2023, 1, 1), 1))
    qtbot.waitUntil(lambda: bool(errors), timeout=3000)
    assert "before the investment start" in errors[0]

    vm.delete_investment(inv_id)
    qtbot.waitUntil(lambda: win.portfolio.stack.currentIndex() == 0, timeout=3000)
