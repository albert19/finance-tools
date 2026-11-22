"""Minimal UI translation layer.

English source strings are the lookup keys. ``tr`` translates at call time (so it
must be called when widgets are built, never at import time); ``N_`` only marks
module-level constants for translation and is translated later with ``tr``.
Placeholders use ``str.format`` syntax: ``tr("Year {year}", year=3)``.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

from finance_app.presentation.translations.es import SPANISH


class Language(StrEnum):
    ENGLISH = "en"
    SPANISH = "es"

    @property
    def native_name(self) -> str:
        return {"en": "English", "es": "Español"}[self.value]

    @classmethod
    def parse(cls, value: object) -> Language:
        try:
            return cls(str(value).lower()[:2])
        except ValueError:
            return cls.ENGLISH


_CATALOGS: dict[Language, dict[str, str]] = {Language.SPANISH: SPANISH}
_current = Language.ENGLISH
_qt_translator: QTranslator | None = None


def N_(text: str) -> str:  # noqa: N802 (gettext convention)
    return text


def tr(text: str, /, **kwargs: object) -> str:
    template = _CATALOGS.get(_current, {}).get(text, text)
    return template.format(**kwargs) if kwargs else template


def current_language() -> Language:
    return _current


def catalog(language: Language) -> dict[str, str]:
    return _CATALOGS.get(language, {})


def set_language(language: Language | str) -> Language:
    """Switch the UI language (also Qt's built-in dialogs/buttons when an app exists)."""
    global _current, _qt_translator
    _current = Language.parse(language)
    app = QCoreApplication.instance()
    if app is not None:
        if _qt_translator is not None:
            app.removeTranslator(_qt_translator)
            _qt_translator = None
        if _current is not Language.ENGLISH:
            translator = QTranslator(app)
            path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
            if translator.load(QLocale(_current.value), "qtbase", "_", path):
                app.installTranslator(translator)
                _qt_translator = translator
    return _current
