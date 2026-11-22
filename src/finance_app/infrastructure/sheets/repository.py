from __future__ import annotations

import copy
import logging
import threading
from collections import defaultdict

from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.portfolio.repository import InvestmentRepository
from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import NotFoundError
from finance_app.infrastructure.sheets.client import Row, SheetsGateway
from finance_app.infrastructure.sheets.mappers import (
    RowMappingError,
    investment_to_row,
    row_to_investment,
    row_to_snapshot,
    snapshot_to_row,
)
from finance_app.infrastructure.sheets.schema import (
    INVESTMENTS_SHEET,
    SNAPSHOTS_SHEET,
    data_range,
    ensure_schema,
    row_range,
)

logger = logging.getLogger(__name__)


class GoogleSheetsInvestmentRepository(InvestmentRepository):
    """Stores investments in an ``Investments`` tab and snapshots in a ``Snapshots`` tab.

    The whole spreadsheet is cached in memory and re-read after every write so that
    row numbers stay correct (and external edits are picked up).
    """

    def __init__(self, gateway: SheetsGateway) -> None:
        self._gateway = gateway
        self._lock = threading.RLock()
        self._sheet_ids: dict[str, int] | None = None
        self._cache: dict[str, Investment] | None = None
        self._investment_rows: dict[str, int] = {}
        self._snapshot_rows: dict[str, int] = {}

    def refresh(self) -> None:
        with self._lock:
            if self._sheet_ids is None:
                self._sheet_ids = ensure_schema(self._gateway, [INVESTMENTS_SHEET, SNAPSHOTS_SHEET])
            inv_rows, snap_rows = self._gateway.batch_get(
                [data_range(INVESTMENTS_SHEET), data_range(SNAPSHOTS_SHEET)]
            )
            self._snapshot_rows = {}
            snapshots: dict[str, list[PerformanceSnapshot]] = defaultdict(list)
            for number, row in self._rows_with_id(snap_rows):
                try:
                    investment_id, snapshot = row_to_snapshot(row)
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", SNAPSHOTS_SHEET, number, exc)
                    continue
                snapshots[investment_id].append(snapshot)
                self._snapshot_rows[snapshot.id] = number

            self._investment_rows, cache = {}, {}
            for number, row in self._rows_with_id(inv_rows):
                try:
                    investment = row_to_investment(row, snapshots.get(str(row[0]), []))
                except RowMappingError as exc:
                    logger.warning("Skipping %s row %d: %s", INVESTMENTS_SHEET, number, exc)
                    continue
                cache[investment.id] = investment
                self._investment_rows[investment.id] = number
            self._cache = cache

    @staticmethod
    def _rows_with_id(rows: list[Row]) -> list[tuple[int, Row]]:
        return [(i + 2, row) for i, row in enumerate(rows) if row and str(row[0]).strip()]

    def _items(self) -> dict[str, Investment]:
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache

    def list(self) -> list[Investment]:
        with self._lock:
            return [copy.deepcopy(i) for i in self._items().values()]

    def get(self, investment_id: str) -> Investment:
        with self._lock:
            try:
                return copy.deepcopy(self._items()[investment_id])
            except KeyError:
                raise NotFoundError(f"Investment {investment_id} not found") from None

    def save(self, investment: Investment) -> None:
        with self._lock:
            existing = self._items().get(investment.id)
            updates: list[tuple[str, list[Row]]] = []
            if existing is not None:
                row = self._investment_rows[investment.id]
                updates.append((row_range(INVESTMENTS_SHEET, row), [investment_to_row(investment)]))
            old = {s.id: s for s in existing.snapshots} if existing else {}
            new_snapshot_rows: list[Row] = []
            for snapshot in investment.snapshots:
                if snapshot.id not in old:
                    new_snapshot_rows.append(snapshot_to_row(investment.id, snapshot))
                elif old[snapshot.id] != snapshot:
                    row = self._snapshot_rows[snapshot.id]
                    updates.append(
                        (
                            row_range(SNAPSHOTS_SHEET, row),
                            [snapshot_to_row(investment.id, snapshot)],
                        )
                    )
            removed = old.keys() - {s.id for s in investment.snapshots}

            self._gateway.update_values(updates)
            if existing is None:
                self._gateway.append_values(
                    data_range(INVESTMENTS_SHEET), [investment_to_row(investment)]
                )
            self._gateway.append_values(data_range(SNAPSHOTS_SHEET), new_snapshot_rows)
            self._delete_snapshot_rows(removed)
            self.refresh()

    def delete(self, investment_id: str) -> None:
        with self._lock:
            investment = self._items().get(investment_id)
            if investment is None:
                raise NotFoundError(f"Investment {investment_id} not found")
            assert self._sheet_ids is not None
            rows = [(self._sheet_ids[INVESTMENTS_SHEET], self._investment_rows[investment_id])]
            rows += [
                (self._sheet_ids[SNAPSHOTS_SHEET], self._snapshot_rows[s.id])
                for s in investment.snapshots
            ]
            self._gateway.delete_rows(rows)
            self.refresh()

    def _delete_snapshot_rows(self, snapshot_ids: set[str]) -> None:
        if snapshot_ids:
            assert self._sheet_ids is not None
            sheet_id = self._sheet_ids[SNAPSHOTS_SHEET]
            self._gateway.delete_rows((sheet_id, self._snapshot_rows[s]) for s in snapshot_ids)
