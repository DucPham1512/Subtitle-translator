"""Shared widgets: frame rectangle selector, image conversion, clip player, small helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QMessageBox, QSizePolicy, QWidget


def to_qimage(frame: np.ndarray) -> QImage:
    """BGR or gray NumPy frame → QImage (copied, so the array can be freed)."""
    frame = np.ascontiguousarray(frame)
    h, w = frame.shape[:2]
    if frame.ndim == 2:
        return QImage(frame.data, w, h, w, QImage.Format.Format_Grayscale8).copy()
    rgb = np.ascontiguousarray(frame[:, :, ::-1])
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


class FrameSelector(QWidget):
    """Shows a frame; the user drags a rectangle. Coordinates are reported in image pixels and fractions."""

    selection_changed = Signal(QRectF)   # fractions of the image (0..1)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.image: QImage | None = None
        self.frame: np.ndarray | None = None
        self.sel: QRectF | None = None        # fractions
        self._drag_start: QPointF | None = None
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def set_frame(self, frame: np.ndarray) -> None:
        self.frame = frame
        self.image = to_qimage(frame)
        self.update()

    def set_selection(self, fractions: QRectF | None) -> None:
        self.sel = fractions
        self.update()

    def _target(self) -> QRectF:
        if self.image is None:
            return QRectF(self.rect())
        iw, ih = self.image.width(), self.image.height()
        scale = min(self.width() / iw, self.height() / ih)
        w, h = iw * scale, ih * scale
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _to_fraction(self, pos: QPointF) -> QPointF:
        t = self._target()
        x = min(1.0, max(0.0, (pos.x() - t.x()) / t.width()))
        y = min(1.0, max(0.0, (pos.y() - t.y()) / t.height()))
        return QPointF(x, y)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.image is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = self._to_fraction(event.position())
            self.sel = QRectF(self._drag_start, self._drag_start)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is not None:
            self.sel = QRectF(self._drag_start, self._to_fraction(event.position())).normalized()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is not None:
            self._drag_start = None
            if self.sel is not None and self.sel.width() > 0.005 and self.sel.height() > 0.005:
                self.selection_changed.emit(self.sel)

    def crop(self) -> np.ndarray | None:
        if self.frame is None or self.sel is None:
            return None
        h, w = self.frame.shape[:2]
        x0, y0 = int(self.sel.left() * w), int(self.sel.top() * h)
        x1, y1 = int(self.sel.right() * w), int(self.sel.bottom() * h)
        if x1 - x0 < 4 or y1 - y0 < 4:
            return None
        return self.frame[y0:y1, x0:x1].copy()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(20, 20, 20))
        t = self._target()
        if self.image is not None:
            p.drawImage(t, self.image)
        if self.sel is not None:
            r = QRectF(t.x() + self.sel.left() * t.width(), t.y() + self.sel.top() * t.height(),
                       self.sel.width() * t.width(), self.sel.height() * t.height())
            p.setPen(QPen(QColor(255, 60, 60), 2))
            p.drawRect(r)
        p.end()


class ClipPlayer:
    """Plays short WAV clips (voice bank) with QtMultimedia."""

    def __init__(self) -> None:
        self._player = None

    def play(self, path: Path) -> None:
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            return
        if self._player is None:
            self._player = QMediaPlayer()
            self._audio = QAudioOutput()
            self._player.setAudioOutput(self._audio)
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()


def confirm(parent: QWidget, title: str, text: str) -> bool:
    box = QMessageBox(QMessageBox.Icon.Question, title, text,
                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, parent)
    box.setDefaultButton(QMessageBox.StandardButton.Cancel)
    return box.exec() == QMessageBox.StandardButton.Yes


def show_error(parent: QWidget, title: str, exc_or_text: object) -> None:
    from app.messages import error_message

    code = getattr(exc_or_text, "code", None)
    text = error_message(code, str(exc_or_text))
    QMessageBox.warning(parent, title, text)


def fmt_ms(ms: int) -> str:
    s, ms = divmod(max(0, ms), 1000)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}.{ms // 100}"
