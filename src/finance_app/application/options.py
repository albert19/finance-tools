"""Selectable options exposed to the UI as (value, label) pairs."""

from __future__ import annotations

from finance_app.domain.budget.category import CategoryKind
from finance_app.domain.simulation.value_objects import (
    CASH_FLOW_FREQUENCIES,
    COMPOUNDING_FREQUENCIES,
    ContributionTiming,
)

Option = tuple[str, str]

CASH_FLOW_FREQUENCY_OPTIONS: tuple[Option, ...] = tuple(
    (f.value, f.label) for f in CASH_FLOW_FREQUENCIES
)
COMPOUNDING_FREQUENCY_OPTIONS: tuple[Option, ...] = tuple(
    (f.value, f.label) for f in COMPOUNDING_FREQUENCIES
)
CONTRIBUTION_TIMING_OPTIONS: tuple[Option, ...] = tuple(
    (t.value, t.label) for t in ContributionTiming
)
CATEGORY_KIND_OPTIONS: tuple[Option, ...] = tuple((kind.value, kind.label) for kind in CategoryKind)
