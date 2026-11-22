"""Return metrics: IRR / XIRR (money-weighted) and CAGR."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from itertools import pairwise

#: (time in years since the first flow, amount). Negative amount = money invested.
CashFlow = tuple[float, float]

_LOWER, _UPPER = -0.99, 100.0


def _npv(rate: float, flows: Sequence[CashFlow]) -> float:
    try:
        return sum(amount / (1 + rate) ** t for t, amount in flows)
    except (OverflowError, ZeroDivisionError):
        return float("inf")


def _d_npv(rate: float, flows: Sequence[CashFlow]) -> float:
    try:
        return sum(-t * amount / (1 + rate) ** (t + 1) for t, amount in flows)
    except (OverflowError, ZeroDivisionError):
        return float("inf")


def _bisect(f: Callable[[float], float], lo: float, hi: float) -> float | None:
    f_lo = f(lo)
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if abs(f_mid) < 1e-9 or hi - lo < 1e-12:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def irr(flows: Sequence[CashFlow]) -> float | None:
    """Annual rate that makes the NPV of ``flows`` zero, or None if undefined."""
    flows = [(t, a) for t, a in flows if a != 0]
    if not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    rate = 0.05
    for _ in range(50):
        value, slope = _npv(rate, flows), _d_npv(rate, flows)
        if slope == 0 or slope == float("inf") or value == float("inf"):
            break
        new_rate = rate - value / slope
        if new_rate <= _LOWER:
            break
        if abs(new_rate - rate) < 1e-10:
            return new_rate
        rate = new_rate
    grid = [_LOWER, -0.5, -0.2, 0.0, 0.1, 0.3, 1.0, 5.0, _UPPER]
    values = [_npv(r, flows) for r in grid]
    for (lo, f_lo), (hi, f_hi) in pairwise(zip(grid, values, strict=True)):
        if f_lo == 0:
            return lo
        if (f_lo > 0) != (f_hi > 0):
            return _bisect(lambda r: _npv(r, flows), lo, hi)
    return None


def xirr(flows: Sequence[tuple[date, float]]) -> float | None:
    """IRR for irregular, dated cash flows (ACT/365)."""
    if not flows:
        return None
    start = min(d for d, _ in flows)
    return irr([((d - start).days / 365.0, amount) for d, amount in flows])


def cagr(start_value: float, end_value: float, years: float) -> float | None:
    if start_value <= 0 or end_value < 0 or years <= 0:
        return None
    return float((end_value / start_value) ** (1 / years) - 1)
