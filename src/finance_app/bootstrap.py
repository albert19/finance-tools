"""Composition root: wires settings, infrastructure, use cases and view models."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from finance_app.application.use_cases.budgets import (
    CreateMonthlyBudget,
    DeleteBudgetLine,
    DeleteMonthlyBudget,
    GetMonthlyBudget,
    ListBudgetPeriods,
    SaveBudgetLine,
    UpdateMonthlyBudget,
)
from finance_app.application.use_cases.categories import (
    CreateCategory,
    DeleteCategory,
    ListCategories,
    SeedDefaultCategories,
    UpdateCategory,
)
from finance_app.application.use_cases.portfolio import (
    CreateInvestmentFromSimulation,
    DeleteInvestment,
    DeleteSnapshot,
    GetInvestmentDetail,
    ListInvestments,
    RecordSnapshot,
    UpdateInvestment,
)
from finance_app.application.use_cases.reports import GetAnnualReport, GetMonthlyReport
from finance_app.application.use_cases.simulation import CompareScenarios, RunSimulation
from finance_app.application.use_cases.transactions import (
    DeleteTransaction,
    ListTransactions,
    RecordTransaction,
)
from finance_app.domain.budget.repository import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from finance_app.domain.budget.services import CategoryUsage
from finance_app.domain.budget.variance import VarianceCalculator
from finance_app.domain.portfolio.comparison import PerformanceComparator
from finance_app.domain.portfolio.repository import InvestmentRepository
from finance_app.domain.simulation.scenarios import ScenarioSet
from finance_app.domain.simulation.simulator import CompoundInterestSimulator
from finance_app.domain.simulation.tax_policy import spanish_savings_policy
from finance_app.infrastructure.config import Settings, default_config_path, load_settings
from finance_app.infrastructure.memory.budget_repository import (
    InMemoryBudgetRepository,
    InMemoryCategoryRepository,
    InMemoryTransactionRepository,
)
from finance_app.infrastructure.memory.repository import InMemoryInvestmentRepository
from finance_app.presentation.budget.view_model import (
    BudgetUseCases,
    BudgetViewModel,
    CategoriesUseCases,
    CategoriesViewModel,
    TransactionsUseCases,
    TransactionsViewModel,
)
from finance_app.presentation.portfolio.view_model import PortfolioUseCases, PortfolioViewModel
from finance_app.presentation.simulator.view_model import SimulatorViewModel
from finance_app.presentation.workers import TaskRunner

logger = logging.getLogger(__name__)


class StorageKind(StrEnum):
    SHEETS = "sheets"
    OFFLINE = "offline"  # Google Sheets not configured
    ERROR = "error"  # configured but could not be initialised
    CUSTOM = "custom"  # repository injected by the caller (tests)


@dataclass(frozen=True, slots=True)
class StorageStatus:
    """Language-neutral description of the storage backend; the UI renders the text."""

    kind: StorageKind
    detail: str = ""

    @property
    def persistent(self) -> bool:
        return self.kind in (StorageKind.SHEETS, StorageKind.CUSTOM)


@dataclass(frozen=True, slots=True)
class BudgetRepositories:
    categories: CategoryRepository
    budgets: BudgetRepository
    transactions: TransactionRepository


@dataclass
class Container:
    settings: Settings
    repository: InvestmentRepository
    budget_repositories: BudgetRepositories
    storage: StorageStatus
    runner: TaskRunner
    simulator_vm: SimulatorViewModel
    portfolio_vm: PortfolioViewModel
    categories_vm: CategoriesViewModel
    budget_vm: BudgetViewModel
    transactions_vm: TransactionsViewModel

    def rebuild(self) -> Container:
        """Fresh view models over the same settings and repositories (e.g. after a UI rebuild)."""
        return build_container(
            self.settings,
            self.repository,
            budget_repositories=self.budget_repositories,
            runner=self.runner,
            storage=self.storage,
        )

    def wait_idle(self, msecs: int = 10_000) -> bool:
        """Block until all background tasks finished (before tearing down the UI)."""
        return self.runner.wait(msecs)


def _memory_budget_repositories() -> BudgetRepositories:
    return BudgetRepositories(
        InMemoryCategoryRepository(),
        InMemoryBudgetRepository(),
        InMemoryTransactionRepository(),
    )


def build_repositories(
    settings: Settings,
) -> tuple[InvestmentRepository, BudgetRepositories, StorageStatus]:
    if not settings.sheets_enabled:
        path = settings.config_path or default_config_path()
        return (
            InMemoryInvestmentRepository(),
            _memory_budget_repositories(),
            StorageStatus(StorageKind.OFFLINE, str(path)),
        )
    from finance_app.infrastructure.sheets.budget_repository import (
        GoogleSheetsBudgetRepository,
        GoogleSheetsCategoryRepository,
        GoogleSheetsTransactionRepository,
    )
    from finance_app.infrastructure.sheets.client import SheetsGateway
    from finance_app.infrastructure.sheets.repository import GoogleSheetsInvestmentRepository

    assert settings.credentials_path and settings.spreadsheet_id
    try:
        gateway = SheetsGateway.from_service_account_file(
            settings.credentials_path, settings.spreadsheet_id
        )
    except Exception as exc:
        logger.exception("Could not initialise Google Sheets")
        return (
            InMemoryInvestmentRepository(),
            _memory_budget_repositories(),
            StorageStatus(StorageKind.ERROR, str(exc)),
        )
    budget_repositories = BudgetRepositories(
        GoogleSheetsCategoryRepository(gateway),
        GoogleSheetsBudgetRepository(gateway),
        GoogleSheetsTransactionRepository(gateway),
    )
    return (
        GoogleSheetsInvestmentRepository(gateway),
        budget_repositories,
        StorageStatus(StorageKind.SHEETS),
    )


def build_container(
    settings: Settings | None = None,
    repository: InvestmentRepository | None = None,
    budget_repositories: BudgetRepositories | None = None,
    runner: TaskRunner | None = None,
    storage: StorageStatus | None = None,
) -> Container:
    settings = settings or load_settings()
    if repository is None or budget_repositories is None:
        built_repository, built_budget, built_storage = build_repositories(settings)
        if repository is None:
            repository = built_repository
        if budget_repositories is None:
            budget_repositories = built_budget
        if storage is None:
            storage = built_storage
    storage = storage or StorageStatus(StorageKind.CUSTOM)
    runner = runner or TaskRunner()

    simulator = CompoundInterestSimulator(spanish_savings_policy(settings.tax_brackets))
    comparator = PerformanceComparator(simulator, settings.deviation_tolerance_pct / 100)
    calculator = VarianceCalculator(settings.budget_tolerance_pct / 100)
    usage = CategoryUsage(budget_repositories.budgets, budget_repositories.transactions)

    simulator_vm = SimulatorViewModel(
        RunSimulation(simulator),
        CompareScenarios(simulator, ScenarioSet(settings.scenario_delta_pct)),
    )
    portfolio_vm = PortfolioViewModel(
        PortfolioUseCases(
            create=CreateInvestmentFromSimulation(repository),
            list=ListInvestments(repository, comparator),
            detail=GetInvestmentDetail(repository, comparator),
            record_snapshot=RecordSnapshot(repository),
            delete_snapshot=DeleteSnapshot(repository),
            update=UpdateInvestment(repository),
            delete=DeleteInvestment(repository),
        ),
        runner,
    )
    categories_vm = CategoriesViewModel(
        CategoriesUseCases(
            list=ListCategories(budget_repositories.categories, usage),
            create=CreateCategory(budget_repositories.categories),
            update=UpdateCategory(budget_repositories.categories),
            delete=DeleteCategory(budget_repositories.categories, usage),
            seed=SeedDefaultCategories(budget_repositories.categories),
        ),
        runner,
    )
    budget_vm = BudgetViewModel(
        BudgetUseCases(
            get=GetMonthlyBudget(budget_repositories.budgets, budget_repositories.categories),
            create=CreateMonthlyBudget(budget_repositories.budgets),
            update=UpdateMonthlyBudget(budget_repositories.budgets),
            delete=DeleteMonthlyBudget(budget_repositories.budgets),
            save_line=SaveBudgetLine(budget_repositories.budgets, budget_repositories.categories),
            delete_line=DeleteBudgetLine(budget_repositories.budgets),
            periods=ListBudgetPeriods(budget_repositories.budgets),
            monthly=GetMonthlyReport(
                budget_repositories.budgets,
                budget_repositories.transactions,
                budget_repositories.categories,
                calculator,
            ),
            annual=GetAnnualReport(
                budget_repositories.budgets,
                budget_repositories.transactions,
                budget_repositories.categories,
                calculator,
            ),
        ),
        runner,
    )
    transactions_vm = TransactionsViewModel(
        TransactionsUseCases(
            list=ListTransactions(budget_repositories.transactions, budget_repositories.categories),
            record=RecordTransaction(
                budget_repositories.transactions, budget_repositories.categories
            ),
            delete=DeleteTransaction(budget_repositories.transactions),
        ),
        runner,
    )
    return Container(
        settings=settings,
        repository=repository,
        budget_repositories=budget_repositories,
        storage=storage,
        runner=runner,
        simulator_vm=simulator_vm,
        portfolio_vm=portfolio_vm,
        categories_vm=categories_vm,
        budget_vm=budget_vm,
        transactions_vm=transactions_vm,
    )
