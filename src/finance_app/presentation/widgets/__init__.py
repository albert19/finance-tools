from __future__ import annotations

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QWidget


def named[W: QWidget](widget: W, object_name: str) -> W:
    """Set the Qt object name (used by the stylesheet) and return the widget."""
    widget.setObjectName(object_name)
    return widget


def spanish_locale() -> QLocale:
    locale = QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)
    locale.setNumberOptions(QLocale.NumberOption.DefaultNumberOptions)
    return locale
