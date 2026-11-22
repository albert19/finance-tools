from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from finance_app.application.dto import SimulationInput
from finance_app.application.options import (
    CASH_FLOW_FREQUENCY_OPTIONS,
    CATEGORY_KIND_OPTIONS,
    COMPOUNDING_FREQUENCY_OPTIONS,
    CONTRIBUTION_TIMING_OPTIONS,
)
from finance_app.bootstrap import build_container
from finance_app.domain.budget.variance import VarianceStatus
from finance_app.domain.portfolio.comparison import PerformanceStatus
from finance_app.domain.portfolio.investment import InvestmentStatus
from finance_app.domain.simulation.scenarios import ScenarioSet
from finance_app.domain.simulation.value_objects import MAX_HORIZON_MONTHS
from finance_app.infrastructure.config import Settings
from finance_app.infrastructure.memory.repository import InMemoryInvestmentRepository
from finance_app.presentation.app import LANGUAGE_KEY, AppController
from finance_app.presentation.formatting import duration
from finance_app.presentation.i18n import Language, catalog, set_language, tr

SRC = Path(__file__).resolve().parents[2] / "src" / "finance_app"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _literals(paths: list[Path], match: callable) -> set[str]:  # type: ignore[valid-type]
    found: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            text = match(node)
            if text:
                found.add(text)
    return found


def _marked(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"tr", "N_"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return None


def _domain_message(node: ast.AST) -> str | None:
    """`errors[...] = "msg"` and `ValidationError.single(field, "msg")`."""
    if (
        isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Subscript)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        return node.value.value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "single"
        and len(node.args) == 2
        and isinstance(node.args[1], ast.Constant)
    ):
        return str(node.args[1].value)
    return None


def required_keys() -> set[str]:
    keys = _literals(sorted((SRC / "presentation").rglob("*.py")), _marked)
    keys |= _literals(
        sorted((SRC / "domain").rglob("*.py")) + sorted((SRC / "application").rglob("*.py")),
        _domain_message,
    )
    keys |= {
        label
        for opts in (
            CASH_FLOW_FREQUENCY_OPTIONS,
            COMPOUNDING_FREQUENCY_OPTIONS,
            CONTRIBUTION_TIMING_OPTIONS,
            CATEGORY_KIND_OPTIONS,
        )
        for _, label in opts
    }
    keys |= {s.value for s in PerformanceStatus} | set(ScenarioSet.NAMES)
    keys |= {s.value for s in VarianceStatus}
    keys |= {s.value.capitalize() for s in InvestmentStatus}
    keys.add(f"Time horizon must be between 1 month and {MAX_HORIZON_MONTHS // 12} years.")
    return keys


@pytest.fixture(autouse=True)
def english_after_test():  # type: ignore[no-untyped-def]
    yield
    set_language(Language.ENGLISH)


def test_every_ui_string_has_a_spanish_translation() -> None:
    missing = sorted(required_keys() - catalog(Language.SPANISH).keys())
    assert not missing, "Missing Spanish translations:\n" + "\n".join(missing)


def test_placeholders_match() -> None:
    for source, translated in catalog(Language.SPANISH).items():
        assert set(PLACEHOLDER.findall(source)) == set(PLACEHOLDER.findall(translated)), source


def test_tr_switches_language_and_formats() -> None:
    assert tr("Final capital") == "Final capital"
    set_language("es")
    assert tr("Final capital") == "Capital final"
    assert tr("Year {year}: {value}", year=3, value="1 €") == "Año 3: 1 €"
    assert duration(30) == "2 años 6 meses"
    assert tr("not in catalog") == "not in catalog"
    assert set_language("fr") is Language.ENGLISH


def test_switching_language_rebuilds_window_and_keeps_state(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    prefs = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    container = build_container(Settings(), InMemoryInvestmentRepository())
    controller = AppController(container, prefs)
    first = controller.window
    qtbot.addWidget(first)
    assert first.tabs.tabText(0) == "Simulator"
    first.simulator.load(SimulationInput(initial_capital=25_000, horizon_months=180))
    first.simulator.inputs.ter.setValue(0.4)  # advanced value while the group is collapsed
    assert not first.simulator.inputs.advanced.isChecked()
    before = first.simulator.inputs.widget_values()
    first.tabs.setCurrentIndex(1)
    first.budget.monthly.set_period(2024, 7)
    first.budget.annual.set_year(2024)
    first.budget.tabs.setCurrentIndex(2)
    first.transactions.picker.set_period(2025, 1, emit=True)
    first.transactions.filter.setCurrentIndex(1)

    first.language_actions[Language.SPANISH].trigger()
    second = controller.window
    qtbot.addWidget(second)
    assert second is not first
    assert second.tabs.tabText(0) == "Simulador" and second.tabs.currentIndex() == 1
    restored = second.simulator.inputs
    assert restored.to_input().initial_capital == 25_000
    assert restored.widget_values() == before and not restored.advanced.isChecked()
    assert restored.ter.value() == pytest.approx(0.4)
    assert second.budget.capture_state() == (2, 2024, 7, 2024)
    assert second.budget.tabs.tabText(0) == "Mensual"
    assert second.transactions.period() == (2025, 1)
    assert second.transactions.filter_kind() == 1
    assert second.simulator.results.cards["final_capital"]._title.text() == "Capital final"
    assert second.language_actions[Language.SPANISH].isChecked()
    assert prefs.value(LANGUAGE_KEY) == "es"

    # The stored preference is applied on the next start
    set_language(Language.ENGLISH)
    third = AppController(container.rebuild(), prefs).window
    qtbot.addWidget(third)
    assert third.tabs.tabText(1) == "Cartera"


def test_config_language_and_translated_validation_errors(qtbot: QtBot, tmp_path: Path) -> None:
    prefs = QSettings(str(tmp_path / "p.ini"), QSettings.Format.IniFormat)
    container = build_container(Settings(language="es"), InMemoryInvestmentRepository())
    window = AppController(container, prefs).window
    qtbot.addWidget(window)
    inputs = window.simulator.inputs
    inputs.initial_capital.setValue(0)
    inputs.contribution.setValue(0)
    qtbot.waitUntil(lambda: "initial_capital" in inputs.error_messages(), timeout=2000)
    assert inputs.error_messages()["initial_capital"].startswith("Introduce un capital")
