from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Rate:
    """A rate stored as a fraction (0.05 == 5 %)."""

    fraction: float

    @classmethod
    def from_percent(cls, percent: float) -> Rate:
        return cls(percent / 100.0)

    @classmethod
    def zero(cls) -> Rate:
        return cls(0.0)

    @property
    def percent(self) -> float:
        return self.fraction * 100.0

    def shifted(self, percentage_points: float) -> Rate:
        return Rate(self.fraction + percentage_points / 100.0)

    def __str__(self) -> str:
        return f"{self.percent:.2f} %"
