"""Cell parsing helpers shared by the spreadsheet row mappers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

Row = list[Any]


class RowMappingError(ValueError):
    pass


def as_dict(row: Sequence[Any], columns: Sequence[str]) -> dict[str, Any]:
    padded = list(row) + [""] * (len(columns) - len(row))
    return dict(zip(columns, padded, strict=False))


def as_float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    if isinstance(value, str):
        value = value.replace(",", ".").strip()
    return float(value)


def as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def as_date(value: Any) -> date:
    return date.fromisoformat(str(value).strip()[:10])


def round_money(value: float) -> float:
    return round(value, 2)
