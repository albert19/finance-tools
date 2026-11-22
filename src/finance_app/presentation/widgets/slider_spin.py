from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QSlider, QWidget

from finance_app.presentation.widgets import spanish_locale


class SliderSpinBox(QWidget):
    """A slider and a spin box kept in sync. The spin box may allow values beyond the slider."""

    valueChanged = Signal(float)

    def __init__(
        self,
        minimum: float,
        maximum: float,
        step: float,
        decimals: int = 2,
        suffix: str = "",
        spin_maximum: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scale = 10**decimals
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(round(minimum * self._scale), round(maximum * self._scale))
        self._slider.setSingleStep(max(1, round(step * self._scale)))
        self._slider.setPageStep(max(1, round(step * 10 * self._scale)))
        self._spin = QDoubleSpinBox()
        self._spin.setDecimals(decimals)
        self._spin.setRange(minimum, spin_maximum if spin_maximum is not None else maximum)
        self._spin.setSingleStep(step)
        self._spin.setSuffix(suffix)
        self._spin.setGroupSeparatorShown(True)
        self._spin.setLocale(spanish_locale())
        self._spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._spin.setMinimumWidth(120)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._slider, 3)
        layout.addWidget(self._spin, 2)
        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)

    @property
    def slider(self) -> QSlider:
        return self._slider

    @property
    def spin(self) -> QDoubleSpinBox:
        return self._spin

    def value(self) -> float:
        return float(self._spin.value())

    def setValue(self, value: float) -> None:  # noqa: N802 (Qt naming)
        self._spin.setValue(value)

    def setRange(self, minimum: float, maximum: float) -> None:  # noqa: N802
        with QSignalBlocker(self._slider):
            self._slider.setRange(round(minimum * self._scale), round(maximum * self._scale))
        self._spin.setRange(minimum, maximum)

    def _on_slider(self, raw: int) -> None:
        with QSignalBlocker(self._spin):
            self._spin.setValue(raw / self._scale)
        self.valueChanged.emit(self.value())

    def _on_spin(self, value: float) -> None:
        with QSignalBlocker(self._slider):
            self._slider.setValue(round(value * self._scale))
        self.valueChanged.emit(float(value))
