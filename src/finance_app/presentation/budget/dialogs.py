from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

from finance_app.application.dto import (
    BudgetLineDTO,
    BudgetLineInput,
    CategoryDTO,
    TransactionDTO,
    TransactionInput,
)
from finance_app.application.options import CATEGORY_KIND_OPTIONS
from finance_app.presentation.budget.period_picker import month_name
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.dialogs import (
    ValidatedDialog,
    date_edit,
    from_qdate,
    money_spin,
)

_KIND_LABELS = dict(CATEGORY_KIND_OPTIONS)


def _kind_combo() -> QComboBox:
    combo = QComboBox()
    for value, label in CATEGORY_KIND_OPTIONS:
        combo.addItem(tr(label), value)
    return combo


class CategoryDialog(ValidatedDialog):
    """Name + kind for a category. The kind is locked when editing."""

    def __init__(self, existing: CategoryDTO | None = None, parent: QWidget | None = None) -> None:
        super().__init__(tr("Edit category") if existing else tr("Add category"), parent)
        self.name = QLineEdit()
        self.name.setMaxLength(60)
        self.kind = _kind_combo()
        if existing:
            self.name.setText(existing.name)
            index = self.kind.findData(existing.kind)
            self.kind.setCurrentIndex(max(index, 0))
            self.kind.setEnabled(False)
            if existing.in_use:
                self.kind.setToolTip(tr("The type cannot change once the category is in use."))
        self.form.addRow(tr("Name"), self.name)
        self.form.addRow(tr("Type"), self.kind)
        self.name.textChanged.connect(self._validate)
        self._validate()

    def validation_error(self) -> str:
        return "" if self.name.text().strip() else tr("Enter a name for the category.")

    def values(self) -> tuple[str, str]:
        return self.name.text().strip(), str(self.kind.currentData())


class BudgetLineDialog(ValidatedDialog):
    """Category + description + expected amount for a budget line."""

    def __init__(
        self,
        categories: Sequence[CategoryDTO],
        existing: BudgetLineDTO | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr("Edit budget line") if existing else tr("Add budget line"), parent)
        self.category = QComboBox()
        self._categories: dict[str, CategoryDTO] = {}
        active = [c for c in categories if not c.archived]
        if existing and existing.category_id not in {c.id for c in active}:
            active = [
                *active,
                CategoryDTO(
                    existing.category_id, existing.category_name, existing.kind, True, True
                ),
            ]
        for c in sorted(active, key=lambda c: (c.kind != "expense", c.name.lower())):
            label = f"{c.name} ({tr(_KIND_LABELS.get(c.kind, c.kind))})"
            self.category.addItem(label, c.id)
            self._categories[c.id] = c
        self.description = QLineEdit()
        self.description.setMaxLength(200)
        self.amount = money_spin()
        self.form.addRow(tr("Category"), self.category)
        self.form.addRow(tr("Description"), self.description)
        self.form.addRow(tr("Expected amount"), self.amount)
        if existing:
            index = self.category.findData(existing.category_id)
            self.category.setCurrentIndex(max(index, 0))
            self.description.setText(existing.description)
            self.amount.setValue(existing.amount)
        self.category.currentIndexChanged.connect(self._validate)
        self.amount.valueChanged.connect(self._validate)
        self._validate()

    def validation_error(self) -> str:
        if self.category.currentData() is None:
            return tr("Create a category first (Budget → Categories tab).")
        if self.amount.value() <= 0:
            return tr("Enter an expected amount greater than zero.")
        return ""

    def line_input(self) -> BudgetLineInput:
        return BudgetLineInput(
            category_id=str(self.category.currentData()),
            amount=self.amount.value(),
            description=self.description.text(),
        )


class TransactionDialog(ValidatedDialog):
    """Date + category + amount + description for a manual entry."""

    def __init__(
        self,
        categories: Sequence[CategoryDTO],
        existing: TransactionDTO | None = None,
        default_date: date | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr("Edit entry") if existing else tr("Add entry"), parent)
        self._categories: dict[str, CategoryDTO] = {c.id: c for c in categories}
        self.kind = _kind_combo()
        self.category = QComboBox()
        self.date = date_edit(existing.date if existing else default_date)
        self.amount = money_spin()
        self.description = QLineEdit()
        self.description.setMaxLength(200)
        self.form.addRow(tr("Type"), self.kind)
        self.form.addRow(tr("Category"), self.category)
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Amount"), self.amount)
        self.form.addRow(tr("Description"), self.description)
        if existing:
            index = self.kind.findData(existing.kind)
            if index >= 0:
                self.kind.setCurrentIndex(index)
            self.amount.setValue(existing.amount)
            self.description.setText(existing.description)
        self.kind.currentIndexChanged.connect(self._fill_categories)
        self.kind.currentIndexChanged.connect(self._validate)
        self.category.currentIndexChanged.connect(self._validate)
        self.amount.valueChanged.connect(self._validate)
        self._fill_categories(existing.category_id if existing else None)
        self._validate()

    def _fill_categories(self, keep_id: str | None = None) -> None:
        kind = str(self.kind.currentData())
        with QSignalBlocker(self.category):
            self.category.clear()
            options = [
                c
                for c in self._categories.values()
                if c.kind == kind and (not c.archived or c.id == keep_id)
            ]
            for c in sorted(options, key=lambda c: c.name.lower()):
                self.category.addItem(c.name, c.id)
            if keep_id:
                index = self.category.findData(keep_id)
                if index >= 0:
                    self.category.setCurrentIndex(index)

    def validation_error(self) -> str:
        if self.category.currentData() is None:
            return tr("Create a category first (Budget → Categories tab).")
        if self.amount.value() <= 0:
            return tr("Enter an amount greater than zero.")
        return ""

    def transaction_input(self) -> TransactionInput:
        return TransactionInput(
            date=from_qdate(self.date.date()),
            category_id=str(self.category.currentData()),
            amount=self.amount.value(),
            description=self.description.text(),
        )


class CopyBudgetDialog(ValidatedDialog):
    """Pick the month whose budget lines are copied into the current one."""

    def __init__(
        self,
        periods: Sequence[tuple[int, int]],
        current: tuple[int, int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(tr("Copy budget from another month"), parent)
        self.periods = QComboBox()
        for year, month in periods:
            if (year, month) != current:
                self.periods.addItem(
                    tr("{month} {year}", month=month_name(month), year=year), (year, month)
                )
        self.form.addRow(tr("Copy from"), self.periods)
        self.periods.currentIndexChanged.connect(self._validate)
        self._validate()

    def validation_error(self) -> str:
        return "" if self.periods.currentData() else tr("There is no other budget to copy.")

    def selected_period(self) -> tuple[int, int] | None:
        return self.periods.currentData()
