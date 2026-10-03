"""Run short operations on a QThreadPool worker so the UI thread never blocks (6.1, NFR-UX1)."""

from __future__ import annotations

import contextlib
import logging
import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

log = logging.getLogger(__name__)

_alive: set[_Signals] = set()   # keep signal carriers alive until they deliver


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals):
        super().__init__()
        self.fn = fn
        self.signals = signals

    def run(self) -> None:
        try:
            result = self.fn()
        except BaseException as exc:  # noqa: BLE001 - delivered to the UI
            log.debug("background task failed: %s", traceback.format_exc())
            self._emit(self.signals.failed, exc)
        else:
            self._emit(self.signals.done, result)

    @staticmethod
    def _emit(signal, value: object) -> None:
        with contextlib.suppress(RuntimeError):   # the window closed while the task ran; nobody waits for it
            signal.emit(value)


def run_async(fn: Callable[[], Any], on_done: Callable[[Any], None] | None = None,
              on_error: Callable[[BaseException], None] | None = None) -> None:
    """Run fn() in the global thread pool; callbacks run on the UI thread."""
    signals = _Signals()
    _alive.add(signals)

    def finish(_: object = None) -> None:
        _alive.discard(signals)

    if on_done:
        signals.done.connect(on_done)
    if on_error:
        signals.failed.connect(on_error)
    signals.done.connect(finish)
    signals.failed.connect(finish)
    QThreadPool.globalInstance().start(_Task(fn, signals))
