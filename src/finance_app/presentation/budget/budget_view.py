from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from finance_app.presentation.budget.annual_view import AnnualView
from finance_app.presentation.budget.category_manager import CategoryManagerView
from finance_app.presentation.budget.monthly_view import MonthlyView
from finance_app.presentation.budget.view_model import BudgetViewModel, CategoriesViewModel
from finance_app.presentation.i18n import tr


class BudgetView(QWidget):
    """Budget section: monthly plan & variance, annual roll-up, category manager."""

    def __init__(
        self,
        budget_vm: BudgetViewModel,
        categories_vm: CategoriesViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = budget_vm
        self.monthly = MonthlyView(budget_vm, categories_vm)
        self.annual = AnnualView(budget_vm)
        self.categories = CategoryManagerView(categories_vm)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.monthly, tr("Monthly"))
        self.tabs.addTab(self.annual, tr("Annual"))
        self.tabs.addTab(self.categories, tr("Categories"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.tabs)

        self.annual.open_month.connect(self._open_month)

    def _open_month(self, year: int, month: int) -> None:
        self.tabs.setCurrentWidget(self.monthly)
        self.monthly.set_period(year, month)

    def capture_state(self) -> tuple[int, int, int, int]:
        """(sub-tab index, budget year, budget month, annual year)."""
        year, month = self.monthly.period()
        return (self.tabs.currentIndex(), year, month, self.annual.year())

    def restore_state(self, state: tuple[int, int, int, int]) -> None:
        tab_index, year, month, annual_year = state
        self.tabs.setCurrentIndex(tab_index)
        self.annual.set_year(annual_year)
        self.monthly.set_period(year, month)
