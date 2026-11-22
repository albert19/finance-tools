from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QWidget

from finance_app.application.dto import SnapshotDTO, SnapshotInput
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.dialogs import (
    ValidatedDialog,
    date_edit,
    from_qdate,
    money_spin,
    to_qdate,
)


class SaveInvestmentDialog(ValidatedDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("Save as investment"), parent)
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("e.g. MSCI World index fund"))
        self.name.setMaxLength(100)
        self.start = date_edit()
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(70)
        self.form.addRow(tr("Name"), self.name)
        self.form.addRow(tr("Start date"), self.start)
        self.form.addRow(tr("Notes"), self.notes)
        self.name.textChanged.connect(self._validate)
        self._validate()

    def validation_error(self) -> str:
        return "" if self.name.text().strip() else tr("Enter a name for the investment.")

    def values(self) -> tuple[str, date, str]:
        return self.name.text().strip(), from_qdate(self.start.date()), self.notes.toPlainText()


class SnapshotDialog(ValidatedDialog):
    def __init__(
        self, start_date: date, existing: SnapshotDTO | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(
            tr("Edit snapshot") if existing else tr("Add performance snapshot"), parent
        )
        self._start = start_date
        self.date = date_edit()
        self.date.setMinimumDate(to_qdate(start_date))
        self.market_value = money_spin()
        self.contribution = money_spin()
        self.withdrawal = money_spin()
        self.note = QLineEdit()
        self.form.addRow(tr("Date"), self.date)
        self.form.addRow(tr("Current market value"), self.market_value)
        self.form.addRow(tr("Contributed since last snapshot"), self.contribution)
        self.form.addRow(tr("Withdrawn since last snapshot"), self.withdrawal)
        self.form.addRow(tr("Note"), self.note)
        if existing:
            self.date.setDate(to_qdate(existing.date))
            self.market_value.setValue(existing.market_value)
            self.contribution.setValue(existing.contribution)
            self.withdrawal.setValue(existing.withdrawal)
            self.note.setText(existing.note)
        self.market_value.valueChanged.connect(self._validate)
        self.date.dateChanged.connect(self._validate)
        self._validate()

    def validation_error(self) -> str:
        if self.market_value.value() <= 0:
            return tr("Enter the current market value (must be greater than zero).")
        if from_qdate(self.date.date()) < self._start:
            return tr("The date cannot be before the investment start date.")
        return ""

    def snapshot_input(self) -> SnapshotInput:
        return SnapshotInput(
            date=from_qdate(self.date.date()),
            market_value=self.market_value.value(),
            contribution=self.contribution.value(),
            withdrawal=self.withdrawal.value(),
            note=self.note.text(),
        )
