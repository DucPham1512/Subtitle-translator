"""Review screen (6.4): flagged lines first, editor with live checks, live preview, keyboard-only workflow.

The review screen never calls an LLM. It only edits review_draft.jsonl (autosaved, atomic writes).
"""

from __future__ import annotations

import html
import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app import shortcuts
from app.messages import error_message, flag_label, status_label
from app.preview import PreviewWidget
from app.services import ReviewData
from app.views.audit import AuditBar
from app.views.cast_panel import BandView, CastPanel
from app.views.common import choose_on_exists, job_busy
from app.widgets import confirm, fmt_ms, show_error
from app.workers import run_async
from subagent.kernel.models import LineTranslation, ReviewedLine
from subagent.stages.review import FLAG_ORDER, RULE_WARNING_FLAGS, needs_attention, review_order

LINE_TYPES = ["dialogue", "sign", "title", "sfx"]


class ReviewView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self._init_state()
        layout = QVBoxLayout(self)
        layout.addLayout(self._build_toolbar())
        self._build_banner(layout)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_line_table())
        right = QSplitter(Qt.Orientation.Vertical)
        self.preview = PreviewWidget()
        right.addWidget(self.preview)
        editor, buttons = self._build_editor()
        split.addWidget(self._build_right_side(right, editor, buttons))
        split.setSizes([620, 700])
        layout.addWidget(split, 1)
        self.editor = editor
        self._connect_editor()
        self._init_timers()

    def _init_state(self) -> None:
        """The episode and line state the screen works on."""
        self.services = self.main.services
        self.data: ReviewData | None = None
        self.lines: dict[str, ReviewedLine] = {}
        self.order: list[str] = []
        self.visible: list[str] = []
        self.current: str | None = None
        self.undo: dict[str, list[ReviewedLine]] = {}
        self.redo: dict[str, list[ReviewedLine]] = {}
        self._last_push: tuple[str, str, float] = ("", "", 0.0)
        self._loading = False
        self._saving = False
        self._save_pending = False
        self.engine = None
        self.rules = None
        self.characters: dict[str, str] = {}
        self._finish_job = ""

    def _build_toolbar(self) -> QHBoxLayout:
        """Episode picker, counter and the line list filters."""
        top = QHBoxLayout()
        top.addWidget(QLabel(self.tr("Episode:")))
        self.episode_box = QComboBox()
        self.episode_box.setMinimumWidth(220)
        self.episode_box.activated.connect(lambda _: self.open_episode(self.episode_box.currentData()))
        top.addWidget(self.episode_box)
        self.counter = QLabel()
        self.counter.setStyleSheet("font-weight: bold;")
        top.addWidget(self.counter, 1)
        self.flag_filter = QComboBox()
        self.speaker_filter = QComboBox()
        self.unapproved = QCheckBox(self.tr("Unapproved only"))
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search Chinese and Vietnamese…"))
        self.search.setClearButtonEnabled(True)
        self.speaker_filter_label = QLabel(self.tr("Speaker:"))
        for w in (QLabel(self.tr("Flag:")), self.flag_filter, self.speaker_filter_label, self.speaker_filter,
                  self.unapproved, self.search):
            top.addWidget(w)
        self.flag_filter.currentIndexChanged.connect(self._apply_filters)
        self.speaker_filter.currentIndexChanged.connect(self._apply_filters)
        self.unapproved.toggled.connect(self._apply_filters)
        self.search.textChanged.connect(self._apply_filters)
        return top

    def _build_banner(self, layout: QVBoxLayout) -> None:
        """Shown when the episode's review is finished."""
        self.read_only_banner = QLabel(self.tr("Read-only: this episode's review is finished."))
        self.read_only_banner.setStyleSheet("background: #fff3cd; color: #664d03; padding: 4px;")
        self.read_only_banner.hide()
        layout.addWidget(self.read_only_banner)

    def _build_line_table(self) -> QTableWidget:
        """The line list (left)."""
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([self.tr("State"), self.tr("Time"), self.tr("Speaker → listener"),
                                              self.tr("Chinese"), self.tr("Vietnamese")])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.currentCellChanged.connect(lambda row, *_: self._select_row(row))
        return self.table

    def _build_editor(self) -> tuple[QWidget, QHBoxLayout]:
        """The line editor and the action buttons (returned for the right side's bottom row)."""
        editor = QWidget()
        form_layout = QVBoxLayout(editor)
        form = QFormLayout()
        self.zh = QLineEdit()
        pinyin_row = QHBoxLayout()
        self.pinyin = QLineEdit()
        self.regen = QPushButton(self.tr("Regenerate"))
        self.regen.setToolTip(self.tr("Discard the manual pinyin and generate it from the Chinese text"))
        pinyin_row.addWidget(self.pinyin, 1)
        pinyin_row.addWidget(self.regen)
        self.vi = QPlainTextEdit()
        self.vi.setFixedHeight(64)
        self.speaker = QComboBox()
        self.listener = QComboBox()
        self.line_type = QComboBox()
        for t in LINE_TYPES:
            self.line_type.addItem({"dialogue": self.tr("Dialogue"), "sign": self.tr("Sign"),
                                    "title": self.tr("Title"), "sfx": self.tr("Sound effect")}[t], t)
        who = self._build_who_row()
        form.addRow(self.tr("Chinese"), self.zh)
        self.band = BandView()
        self.band.setToolTip(self.tr("The original subtitle in the video at this line (the preview hides it)"))
        form.addRow(self.tr("Original"), self.band)
        self.ocr_crop = BandView()
        self.ocr_crop.setToolTip(self.tr("What OCR read for this line after pre-processing (segmentation and "
                                         "cropping), at its position in the band; grey was not read"))
        form.addRow(self.tr("OCR read"), self.ocr_crop)
        form.addRow(self.tr("Pinyin"), pinyin_row)
        form.addRow(self.tr("Vietnamese"), self.vi)
        form.addRow(self.tr("Speaker → listener"), who)
        self.form, self.who = form, who
        from app.views.character_browser import CharacterStrip
        from app.widgets import ClipPlayer

        self.clip_player = ClipPlayer()
        self.card_strip = CharacterStrip(self.clip_player)
        self.card_strip.setToolTip(self.tr("Who the speaker is: picture, first episode, description and a voice "
                                           "sample from an episode you reviewed"))
        form.addRow("", self.card_strip)
        self.card_strip.use_btn.clicked.connect(self._pin_card)
        self._card_for: str | None = None
        form_layout.addLayout(form)
        self.warnings = QLabel()
        self.warnings.setWordWrap(True)
        self.warnings.setStyleSheet("color: #b35c00;")
        form_layout.addWidget(self.warnings)
        self.context = QTextBrowser()
        self.context.setOpenLinks(False)
        form_layout.addWidget(self.context, 1)
        buttons = self._build_action_buttons()
        return editor, buttons

    def _build_who_row(self) -> QHBoxLayout:
        """Speaker → listener, line type, and the character buttons (new character, new NPC, browse, suggestion)."""
        who = QHBoxLayout()
        who.addWidget(self.speaker, 1)
        self.who_arrow = QLabel("→")
        who.addWidget(self.who_arrow)
        who.addWidget(self.listener, 1)
        who.addWidget(self.line_type)
        self.new_char_btn = QPushButton(self.tr("New character…"))
        self.new_char_btn.setToolTip(self.tr("Add a character to memory and assign it to this line"))
        self.new_char_btn.clicked.connect(self._new_character)
        who.addWidget(self.new_char_btn)
        self.new_npc_btn = QPushButton(self.tr("New NPC"))
        self.new_npc_btn.setToolTip(self.tr(
            "Give this line's speaker a new automatic id (npc_<episode>_<n>) without saving anything to memory. "
            "Use the same id on the character's other lines: at Finish review, with at least 3 approved lines as "
            "speaker it goes on probation, and becomes a character only if it speaks again in the next 2 episodes."))
        self.new_npc_btn.clicked.connect(self._new_npc)
        who.addWidget(self.new_npc_btn)
        self.browse_btn = QPushButton(self.tr("Browse characters…"))
        self.browse_btn.setToolTip(self.tr("See every character's picture, first episode and voice sample, and "
                                           "assign one to this line"))
        self.browse_btn.clicked.connect(self._browse_characters)
        who.addWidget(self.browse_btn)
        self.suggest_btn = QPushButton()
        self.suggest_btn.setToolTip(self.tr("Use the speaker Partial review suggests (the line is then flagged so you "
                                            "check its pronouns)"))
        self.suggest_btn.clicked.connect(self._use_suggestion)
        self.suggest_btn.hide()
        who.addWidget(self.suggest_btn)
        return who

    def _build_action_buttons(self) -> QHBoxLayout:
        """Approve, finish, reset, delete, discard and partial review (shown under both right-side views)."""
        buttons = QHBoxLayout()
        self.approve_btn = QPushButton(self.tr("Approve and next"))
        self.approve_rest_btn = QPushButton(self.tr("Approve all remaining non-flagged…"))
        self.finish_btn = QPushButton(self.tr("Finish review…"))
        self.finish_btn.setStyleSheet("font-weight: bold;")
        self.reset_btn = QPushButton(self.tr("Reset line"))
        self.reset_btn.setToolTip(self.tr("Undo every review change to this line (back to the pipeline's version)"))
        self.delete_btn = QPushButton(self.tr("Delete line"))
        self.delete_btn.setToolTip(self.tr("Remove this line from the video (e.g. OCR noise). It can be restored."))
        self.discard_btn = QPushButton(self.tr("Discard review…"))
        self.partial_btn = QPushButton(self.tr("Partial review…"))
        self.partial_btn.setToolTip(self.tr(
            "Learn from the lines you approved so far (speakers, talking marks, character boxes, voices) and "
            "re-check the remaining lines. Nothing is saved to memory until you finish the review."))
        self.partial_btn.clicked.connect(self._partial_review)
        for b in (self.approve_btn, self.approve_rest_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        for b in (self.reset_btn, self.delete_btn, self.discard_btn, self.partial_btn, self.finish_btn):
            buttons.addWidget(b)
        return buttons

    def _build_right_side(self, right: QSplitter, editor: QWidget, buttons: QHBoxLayout) -> QWidget:
        """Line / On screen tabs, the audit bar and the action buttons."""
        right.addWidget(editor)
        right.setSizes([380, 420])
        # the right side switches between the line (player + editor) and the characters on screen
        # (picture in the player's place, recognition table in the editor's place)
        self.cast_panel = CastPanel()
        self.cast_panel.review_changed.connect(self._cast_review_changed)
        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(right, self.tr("Line"))
        self.right_tabs.addTab(self.cast_panel, self.tr("On screen"))
        self.right_tabs.currentChanged.connect(self._right_tab_changed)
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.right_tabs, 1)
        self.audit_bar = AuditBar()                       # audit mode only (6.11)
        self.audit_bar.changed.connect(self._audit_changed)
        self.audit_bar.all_correct.connect(self._audit_all_correct)
        self.audit_bar.next_unmarked.connect(self._audit_next)
        self.audit_bar.hide()
        right_layout.addWidget(self.audit_bar)
        right_layout.addLayout(buttons)                   # approve / finish stay visible in both views
        return right_box

    def _connect_editor(self) -> None:
        """Editor fields and action buttons to their handlers."""
        self.zh.textEdited.connect(lambda t: self._edit("zh", t))
        self.pinyin.textEdited.connect(lambda t: self._edit("pinyin", t))
        self.vi.textChanged.connect(lambda: self._edit("vi", self.vi.toPlainText()))
        self.speaker.currentIndexChanged.connect(lambda _: self._edit("speaker", self.speaker.currentData()))
        self.speaker.currentIndexChanged.connect(lambda _: self._show_card())
        self.listener.currentIndexChanged.connect(lambda _: self._edit("listener", self.listener.currentData()))
        self.line_type.currentIndexChanged.connect(lambda _: self._edit("line_type", self.line_type.currentData()))
        self.regen.clicked.connect(self._regenerate_pinyin)
        self.approve_btn.clicked.connect(self.approve_and_next)
        self.approve_rest_btn.clicked.connect(self._approve_rest)
        self.finish_btn.clicked.connect(self._finish)
        self.reset_btn.clicked.connect(self._reset_line)
        self.delete_btn.clicked.connect(self._toggle_delete)
        self.discard_btn.clicked.connect(self._discard_review)
        self.originals: dict[str, ReviewedLine] = {}
        self.main.jobs.finished.connect(self._job_finished)

    def _init_timers(self) -> None:
        """Debounce timers, audit state and keyboard shortcuts."""
        self._save_timer = self._timer(1000, self._save)
        self._preview_timer = self._timer(300, self._refresh_preview)
        self._rules_timer = self._timer(150, self._check_rules)
        self._picture_timer = self._timer(150, self._load_picture)
        self._frames: dict[str, tuple] = {}       # event id -> (frame, band crop), most recent lines
        self._partial_job = ""
        self.audit_mode = False
        self.audit_sample: dict = {}
        self.audit_marks: dict = {}
        self._audit_timer = self._timer(500, self._save_audit)
        self._shortcuts: list[QShortcut] = []
        self._install_shortcuts()
        self._set_enabled(False)

    def _timer(self, ms: int, slot) -> QTimer:
        t = QTimer(self)
        t.setSingleShot(True)
        t.setInterval(ms)
        t.timeout.connect(slot)
        return t

    # -- shortcuts ----------------------------------------------------------------------------------

    def _install_shortcuts(self) -> None:
        for s in self._shortcuts:
            s.setParent(None)
        self._shortcuts = []
        actions = {
            "approve_next": self.approve_and_next,
            "delete_line": self._toggle_delete,
            "next_line": lambda: self._move(1),
            "prev_line": lambda: self._move(-1),
            "replay": self.preview.replay,
            "play_pause": self.preview.toggle_pause,
            "toggle_loop": lambda: self.preview.set_loop(not self.preview._loop),
            "focus_vi": lambda: self.vi.setFocus(),
            "undo": self._undo,
            "redo": self._redo,
            "search": lambda: (self.search.setFocus(), self.search.selectAll()),
            "cast_checked": self.cast_panel.toggle_checked,
        }
        for action, slot in actions.items():
            sc = QShortcut(shortcuts.sequence(action), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)
            self._shortcuts.append(sc)

    # -- loading ------------------------------------------------------------------------------------

    def activate(self) -> None:
        self._install_shortcuts()
        self._fill_episode_box()
        if self.data is None and self.episode_box.count():
            self.open_episode(self.episode_box.currentData())

    def _fill_episode_box(self) -> None:
        current = self.data.episode.id if self.data else None
        self.episode_box.blockSignals(True)
        self.episode_box.clear()
        for ep in self.services.review_candidates():
            self.episode_box.addItem(f"{ep.id} — {status_label(ep.status)}", ep.id)
        if current:
            self.episode_box.setCurrentIndex(max(0, self.episode_box.findData(current)))
        self.episode_box.blockSignals(False)
        if not self.episode_box.count():
            self.counter.setText(self.tr("No episode is waiting for review. Run an episode in human mode first."))

    def open_episode(self, episode_id: str | None, *, event_id: str | None = None, read_only: bool | None = None,
                     audit: bool = False) -> None:
        if not episode_id:
            return
        self.flush()
        self._fill_episode_box()
        self.audit_mode = audit
        self.audit_bar.setVisible(audit)
        self.audit_sample, self.audit_marks = {}, {}

        def load():
            data = self.services.load_review(episode_id, read_only=True if audit else read_only)
            if audit:
                self.audit_sample, self.audit_marks = self.services.audit_data(episode_id)
            engine = self.services.pinyin_engine()
            rules = self.services.rule_context(episode_id)
            chars = {c.id: c.name_vi + (" " + self.tr("(archived)") if c.archived else "")
                     for c in self.services.store.characters()}
            for vid, kind in self.services.episode_voices(episode_id).items():
                chars.setdefault(vid, self._voice_label(vid, kind))
            return data, engine, rules, chars, self.services.original_lines(episode_id)

        def loaded(result) -> None:
            if self.audit_mode and not event_id:
                first = next(iter(e for e in self.audit_sample if e not in self.audit_marks), None)
                self._loaded(*result, event_id=first or next(iter(self.audit_sample), None))
            else:
                self._loaded(*result, event_id=event_id)

        run_async(load, loaded, lambda exc: show_error(self, self.tr("Review"), exc))

    def _loaded(self, data: ReviewData, engine, rules, chars: dict[str, str], originals: dict[str, ReviewedLine], *,
                event_id: str | None) -> None:
        self.data, self.engine, self.rules, self.characters = data, engine, rules, chars
        self.originals = originals
        self.lines = {line.event_id: line for line in data.lines}
        self.undo, self.redo = {}, {}
        idx = self.episode_box.findData(data.episode.id)
        if idx < 0:
            self.episode_box.addItem(f"{data.episode.id} — {status_label(data.episode.status)}", data.episode.id)
            idx = self.episode_box.count() - 1
        self.episode_box.setCurrentIndex(idx)
        self.read_only_banner.setVisible(data.read_only)
        self._fill_filters()
        self._fill_character_boxes()
        self._resort()
        self._set_enabled(True)
        self._open_preview()
        target = event_id or QSettings().value(f"review/{data.episode.id}/last")
        self._apply_filters(select=str(target) if target else None)

    def _fill_filters(self) -> None:
        for box in (self.flag_filter, self.speaker_filter):
            box.blockSignals(True)
            box.clear()
        self.flag_filter.addItem(self.tr("All"), None)
        for f in FLAG_ORDER:
            self.flag_filter.addItem(flag_label(f), f)
        self.flag_filter.addItem(flag_label("rule_warnings"), "rule_warnings")
        self.speaker_filter.addItem(self.tr("All"), None)
        for cid, name in sorted(self.characters.items(), key=lambda kv: kv[1]):
            self.speaker_filter.addItem(f"{name} ({cid})", cid)
        for box in (self.flag_filter, self.speaker_filter):
            box.blockSignals(False)

    def _fill_character_boxes(self) -> None:
        line = self.lines.get(self.current) if self.current else None
        for box, value in ((self.speaker, line.speaker if line else None),
                           (self.listener, line.listener if line else None)):
            box.blockSignals(True)
            box.clear()
            box.addItem("—", None)
            for cid, name in sorted(self.characters.items(), key=lambda kv: kv[1]):
                box.addItem(f"{name} ({cid})", cid)
            box.setCurrentIndex(max(0, box.findData(value)))    # refilling keeps the line's choice shown
            box.blockSignals(False)

    def _new_character(self) -> None:
        """Create a character without leaving review; saved through the Memory Manager as a human edit."""
        from app.views.character_dialog import NewCharacterDialog

        if self.data is None or self.data.read_only:
            return
        dialog = NewCharacterDialog(self, set(self.characters), self.zh.selectedText().strip())
        if dialog.exec():
            self.create_character(dialog.data())

    def _card_loader(self):
        ep_id = self.data.episode.id
        draft = [line.model_copy() for line in self.lines.values()]
        return lambda cid: self.services.character_card(ep_id, cid, draft)

    def _show_card(self) -> None:
        """The speaker's card under the speaker row (picture, first episode, description, voice sample)."""
        cid = self.speaker.currentData()
        self.card_strip.use_btn.setEnabled(bool(cid) and self.data is not None and not self.data.read_only)
        if cid == self._card_for:
            return
        self._card_for = cid
        if self.data is None or cid is None:
            self.card_strip.clear()
            return
        self.card_strip.clear(self.tr("Loading…"))
        load = self._card_loader()

        def done(card) -> None:
            if self._card_for == card.id:          # still the speaker shown
                self.card_strip.show_card(card)

        run_async(lambda: load(cid), done, lambda exc: self.card_strip.clear(str(exc)))

    def _pin_card(self) -> None:
        """"Use this line": the current line becomes its speaker's card sample (voice + the talking box shown in On
        screen, none: no picture). The card only; memory learns nothing from it."""
        if self.data is None or self.data.read_only or self.current is None:
            return
        line = self.lines[self.current].model_copy(deep=True)
        if not line.speaker:
            return
        ep_id, cast = self.data.episode.id, self.data.cast.get(line.event_id)

        def done(_) -> None:
            self._card_for = None                  # reload the card with the new sample
            self._show_card()

        self.card_strip.clear(self.tr("Saving the sample…"))
        run_async(lambda: self.services.pin_character_card(ep_id, line, cast), done,
                  lambda exc: show_error(self, self.tr("Use this line"), exc))

    def _browse_characters(self) -> None:
        from app.views.character_browser import CharacterBrowser

        if self.data is None:
            return
        dialog = CharacterBrowser(self, dict(self.characters), self._card_loader(), self.clip_player,
                                  read_only=self.data.read_only or self.current is None)
        dialog.exec()
        choice = dialog.choice
        dialog.deleteLater()
        if choice is not None and self.current is not None:
            role, cid = choice
            box = self.speaker if role == "speaker" else self.listener
            box.setCurrentIndex(box.findData(cid))       # records the edit like a manual choice (one undo step)

    def _voice_label(self, cid: str, kind: str) -> str:
        if kind.startswith("candidate:"):
            return self.tr("{id} (on probation since {ep})").format(id=cid, ep=kind.split(":", 1)[1])
        if kind == "review":
            return self.tr("{id} (new NPC)").format(id=cid)
        return cid

    def _new_npc(self) -> None:
        """A new automatic id for this line's speaker; no memory write (probation decides at finish, 5.15b)."""
        from subagent.memory.characters import is_auto_id, new_voice_id

        if self.data is None or self.data.read_only or self.current is None:
            return
        prefix = self.services.config.voice.new_voice_prefix
        number = self.data.episode.number
        used = [int(c.rsplit("_", 1)[-1]) for c in self.characters
                if is_auto_id(c, prefix) and int(c.rsplit("_", 2)[-2]) == number]
        cid = new_voice_id(prefix, number, max(used, default=0) + 1)
        self.characters[cid] = self._voice_label(cid, "review")
        self._fill_character_boxes()
        self.speaker_filter.addItem(self.characters[cid], cid)
        if self.rules is not None:
            self.rules.character_ids.add(cid)
        self._load_editor(self.lines[self.current])
        self.speaker.setCurrentIndex(self.speaker.findData(cid))     # records the edit like a manual choice

    def create_character(self, data: dict) -> None:
        from app.views.character_dialog import character_proposals

        manager = self.services.manager()
        target_line = self.current
        episode_id = self.data.episode.id if self.data else None

        def save():
            result = manager.manual_edit(character_proposals(data))
            return result, self.services.rule_context(episode_id), self.services.pinyin_engine()

        def done(outcome) -> None:
            result, rules, engine = outcome
            if any(key == f"characters:{data['id']}" for key, _ in result.rejected):
                show_error(self, self.tr("New character"), "\n".join(f"{k}: {r}" for k, r in result.rejected))
                return
            self.rules, self.engine = rules, engine
            self.characters[data["id"]] = data["name_vi"]
            self._fill_character_boxes()
            self.speaker_filter.addItem(f"{data['name_vi']} ({data['id']})", data["id"])
            if target_line is not None and target_line == self.current:
                self._load_editor(self.lines[target_line])
                box = {"speaker": self.speaker, "listener": self.listener}.get(data.get("role"))
                if box is not None:
                    box.setCurrentIndex(box.findData(data["id"]))   # records the edit like a manual choice

        run_async(save, done, lambda exc: show_error(self, self.tr("New character"), exc))

    def _resort(self) -> None:
        self.order = [line.event_id for line in review_order(list(self.lines.values()))]

    # -- list ---------------------------------------------------------------------------------------

    def _matches(self, line: ReviewedLine) -> bool:
        if self.audit_mode and line.event_id not in self.audit_sample:
            return False
        flag = self.flag_filter.currentData()
        if flag == "rule_warnings":
            if not any(f in RULE_WARNING_FLAGS for f in line.flags):
                return False
        elif flag and flag not in line.flags:
            return False
        speaker = self.speaker_filter.currentData()
        if speaker and line.speaker != speaker:
            return False
        if self.unapproved.isChecked() and line.approved:
            return False
        q = self.search.text().strip().lower()
        return not q or q in line.zh.lower() or q in line.vi.lower()

    def _apply_filters(self, *_: object, select: str | None = None) -> None:
        keep = select or self.current
        self.visible = [eid for eid in self.order if self._matches(self.lines[eid])]
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.visible))
        for row, eid in enumerate(self.visible):
            self._fill_row(row, self.lines[eid])
        self.table.blockSignals(False)
        self._update_counter()
        if keep in self.visible:
            self._select(keep)
        elif self.visible:
            self._select(self.visible[0])
        else:
            self.current = None
            self._load_editor(None)

    def _fill_row(self, row: int, line: ReviewedLine) -> None:
        flagged = needs_attention(line)
        state = "✕" if line.deleted else "✓" if line.approved else ("⚑" if flagged else "·")
        if self.audit_mode:
            mark = self.audit_marks.get(line.event_id)
            state = "·" if mark is None or not mark.marked() else "✗" if mark.any_wrong() else "✓"
        who = f"{self._name(line.speaker)} → {self._name(line.listener)}" if line.line_type == "dialogue" \
            else f"[{self.line_type.itemText(LINE_TYPES.index(line.line_type))}]"
        values = [state, fmt_ms(line.start_ms), who, line.zh, line.vi]
        for col, v in enumerate(values):
            item = QTableWidgetItem(v)
            if col == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setToolTip(", ".join(flag_label(f) for f in line.flags) or self.tr("No flags"))
                if flagged and not line.approved:
                    item.setForeground(Qt.GlobalColor.darkYellow)
            if line.deleted:
                font = item.font()
                font.setStrikeOut(col > 0)
                item.setFont(font)
                item.setForeground(Qt.GlobalColor.gray)
                if col == 0:
                    item.setToolTip(self.tr("Deleted: not shown in the video"))
            self.table.setItem(row, col, item)

    def _name(self, cid: str | None) -> str:
        return self.characters.get(cid, cid) if cid else "—"

    def _update_counter(self) -> None:
        lines = [x for x in self.lines.values() if not x.deleted]
        deleted = len(self.lines) - len(lines)
        flagged_left = sum(1 for x in lines if needs_attention(x) and not x.approved)
        approved = sum(1 for x in lines if x.approved)
        text = self.tr("Flagged remaining: {flagged} · Approved: {approved} / {total}").format(
            flagged=flagged_left, approved=approved, total=len(lines))
        if deleted:
            text += " · " + self.tr("Deleted: {n}").format(n=deleted)
        self.counter.setText(text)
        ro = self.data is None or self.data.read_only
        self.approve_rest_btn.setEnabled(not ro and flagged_left == 0 and approved < len(lines))
        self.partial_btn.setEnabled(not ro and 0 < approved < len(lines) and not self._partial_job)
        self.finish_btn.setEnabled(not ro and bool(self.lines) and approved == len(lines))

    def _select(self, event_id: str) -> None:
        row = self.visible.index(event_id)
        self.table.setCurrentCell(row, 0)
        self._select_row(row)

    def _select_row(self, row: int) -> None:
        if not (0 <= row < len(self.visible)):
            return
        eid = self.visible[row]
        if eid == self.current and self.editor.property("loaded_id") == eid:
            return
        self.current = eid
        self._load_editor(self.lines[eid])
        if self.data:
            QSettings().setValue(f"review/{self.data.episode.id}/last", eid)
        line = self.lines[eid]
        self.preview.play_line(line.start_ms, line.end_ms)

    def _move(self, step: int) -> None:
        if not self.visible:
            return
        idx = self.visible.index(self.current) if self.current in self.visible else -1
        self._select(self.visible[max(0, min(len(self.visible) - 1, idx + step))])

    # -- editor -------------------------------------------------------------------------------------

    def _set_enabled(self, on: bool) -> None:
        ro = self.data is not None and self.data.read_only
        for w in (self.zh, self.pinyin, self.regen, self.vi, self.speaker, self.listener, self.line_type,
                  self.new_char_btn, self.new_npc_btn):
            w.setEnabled(on and not ro)
        self.approve_btn.setEnabled(on and not ro)
        for b in (self.approve_btn, self.approve_rest_btn, self.finish_btn, self.reset_btn, self.delete_btn,
                  self.discard_btn, self.partial_btn):
            b.setVisible(not ro)
        self.discard_btn.setEnabled(on and not ro)
        if not on:
            self.approve_rest_btn.setEnabled(False)
            self.finish_btn.setEnabled(False)
        self._show_identification()

    @property
    def identify(self) -> bool:
        return self.services.config.show.character_identification

    def _show_identification(self) -> None:
        """Character identification off (5.11a): no speakers, so the speaker / listener fields, character cards,
        the On screen view and partial review are hidden; the line type stays."""
        on = self.identify
        for w in (self.speaker, self.who_arrow, self.listener, self.new_char_btn, self.new_npc_btn, self.browse_btn,
                  self.speaker_filter_label, self.speaker_filter):
            w.setVisible(on)
        if not on:
            self.suggest_btn.hide()
            self.partial_btn.hide()
        self.form.setRowVisible(self.card_strip, on)
        label = self.form.labelForField(self.who)
        if label is not None:
            label.setText(self.tr("Speaker → listener") if on else self.tr("Line type"))
        self.table.setColumnHidden(2, not on)
        self.right_tabs.setTabVisible(1, on)

    def _load_editor(self, line: ReviewedLine | None) -> None:
        self._loading = True
        self.editor.setProperty("loaded_id", line.event_id if line else None)
        self.zh.setText(line.zh if line else "")
        self.pinyin.setText(line.pinyin if line else "")
        self.pinyin.setStyleSheet("font-style: italic;" if line and line.pinyin_overridden else "")
        self.vi.setPlainText(line.vi if line else "")
        for box, value in ((self.speaker, line.speaker if line else None), (self.listener, line.listener if line else None)):
            idx = box.findData(value)
            if idx < 0 and value:
                box.addItem(self.tr("{id} (unknown)").format(id=value), value)
                idx = box.count() - 1
            box.setCurrentIndex(max(0, idx))
        self.line_type.setCurrentIndex(LINE_TYPES.index(line.line_type) if line else 0)
        if self.audit_mode:
            self._show_audit(line)
        sug = self._suggestion(line) if line else None
        self.suggest_btn.setVisible(sug is not None and self.identify)
        if sug is not None:
            self.suggest_btn.setText(self.tr("Use {name}").format(name=self._name(sug.suggested_speaker)))
        self._loading = False
        self._line_state(line)
        self._render_context()
        self._rules_timer.start()
        self._picture_timer.start()

    def _line_state(self, line: ReviewedLine | None) -> None:
        """A deleted line can only be restored; everything else is locked until then."""
        writable = line is not None and self.data is not None and not self.data.read_only
        editable = writable and not line.deleted
        for w in (self.zh, self.pinyin, self.regen, self.vi, self.speaker, self.listener, self.line_type,
                  self.new_char_btn, self.new_npc_btn, self.approve_btn):
            w.setEnabled(editable)
        self.delete_btn.setEnabled(writable)
        self.delete_btn.setText(self.tr("Restore line") if line and line.deleted else self.tr("Delete line"))
        self.reset_btn.setEnabled(writable and line.event_id in self.originals
                                  and self.lines.get(line.event_id) != self.originals[line.event_id])

    def _push_undo(self, eid: str, field: str) -> None:
        now = time.monotonic()
        last_id, last_field, last_t = self._last_push
        if last_id == eid and last_field == field and now - last_t < 1.5:
            self._last_push = (eid, field, now)
            return
        self.undo.setdefault(eid, []).append(self.lines[eid].model_copy(deep=True))
        self.redo[eid] = []
        self._last_push = (eid, field, now)

    def _edit(self, field: str, value: object) -> None:
        if self._loading or self.current is None or (self.data and self.data.read_only):
            return
        line = self.lines[self.current]
        if getattr(line, field) == value:
            return
        self._push_undo(line.event_id, field)
        updates: dict = {field: value, "edited": True}
        if field == "pinyin":
            updates["pinyin_overridden"] = True
            self.pinyin.setStyleSheet("font-style: italic;")
        self.lines[line.event_id] = line.model_copy(update=updates)
        if field == "zh":
            self._regenerate_async(line.event_id)
        self._changed(line.event_id)

    def _regenerate_async(self, eid: str) -> None:
        if self.engine is None:
            return
        from subagent.stages.review import regenerate_pinyin

        snapshot = self.lines[eid]
        engine = self.engine

        def done(updated: ReviewedLine) -> None:
            current = self.lines.get(eid)
            if current is None or current.zh != snapshot.zh:
                return   # edited again meanwhile; a newer request follows
            self.lines[eid] = current.model_copy(update={"pinyin": updated.pinyin, "flags": updated.flags})
            if eid == self.current:
                self._loading = True
                self.pinyin.setText(updated.pinyin)
                self._loading = False
                self._render_context()
            self._changed(eid)

        run_async(lambda: regenerate_pinyin(snapshot, engine), done)

    def _regenerate_pinyin(self) -> None:
        if self.current is None:
            return
        self._push_undo(self.current, "pinyin_regen")
        self.lines[self.current] = self.lines[self.current].model_copy(update={"pinyin_overridden": False})
        self.pinyin.setStyleSheet("")
        self._regenerate_async(self.current)

    def _changed(self, eid: str) -> None:
        if eid in self.visible:
            self._fill_row(self.visible.index(eid), self.lines[eid])
        self._update_counter()
        self._save_timer.start()
        self._preview_timer.start()
        if eid == self.current:
            self._rules_timer.start()

    def _undo(self) -> None:
        self._undo_redo(self.undo, self.redo)

    def _redo(self) -> None:
        self._undo_redo(self.redo, self.undo)

    def _undo_redo(self, source: dict, target: dict) -> None:
        eid = self.current
        if not eid or not source.get(eid) or (self.data and self.data.read_only):
            return
        target.setdefault(eid, []).append(self.lines[eid].model_copy(deep=True))
        self.lines[eid] = source[eid].pop()
        self._last_push = ("", "", 0.0)
        self._load_editor(self.lines[eid])
        self._changed(eid)

    # -- approve / finish ---------------------------------------------------------------------------

    def approve_and_next(self) -> None:
        if self.audit_mode:
            self._audit_all_correct()
            return
        if self.current is None or (self.data and self.data.read_only):
            return
        eid = self.current
        if not self.lines[eid].approved and not self.lines[eid].deleted:
            self._push_undo(eid, "approved")
            self.lines[eid] = self.lines[eid].model_copy(update={"approved": True})
            self._changed(eid)
        self._select_next_pending(eid)

    def _select_next_pending(self, eid: str) -> None:
        pending = [x for x in self.visible if not self.lines[x].approved and not self.lines[x].deleted]
        after = [x for x in pending if self.visible.index(x) > self.visible.index(eid)]
        nxt = (after or pending or [eid])[0]
        self._select(nxt)

    def _approve_rest(self) -> None:
        rest = [eid for eid, x in self.lines.items() if not x.approved and not x.deleted and not needs_attention(x)]
        if not rest or not confirm(self, self.tr("Approve remaining lines"), self.tr(
                "Approve all {n} remaining lines that have no flags?").format(n=len(rest))):
            return
        for eid in rest:
            self._push_undo(eid, "approved")
            self.lines[eid] = self.lines[eid].model_copy(update={"approved": True})
        self._apply_filters()
        self._save_timer.start()

    def _toggle_delete(self) -> None:
        if self.current is None or (self.data and self.data.read_only):
            return
        eid = self.current
        self._push_undo(eid, "deleted")
        deleted = not self.lines[eid].deleted
        self.lines[eid] = self.lines[eid].model_copy(update={"deleted": deleted, "edited": True})
        self._changed(eid)
        if deleted:
            self._select_next_pending(eid)
        else:
            self._load_editor(self.lines[eid])

    def _reset_line(self) -> None:
        eid = self.current
        if eid is None or eid not in self.originals or (self.data and self.data.read_only):
            return
        self._push_undo(eid, "reset")
        self._last_push = ("", "", 0.0)
        self.lines[eid] = self.originals[eid].model_copy(deep=True)
        self._load_editor(self.lines[eid])
        self._changed(eid)

    def _discard_review(self) -> None:
        if not self.data or self.data.read_only or not self.originals:
            return
        changed = sum(1 for eid, line in self.lines.items() if line != self.originals.get(eid))
        if not confirm(self, self.tr("Discard review"), self.tr(
                "Discard the whole review of {ep}?\n\nAll edits, approvals and deletions ({n} lines) are replaced by "
                "the pipeline's output. This cannot be undone.").format(ep=self.data.episode.id, n=changed)):
            return
        self.discard_review()

    def discard_review(self) -> None:
        """Replace the draft by the pipeline's output (after confirmation)."""
        self._save_timer.stop()
        self.lines = {eid: line.model_copy(deep=True) for eid, line in self.originals.items()}
        self.undo, self.redo = {}, {}
        self._last_push = ("", "", 0.0)
        self.services.save_draft(self.data.episode.id, list(self.lines.values()))
        self._resort()
        self.current = None
        self._apply_filters()
        self._preview_timer.start()

    def _finish(self) -> None:
        if not self.data or job_busy(self, self.main):
            return
        ep = self.data.episode.id
        edited = sum(1 for x in self.lines.values() if x.edited)
        if not confirm(self, self.tr("Finish review"), self.tr(
                "Finish the review of {ep}?\n\n{edited} edited lines will update memory (glossary changes are locked), "
                "then the video is rendered to the output folder.").format(ep=ep, edited=edited)):
            return
        self.flush()
        on_exists = choose_on_exists(self, self.main, ep)
        if on_exists is None:
            return
        self._finish_job = f"{ep} (finish review)"
        self.main.jobs.start(self._finish_job, ["finish-review", ep, "--on-exists", on_exists])
        self.main.go("episodes")

    def _job_finished(self, name: str, code: int, error: dict) -> None:
        if name and name == self._partial_job:
            self._partial_finished(code, error)
            return
        if name != self._finish_job:
            return
        self._finish_job = ""
        if code != 0:
            QMessageBox.warning(self, self.tr("Finish review"),
                                error_message(error.get("error_code"), error.get("message", "")))
        elif self.data:
            self.open_episode(self.data.episode.id)

    # -- audit (6.11) --------------------------------------------------------------------------------

    def _audit_progress(self) -> str:
        marked = sum(1 for e in self.audit_sample if e in self.audit_marks and self.audit_marks[e].marked())
        return self.tr("{marked} / {total} sampled lines marked").format(marked=marked, total=len(self.audit_sample))

    def _show_audit(self, line: ReviewedLine | None) -> None:
        eid = line.event_id if line else None
        self.audit_bar.set_characters(self.characters)
        self.audit_bar.show_mark(self.audit_marks.get(eid), self.audit_sample.get(eid), self._audit_progress())

    def _audit_changed(self, _: object = None) -> None:
        if not self.audit_mode or self.current is None or self.current not in self.audit_sample:
            return
        from subagent.kernel.util import now_iso

        mark = self.audit_bar.current(self.current)
        if mark.marked():
            self.audit_marks[self.current] = mark.model_copy(update={
                "marked_at": now_iso(), "speaker_value": self.lines[self.current].speaker})
        else:
            self.audit_marks.pop(self.current, None)
        if self.current in self.visible:
            self._fill_row(self.visible.index(self.current), self.lines[self.current])
        self._show_audit(self.lines[self.current])
        self._audit_timer.start()

    def _audit_all_correct(self) -> None:
        if not self.audit_mode or self.current is None or self.current not in self.audit_sample:
            return
        from subagent.kernel.models import AUDIT_ASPECTS, AuditMark
        from subagent.kernel.util import now_iso

        old = self.audit_marks.get(self.current)
        na = old.na if old else []
        self.audit_marks[self.current] = AuditMark(
            event_id=self.current, na=na, note=old.note if old else "", marked_at=now_iso(),
            speaker_value=self.lines[self.current].speaker,
            **{a: (None if a in na else True) for a in AUDIT_ASPECTS})
        self._fill_row(self.visible.index(self.current), self.lines[self.current])
        self._audit_timer.start()
        self._audit_next()

    def _audit_next(self) -> None:
        order = [e for e in self.visible if e in self.audit_sample]
        if not order:
            return
        start = order.index(self.current) + 1 if self.current in order else 0
        for e in order[start:] + order[:start]:
            m = self.audit_marks.get(e)
            if m is None or (m.speaker is False and not m.correct_speaker):     # unmarked, or answer missing
                self._select(e)
                return
        self._show_audit(self.lines.get(self.current))      # everything is marked

    def _save_audit(self) -> None:
        if self.data is None:
            return
        ep, marks = self.data.episode.id, dict(self.audit_marks)
        run_async(lambda: self.services.save_audit_marks(ep, marks), None,
                  lambda exc: show_error(self, self.tr("Audit"), exc))

    # -- partial review ------------------------------------------------------------------------------

    def _suggestion(self, line: ReviewedLine):
        """The partial review's suggestion for a remaining line, when it is still different from its speaker."""
        if self.data is None or line.approved or line.deleted:
            return None
        s = self.data.partial.get(line.event_id)
        return s if s is not None and s.suggested_speaker and s.suggested_speaker != line.speaker else None

    def _partial_review(self) -> None:
        if self.data is None or self.data.read_only:
            return
        self._save_timer.stop()             # the job reads the draft: save it now, synchronously
        self.services.save_draft(self.data.episode.id, list(self.lines.values()))
        if not self.main.jobs.start("partial_review", ["partial-review", self.data.episode.id]):
            show_error(self, self.tr("Partial review"), self.tr("Another job is running."))
            return
        self._partial_job = "partial_review"
        self.partial_btn.setEnabled(False)
        self.partial_btn.setText(self.tr("Partial review running…"))

    def _partial_finished(self, code: int, error: dict) -> None:
        self._partial_job = ""
        self.partial_btn.setText(self.tr("Partial review…"))
        if code != 0:
            QMessageBox.warning(self, self.tr("Partial review"),
                                error_message(error.get("error_code"), error.get("message", "")))
            self._update_counter()
            return
        if self.data is None:
            return
        from subagent.partial_review import PARTIAL_FLAG

        ep_id = self.data.episode.id
        self.data.partial = self.services.partial_suggestions(ep_id)
        changed = 0
        for eid, line in list(self.lines.items()):
            sug = self._suggestion(line)
            flags = [f for f in line.flags if f != "partial_suggestion"]
            if sug is None:
                if flags != line.flags:          # an old suggestion flag: not a reviewer edit, no undo step
                    self.lines[eid] = line.model_copy(update={"flags": flags})
                    self._changed(eid)
                continue
            # the new speaker is set on the line: one undo step per line restores speaker and flags
            self._push_undo(eid, "partial_speaker")
            flags += [f for f in (PARTIAL_FLAG, "check_pronouns") if f not in flags]
            self.lines[eid] = line.model_copy(update={"speaker": sug.suggested_speaker, "edited": True,
                                                      "flags": flags})
            self._changed(eid)
            changed += 1
        self._frames.clear()
        if self.current:
            self._load_editor(self.lines[self.current])
        self._update_counter()
        QMessageBox.information(self, self.tr("Partial review"), self.tr(
            "Re-checked the remaining lines with what you approved so far.\n{n} lines got a new speaker "
            "(flag: Speaker set by partial review). Check their pronouns; Undo on a line restores its "
            "speaker.").format(n=changed))

    def _use_suggestion(self) -> None:
        if self.current is None:
            return
        line = self.lines[self.current]
        sug = self._suggestion(line)
        if sug is None:
            return
        self._edit("speaker", sug.suggested_speaker)      # one undo step restores speaker and flags
        line = self.lines[self.current]
        flags = [f for f in line.flags if f != "partial_suggestion"]
        if "check_pronouns" not in flags:
            flags.append("check_pronouns")
        self.lines[self.current] = line.model_copy(update={"flags": flags})
        self._load_editor(self.lines[self.current])
        self._changed(self.current)

    # -- context / checks ---------------------------------------------------------------------------

    def _render_context(self) -> None:
        if not self.data or self.current is None:
            self.context.clear()
            return
        line = self.lines[self.current]
        event = self.data.events.get(line.event_id)
        tr = self.data.translations.get(line.event_id)
        parts = []

        def section(title: str, body: str) -> None:
            parts.append(f"<b>{html.escape(title)}</b>{body}")

        def bullets(items: list[str]) -> str:
            return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

        if line.deleted:
            note = self.tr("This line is not shown in the video. Use Restore line to bring it back.")
            section(self.tr("Deleted"), f"<p>{html.escape(note)}</p>")
        if line.flags:
            section(self.tr("Flags"), bullets([html.escape(flag_label(f)) for f in line.flags]))
        notes = (event.notes if event else []) + ([tr.notes] if tr and tr.notes else [])
        script_note = self.data.script_notes.get(line.event_id)
        if script_note:
            notes.append(self.tr("Script review: {note}").format(note=script_note))
        if notes:
            section(self.tr("Reasons"), bullets([html.escape(n) for n in notes]))
        evals = self.data.evaluations.get(line.event_id, [])
        sug = self._suggestion(line)
        partial = self.data.partial.get(line.event_id) if not line.approved else None
        if partial is not None:
            items = []
            if sug:
                items.append(self.tr("Suggested speaker: <b>{name}</b> ({reason})").format(
                    name=html.escape(self._name(sug.suggested_speaker)), reason=html.escape(sug.reason)))
            if partial.talking:
                items.append(self.tr("Talking on screen: {name}").format(name=html.escape(self._name(partial.talking))))
            if partial.voice and partial.voice.candidates:
                c, s = partial.voice.candidates[0]
                items.append(self.tr("Voice: {name} {score:.2f} ({status})").format(
                    name=html.escape(self._name(c)), score=s, status=html.escape(partial.voice.status)))
            if items:
                section(self.tr("Partial review"), bullets(items))
        if evals:
            last = evals[-1]
            scores = ", ".join(f"{k} {v}" for k, v in last.scores.items())
            feedback = html.escape(last.feedback).replace("\n", "<br>")
            body = f"<p>{html.escape(scores)}</p><p>{feedback}</p>"
            if last.suggestion and last.suggestion.strip() != line.vi.strip():
                body = "<p>" + self.tr("Evaluator suggests: <b>{vi}</b>").format(vi=html.escape(last.suggestion))                     + "</p>" + body
            section(self.tr("Evaluator (attempt {n})").format(n=last.attempt), body)
        if self.rules is not None:
            gl = self.rules.glossary_in(line.zh)
            if gl:
                from subagent.kernel.textutil import contains_term

                section(self.tr("Glossary terms"), bullets([
                    f"{html.escape(g.zh)} → <b>{html.escape(g.vi)}</b> {'✓' if contains_term(line.vi, g.vi) else '✗'}"
                    for g in gl]))
            if line.speaker and line.listener:
                variants = self.rules.pronoun_variants(line.speaker, line.listener)
                rows = [html.escape(f"{v.self_term} / {v.address_term}" + (f" ({v.context})" if v.context else ""))
                        for v in variants] or [html.escape(self.tr("No pronoun pair in memory yet"))]
                title = self.tr("Pronouns {speaker} → {listener}").format(
                    speaker=self._name(line.speaker), listener=self._name(line.listener))
                section(title, bullets(rows))
        self.context.setHtml("".join(parts) or html.escape(self.tr("No notes for this line.")))

    # -- picture: original subtitle + characters on screen -------------------------------------------

    def _load_picture(self) -> None:
        eid = self.current
        if self.data is None or eid is None or eid not in self.lines:
            return
        if eid in self._frames:
            self._show_picture(eid)
            return
        line, data = self.lines[eid], self.data
        event = data.events.get(eid)

        def fetch():
            frame = self.services.line_frame(data.episode.id, line.start_ms, line.end_ms, event, data.video)
            return (*frame, self.services.line_ocr_crop(data.episode.id, event))

        def done(result) -> None:
            self._frames[eid] = result
            while len(self._frames) > 40:
                self._frames.pop(next(iter(self._frames)))
            if eid == self.current:
                self._show_picture(eid)

        def failed(exc: BaseException) -> None:
            if eid == self.current:
                msg = self.tr("The video is not available: {error}").format(error=exc)
                self.band.show_band(None, None, msg)
                self._show_ocr_crop(None)
                self.cast_panel.show_line(None, None, {}, self.characters, self.services.config.cast.frame_width,
                                          False, msg)

        run_async(fetch, done, failed)

    def _show_ocr_crop(self, image) -> None:
        if image is None:
            self.ocr_crop.show_band(None, None, self.tr(
                "Not saved: the episode's temporary files were cleaned up, or OCR ran without pre-processing"))
        else:
            self.ocr_crop.show_band(image, (0, 0, image.shape[1], image.shape[0]))

    def _show_picture(self, eid: str) -> None:
        frame, crop, analysed, ocr_crop = self._frames[eid]
        line = self.lines[eid]
        self.band.show_band(frame, crop)
        self._show_ocr_crop(ocr_crop)
        cast = self.data.cast.get(eid) if self.data else None
        partial = self.data.partial.get(eid) if self.data and not line.approved else None
        if cast is not None and partial is not None and partial.cast:
            cast = cast.model_copy(deep=True)
            for pos, d in enumerate(cast.detections):
                if str(pos) in partial.cast:
                    d.character = partial.cast[str(pos)]
                    d.similarity = partial.similarity.get(str(pos), d.similarity)
        editable = bool(self.data and not self.data.read_only and not line.deleted)
        missing = "" if self.data and self.data.cast else self.tr(
            "No cast data for this episode (the Characters on screen stage did not run).")
        review = {"cast_labels": line.cast_labels, "cast_boxes": line.cast_boxes,
                  "cast_added": [a.model_dump() for a in line.cast_added], "cast_talking": line.cast_talking,
                  "cast_checked": line.cast_checked}
        if analysed is not None:     # the exact frame the stage analysed: boxes line up even on moving characters
            self.cast_panel.show_line(analysed, cast, review, self.characters, analysed.shape[1], editable, missing,
                                      rgb=True)
        else:
            self.cast_panel.show_line(frame, cast, review, self.characters, self.services.config.cast.frame_width,
                                      editable, missing)

    def _right_tab_changed(self, index: int) -> None:
        if index == 1:
            self.cast_panel.split.setSizes(self.right_sizes())
            self._picture_timer.start()

    def right_sizes(self) -> list[int]:
        """Picture / table heights matching the player / editor split of the Line view."""
        line = self.right_tabs.widget(0)
        return line.sizes() if hasattr(line, "sizes") else [380, 420]

    def _cast_review_changed(self, review: dict) -> None:
        """Box corrections, moved/drawn boxes and the talking mark: one undo step."""
        from subagent.kernel.models import CastBoxEdit

        if self._loading or self.current is None or (self.data and self.data.read_only):
            return
        line = self.lines[self.current]
        updates = {"cast_labels": review["cast_labels"], "cast_boxes": review["cast_boxes"],
                   "cast_added": [CastBoxEdit(**a) for a in review["cast_added"]],
                   "cast_talking": review["cast_talking"], "cast_checked": review.get("cast_checked", False)}
        if all(getattr(line, k) == v for k, v in updates.items()):
            return
        self._push_undo(line.event_id, "cast")
        self.lines[line.event_id] = line.model_copy(update={**updates, "edited": True})
        self._changed(line.event_id)

    def _check_rules(self) -> None:
        if not self.data or self.current is None or self.rules is None:
            self.warnings.clear()
            return
        from subagent.stages.evaluate import rule_checks

        line = self.lines[self.current]
        event = self.data.events.get(line.event_id)
        if event is None:
            return
        rules, eid = self.rules, line.event_id

        def check():
            ev = event.model_copy(update={"zh": line.zh, "start_ms": line.start_ms, "end_ms": line.end_ms})
            lt = LineTranslation(event_id=eid, speaker=line.speaker, listener=line.listener, speaker_conf=1.0,
                                 line_type=line.line_type, vi=line.vi, attempts=0)
            failures, warnings = rule_checks(lt, ev, None, rules)
            return [f.message for f in failures] + warnings

        def show(messages: list[str]) -> None:
            if eid == self.current:
                self.warnings.setText("\n".join(f"⚠ {m}" for m in messages))
                self._render_context()

        run_async(check, show)

    # -- preview / saving ---------------------------------------------------------------------------

    def _open_preview(self) -> None:
        if not self.preview.available or not self.data:
            return
        data = self.data
        source = Path(data.episode.source_path)
        if not source.is_file():
            return
        lines = list(self.lines.values())

        def prepare():
            video = data.video or self.services.video_info(data.episode.id)
            ass = self.services.write_preview(data.episode.id, lines, video)
            return video, ass

        def opened(result) -> None:
            video, ass = result
            self.preview.open(source, vf=self.services.mask_filter(video), subtitles=ass,
                              fonts_dir=self.services.paths.fonts)

        run_async(prepare, opened, lambda exc: self.warnings.setText(str(exc)))

    def _refresh_preview(self) -> None:
        if not self.preview.available or not self.data or not self.data.video:
            return
        lines, ep, video = list(self.lines.values()), self.data.episode.id, self.data.video
        run_async(lambda: self.services.write_preview(ep, lines, video), lambda _: self.preview.reload_subtitles())

    def _save(self) -> None:
        if not self.data or self.data.read_only:
            return
        if self._saving:
            self._save_pending = True
            return
        self._saving = True
        ep, lines = self.data.episode.id, [x.model_copy() for x in self.lines.values()]

        def done(_: object = None) -> None:
            self._saving = False
            if self._save_pending:
                self._save_pending = False
                self._save()

        def failed(exc: BaseException) -> None:
            done()
            show_error(self, self.tr("Autosave failed"), exc)

        run_async(lambda: self.services.save_draft(ep, lines), done, failed)

    def flush(self) -> None:
        """Save synchronously (switching episode, finishing, closing): no work is lost (NFR-UX3)."""
        if self._audit_timer.isActive() and self.data:
            self._audit_timer.stop()
            self.services.save_audit_marks(self.data.episode.id, dict(self.audit_marks))
        if self._save_timer.isActive() and self.data and not self.data.read_only:
            self._save_timer.stop()
            self.services.save_draft(self.data.episode.id, list(self.lines.values()))

    def shutdown(self) -> None:
        self.flush()
        self.preview.shutdown()
