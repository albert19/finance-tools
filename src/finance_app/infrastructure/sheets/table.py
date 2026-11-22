"""Per-sheet row bookkeeping for the Google Sheets repositories."""

from __future__ import annotations

from collections.abc import Iterable

from finance_app.infrastructure.sheets.cells import Row
from finance_app.infrastructure.sheets.client import SheetsGateway
from finance_app.infrastructure.sheets.schema import data_range, row_range


class SheetTable:
    """Caches the id -> row-number mapping of one sheet and knows how to write to it.

    Row numbers are refreshed by ``read`` (called by the repository after every
    write) so external edits are picked up and positions stay correct.
    """

    def __init__(self, gateway: SheetsGateway, sheet: str) -> None:
        self._gateway = gateway
        self.sheet = sheet
        self.rows: dict[str, int] = {}
        self.sheet_id: int | None = None

    def read(self) -> list[tuple[int, Row]]:
        """Return all data rows as (1-based row number, row); refreshes ``self.rows``."""
        values = self._gateway.batch_get([data_range(self.sheet)])[0]
        self.rows = {}
        numbered: list[tuple[int, Row]] = []
        for index, row in enumerate(values):
            if row and str(row[0]).strip():
                number = index + 2
                self.rows[str(row[0])] = number
                numbered.append((number, row))
        return numbered

    def update(self, entity_id: str, row: Row) -> None:
        self._gateway.update_values([(row_range(self.sheet, self.rows[entity_id]), [row])])

    def append(self, rows: Iterable[Row]) -> None:
        rows = list(rows)
        if rows:
            self._gateway.append_values(data_range(self.sheet), rows)

    def delete(self, entity_ids: Iterable[str]) -> None:
        ids = set(entity_ids)
        if ids:
            assert self.sheet_id is not None
            self._gateway.delete_rows((self.sheet_id, self.rows[i]) for i in ids)
