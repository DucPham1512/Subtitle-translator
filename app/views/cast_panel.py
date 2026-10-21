"""Review screen pieces that show the picture behind a line (6.4):

- BandView: the original subtitle pixels in the subtitle band (the preview masks them), to check OCR text.
- CastPanel: the frame the cast stage analysed with every character box (5.8b): recognised in green, unknown
  sprites in orange, boxes the reviewer drew in blue, the talking sprite outlined in red. The reviewer can
  correct names, move/resize boxes, draw a box around a missed character, and mark who is talking. All of it
  is one editable part of the line (cast_labels / cast_boxes / cast_added / cast_talking) and teaches the
  sprite bank when the review is finished.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from subagent.cast.cast import NOT_A_CHARACTER
from subagent.kernel.models import CastLine

GREEN, ORANGE, BLUE, RED = QColor(40, 200, 90), QColor(255, 150, 30), QColor(60, 150, 255), QColor(235, 40, 40)
REMOVE = "__remove__"
HANDLE = 8          # screen pixels around a corner that grab it for resizing
MIN_BOX = 12        # smallest box, screen pixels


def to_pixmap(img: np.ndarray, *, rgb: bool = False) -> QPixmap:
    if img.ndim == 2:                  # greyscale (OCR crops): same grey in all three channels
        img, rgb = np.repeat(img[:, :, None], 3, axis=2), True
    data = np.ascontiguousarray(img if rgb else img[:, :, ::-1])
    h, w = data.shape[:2]
    return QPixmap.fromImage(QImage(data.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy())


class ScaledImage(QLabel):
    """A pixmap drawn as large as the widget allows, keeping its aspect ratio; text when there is none."""

    def __init__(self, placeholder: str = ""):
        super().__init__(placeholder)
        self._pix: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(60)

    def set_pixmap(self, pix: QPixmap | None, text: str = "") -> None:
        self._pix = pix
        self.setText("" if pix is not None else text)
        self.update()

    def has_image(self) -> bool:
        return self._pix is not None and not self._pix.isNull()

    def image_rect(self) -> QRectF:
        if not self.has_image():
            return QRectF()
        size = self._pix.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        return QRectF((self.width() - size.width()) / 2, (self.height() - size.height()) / 2, size.width(),
                      size.height())

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.has_image():
            super().paintEvent(event)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(self.image_rect(), self._pix, QRectF(self._pix.rect()))
        self.paint_overlay(p)
        p.end()

    def paint_overlay(self, p: QPainter) -> None:
        pass


class BandView(ScaledImage):
    """The subtitle band: full width, height following the band's aspect ratio."""

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(24)
        self.setFixedHeight(40)

    def show_band(self, frame: np.ndarray | None, crop: tuple[int, int, int, int] | None, text: str = "") -> None:
        if frame is None or crop is None:
            self.set_pixmap(None, text)
        else:
            x, y, w, h = crop
            self.set_pixmap(to_pixmap(frame[y:y + h, x:x + w]))
        self._fit_height()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._fit_height()

    def _fit_height(self) -> None:
        if self.has_image() and self.width() > 10:
            ratio = self._pix.height() / max(1, self._pix.width())
            self.setFixedHeight(max(24, min(90, int(self.width() * ratio))))
        else:
            self.setFixedHeight(28)


class CastCanvas(ScaledImage):
    """The analysed frame with boxes drawn at screen scale; drag to move/resize, drag on empty space to draw."""

    moved = Signal(str, list)      # box key, new box (cast-frame coordinates)
    drawn = Signal(list)
    deleted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setMouseTracking(True)
        self.boxes: list[dict] = []    # {"key", "box", "color", "text", "talking"}
        self.frame_width = 960
        self.editable = False
        self.selected: str | None = None
        self._drag: tuple[str, str, QPointF, list[float]] | None = None   # (mode, key, start, original box)
        self._new: tuple[QPointF, QPointF] | None = None

    def _k(self) -> float:
        r = self.image_rect()
        return r.width() / self.frame_width if r.width() else 1.0

    def to_screen(self, box: list[float]) -> QRectF:
        r, k = self.image_rect(), self._k()
        return QRectF(r.x() + box[0] * k, r.y() + box[1] * k, (box[2] - box[0]) * k, (box[3] - box[1]) * k)

    def to_frame(self, pt: QPointF) -> tuple[float, float]:
        r, k = self.image_rect(), self._k()
        x = min(max(pt.x(), r.left()), r.right())
        y = min(max(pt.y(), r.top()), r.bottom())
        return (x - r.x()) / k, (y - r.y()) / k

    def paint_overlay(self, p: QPainter) -> None:
        font = QFont()
        font.setPixelSize(11)
        p.setFont(font)
        metrics = p.fontMetrics()
        for b in self.boxes:
            rect = self.to_screen(b["box"])
            if b["talking"]:
                p.setPen(QPen(RED, 4))
                p.drawRect(rect.adjusted(-3, -3, 3, 3))
            p.setPen(QPen(b["color"], 3 if b["key"] == self.selected else 2))
            p.drawRect(rect)
            tw, th = metrics.horizontalAdvance(b["text"]) + 6, metrics.height()
            p.fillRect(QRectF(rect.x() + 2, rect.y() + 2, tw, th), QColor(0, 0, 0, 150))
            p.setPen(b["color"])
            p.drawText(QRectF(rect.x() + 5, rect.y() + 2, tw, th), Qt.AlignmentFlag.AlignVCenter, b["text"])
            if self.editable and b["key"] == self.selected:
                for c in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                    p.fillRect(QRectF(c.x() - 3, c.y() - 3, 6, 6), b["color"])
        if self._new:
            p.setPen(QPen(BLUE, 2, Qt.PenStyle.DashLine))
            p.drawRect(QRectF(self._new[0], self._new[1]).normalized())

    def _hit(self, pt: QPointF) -> tuple[str, str] | None:
        """(mode, key): mode is a corner name for resizing or "move"; the topmost (last drawn) box wins."""
        for b in reversed(self.boxes):
            rect = self.to_screen(b["box"])
            for name, c in (("tl", rect.topLeft()), ("tr", rect.topRight()), ("bl", rect.bottomLeft()),
                            ("br", rect.bottomRight())):
                if abs(pt.x() - c.x()) <= HANDLE and abs(pt.y() - c.y()) <= HANDLE:
                    return name, b["key"]
            if rect.contains(pt):
                return "move", b["key"]
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.editable or not self.has_image() or event.button() != Qt.MouseButton.LeftButton:
            return
        pt = event.position()
        hit = self._hit(pt)
        if hit:
            mode, key = hit
            self.selected = key
            box = next(b["box"] for b in self.boxes if b["key"] == key)
            self._drag = (mode, key, pt, list(box))
        elif self.image_rect().contains(pt):
            self.selected = None
            self._new = (pt, pt)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        pt = event.position()
        if self._new:
            self._new = (self._new[0], pt)
        elif self._drag:
            mode, key, start, orig = self._drag
            sx, sy = self.to_frame(start)
            ex, ey = self.to_frame(pt)
            dx, dy = ex - sx, ey - sy
            x0, y0, x1, y1 = orig
            if mode == "move":
                x0, x1, y0, y1 = x0 + dx, x1 + dx, y0 + dy, y1 + dy
            else:
                if "l" in mode:
                    x0 += dx
                if "r" in mode:
                    x1 += dx
                if "t" in mode:
                    y0 += dy
                if "b" in mode:
                    y1 += dy
            for b in self.boxes:
                if b["key"] == key:
                    b["box"] = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        elif self.editable:
            hit = self._hit(pt)
            cursor = Qt.CursorShape.CrossCursor
            if hit and hit[0] in ("tl", "br"):
                cursor = Qt.CursorShape.SizeFDiagCursor
            elif hit and hit[0] in ("tr", "bl"):
                cursor = Qt.CursorShape.SizeBDiagCursor
            elif hit:
                cursor = Qt.CursorShape.SizeAllCursor
            self.setCursor(cursor)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._new:
            a, b = self._new
            self._new = None
            if abs(a.x() - b.x()) >= MIN_BOX and abs(a.y() - b.y()) >= MIN_BOX:
                (x0, y0), (x1, y1) = self.to_frame(a), self.to_frame(b)
                self.drawn.emit([round(min(x0, x1), 1), round(min(y0, y1), 1), round(max(x0, x1), 1),
                                 round(max(y0, y1), 1)])
        elif self._drag:
            _, key, _, orig = self._drag
            self._drag = None
            box = next(b["box"] for b in self.boxes if b["key"] == key)
            if [round(v, 1) for v in box] != [round(v, 1) for v in orig]:
                self.moved.emit(key, [round(v, 1) for v in box])
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.editable and self.selected and self.selected.startswith("a") and event.key() in (
                Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleted.emit(self.selected)
            self.selected = None
            return
        super().keyPressEvent(event)


class CastPanel(QWidget):
    """Picture (where the player is in the Line view) + legend and table (where the editor is).

    Emits `review_changed` with the line's four reviewer fields after every change."""

    review_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image = CastCanvas()
        self.image.moved.connect(self._moved)
        self.image.drawn.connect(self._drawn)
        self.image.deleted.connect(self._remove_added)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([self.tr("Box"), self.tr("Recognised as"), self.tr("Talking"),
                                              self.tr("Correct to")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.note = QLabel()
        self.note.setWordWrap(True)
        # picture where the player is in the Line view, legend + table where the editor is
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.addWidget(self.image)
        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.addWidget(self.note)
        lower_layout.addWidget(self.table, 1)
        self.checked = QCheckBox(self.tr("On screen checked: every box and the talking mark are right"))
        self.checked.setToolTip(self.tr(
            "Tick after correcting this line's boxes, names and talking mark. A box you left alone then counts as "
            "confirmed, which makes the line usable for measuring character recognition."))
        self.checked.toggled.connect(self._checked_toggled)
        lower_layout.addWidget(self.checked)
        self.split.addWidget(lower)
        self.split.setSizes([380, 420])
        layout.addWidget(self.split, 1)
        self._cast: CastLine | None = None
        self._names: dict[str, str] = {}
        self._review: dict = {"cast_labels": {}, "cast_boxes": {}, "cast_added": [], "cast_talking": None,
                              "cast_checked": False}
        self._editable = False
        self._loading = False

    # -- state ---------------------------------------------------------------------------------------

    def show_line(self, frame: np.ndarray | None, cast: CastLine | None, review: dict, names: dict[str, str],
                  frame_width: int, editable: bool, missing: str = "", *, rgb: bool = False) -> None:
        """frame: the analysed frame (RGB when `rgb`, else BGR); boxes are in `frame_width`-wide coordinates."""
        self._cast, self._names, self._editable = cast, names, editable
        self._review = {"cast_labels": dict(review.get("cast_labels") or {}),
                        "cast_boxes": {k: list(v) for k, v in (review.get("cast_boxes") or {}).items()},
                        "cast_added": [dict(a) for a in (review.get("cast_added") or [])],
                        "cast_talking": review.get("cast_talking"),
                        "cast_checked": bool(review.get("cast_checked"))}
        self.checked.blockSignals(True)
        self.checked.setChecked(self._review["cast_checked"])
        self.checked.setEnabled(editable and cast is not None)
        self.checked.blockSignals(False)
        self.image.frame_width = frame_width
        self.image.editable = editable and frame is not None
        self.image.set_pixmap(to_pixmap(frame, rgb=rgb) if frame is not None else None, missing)
        if frame is None:
            self.note.setText(missing)
        elif editable:
            self.note.setText(self.tr(
                "Green: recognised · orange: not recognised · blue: drawn by you · red outline: talking. Drag a box "
                "to move it, drag a corner to resize, drag on empty space to draw a box around a missed character "
                "(Delete removes a drawn box). Your corrections teach the sprite bank when you finish the review."))
        else:
            self.note.setText(self.tr("Green: recognised · orange: not recognised · blue: drawn by you · "
                                      "red outline: talking."))
        self._refresh()

    def _talking_key(self) -> str | None:
        t = self._review["cast_talking"]
        if t == "none":
            return None
        if t:
            return t
        return str(self._cast.talking) if self._cast and self._cast.talking is not None else None

    def _refresh(self) -> None:
        self._loading = True
        talking = self._talking_key()
        labels = self._review["cast_labels"]
        boxes: list[dict] = []
        rows: list[tuple[str, str, str]] = []          # key, box column, recognised column
        for pos, d in enumerate(self._cast.detections if self._cast else []):
            key = str(pos)
            label = labels.get(key)
            if label == NOT_A_CHARACTER:
                who, color = self.tr("not a character"), ORANGE
            elif label:
                who, color = self._names.get(label, label), GREEN
            elif d.character:
                who, color = self._names.get(d.character, d.character), GREEN
            else:
                who, color = d.unknown or "?", ORANGE
            boxes.append({"key": key, "box": self._review["cast_boxes"].get(key, d.box), "color": color,
                          "text": f"{pos + 1} {who}", "talking": talking == key})
            seen = self._names.get(d.character, d.character) if d.character else self.tr("unknown ({id})").format(
                id=d.unknown)
            rows.append((key, str(pos + 1), f"{seen}  {d.similarity:.2f}"))
        for i, a in enumerate(self._review["cast_added"]):
            key = f"a{i}"
            who = self._names.get(a.get("character"), a.get("character")) if a.get("character") else "?"
            boxes.append({"key": key, "box": a["box"], "color": BLUE, "text": f"A{i + 1} {who}",
                          "talking": talking == key})
            rows.append((key, f"A{i + 1}", self.tr("drawn by you")))
        self.image.boxes = boxes
        self.image.update()
        self.table.setRowCount(0)
        for row, (key, box_text, seen) in enumerate(rows):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(box_text))
            self.table.setItem(row, 1, QTableWidgetItem(seen))
            check = QCheckBox()
            check.setChecked(talking == key)
            check.setEnabled(self._editable)
            check.toggled.connect(lambda on, k=key: self._talking(k, on))
            self.table.setCellWidget(row, 2, check)
            combo = QComboBox()
            combo.addItem(self.tr("(choose a character)") if key.startswith("a") else self.tr("(as recognised)"),
                          None)
            for cid, name in sorted(self._names.items(), key=lambda kv: kv[1]):
                combo.addItem(f"{name} ({cid})", cid)
            if key.startswith("a"):
                combo.addItem(self.tr("Remove this box"), REMOVE)
                current = self._review["cast_added"][int(key[1:])].get("character")
            else:
                combo.addItem(self.tr("Not a character"), NOT_A_CHARACTER)
                current = labels.get(key)
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.setEnabled(self._editable)
            combo.currentIndexChanged.connect(lambda _, k=key, c=combo: self._named(k, c.currentData()))
            self.table.setCellWidget(row, 3, combo)
        self._loading = False

    def review(self) -> dict:
        return {"cast_labels": dict(self._review["cast_labels"]),
                "cast_boxes": {k: list(v) for k, v in self._review["cast_boxes"].items()},
                "cast_added": [dict(a) for a in self._review["cast_added"]],
                "cast_talking": self._review["cast_talking"],
                "cast_checked": self._review["cast_checked"]}

    def _emit(self) -> None:
        self._refresh()
        self.review_changed.emit(self.review())

    def _checked_toggled(self, on: bool) -> None:
        if self._loading or not self._editable:
            return
        self._review["cast_checked"] = on
        self._emit()

    def toggle_checked(self) -> None:
        """Keyboard: tick / untick "On screen checked"."""
        if self.checked.isEnabled():
            self.checked.setChecked(not self.checked.isChecked())

    # -- edits ---------------------------------------------------------------------------------------

    def _named(self, key: str, value: str | None) -> None:
        if self._loading:
            return
        if key.startswith("a"):
            if value == REMOVE:
                self._remove_added(key)
                return
            self._review["cast_added"][int(key[1:])]["character"] = value
        elif value is None:
            self._review["cast_labels"].pop(key, None)
        else:
            self._review["cast_labels"][key] = value
        self._emit()

    def _talking(self, key: str, on: bool) -> None:
        if self._loading:
            return
        self._review["cast_talking"] = key if on else "none"
        self._emit()

    def _moved(self, key: str, box: list) -> None:
        if key.startswith("a"):
            self._review["cast_added"][int(key[1:])]["box"] = box
        else:
            self._review["cast_boxes"][key] = box
        self._emit()

    def _drawn(self, box: list) -> None:
        self._review["cast_added"].append({"box": box, "character": None})
        self.image.selected = f"a{len(self._review['cast_added']) - 1}"
        self._emit()

    def _remove_added(self, key: str) -> None:
        i = int(key[1:])
        del self._review["cast_added"][i]
        t = self._review["cast_talking"]
        if t == key:
            self._review["cast_talking"] = None
        elif t and t.startswith("a") and int(t[1:]) > i:
            self._review["cast_talking"] = f"a{int(t[1:]) - 1}"
        self._emit()
