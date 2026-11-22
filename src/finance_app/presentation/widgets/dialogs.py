"""Shared building blocks for the application's modal dialogs."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from finance_app.presentation.widgets import named, spanish_locale


def to_qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def from_qdate(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def date_edit(value: date | None = None) -> QDateEdit:
    edit = QDateEdit(to_qdate(value) if value else QDate.currentDate())
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd/MM/yyyy")
    return edit


def money_spin(maximum: float = 1_000_000_000) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0, maximum)
    spin.setDecimals(2)
    spin.setSingleStep(100)
    spin.setSuffix(" €")
    spin.setGroupSeparatorShown(True)
    spin.setLocale(spanish_locale())
    return spin


class ValidatedDialog(QDialog):
    """Base dialog that blocks OK and shows a message while the inputs are invalid."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.form = QFormLayout()
        self.error = named(QLabel(), "ErrorLabel")
        self.error.setWordWrap(True)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(self.error)
        layout.addWidget(self.buttons)

    def validation_error(self) -> str:
        """Empty string means the inputs are valid; subclasses override."""
        return ""

    def _validate(self, *_args: object) -> None:
        message = self.validation_error()
        self.error.setText(message)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not message)
