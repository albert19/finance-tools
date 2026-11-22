from __future__ import annotations

from collections.abc import Mapping


class DomainError(Exception):
    """Base class for all domain errors."""


class ValidationError(DomainError):
    """Raised when a value object or entity receives invalid data.

    ``errors`` maps a field name to a human readable message so the UI can
    show each message next to the offending input.
    """

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors: dict[str, str] = dict(errors)
        super().__init__("; ".join(f"{k}: {v}" for k, v in self.errors.items()))

    @classmethod
    def single(cls, field: str, message: str) -> ValidationError:
        return cls({field: message})


class NotFoundError(DomainError):
    """Raised when an aggregate cannot be found in a repository."""
