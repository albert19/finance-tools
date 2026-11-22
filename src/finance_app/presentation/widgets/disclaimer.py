from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from finance_app.presentation.i18n import N_, tr

DISCLAIMER_TEXT = N_(
    "<b>Disclaimer:</b> this is a simulation for informational and educational purposes only. "
    "It is not financial or tax advice. Projected returns are hypothetical, and past "
    "performance does not guarantee future results. Tax rules can change; check them with a "
    "qualified advisor."
)


class DisclaimerBanner(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr(DISCLAIMER_TEXT), parent)
        self.setObjectName("Disclaimer")
        self.setWordWrap(True)
