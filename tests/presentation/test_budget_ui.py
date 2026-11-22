from __future__ import annotations

from datetime import date

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from finance_app.application.dto import BudgetLineInput, TransactionInput
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


def _seed(window: tuple[MainWindow, Container], qtbot: QtBot) -> tuple[str, str]:
    win, container = window
    vm = container.categories_vm
    vm.seed_defaults(["Salary"], ["Groceries"])
    qtbot.waitUntil(lambda: len(vm.categories) >= 2, timeout=3000)
    kinds = {c.name: c for c in vm.categories}
    return kinds["Salary"].id, kinds["Groceries"].id


def _wait_monthly(qtbot: QtBot, win: MainWindow) -> None:
    qtbot.waitUntil(lambda: win.budget.monthly.report is not None, timeout=3000)


def test_budget_flow(qtbot: QtBot, window: tuple[MainWindow, Container]) -> None:
    win, container = window
    income, expense = _seed(window, qtbot)

    # Monthly view shows the empty state before a budget exists
    vm = container.budget_vm
    vm.select_period(2025, 3)
    _wait_monthly(qtbot, win)
    assert win.budget.monthly.report.budget is None
    assert win.budget.monthly.stack.currentIndex() == 0

    # Create a budget with two lines in the expense category plus an income line
    vm.create_budget()
    qtbot.waitUntil(
        lambda: (
            win.budget.monthly.report is not None and win.budget.monthly.report.budget is not None
        ),
        timeout=3000,
    )
    budget_id = win.budget.monthly.report.budget.id  # type: ignore[union-attr]
    vm.save_line(budget_id, BudgetLineInput(expense, 500, "weekly shop"))
    vm.save_line(budget_id, BudgetLineInput(expense, 50, "market"))
    vm.save_line(budget_id, BudgetLineInput(income, 3000, "paycheck"))
    qtbot.waitUntil(
        lambda: (
            win.budget.monthly.report.budget is not None
            and len(win.budget.monthly.report.budget.lines) == 3
        ),
        timeout=3000,
    )
    assert win.budget.monthly.income_table.rowCount() == 1
    assert win.budget.monthly.expense_table.rowCount() == 2

    # Record transactions and check variance
    tx_vm = container.transactions_vm
    tx_vm.select_period(2025, 3)
    tx_vm.record(TransactionInput(date(2025, 3, 2), expense, 400, "shop"))
    tx_vm.record(TransactionInput(date(2025, 3, 3), income, 3100, "paycheck"))
    qtbot.waitUntil(
        lambda: (
            win.budget.monthly.report is not None
            and len(win.budget.monthly.report.transactions) == 2
        ),
        timeout=3000,
    )
    report = win.budget.monthly.report
    rows = {r.category_id: r for r in report.rows}
    assert rows[expense].planned == 550 and rows[expense].actual == 400
    assert rows[expense].status == "Favorable"
    assert rows[income].actual == 3100
    assert report.totals.actual_net == pytest.approx(2700)
    assert win.budget.monthly.kpis.cards["planned_income"].value_text == "3.000,00 €"
    assert win.budget.monthly.variance_table.rowCount() == len(report.rows)
    assert win.budget.monthly.budget_chart.chart().series()

    # Transactions view lists entries and totals
    tx_view = win.transactions
    qtbot.waitUntil(lambda: tx_view.table.rowCount() == 2, timeout=3000)
    assert "2.700" in tx_view.totals.text()

    # Annual view rolls the month up
    vm.select_year(2025)
    qtbot.waitUntil(
        lambda: win.budget.annual.report is not None and win.budget.annual.report.year == 2025,
        timeout=3000,
    )
    annual = win.budget.annual.report
    assert annual.totals.planned_income == pytest.approx(3000)
    march = annual.months[2]
    assert march.has_budget and march.totals.actual_expenses == pytest.approx(400)
    assert win.budget.annual.months_table.rowCount() == 12

    # Copy to next month
    vm.select_period(2025, 4)
    _wait_monthly(qtbot, win)
    vm.create_budget(copy_from=(2025, 3))
    qtbot.waitUntil(
        lambda: (
            win.budget.monthly.report is not None
            and win.budget.monthly.report.budget is not None
            and win.budget.monthly.report.budget.year == 2025
            and win.budget.monthly.report.budget.month == 4
            and len(win.budget.monthly.report.budget.lines) == 3
        ),
        timeout=3000,
    )


def test_delete_flows(
    qtbot: QtBot, window: tuple[MainWindow, Container], monkeypatch: pytest.MonkeyPatch
) -> None:
    win, container = window
    income, _ = _seed(window, qtbot)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    vm = container.budget_vm
    vm.select_period(2025, 3)
    vm.create_budget()
    qtbot.waitUntil(
        lambda: (
            win.budget.monthly.report is not None and win.budget.monthly.report.budget is not None
        ),
        timeout=3000,
    )
    budget_id = win.budget.monthly.report.budget.id  # type: ignore[union-attr]

    tx_vm = container.transactions_vm
    tx_vm.select_period(2025, 3)
    tx_vm.record(TransactionInput(date(2025, 3, 2), income, 100))
    qtbot.waitUntil(lambda: win.transactions.table.rowCount() == 1, timeout=3000)
    win.transactions.table.selectRow(0)
    win.transactions.delete_button.click()
    qtbot.waitUntil(lambda: win.transactions.table.rowCount() == 0, timeout=3000)

    vm.delete_budget(budget_id)
    qtbot.waitUntil(
        lambda: win.budget.monthly.report is not None and win.budget.monthly.report.budget is None,
        timeout=3000,
    )

    # Category in use by a transaction cannot be deleted
    tx_vm.record(TransactionInput(date(2025, 3, 2), income, 100))
    qtbot.waitUntil(lambda: win.transactions.table.rowCount() == 1, timeout=3000)
    errors: list[str] = []
    container.categories_vm.error.connect(errors.append)
    container.categories_vm.delete(income)
    qtbot.waitUntil(lambda: bool(errors), timeout=3000)
    assert "cannot be deleted" in errors[0]
