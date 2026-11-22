"""Run blocking calls (Google Sheets I/O) on a thread pool and deliver results on the GUI thread."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

logger = logging.getLogger(__name__)

Success = Callable[[Any], None]
Failure = Callable[[Exception], None]


class _Signals(QObject):
    finished = Signal(int, object, object)  # task id, result, error


class _Task(QRunnable):
    def __init__(self, task_id: int, fn: Callable[[], Any], signals: _Signals) -> None:
        super().__init__()
        self._id, self._fn, self._signals = task_id, fn, signals

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # delivered to the UI as an error message
            logger.exception("Background task failed")
            self._signals.finished.emit(self._id, None, exc)
        else:
            self._signals.finished.emit(self._id, result, None)


class TaskRunner(QObject):
    """Submits callables to a QThreadPool; callbacks always run on the GUI thread."""

    busy_changed = Signal(bool)

    def __init__(self, pool: QThreadPool | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = pool or QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.finished.connect(self._on_finished)
        self._ids = itertools.count()
        self._pending: dict[int, tuple[Success | None, Failure | None]] = {}

    @property
    def busy(self) -> bool:
        return bool(self._pending)

    def submit(
        self,
        fn: Callable[[], Any],
        on_success: Success | None = None,
        on_error: Failure | None = None,
    ) -> None:
        task_id = next(self._ids)
        self._pending[task_id] = (on_success, on_error)
        if len(self._pending) == 1:
            self.busy_changed.emit(True)
        self._pool.start(_Task(task_id, fn, self._signals))

    @Slot(int, object, object)
    def _on_finished(self, task_id: int, result: Any, error: Exception | None) -> None:
        on_success, on_error = self._pending.pop(task_id, (None, None))
        if not self._pending:
            self.busy_changed.emit(False)
        if error is not None:
            if on_error:
                on_error(error)
        elif on_success:
            on_success(result)

    def wait(self, msecs: int = 10_000) -> bool:
        return bool(self._pool.waitForDone(msecs))
