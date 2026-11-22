"""Shared plumbing for view models that run work on a background task runner."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from finance_app.presentation.errors import describe_error
from finance_app.presentation.workers import TaskRunner


class BaseViewModel(QObject):
    error = Signal(str)
    busy_changed = Signal(bool)
    message = Signal(str)

    def __init__(self, runner: TaskRunner) -> None:
        super().__init__()
        self._runner = runner
        self._runner.busy_changed.connect(self.busy_changed)

    def _run(
        self,
        fn: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        message: str | None = None,
    ) -> None:
        def done(result: Any) -> None:
            if message:
                self.message.emit(message)
            if on_success:
                on_success(result)

        self._runner.submit(fn, done, lambda e: self.error.emit(describe_error(e)))

    def wait_idle(self, msecs: int = 10_000) -> bool:
        """Block until background tasks finished (used before tearing down the UI)."""
        return self._runner.wait(msecs)
