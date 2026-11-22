from __future__ import annotations

from datetime import date

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QSpinBox, QWidget

from finance_app.domain.budget.period import MAX_YEAR, MIN_YEAR
from finance_app.presentation.i18n import N_, tr

MONTH_NAMES: tuple[str, ...] = (
    N_("January"),
    N_("February"),
    N_("March"),
    N_("April"),
    N_("May"),
    N_("June"),
    N_("July"),
    N_("August"),
    N_("September"),
    N_("October"),
    N_("November"),
    N_("December"),
)


def month_name(month: int) -> str:
    return tr(MONTH_NAMES[month - 1])


class PeriodPicker(QWidget):
    """Month + year selectors with previous/next navigation."""

    period_changed = Signal(int, int)  # year, month

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.previous_button = QPushButton("◀")
        self.previous_button.setFixedWidth(32)
        self.month = QComboBox()
        self.month.addItems([tr(name) for name in MONTH_NAMES])
        self.year = QSpinBox()
        self.year.setRange(MIN_YEAR, MAX_YEAR)
        today = date.today()
        self.year.setValue(today.year)
        self.month.setCurrentIndex(today.month - 1)
        self.next_button = QPushButton("▶")
        self.next_button.setFixedWidth(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.month)
        layout.addWidget(self.year)
        layout.addWidget(self.next_button)

        self.previous_button.clicked.connect(lambda: self._step(-1))
        self.next_button.clicked.connect(lambda: self._step(1))
        self.month.currentIndexChanged.connect(self._emit)
        self.year.valueChanged.connect(self._emit)

    def period(self) -> tuple[int, int]:
        return self.year.value(), self.month.currentIndex() + 1

    def set_period(self, year: int, month: int, emit: bool = False) -> None:
        with QSignalBlocker(self.month), QSignalBlocker(self.year):
            self.year.setValue(year)
            self.month.setCurrentIndex(month - 1)
        if emit:
            self._emit()

    def _step(self, delta: int) -> None:
        month = self.month.currentIndex() + delta
        if month < 0:
            month, year = 11, self.year.value() - 1
        elif month > 11:
            month, year = 0, self.year.value() + 1
        else:
            year = self.year.value()
        self.set_period(year, month + 1, emit=True)

    def _emit(self, *_args: object) -> None:
        year, month = self.period()
        self.period_changed.emit(year, month)


class YearPicker(QWidget):
    """Year selector with previous/next navigation."""

    year_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.previous_button = QPushButton("◀")
        self.previous_button.setFixedWidth(32)
        self.year = QSpinBox()
        self.year.setRange(MIN_YEAR, MAX_YEAR)
        self.year.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.year.setValue(date.today().year)
        self.next_button = QPushButton("▶")
        self.next_button.setFixedWidth(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.year)
        layout.addWidget(self.next_button)

        self.previous_button.clicked.connect(lambda: self.year.stepDown())
        self.next_button.clicked.connect(lambda: self.year.stepUp())
        self.year.valueChanged.connect(self.year_changed.emit)
