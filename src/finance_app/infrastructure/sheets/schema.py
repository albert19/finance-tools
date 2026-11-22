from __future__ import annotations

import threading
from collections.abc import Iterable

from finance_app.infrastructure.sheets.client import SheetsGateway

INVESTMENTS_SHEET = "Investments"
SNAPSHOTS_SHEET = "Snapshots"
CATEGORIES_SHEET = "Categories"
BUDGETS_SHEET = "Budgets"
BUDGET_LINES_SHEET = "Budget lines"
TRANSACTIONS_SHEET = "Transactions"

INVESTMENT_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "created_at",
    "start_date",
    "status",
    "initial_capital",
    "contribution",
    "contribution_frequency",
    "contribution_timing",
    "annual_rate_pct",
    "compounding_frequency",
    "horizon_months",
    "inflation_pct",
    "ter_pct",
    "contribution_increase_pct",
    "withdrawal_amount",
    "withdrawal_frequency",
    "withdrawal_start_month",
    "apply_taxes",
    "notes",
)
SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "id",
    "investment_id",
    "date",
    "market_value",
    "contribution",
    "withdrawal",
    "note",
)
CATEGORY_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "kind",
    "archived",
)
BUDGET_COLUMNS: tuple[str, ...] = (
    "id",
    "year",
    "month",
    "notes",
    "created_at",
)
BUDGET_LINE_COLUMNS: tuple[str, ...] = (
    "id",
    "budget_id",
    "category_id",
    "description",
    "amount",
)
TRANSACTION_COLUMNS: tuple[str, ...] = (
    "id",
    "date",
    "category_id",
    "amount",
    "description",
)

SCHEMA: dict[str, tuple[str, ...]] = {
    INVESTMENTS_SHEET: INVESTMENT_COLUMNS,
    SNAPSHOTS_SHEET: SNAPSHOT_COLUMNS,
    CATEGORIES_SHEET: CATEGORY_COLUMNS,
    BUDGETS_SHEET: BUDGET_COLUMNS,
    BUDGET_LINES_SHEET: BUDGET_LINE_COLUMNS,
    TRANSACTIONS_SHEET: TRANSACTION_COLUMNS,
}


def column_letter(index: int) -> str:
    """1-based column index -> A1 letter (1 -> A, 27 -> AA)."""
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def data_range(sheet: str, first_row: int = 2) -> str:
    return f"'{sheet}'!A{first_row}:{column_letter(len(SCHEMA[sheet]))}"


def row_range(sheet: str, row: int) -> str:
    return f"'{sheet}'!A{row}:{column_letter(len(SCHEMA[sheet]))}{row}"


# Several repositories bootstrap their tabs concurrently on app start; the
# list-then-create sequence must be atomic or two threads can both try to
# create the same tab (HTTP 400) while the gateway serializes single calls.
_SCHEMA_LOCK = threading.Lock()


def ensure_schema(gateway: SheetsGateway, titles: Iterable[str] | None = None) -> dict[str, int]:
    """Create missing tabs and header rows. Returns the sheet ids by title."""
    with _SCHEMA_LOCK:
        return _ensure_schema(gateway, titles)


def _ensure_schema(gateway: SheetsGateway, titles: Iterable[str] | None = None) -> dict[str, int]:
    wanted = {title: SCHEMA[title] for title in (titles or SCHEMA)}
    existing = gateway.sheet_ids()
    missing = [title for title in wanted if title not in existing]
    if missing:
        gateway.add_sheets(missing)
        existing = gateway.sheet_ids()
    headers = gateway.batch_get([f"'{title}'!1:1" for title in wanted])
    updates = [
        (row_range(title, 1), [list(columns)])
        for (title, columns), current in zip(wanted.items(), headers, strict=True)
        if not current or list(current[0]) != list(columns)
    ]
    gateway.update_values(updates)
    return {title: existing[title] for title in wanted}
