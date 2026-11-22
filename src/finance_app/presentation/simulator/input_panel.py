from __future__ import annotations

from dataclasses import fields

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from finance_app.application.dto import SimulationInput
from finance_app.application.options import (
    CASH_FLOW_FREQUENCY_OPTIONS,
    COMPOUNDING_FREQUENCY_OPTIONS,
    CONTRIBUTION_TIMING_OPTIONS,
    Option,
)
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets import named
from finance_app.presentation.widgets.slider_spin import SliderSpinBox

_HORIZON_LIMITS = {"years": (1, 60), "months": (1, 720)}
_DEFAULTS = SimulationInput()
_ADVANCED_FIELDS = {
    "contribution_timing",
    "inflation_pct",
    "ter_pct",
    "contribution_increase_pct",
    "withdrawal_amount",
    "withdrawal_frequency",
    "withdrawal_start_month",
    "apply_taxes",
}
# Domain error keys -> input widgets keys
_ERROR_KEYS = {
    "annual_rate": "annual_rate_pct",
    "inflation": "inflation_pct",
    "ter": "ter_pct",
    "contribution_increase": "contribution_increase_pct",
}


def _combo(options: tuple[Option, ...], current: str) -> QComboBox:
    combo = QComboBox()
    for value, label in options:
        combo.addItem(tr(label), value)
    combo.setCurrentIndex(max(0, combo.findData(current)))
    return combo


class InputPanel(QWidget):
    """All simulation inputs. Emits ``changed`` whenever any value changes."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        d = _DEFAULTS
        self.initial_capital = SliderSpinBox(0, 500_000, 1_000, 2, " €", spin_maximum=100_000_000)
        self.contribution = SliderSpinBox(0, 5_000, 50, 2, " €", spin_maximum=1_000_000)
        self.contribution_frequency = _combo(CASH_FLOW_FREQUENCY_OPTIONS, d.contribution_frequency)
        self.annual_rate = SliderSpinBox(-10, 25, 0.1, 2, " %", spin_maximum=100)
        self.annual_rate.spin.setMinimum(-50)
        self.horizon = SliderSpinBox(1, 60, 1, 0)
        self.horizon_unit = QComboBox()
        self.horizon_unit.addItem(tr("Years"), "years")
        self.horizon_unit.addItem(tr("Months"), "months")
        self.compounding_frequency = _combo(COMPOUNDING_FREQUENCY_OPTIONS, d.compounding_frequency)

        self.contribution_timing = _combo(CONTRIBUTION_TIMING_OPTIONS, d.contribution_timing)
        self.inflation = SliderSpinBox(0, 15, 0.1, 2, " %", spin_maximum=50)
        self.ter = SliderSpinBox(0, 3, 0.01, 2, " %", spin_maximum=10)
        self.contribution_increase = SliderSpinBox(0, 15, 0.5, 2, " %", spin_maximum=50)
        self.apply_taxes = QCheckBox(tr("Apply Spanish savings tax to gains"))
        self.apply_taxes.setChecked(True)
        self.apply_taxes.setToolTip(
            tr(
                "Progressive savings-income brackets (19–30 %) applied to realised gains on "
                "withdrawals and to the remaining gains when liquidating at the end. "
                "Yearly dividend taxation is not modelled."
            )
        )
        self.withdrawal_amount = SliderSpinBox(0, 10_000, 50, 2, " €", spin_maximum=10_000_000)
        self.withdrawal_frequency = _combo(CASH_FLOW_FREQUENCY_OPTIONS, d.withdrawal_frequency)
        self.withdrawal_start_years = SliderSpinBox(0, 60, 1, 0, tr(" yrs"))

        self._errors: dict[str, QLabel] = {}
        self._general_error = self._error_label()
        self._build_layout()
        self.initial_capital.setValue(d.initial_capital)
        self.contribution.setValue(d.contribution)
        self.annual_rate.setValue(d.annual_rate_pct)
        self.horizon.setValue(d.horizon_months // 12)
        self.withdrawal_start_years.setValue(20)
        self._wire()

    @staticmethod
    def _error_label() -> QLabel:
        label = named(QLabel(), "ErrorLabel")
        label.setWordWrap(True)
        label.hide()
        return label

    def _row(self, form: QFormLayout, label: str, widget: QWidget, key: str, tip: str = "") -> None:
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(1)
        box.addWidget(widget)
        error = self._error_label()
        box.addWidget(error)
        self._errors[key] = error
        title = QLabel(tr(label))
        if tip:
            title.setToolTip(tr(tip))
            container.setToolTip(tr(tip))
        form.addRow(title, container)

    def _build_layout(self) -> None:
        basic = QGroupBox(tr("Basic"))
        form = QFormLayout(basic)
        self._row(form, "Initial capital", self.initial_capital, "initial_capital")
        self._row(
            form,
            "Periodic contribution",
            self.contribution,
            "contribution",
            "Amount added every period (can be zero).",
        )
        self._row(
            form, "Contribution frequency", self.contribution_frequency, "contribution_frequency"
        )
        self._row(
            form,
            "Expected annual return",
            self.annual_rate,
            "annual_rate_pct",
            "Nominal annual rate before fees.",
        )
        horizon = QWidget()
        h = QHBoxLayout(horizon)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.horizon, 1)
        h.addWidget(self.horizon_unit)
        self._row(form, "Time horizon", horizon, "horizon_months")
        self._row(
            form,
            "Compounding",
            self.compounding_frequency,
            "compounding_frequency",
            "How often interest is reinvested.",
        )

        self.advanced = QGroupBox(tr("Advanced"))
        self.advanced.setCheckable(True)
        self.advanced.setChecked(False)
        adv = QFormLayout(self.advanced)
        self._row(
            adv,
            "Contribution timing",
            self.contribution_timing,
            "contribution_timing",
            "Contributions at the beginning of the period earn interest for that period.",
        )
        self._row(
            adv,
            "Annual contribution increase",
            self.contribution_increase,
            "contribution_increase_pct",
        )
        self._row(
            adv,
            "Estimated inflation",
            self.inflation,
            "inflation_pct",
            "Used to compute the real value (purchasing power).",
        )
        self._row(
            adv,
            "Annual fees (TER)",
            self.ter,
            "ter_pct",
            "Total expense ratio charged on the balance.",
        )
        adv.addRow(self.apply_taxes)
        adv.addRow(QLabel(tr("<b>Withdrawals</b> (retirement phase, set amount to 0 to disable)")))
        self._row(adv, "Withdrawal amount", self.withdrawal_amount, "withdrawal_amount")
        self._row(adv, "Withdrawal frequency", self.withdrawal_frequency, "withdrawal_frequency")
        self._row(
            adv,
            "Start withdrawals after",
            self.withdrawal_start_years,
            "withdrawal_start_month",
            "Contributions stop when withdrawals start.",
        )

        layout = QVBoxLayout(self)
        layout.addWidget(basic)
        layout.addWidget(self.advanced)
        layout.addWidget(self._general_error)
        layout.addStretch(1)

    def _wire(self) -> None:
        for slider in (
            self.initial_capital,
            self.contribution,
            self.annual_rate,
            self.horizon,
            self.inflation,
            self.ter,
            self.contribution_increase,
            self.withdrawal_amount,
            self.withdrawal_start_years,
        ):
            slider.valueChanged.connect(self.changed)
        for combo in (
            self.contribution_frequency,
            self.compounding_frequency,
            self.contribution_timing,
            self.withdrawal_frequency,
        ):
            combo.currentIndexChanged.connect(self.changed)
        self.apply_taxes.toggled.connect(self.changed)
        self.advanced.toggled.connect(self.changed)
        self.horizon_unit.currentIndexChanged.connect(self._on_unit_changed)

    def _on_unit_changed(self) -> None:
        months = self._horizon_months_for(self._previous_unit())
        unit = self.horizon_unit.currentData()
        low, high = _HORIZON_LIMITS[unit]
        with QSignalBlocker(self.horizon):
            self.horizon.setRange(low, high)
            self.horizon.setValue(months if unit == "months" else max(1, round(months / 12)))
        self.changed.emit()

    def _previous_unit(self) -> str:
        return "years" if self.horizon_unit.currentData() == "months" else "months"

    def _horizon_months_for(self, unit: str) -> int:
        value = round(self.horizon.value())
        return value * 12 if unit == "years" else value

    def horizon_months(self) -> int:
        return self._horizon_months_for(self.horizon_unit.currentData())

    def to_input(self) -> SimulationInput:
        """Inputs to simulate: advanced fields fall back to defaults while the group is off."""
        full = self.widget_values()
        if self.advanced.isChecked():
            return full
        return SimulationInput(
            **{
                f.name: getattr(full, f.name)
                for f in fields(full)
                if f.name not in _ADVANCED_FIELDS
            },
            apply_taxes=False,
        )

    def widget_values(self) -> SimulationInput:
        """Every widget value, including advanced ones even when the group is collapsed."""
        return SimulationInput(
            initial_capital=self.initial_capital.value(),
            contribution=self.contribution.value(),
            contribution_frequency=self.contribution_frequency.currentData(),
            annual_rate_pct=self.annual_rate.value(),
            compounding_frequency=self.compounding_frequency.currentData(),
            horizon_months=self.horizon_months(),
            contribution_timing=self.contribution_timing.currentData(),
            inflation_pct=self.inflation.value(),
            ter_pct=self.ter.value(),
            contribution_increase_pct=self.contribution_increase.value(),
            withdrawal_amount=self.withdrawal_amount.value(),
            withdrawal_frequency=self.withdrawal_frequency.currentData(),
            withdrawal_start_month=round(self.withdrawal_start_years.value()) * 12,
            apply_taxes=self.apply_taxes.isChecked(),
        )

    def load_input(self, data: SimulationInput, advanced: bool | None = None) -> None:
        """Populate the widgets (emits a single ``changed``).

        ``advanced`` forces the Advanced group state; by default it is enabled only when
        ``data`` uses non-default advanced values.
        """
        with QSignalBlocker(self):
            self.initial_capital.setValue(data.initial_capital)
            self.contribution.setValue(data.contribution)
            self.annual_rate.setValue(data.annual_rate_pct)
            for combo, value in (
                (self.contribution_frequency, data.contribution_frequency),
                (self.compounding_frequency, data.compounding_frequency),
                (self.contribution_timing, data.contribution_timing),
                (self.withdrawal_frequency, data.withdrawal_frequency),
            ):
                combo.setCurrentIndex(max(0, combo.findData(value)))
            in_years = data.horizon_months % 12 == 0
            self.horizon_unit.setCurrentIndex(0 if in_years else 1)
            self.horizon.setRange(*_HORIZON_LIMITS["years" if in_years else "months"])
            self.horizon.setValue(data.horizon_months // 12 if in_years else data.horizon_months)
            self.inflation.setValue(data.inflation_pct)
            self.ter.setValue(data.ter_pct)
            self.contribution_increase.setValue(data.contribution_increase_pct)
            self.withdrawal_amount.setValue(data.withdrawal_amount)
            self.withdrawal_start_years.setValue(data.withdrawal_start_month / 12)
            self.apply_taxes.setChecked(data.apply_taxes)
            self.advanced.setChecked(
                advanced
                if advanced is not None
                else data
                != SimulationInput(
                    **{
                        f.name: getattr(data, f.name)
                        for f in fields(data)
                        if f.name not in _ADVANCED_FIELDS
                    },
                )
            )
        self.changed.emit()

    def show_errors(self, errors: dict[str, str]) -> None:
        self.clear_errors()
        general: list[str] = []
        for key, message in errors.items():
            label = self._errors.get(_ERROR_KEYS.get(key, key))
            if label is None:
                general.append(tr(message))
            else:
                label.setText(tr(message))
                label.show()
        if general:
            self._general_error.setText("\n".join(general))
            self._general_error.show()
        advanced_keys = {_ERROR_KEYS.get(k, k) for k in errors} & _ADVANCED_FIELDS
        if advanced_keys and not self.advanced.isChecked():
            self.advanced.setChecked(True)

    def clear_errors(self) -> None:
        for label in (*self._errors.values(), self._general_error):
            label.clear()
            label.hide()

    def error_messages(self) -> dict[str, str]:
        return {k: lbl.text() for k, lbl in self._errors.items() if lbl.isVisibleTo(self)}
