from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from enum import StrEnum

from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import NotFoundError, ValidationError
from finance_app.domain.simulation.value_objects import SimulationParameters


class InvestmentStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass(eq=False)
class Investment:
    """Aggregate root: an investment planned with a simulation and tracked with snapshots."""

    id: str
    name: str
    start_date: date
    parameters: SimulationParameters
    status: InvestmentStatus = InvestmentStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0))
    notes: str = ""
    _snapshots: list[PerformanceSnapshot] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.name = self._valid_name(self.name)
        snapshots, self._snapshots = self._snapshots, []
        for snapshot in snapshots:
            self.record_snapshot(snapshot)

    @classmethod
    def create(
        cls, name: str, start_date: date, parameters: SimulationParameters, notes: str = ""
    ) -> Investment:
        return cls(uuid.uuid4().hex, name, start_date, parameters, notes=notes)

    @staticmethod
    def _valid_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValidationError.single("name", "Name cannot be empty.")
        if len(name) > 100:
            raise ValidationError.single("name", "Name must be at most 100 characters.")
        return name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Investment) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def snapshots(self) -> tuple[PerformanceSnapshot, ...]:
        return tuple(self._snapshots)

    @property
    def latest_snapshot(self) -> PerformanceSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def rename(self, name: str) -> None:
        self.name = self._valid_name(name)

    def close(self) -> None:
        self.status = InvestmentStatus.CLOSED

    def reopen(self) -> None:
        self.status = InvestmentStatus.ACTIVE

    def record_snapshot(self, snapshot: PerformanceSnapshot) -> None:
        if snapshot.date < self.start_date:
            raise ValidationError.single(
                "date", "Snapshot date cannot be before the investment start date."
            )
        if any(s.date == snapshot.date and s.id != snapshot.id for s in self._snapshots):
            raise ValidationError.single("date", "A snapshot already exists for that date.")
        self._snapshots = [s for s in self._snapshots if s.id != snapshot.id] + [snapshot]
        self._snapshots.sort(key=lambda s: s.date)

    def update_snapshot(self, snapshot_id: str, **changes: object) -> PerformanceSnapshot:
        updated = replace(self.get_snapshot(snapshot_id), **changes)  # type: ignore[arg-type]
        self.record_snapshot(updated)
        return updated

    def get_snapshot(self, snapshot_id: str) -> PerformanceSnapshot:
        for snapshot in self._snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
        raise NotFoundError(f"Snapshot {snapshot_id} not found")

    def remove_snapshot(self, snapshot_id: str) -> None:
        self.get_snapshot(snapshot_id)
        self._snapshots = [s for s in self._snapshots if s.id != snapshot_id]
