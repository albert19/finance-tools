from __future__ import annotations

from collections.abc import Sequence

from finance_app.application.budget_assemblers import category_dto
from finance_app.application.dto import CategoryDTO
from finance_app.domain.budget.category import Category, CategoryKind
from finance_app.domain.budget.repository import CategoryRepository
from finance_app.domain.budget.services import CategoryUsage
from finance_app.domain.shared.errors import ValidationError


class ListCategories:
    def __init__(self, categories: CategoryRepository, usage: CategoryUsage | None = None) -> None:
        self._categories = categories
        self._usage = usage

    def execute(self, include_archived: bool = True) -> list[CategoryDTO]:
        categories = sorted(
            self._categories.list(), key=lambda c: (c.kind is CategoryKind.INCOME, c.name.lower())
        )
        if not include_archived:
            categories = [c for c in categories if not c.archived]
        return [
            category_dto(c, in_use=self._usage.is_used(c.id) if self._usage else False)
            for c in categories
        ]


class CreateCategory:
    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def execute(self, name: str, kind: str) -> str:
        category = Category.create(name, kind)
        self._check_unique(category)
        self._categories.save(category)
        return category.id

    def _check_unique(self, category: Category) -> None:
        if any(
            c.kind is category.kind and c.name.lower() == category.name.lower()
            for c in self._categories.list()
        ):
            raise ValidationError.single(
                "name", "A category with this name already exists for this type."
            )


class UpdateCategory:
    """Renames or archives/unarchives a category. The kind is immutable."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def execute(
        self,
        category_id: str,
        *,
        name: str | None = None,
        archived: bool | None = None,
    ) -> None:
        category = self._categories.get(category_id)
        if name is not None:
            category.rename(name)
            if any(
                c.id != category.id
                and c.kind is category.kind
                and c.name.lower() == category.name.lower()
                for c in self._categories.list()
            ):
                raise ValidationError.single(
                    "name", "A category with this name already exists for this type."
                )
        if archived is not None:
            if archived:
                category.archive()
            else:
                category.unarchive()
        self._categories.save(category)


class DeleteCategory:
    def __init__(self, categories: CategoryRepository, usage: CategoryUsage) -> None:
        self._categories = categories
        self._usage = usage

    def execute(self, category_id: str) -> None:
        self._categories.get(category_id)
        self._usage.ensure_unused(category_id)
        self._categories.delete(category_id)


class SeedDefaultCategories:
    """Creates a starter set of categories; the caller supplies the (translated) names."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def execute(self, income_names: Sequence[str], expense_names: Sequence[str]) -> list[str]:
        create = CreateCategory(self._categories)
        existing = {(c.kind, c.name.lower()) for c in self._categories.list()}
        created: list[str] = []
        for kind, names in (
            (CategoryKind.INCOME, income_names),
            (CategoryKind.EXPENSE, expense_names),
        ):
            for name in names:
                name = name.strip()
                if name and (kind, name.lower()) not in existing:
                    created.append(create.execute(name, kind.value))
                    existing.add((kind, name.lower()))
        return created
