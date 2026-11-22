from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets import named


class KpiCard(QFrame):
    def __init__(self, title: str, tooltip: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        self._title = named(QLabel(tr(title)), "KpiTitle")
        self._value = named(QLabel("—"), "KpiValue")
        self._hint = named(QLabel(""), "KpiHint")
        self._hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        for widget in (self._title, self._value, self._hint):
            layout.addWidget(widget)
        if tooltip:
            self.setToolTip(tr(tooltip))

    def set_value(self, text: str, hint: str = "", color: str | None = None) -> None:
        self._value.setText(text)
        self._value.setStyleSheet(f"color: {color};" if color else "")
        self._hint.setText(hint)
        self._hint.setVisible(bool(hint))

    @property
    def value_text(self) -> str:
        return self._value.text()


class KpiGrid(QWidget):
    """Lays out KPI cards in a fixed number of columns, keyed by name."""

    def __init__(
        self, cards: list[tuple[str, str, str]], columns: int = 4, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.cards: dict[str, KpiCard] = {}
        for i, (key, title, tooltip) in enumerate(cards):
            card = KpiCard(title, tooltip)
            self.cards[key] = card
            layout.addWidget(card, i // columns, i % columns)

    def clear(self) -> None:
        for card in self.cards.values():
            card.set_value("—")
