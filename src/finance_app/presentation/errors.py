from __future__ import annotations

from finance_app.domain.shared.errors import DomainError, ValidationError
from finance_app.presentation.i18n import tr


def describe_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "\n".join(tr(m) for m in error.errors.values())
    if isinstance(error, DomainError):
        return tr(str(error))
    return f"{type(error).__name__}: {error}"
