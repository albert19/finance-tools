from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QCoreApplication, QObject, QSettings, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import SimulationInput
from finance_app.bootstrap import Container, StorageKind, StorageStatus
from finance_app.presentation.budget.budget_view import BudgetView
from finance_app.presentation.budget.transactions_view import TransactionsView
from finance_app.presentation.i18n import Language, current_language, set_language, tr
from finance_app.presentation.portfolio.dialogs import SaveInvestmentDialog
from finance_app.presentation.portfolio.portfolio_view import PortfolioView
from finance_app.presentation.simulator.simulator_view import SimulatorView
from finance_app.presentation.widgets import named
from finance_app.presentation.widgets.disclaimer import DisclaimerBanner

LANGUAGE_KEY = "ui/language"


def storage_banner(storage: StorageStatus) -> str | None:
    if storage.kind is StorageKind.OFFLINE:
        return tr(
            "Offline mode: data is kept in memory only. Configure Google Sheets "
            "in {path} to persist it (see README).",
            path=storage.detail,
        )
    if storage.kind is StorageKind.ERROR:
        return tr(
            "Google Sheets unavailable ({error}). Running offline: data will not be saved.",
            error=storage.detail,
        )
    return None


def storage_label(storage: StorageStatus) -> str:
    return {
        StorageKind.SHEETS: tr("Storage: Google Sheets"),
        StorageKind.CUSTOM: tr("Storage: custom repository"),
    }.get(storage.kind, tr("Offline"))


@dataclass(frozen=True, slots=True)
class WindowState:
    """What survives a UI rebuild (e.g. when switching language)."""

    simulation: SimulationInput
    advanced: bool
    tab_index: int
    selected_investment: str | None
    geometry: QByteArray
    budget_state: tuple[int, int, int, int]
    transactions_period: tuple[int, int]
    transactions_filter: int


class MainWindow(QMainWindow):
    language_requested = Signal(str)

    def __init__(self, container: Container) -> None:
        super().__init__()
        self.setWindowTitle(tr("Finance manager"))
        self.resize(1400, 900)
        self.container = container
        self._portfolio_vm = container.portfolio_vm

        self.simulator = SimulatorView(container.simulator_vm)
        self.portfolio = PortfolioView(container.portfolio_vm)
        self.budget = BudgetView(container.budget_vm, container.categories_vm)
        self.transactions = TransactionsView(container.transactions_vm, container.categories_vm)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.simulator, tr("Simulator"))
        self.tabs.addTab(self.portfolio, tr("Portfolio"))
        self.tabs.addTab(self.budget, tr("Budget"))
        self.tabs.addTab(self.transactions, tr("Transactions"))

        central = QWidget()
        layout = QVBoxLayout(central)
        banner_text = storage_banner(container.storage)
        if banner_text:
            banner = named(QLabel(banner_text), "Banner")
            banner.setWordWrap(True)
            layout.addWidget(banner)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(DisclaimerBanner())
        self.setCentralWidget(central)
        self._build_language_menu()

        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setMaximumWidth(120)
        self.busy.hide()
        self.statusBar().addPermanentWidget(QLabel(storage_label(container.storage)))
        self.statusBar().addPermanentWidget(self.busy)

        self.simulator.save_requested.connect(self._save_investment)
        self.portfolio.open_in_simulator.connect(self._open_in_simulator)
        container.runner.busy_changed.connect(self.busy.setVisible)
        for vm in (
            container.portfolio_vm,
            container.categories_vm,
            container.budget_vm,
            container.transactions_vm,
        ):
            vm.message.connect(self._show_message)
            vm.error.connect(self._show_error)
        vm = self._portfolio_vm
        vm.created.connect(self._on_created)
        # Data entered in one section changes what the others show.
        container.transactions_vm.changed.connect(container.budget_vm.reload)
        container.categories_vm.changed.connect(self._on_categories_changed)

    def _build_language_menu(self) -> None:
        menu = self.menuBar().addMenu(tr("&Language"))
        group = QActionGroup(self)
        group.setExclusive(True)
        self.language_actions: dict[Language, QAction] = {}
        for language in Language:
            action = QAction(language.native_name, self, checkable=True)
            action.setChecked(language is current_language())
            action.triggered.connect(
                lambda _checked=False, code=language.value: self.language_requested.emit(code)
            )
            group.addAction(action)
            menu.addAction(action)
            self.language_actions[language] = action

    def _on_categories_changed(self) -> None:
        self.container.budget_vm.reload()
        self.container.transactions_vm.load()

    def _show_message(self, text: str) -> None:
        self.statusBar().showMessage(text, 5000)

    def _show_error(self, text: str) -> None:
        QMessageBox.warning(self, tr("Something went wrong"), text)

    def _on_created(self, _investment_id: str) -> None:
        self.tabs.setCurrentWidget(self.portfolio)

    def _save_investment(self, simulation: SimulationInput) -> None:
        dialog = SaveInvestmentDialog(self)
        if dialog.exec():
            name, start, notes = dialog.values()
            self._portfolio_vm.create_from_simulation(name, start, simulation, notes)

    def _open_in_simulator(self, simulation: SimulationInput) -> None:
        self.simulator.load(simulation)
        self.tabs.setCurrentWidget(self.simulator)

    def capture_state(self) -> WindowState:
        return WindowState(
            simulation=self.simulator.inputs.widget_values(),
            advanced=self.simulator.inputs.advanced.isChecked(),
            tab_index=self.tabs.currentIndex(),
            selected_investment=self._portfolio_vm.selected_id,
            geometry=self.saveGeometry(),
            budget_state=self.budget.capture_state(),
            transactions_period=self.transactions.period(),
            transactions_filter=self.transactions.filter_kind(),
        )

    def restore_state(self, state: WindowState) -> None:
        self.restoreGeometry(state.geometry)
        self.simulator.load(state.simulation, state.advanced)
        self.simulator.run_now()
        self.tabs.setCurrentIndex(state.tab_index)
        self._portfolio_vm.selected_id = state.selected_investment
        self.budget.restore_state(state.budget_state)
        self.transactions.set_filter_kind(state.transactions_filter)
        self.transactions.set_period(*state.transactions_period)


class AppController(QObject):
    """Owns the main window; rebuilds it (keeping state) when the language changes."""

    language_changed = Signal(str)

    def __init__(self, container: Container, preferences: QSettings) -> None:
        super().__init__()
        self._preferences = preferences
        stored = preferences.value(LANGUAGE_KEY)
        set_language(str(stored) if stored else container.settings.language)
        self.window = self._open(container)

    def _open(self, container: Container, state: WindowState | None = None) -> MainWindow:
        window = MainWindow(container)
        window.language_requested.connect(self.switch_language)
        if state is not None:
            window.restore_state(state)
        window.show()
        container.portfolio_vm.load()
        container.categories_vm.load()
        container.budget_vm.load_periods()
        if state is None:
            today = container.budget_vm.period
            container.budget_vm.select_period(today.year, today.month)
            container.budget_vm.select_year(today.year)
            container.transactions_vm.select_period(today.year, today.month)
        return window

    def switch_language(self, code: str) -> None:
        language = Language.parse(code)
        if language is current_language():
            return
        self._preferences.setValue(LANGUAGE_KEY, language.value)
        old = self.window
        old.container.wait_idle()
        QCoreApplication.processEvents()  # deliver pending results to the old window
        state = old.capture_state()
        set_language(language)
        self.window = self._open(old.container.rebuild(), state)
        old.close()
        old.deleteLater()
        self.language_changed.emit(language.value)
