"""Data transfer objects exchanged between the UI and the application layer.

Only primitive types are used so that the presentation layer never depends on
domain objects. Percentages are expressed in percent (5.0 == 5 %).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SimulationInput:
    initial_capital: float = 10_000.0
    contribution: float = 200.0
    contribution_frequency: str = "monthly"
    annual_rate_pct: float = 6.0
    compounding_frequency: str = "monthly"
    horizon_months: int = 240
    contribution_timing: str = "end"
    inflation_pct: float = 0.0
    ter_pct: float = 0.0
    contribution_increase_pct: float = 0.0
    withdrawal_amount: float = 0.0
    withdrawal_frequency: str = "monthly"
    withdrawal_start_month: int = 0
    apply_taxes: bool = False


@dataclass(frozen=True, slots=True)
class RowDTO:
    index: int
    opening: float
    contribution: float
    interest: float
    fees: float
    withdrawal: float
    taxes: float
    closing: float
    cost_basis: float
    gains: float
    real_closing: float


@dataclass(frozen=True, slots=True)
class SummaryDTO:
    final_capital: float
    final_capital_net: float
    total_contributed: float
    total_withdrawn: float
    interest_earned: float
    total_fees: float
    total_taxes: float
    real_final_capital: float
    real_final_capital_net: float
    total_return_pct: float
    irr_pct: float | None
    irr_net_pct: float | None
    depletion_month: int | None


@dataclass(frozen=True, slots=True)
class SimulationOutput:
    summary: SummaryDTO
    yearly: tuple[RowDTO, ...]
    monthly: tuple[RowDTO, ...]


@dataclass(frozen=True, slots=True)
class ScenarioOutput:
    name: str
    annual_rate_pct: float
    result: SimulationOutput


@dataclass(frozen=True, slots=True)
class SnapshotInput:
    date: date
    market_value: float
    contribution: float = 0.0
    withdrawal: float = 0.0
    note: str = ""


@dataclass(frozen=True, slots=True)
class SnapshotDTO:
    id: str
    date: date
    market_value: float
    contribution: float
    withdrawal: float
    note: str
    projected: float
    deviation: float
    deviation_pct: float | None
    contributed_actual: float


@dataclass(frozen=True, slots=True)
class InvestmentSummaryDTO:
    id: str
    name: str
    start_date: date
    status: str
    expected_rate_pct: float
    initial_capital: float
    latest_date: date | None
    latest_value: float | None
    projected_at_latest: float | None
    deviation_pct: float | None
    performance: str


@dataclass(frozen=True, slots=True)
class InvestmentDetailDTO:
    summary: InvestmentSummaryDTO
    notes: str
    parameters: SimulationInput
    projection: tuple[tuple[date, float], ...]
    projection_contributed: tuple[tuple[date, float], ...]
    projected_final: float
    snapshots: tuple[SnapshotDTO, ...]
    actual_xirr_pct: float | None


# --- Budgeting ---


@dataclass(frozen=True, slots=True)
class CategoryDTO:
    id: str
    name: str
    kind: str  # CategoryKind value: "income" | "expense"
    archived: bool
    in_use: bool


@dataclass(frozen=True, slots=True)
class BudgetLineInput:
    category_id: str
    amount: float
    description: str = ""


@dataclass(frozen=True, slots=True)
class BudgetLineDTO:
    id: str
    category_id: str
    category_name: str
    kind: str
    description: str
    amount: float


@dataclass(frozen=True, slots=True)
class MonthlyBudgetDTO:
    id: str
    year: int
    month: int
    notes: str
    lines: tuple[BudgetLineDTO, ...]
    planned_income: float
    planned_expenses: float


@dataclass(frozen=True, slots=True)
class TransactionInput:
    date: date
    category_id: str
    amount: float
    description: str = ""


@dataclass(frozen=True, slots=True)
class TransactionDTO:
    id: str
    date: date
    category_id: str
    category_name: str
    kind: str
    amount: float
    description: str


@dataclass(frozen=True, slots=True)
class VarianceRowDTO:
    category_id: str
    name: str
    kind: str
    planned: float
    actual: float
    variance: float
    variance_pct: float | None
    status: str  # VarianceStatus value


@dataclass(frozen=True, slots=True)
class TotalsDTO:
    planned_income: float
    actual_income: float
    planned_expenses: float
    actual_expenses: float
    planned_net: float
    actual_net: float


@dataclass(frozen=True, slots=True)
class MonthlyReportDTO:
    year: int
    month: int
    budget: MonthlyBudgetDTO | None
    rows: tuple[VarianceRowDTO, ...]
    totals: TotalsDTO
    transactions: tuple[TransactionDTO, ...]


@dataclass(frozen=True, slots=True)
class MonthTotalsDTO:
    year: int
    month: int
    has_budget: bool
    totals: TotalsDTO


@dataclass(frozen=True, slots=True)
class AnnualReportDTO:
    year: int
    rows: tuple[VarianceRowDTO, ...]
    months: tuple[MonthTotalsDTO, ...]
    totals: TotalsDTO
