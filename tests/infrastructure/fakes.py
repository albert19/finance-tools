from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

Row = list[Any]
_RANGE = re.compile(r"^'(?P<sheet>[^']+)'!(?:[A-Z]+)?(?P<start>\d+)(?::[A-Z]*(?P<end>\d+)?)?$")


class FakeSheetsGateway:
    """In-memory stand-in for SheetsGateway that mimics row semantics."""

    def __init__(self) -> None:
        self.sheets: dict[str, list[Row]] = {}
        self.ids: dict[str, int] = {}
        self.calls: list[str] = []

    def _parse(self, range_: str) -> tuple[str, int, int | None]:
        m = _RANGE.match(range_)
        assert m, range_
        end = m.group("end")
        return m.group("sheet"), int(m.group("start")), int(end) if end else None

    def sheet_ids(self) -> dict[str, int]:
        self.calls.append("sheet_ids")
        return dict(self.ids)

    def add_sheets(self, titles: Iterable[str]) -> None:
        for t in titles:
            self.sheets[t] = []
            self.ids[t] = len(self.ids) + 100

    def batch_get(self, ranges: Sequence[str]) -> list[list[Row]]:
        self.calls.append("batch_get")
        out = []
        for r in ranges:
            sheet, start, end = self._parse(r)
            rows = self.sheets[sheet][start - 1 : end]
            out.append([list(x) for x in rows])
        return out

    def update_values(self, data: Sequence[tuple[str, list[Row]]]) -> None:
        for r, values in data:
            sheet, start, _ = self._parse(r)
            rows = self.sheets[sheet]
            while len(rows) < start - 1 + len(values):
                rows.append([])
            for i, v in enumerate(values):
                rows[start - 1 + i] = list(v)

    def append_values(self, range_: str, rows: list[Row]) -> None:
        sheet, _, _ = self._parse(range_)
        self.sheets[sheet].extend(list(r) for r in rows)

    def delete_rows(self, rows: Iterable[tuple[int, int]]) -> None:
        by_id = {v: k for k, v in self.ids.items()}
        for sheet_id, row in sorted(set(rows), key=lambda r: (r[0], -r[1])):
            del self.sheets[by_id[sheet_id]][row - 1]
