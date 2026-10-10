"""Who is this character? (6.4) The review screen's card strip under the speaker row and the character browser:
picture, first episode, description and a voice sample per id, so a returning NPC gets the id it had before."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.widgets import ClipPlayer
from app.workers import run_async

PICTURE_H = 56


def _pixmap(card, height: int = PICTURE_H) -> QPixmap | None:
    if card is None or card.picture is None:
        return None
    pix = QPixmap(str(card.picture))
    return None if pix.isNull() else pix.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)


def describe(widget: QWidget, card) -> str:
    """One line about a card, in the interface language."""
    parts = [f"{card.name} ({card.id})" if card.name != card.id else card.id]
    if card.kind == "candidate":
        parts.append(widget.tr("on probation"))
    if card.first_episode:
        parts.append(widget.tr("first seen {ep}").format(ep=card.first_episode))
    if card.description:
        parts.append(card.description)
    if getattr(card, "aliases", None):
        parts.append(widget.tr("called {names}").format(names=", ".join(card.aliases)))
    if card.source == "pinned":
        parts.append(widget.tr("sample chosen by you"))
    elif card.source == "none":
        parts.append(widget.tr("no reviewed line yet"))
    return " · ".join(parts)


class CharacterStrip(QWidget):
    """Picture, first episode, description and ▶ for the line's speaker."""

    def __init__(self, player: ClipPlayer, parent: QWidget | None = None):
        super().__init__(parent)
        self.player = player
        self.card = None
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.picture = QLabel()
        self.picture.setFixedSize(PICTURE_H, PICTURE_H)
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(36)
        self.play_btn.setToolTip(self.tr("Play a line this character speaks in an earlier episode"))
        self.play_btn.clicked.connect(self._play)
        self.use_btn = QPushButton(self.tr("Use this line"))
        self.use_btn.setToolTip(self.tr(
            "Make this line the speaker's sample: its voice, and the character marked talking in On screen as the "
            "picture (nobody marked talking: no picture, e.g. for a narrator). Changes the card only."))
        row.addWidget(self.picture)
        row.addWidget(self.text, 1)
        row.addWidget(self.play_btn)
        row.addWidget(self.use_btn)
        self.clear()

    def clear(self, text: str = "") -> None:
        self.card = None
        self.picture.clear()
        self.text.setText(text)
        self.play_btn.setEnabled(False)

    def show_card(self, card) -> None:
        self.card = card
        pix = _pixmap(card)
        if pix is None:
            self.picture.clear()
        else:
            self.picture.setPixmap(pix)
        self.text.setText(describe(self, card))
        self.play_btn.setEnabled(card.clip is not None)

    def _play(self) -> None:
        if self.card is not None and self.card.clip is not None:
            self.player.play(self.card.clip)


class CharacterBrowser(QDialog):
    """Every id the line can take, with its card; "Use as speaker / listener" assigns it."""

    def __init__(self, parent: QWidget, ids: dict[str, str], load: Callable[[str], object],
                 player: ClipPlayer, read_only: bool = False):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Browse characters"))
        self.resize(820, 560)
        self.player = player
        self.choice: tuple[str, str] | None = None        # (speaker | listener, id)
        self.cards: dict[str, object] = {}
        box = QVBoxLayout(self)
        box.addWidget(QLabel(self.tr("Pictures and voice samples come from a line each character speaks in an "
                                     "episode you reviewed. Pick the one who speaks here.")))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self.tr("Picture"), self.tr("Character"), self.tr("Voice")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(PICTURE_H + 8)
        self.ids = sorted(ids, key=lambda c: ids[c])
        for row, cid in enumerate(self.ids):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem())
            item = QTableWidgetItem(ids[cid])
            item.setData(Qt.ItemDataRole.UserRole, cid)
            self.table.setItem(row, 1, item)
            play = QPushButton("▶")
            play.setEnabled(False)
            play.clicked.connect(lambda _=False, c=cid: self._play(c))
            self.table.setCellWidget(row, 2, play)
            run_async(lambda c=cid: load(c), lambda card, r=row: self._loaded(r, card))
        box.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        self.speaker_btn = QPushButton(self.tr("Use as speaker"))
        self.listener_btn = QPushButton(self.tr("Use as listener"))
        close = QPushButton(self.tr("Close"))
        self.speaker_btn.clicked.connect(lambda: self._choose("speaker"))
        self.listener_btn.clicked.connect(lambda: self._choose("listener"))
        close.clicked.connect(self.reject)
        for b in (self.speaker_btn, self.listener_btn):
            b.setEnabled(not read_only)
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(close)
        box.addLayout(buttons)

    def _loaded(self, row: int, card) -> None:
        try:
            if row >= self.table.rowCount():
                return
        except RuntimeError:                  # the dialog closed before this card finished loading
            return
        self.cards[card.id] = card
        self.table.item(row, 1).setText(describe(self, card))
        pix = _pixmap(card)
        if pix is not None:
            label = QLabel()
            label.setPixmap(pix)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 0, label)
        widget = self.table.cellWidget(row, 2)
        if widget is not None:
            widget.setEnabled(card.clip is not None)

    def _play(self, cid: str) -> None:
        card = self.cards.get(cid)
        if card is not None and card.clip is not None:
            self.player.play(card.clip)

    def selected_id(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        return self.table.item(rows[0].row(), 1).data(Qt.ItemDataRole.UserRole) if rows else None

    def _choose(self, role: str) -> None:
        cid = self.selected_id()
        if cid is not None:
            self.choice = (role, cid)
            self.accept()
