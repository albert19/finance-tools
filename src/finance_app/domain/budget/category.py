from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from finance_app.domain.shared.errors import ValidationError

MAX_CATEGORY_NAME = 60


class CategoryKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"

    @property
    def label(self) -> str:
        return self.value.capitalize()


@dataclass(eq=False)
class Category:
    """An income or expense classification shared by budgets and transactions."""

    id: str
    name: str
    kind: CategoryKind
    archived: bool = False

    def __post_init__(self) -> None:
        self.name = self._valid_name(self.name)
        self.kind = CategoryKind(self.kind)

    @classmethod
    def create(cls, name: str, kind: CategoryKind | str) -> Category:
        return cls(uuid.uuid4().hex, name, CategoryKind(kind))

    @staticmethod
    def _valid_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValidationError.single("name", "Category name cannot be empty.")
        if len(name) > MAX_CATEGORY_NAME:
            raise ValidationError.single("name", "Category name must be at most 60 characters.")
        return name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Category) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def rename(self, name: str) -> None:
        self.name = self._valid_name(name)

    def archive(self) -> None:
        self.archived = True

    def unarchive(self) -> None:
        self.archived = False
