from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from finance_app.bootstrap import build_container
from finance_app.presentation.app import AppController
from finance_app.presentation.theme import STYLESHEET


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setOrganizationName("finance-app")
    app.setApplicationName("finance-app")
    app.setApplicationDisplayName("Finance manager")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    controller = AppController(build_container(), QSettings())
    app.aboutToQuit.connect(lambda: controller.window.container.wait_idle())
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
