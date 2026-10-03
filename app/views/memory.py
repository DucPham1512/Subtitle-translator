"""Memory screen (6.7): view, edit (as locked human edits), history, diff and rollback.

All writes go through MemoryManager (source="human"). Editing and rollback are disabled while a job runs.
"""

from __future__ import annotations

import html
import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.widgets import ClipPlayer, confirm, show_error
from app.workers import run_async
from subagent.memory import briefings as bf
from subagent.memory.store import row_key
from subagent.models import MemoryProposal

LOCKED_COL = "locked"
BOOL_COLS = ("generic",)        # shown as checkboxes, saved as 0 / 1


def _item(text: object, editable: bool = True) -> QTableWidgetItem:
    item = QTableWidgetItem("" if text is None else str(text))
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class EntryTable(QWidget):
    """Editable table for characters or glossary. Saves as human proposals (locked unless unchecked)."""

    def __init__(self, view: MemoryView, table: str, kind: str, columns: list[str], key_cols: list[str],
                 labels: dict[str, str]):
        super().__init__()
        self.view = view
        self.table_name = table
        self.kind = kind
        self.columns = columns
        self.key_cols = key_cols
        self.all_cols = columns + [LOCKED_COL, "source", "updated_at"] if table == "glossary" else \
            columns + [LOCKED_COL, "updated_at"]
        self.original: dict[str, dict] = {}
        self.deleted: dict[str, dict] = {}
        self._filling = False
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.add_btn = QPushButton(self.tr("Add"))
        self.del_btn = QPushButton(self.tr("Delete"))
        self.save_btn = QPushButton(self.tr("Save changes"))
        self.revert_btn = QPushButton(self.tr("Discard changes"))
        for w in (self.search, self.add_btn, self.del_btn, self.revert_btn, self.save_btn):
            bar.addWidget(w)
        layout.addLayout(bar)
        self.grid = QTableWidget(0, len(self.all_cols))
        self.grid.setHorizontalHeaderLabels([labels.get(c, c) for c in self.all_cols])
        self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self.grid.setSortingEnabled(True)
        self.grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._menu)
        self.grid.itemChanged.connect(self._changed)
        layout.addWidget(self.grid)
        self.status = QLabel()
        layout.addWidget(self.status)
        self.add_btn.clicked.connect(self._add)
        self.del_btn.clicked.connect(self._delete)
        self.save_btn.clicked.connect(self._save)
        self.revert_btn.clicked.connect(self.load)

    def set_editable(self, on: bool) -> None:
        for b in (self.add_btn, self.del_btn, self.save_btn, self.revert_btn):
            b.setEnabled(on)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
                                  if on else QAbstractItemView.EditTrigger.NoEditTriggers)

    def load(self) -> None:
        run_async(lambda: self.view.services.store.table_rows(self.table_name), self._fill,
                  lambda exc: show_error(self, self.tr("Memory"), exc))

    def _fill(self, rows: list[dict]) -> None:
        self._filling = True
        self.grid.setSortingEnabled(False)
        self.original = {row_key(self.table_name, r): r for r in rows}
        self.deleted = {}
        self.grid.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self._set_row(i, r, new=False)
        self.grid.setSortingEnabled(True)
        self._filling = False
        self.status.setText(self.tr("{n} entries").format(n=len(rows)))
        self._filter()

    def _set_row(self, i: int, r: dict, new: bool) -> None:
        for j, col in enumerate(self.all_cols):
            if col == LOCKED_COL or col in BOOL_COLS:
                item = _item("", editable=False)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if r.get(col) else Qt.CheckState.Unchecked)
            else:
                editable = col in self.columns and (new or col not in self.key_cols)
                item = _item(r.get(col), editable)
            if j == 0:
                item.setData(Qt.ItemDataRole.UserRole, None if new else row_key(self.table_name, r))
            self.grid.setItem(i, j, item)

    def _row_dict(self, i: int) -> dict:
        d = {}
        for j, col in enumerate(self.all_cols):
            item = self.grid.item(i, j)
            if col == LOCKED_COL or col in BOOL_COLS:
                d[col] = item.checkState() == Qt.CheckState.Checked
            elif col in self.columns:
                d[col] = item.text().strip() if item else ""
        return d

    def _changed(self, item: QTableWidgetItem) -> None:
        if not self._filling:
            f = item.font()
            f.setItalic(True)
            item.setFont(f)
            self.status.setText(self.tr("Unsaved changes"))

    def _filter(self) -> None:
        q = self.search.text().strip().lower()
        for i in range(self.grid.rowCount()):
            text = " ".join(self.grid.item(i, j).text().lower() for j in range(len(self.columns)) if self.grid.item(i, j))
            self.grid.setRowHidden(i, bool(q) and q not in text)

    def _add(self) -> None:
        self.grid.setSortingEnabled(False)
        i = self.grid.rowCount()
        self.grid.insertRow(i)
        self._filling = True
        self._set_row(i, {LOCKED_COL: 1}, new=True)
        self._filling = False
        self.grid.scrollToItem(self.grid.item(i, 0))
        self.grid.editItem(self.grid.item(i, 0))

    def _delete(self) -> None:
        rows = sorted({i.row() for i in self.grid.selectedIndexes()}, reverse=True)
        if not rows:
            return
        locked = [i for i in rows if self._row_dict(i)[LOCKED_COL]]
        if locked and not confirm(self, self.tr("Delete locked entries"), self.tr(
                "{n} of the selected entries are locked (confirmed by a person). Delete them anyway? "
                "Deleting a character also deletes its pronoun pairs and voice.").format(n=len(locked))):
            return
        for i in rows:
            key = self.grid.item(i, 0).data(Qt.ItemDataRole.UserRole)
            if key is not None:
                self.deleted[key] = self.original[key]
            self.grid.removeRow(i)
        self.status.setText(self.tr("Unsaved changes"))

    def _save(self) -> None:
        proposals = []
        for row in self.deleted.values():
            proposals.append(MemoryProposal(kind=self.kind, source="human",
                                            payload={**{k: row[k] for k in self.key_cols}, "_delete": True}))
        for i in range(self.grid.rowCount()):
            d = self._row_dict(i)
            key = self.grid.item(i, 0).data(Qt.ItemDataRole.UserRole)
            orig = self.original.get(key) if key else None
            if any(not d.get(k) for k in self.key_cols):
                continue
            if orig is not None and all((bool(orig.get(c)) == d[c]) if c in BOOL_COLS else (orig.get(c) or "") == d[c]
                                        for c in self.columns) \
                    and bool(orig.get(LOCKED_COL)) == d[LOCKED_COL]:
                continue
            payload = {c: (int(d[c]) if c in BOOL_COLS else d[c] or None) for c in self.columns}
            payload["_locked"] = d[LOCKED_COL]
            proposals.append(MemoryProposal(kind=self.kind, source="human", payload=payload))
        if not proposals:
            self.status.setText(self.tr("Nothing to save"))
            return
        self.view.manual_edit(proposals, self.load)

    def _menu(self, pos) -> None:
        item = self.grid.itemAt(pos)
        if item is None:
            return
        key = self.grid.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if key is None:
            return
        menu = QMenu(self)
        action = menu.addAction(self.tr("History…"))
        if menu.exec(self.grid.viewport().mapToGlobal(pos)) is action:
            self.view.show_entry_history(self.table_name, key)


class PairDialog(QDialog):
    """Edit the pronoun variants of one speaker → listener pair."""

    def __init__(self, parent: QWidget, speaker: str, listener: str, variants: list[dict]):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Pronouns {speaker} → {listener}").format(speaker=speaker, listener=listener))
        self.resize(640, 300)
        self.speaker, self.listener = speaker, listener
        self.original = variants
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Leave the context empty for the default pair. Rows without terms are deleted.")))
        self.grid = QTableWidget(len(variants), 4)
        self.grid.setHorizontalHeaderLabels([self.tr("Context"), self.tr("Self term"), self.tr("Address term"),
                                             self.tr("Since episode")])
        self.grid.horizontalHeader().setStretchLastSection(True)
        for i, v in enumerate(variants):
            for j, col in enumerate(("context", "self_term", "address_term", "since_episode")):
                self.grid.setItem(i, j, _item(v.get(col)))
        layout.addWidget(self.grid)
        row = QHBoxLayout()
        add = QPushButton(self.tr("Add variant"))
        add.clicked.connect(lambda: self.grid.insertRow(self.grid.rowCount()))
        row.addWidget(add)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)

    def proposals(self) -> list[MemoryProposal]:
        def text(i: int, j: int) -> str:
            item = self.grid.item(i, j)
            return item.text().strip() if item else ""

        keep, out = set(), []
        for i in range(self.grid.rowCount()):
            ctx, self_term, address, since = (text(i, j) for j in range(4))
            if not self_term or not address:
                continue
            keep.add(ctx)
            out.append(MemoryProposal(kind="pronoun_pair", source="human", payload={
                "speaker_id": self.speaker, "listener_id": self.listener, "self_term": self_term,
                "address_term": address, "context": ctx, "since_episode": since or None}))
        for v in self.original:
            if (v.get("context") or "") not in keep:
                out.append(MemoryProposal(kind="pronoun_pair", source="human", payload={
                    "speaker_id": self.speaker, "listener_id": self.listener, "context": v.get("context") or "",
                    "_delete": True}))
        return out


class MemoryView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        self.player = ClipPlayer()
        layout = QVBoxLayout(self)
        self.banner = QLabel(self.tr("A job is running: memory is read-only until it finishes."))
        self.banner.setStyleSheet("background: #fff3cd; color: #664d03; padding: 4px;")
        self.banner.hide()
        layout.addWidget(self.banner)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        labels = {"id": self.tr("Id"), "name_zh": self.tr("Chinese"), "name_vi": self.tr("Vietnamese"),
                  "description": self.tr("Description"), "zh": self.tr("Chinese"), "vi": self.tr("Vietnamese"),
                  "pinyin": self.tr("Pinyin"), "type": self.tr("Type"), "notes": self.tr("Notes"),
                  "first_episode": self.tr("First episode"), "locked": self.tr("Locked"), "source": self.tr("Source"),
                  "updated_at": self.tr("Updated"), "remove_count": self.tr("Times removed"),
                  "keep_count": self.tr("Times kept"), "last_episode": self.tr("Last episode"),
                  "status": self.tr("Status"), "status_note": self.tr("Status reason"),
                  "generic": self.tr("Generic")}
        self.characters = EntryTable(self, "characters", "character",
                                     ["id", "name_zh", "name_vi", "description", "status", "status_note", "generic"],
                                     ["id"], labels)
        self.glossary = EntryTable(self, "glossary", "glossary",
                                   ["zh", "vi", "pinyin", "type", "notes", "first_episode"], ["zh"], labels)
        self.line_decisions = EntryTable(self, "line_decisions", "line_decision",
                                         ["zh", "remove_count", "keep_count", "last_episode"], ["zh"], labels)
        self.tabs.addTab(self.characters, self.tr("Characters"))
        self.tabs.addTab(self.glossary, self.tr("Glossary"))
        self.tabs.addTab(self._pronoun_tab(), self.tr("Pronoun matrix"))
        self.tabs.addTab(self._markdown_tab(), self.tr("Briefings"))
        self.tabs.addTab(self._style_tab(), self.tr("Style rules"))
        self.tabs.addTab(self._voice_tab(), self.tr("Voice bank"))
        self.tabs.addTab(self.line_decisions, self.tr("Line decisions"))
        self.tabs.addTab(self._conflicts_tab(), self.tr("Conflicts"))
        self.tabs.addTab(self._history_tab(), self.tr("History"))
        self.tabs.currentChanged.connect(lambda _: self._load_current())
        main.jobs.started.connect(lambda _: self._set_editable())
        main.jobs.finished.connect(lambda *_: (self._set_editable(), self._load_current()))

    def activate(self) -> None:
        self._set_editable()
        self._load_current()

    def _editable(self) -> bool:
        return not self.main.jobs.is_running() and not self.services.jobs_running()

    def _set_editable(self) -> None:
        on = self._editable()
        self.banner.setVisible(not on)
        for t in (self.characters, self.glossary, self.line_decisions):
            t.set_editable(on)
        for b in (self.md_edit_btn, self.style_edit_btn, self.rollback_btn, self.accept_btn, self.reject_btn,
                  self.recompute_btn):
            b.setEnabled(on)

    def _load_current(self) -> None:
        w = self.tabs.currentWidget()
        if w is self.characters or w is self.glossary or w is self.line_decisions:
            w.load()
        elif w is self.pronoun_tab:
            self._load_pronouns()
        elif w is self.md_tab:
            self._load_md_list()
        elif w is self.style_tab:
            self._load_style()
        elif w is self.voice_tab:
            self._load_voices()
        elif w is self.conflict_tab:
            self._load_conflicts()
        elif w is self.history_tab:
            self._load_history()

    def manual_edit(self, proposals: list[MemoryProposal], then) -> None:
        if not self._editable():
            self._set_editable()
            return
        manager = self.services.manager()

        def done(result) -> None:
            if result.rejected:
                show_error(self, self.tr("Some changes were not saved"),
                           "\n".join(f"{k}: {r}" for k, r in result.rejected))
            then()

        run_async(lambda: manager.manual_edit(proposals), done, lambda exc: show_error(self, self.tr("Memory"), exc))

    # -- pronoun matrix -----------------------------------------------------------------------------

    def _pronoun_tab(self) -> QWidget:
        self.pronoun_tab = QWidget()
        layout = QVBoxLayout(self.pronoun_tab)
        layout.addWidget(QLabel(self.tr("Rows: speaker. Columns: listener. Cell: self term / address term. "
                                        "Double-click a cell to edit.")))
        self.matrix = QTableWidget()
        self.matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix.cellDoubleClicked.connect(self._edit_pair)
        layout.addWidget(self.matrix)
        return self.pronoun_tab

    def _load_pronouns(self) -> None:
        store = self.services.store
        run_async(lambda: (store.characters(), store.pronoun_pairs()), lambda r: self._fill_matrix(*r))

    def _fill_matrix(self, chars, pairs) -> None:
        self._chars = [c.id for c in chars]
        self._pairs: dict[tuple[str, str], list[dict]] = {}
        for p in pairs:
            self._pairs.setdefault((p.speaker_id, p.listener_id), []).append(p.model_dump())
        names = [f"{c.name_vi}\n({c.id})" for c in chars]
        self.matrix.setRowCount(len(chars))
        self.matrix.setColumnCount(len(chars))
        self.matrix.setHorizontalHeaderLabels(names)
        self.matrix.setVerticalHeaderLabels(names)
        for i, s in enumerate(self._chars):
            for j, lst in enumerate(self._chars):
                variants = self._pairs.get((s, lst), [])
                default = next((v for v in variants if not v["context"]), variants[0] if variants else None)
                text = f"{default['self_term']} / {default['address_term']}" if default else ""
                if len(variants) > 1:
                    text += f"  (+{len(variants) - 1})"
                item = _item(text, editable=False)
                if variants and all(v["locked"] for v in variants):
                    item.setToolTip(self.tr("Locked"))
                if i == j:
                    item.setBackground(QBrush(QColor(128, 128, 128, 40)))
                self.matrix.setItem(i, j, item)
        self.matrix.resizeColumnsToContents()

    def _edit_pair(self, row: int, col: int) -> None:
        if not self._editable() or row == col:
            return
        s, lst = self._chars[row], self._chars[col]
        dialog = PairDialog(self, s, lst, self._pairs.get((s, lst), []))
        if dialog.exec():
            self.manual_edit(dialog.proposals(), self._load_pronouns)

    # -- markdown -----------------------------------------------------------------------------------

    def _md_editor(self) -> tuple[QStackedWidget, QTextBrowser, QPlainTextEdit]:
        stack = QStackedWidget()
        view = QTextBrowser()
        edit = QPlainTextEdit()
        stack.addWidget(view)
        stack.addWidget(edit)
        return stack, view, edit

    def _markdown_tab(self) -> QWidget:
        self.md_tab = QWidget()
        layout = QHBoxLayout(self.md_tab)
        self.md_list = QListWidget()
        self.md_list.setMaximumWidth(220)
        self.md_list.currentTextChanged.connect(self._show_md)
        layout.addWidget(self.md_list)
        right = QVBoxLayout()
        self.md_stack, self.md_view, self.md_edit = self._md_editor()
        right.addWidget(self.md_stack)
        row = QHBoxLayout()
        self.md_edit_btn = QPushButton(self.tr("Edit"))
        self.md_save_btn = QPushButton(self.tr("Save"))
        self.md_save_btn.hide()
        self.md_edit_btn.clicked.connect(lambda: self._toggle_edit(self.md_stack, self.md_edit_btn, self.md_save_btn))
        self.md_save_btn.clicked.connect(self._save_md)
        row.addStretch(1)
        row.addWidget(self.md_edit_btn)
        row.addWidget(self.md_save_btn)
        right.addLayout(row)
        layout.addLayout(right, 1)
        return self.md_tab

    def _load_md_list(self) -> None:
        current = self.md_list.currentItem().text() if self.md_list.currentItem() else "INDEX.md"
        names = ["INDEX.md", "story_so_far.md"] + [f"{e}.md" for e in bf.list_episode_briefings(self.services.paths.memory)]
        self.md_list.clear()
        self.md_list.addItems(names)
        items = self.md_list.findItems(current, Qt.MatchFlag.MatchExactly)
        self.md_list.setCurrentItem(items[0] if items else self.md_list.item(0))

    def _show_md(self, name: str) -> None:
        if not name:
            return
        path = self.services.paths.memory / "briefings" / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        self.md_view.setMarkdown(text)
        self.md_edit.setPlainText(text)
        self.md_stack.setCurrentIndex(0)
        self.md_edit_btn.show()
        self.md_save_btn.hide()

    def _toggle_edit(self, stack: QStackedWidget, edit_btn: QPushButton, save_btn: QPushButton) -> None:
        stack.setCurrentIndex(1)
        edit_btn.hide()
        save_btn.show()

    def _save_md(self) -> None:
        name = self.md_list.currentItem().text() if self.md_list.currentItem() else None
        if name:
            self._write_text(name, self.md_edit.toPlainText(), lambda: self._show_md(name))

    def _write_text(self, name: str, content: str, then) -> None:
        manager = self.services.manager()
        run_async(lambda: manager.write_text_file(name, content), lambda _: then(),
                  lambda exc: show_error(self, self.tr("Memory"), exc))

    def _style_tab(self) -> QWidget:
        self.style_tab = QWidget()
        layout = QVBoxLayout(self.style_tab)
        self.style_stack, self.style_view, self.style_edit = self._md_editor()
        layout.addWidget(self.style_stack)
        row = QHBoxLayout()
        self.style_edit_btn = QPushButton(self.tr("Edit"))
        self.style_save_btn = QPushButton(self.tr("Save"))
        self.style_save_btn.hide()
        self.style_edit_btn.clicked.connect(
            lambda: self._toggle_edit(self.style_stack, self.style_edit_btn, self.style_save_btn))
        self.style_save_btn.clicked.connect(
            lambda: self._write_text("style_rules.md", self.style_edit.toPlainText(), self._load_style))
        row.addStretch(1)
        row.addWidget(self.style_edit_btn)
        row.addWidget(self.style_save_btn)
        layout.addLayout(row)
        return self.style_tab

    def _load_style(self) -> None:
        path = self.services.paths.memory / "style_rules.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        self.style_view.setMarkdown(text)
        self.style_edit.setPlainText(text)
        self.style_stack.setCurrentIndex(0)
        self.style_edit_btn.show()
        self.style_save_btn.hide()

    # -- voices -------------------------------------------------------------------------------------

    def _voice_tab(self) -> QWidget:
        self.voice_tab = QWidget()
        layout = QHBoxLayout(self.voice_tab)
        left = QVBoxLayout()
        self.voice_table = QTableWidget(0, 3)
        self.voice_table.setHorizontalHeaderLabels([self.tr("Character"), self.tr("Clips in bank"),
                                                    self.tr("Clip files")])
        self.voice_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.voice_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.voice_table.itemSelectionChanged.connect(self._show_clips)
        left.addWidget(self.voice_table)
        self.clip_list = QListWidget()
        self.clip_list.itemDoubleClicked.connect(lambda item: self.player.play(item.data(Qt.ItemDataRole.UserRole)))
        left.addWidget(QLabel(self.tr("Clips (double-click to play):")))
        left.addWidget(self.clip_list)
        self.recompute_btn = QPushButton(self.tr("Recompute selected voices"))
        self.recompute_btn.clicked.connect(self._recompute)
        left.addWidget(self.recompute_btn)
        layout.addLayout(left, 1)
        right = QVBoxLayout()
        right.addWidget(QLabel(self.tr("Voice similarity (confusable pairs in red)")))
        self.heatmap = QTableWidget()
        self.heatmap.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        right.addWidget(self.heatmap)
        layout.addLayout(right, 2)
        return self.voice_tab

    def _load_voices(self) -> None:
        from subagent.memory.bootstrap import all_similarities, voice_clips

        store, paths = self.services.store, self.services.paths

        def load():
            bank = store.voice_bank()
            return store.voice_counts(), voice_clips(paths), all_similarities(bank), store.confusable_pairs()

        run_async(load, lambda r: self._fill_voices(*r))

    def _fill_voices(self, counts, clips, sims, confusable) -> None:
        self._clips = clips
        chars = sorted(set(counts) | set(clips))
        self.voice_table.setRowCount(len(chars))
        for i, c in enumerate(chars):
            for j, v in enumerate((c, counts.get(c, 0), len(clips.get(c, [])))):
                self.voice_table.setItem(i, j, _item(v, editable=False))
        bank_chars = sorted(counts)
        self.heatmap.setRowCount(len(bank_chars))
        self.heatmap.setColumnCount(len(bank_chars))
        self.heatmap.setHorizontalHeaderLabels(bank_chars)
        self.heatmap.setVerticalHeaderLabels(bank_chars)
        threshold = self.services.config.voice.confusable_similarity
        for i, a in enumerate(bank_chars):
            for j, b in enumerate(bank_chars):
                if a == b:
                    self.heatmap.setItem(i, j, _item("—", editable=False))
                    continue
                sim = sims.get(tuple(sorted((a, b))), 0.0)
                item = _item(f"{sim:.2f}", editable=False)
                shade = int(max(0.0, min(1.0, sim)) * 200)
                item.setBackground(QBrush(QColor(255, 255 - shade, 255 - shade) if sim >= threshold
                                          else QColor(255 - shade // 2, 255 - shade // 3, 255)))
                if tuple(sorted((a, b))) in confusable:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.heatmap.setItem(i, j, item)

    def _show_clips(self) -> None:
        self.clip_list.clear()
        rows = {i.row() for i in self.voice_table.selectedIndexes()}
        for r in sorted(rows):
            char = self.voice_table.item(r, 0).text()
            for f in getattr(self, "_clips", {}).get(char, []):
                item_text = f"{char}: {f.name}"
                self.clip_list.addItem(item_text)
                self.clip_list.item(self.clip_list.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def _recompute(self) -> None:
        chars = sorted({self.voice_table.item(i.row(), 0).text() for i in self.voice_table.selectedIndexes()})
        if not chars:
            return
        if not self.main.jobs.start(self.tr("recompute voices"), ["bootstrap", "--voices", *chars]):
            show_error(self, self.tr("Voice bank"), self.tr("Another job is running."))

    # -- conflicts ----------------------------------------------------------------------------------

    def _conflicts_tab(self) -> QWidget:
        self.conflict_tab = QWidget()
        layout = QVBoxLayout(self.conflict_tab)
        self.conflict_table = QTableWidget(0, 6)
        self.conflict_table.setHorizontalHeaderLabels([self.tr("Table"), self.tr("Key"), self.tr("Current"),
                                                       self.tr("Proposed"), self.tr("Source / evidence"),
                                                       self.tr("Reason")])
        self.conflict_table.horizontalHeader().setStretchLastSection(True)
        self.conflict_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.conflict_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.conflict_table)
        row = QHBoxLayout()
        self.accept_btn = QPushButton(self.tr("Accept proposal"))
        self.reject_btn = QPushButton(self.tr("Reject proposal"))
        self.accept_btn.clicked.connect(lambda: self._resolve(True))
        self.reject_btn.clicked.connect(lambda: self._resolve(False))
        row.addStretch(1)
        row.addWidget(self.accept_btn)
        row.addWidget(self.reject_btn)
        layout.addLayout(row)
        return self.conflict_tab

    def _load_conflicts(self) -> None:
        manager = self.services.manager()
        run_async(manager.conflicts, self._fill_conflicts)

    def _fill_conflicts(self, conflicts) -> None:
        self._conflicts = conflicts
        self.conflict_table.setRowCount(len(conflicts))
        for i, c in enumerate(conflicts):
            current = {k: v for k, v in c.current.items() if k in ("vi", "self_term", "address_term", "name_vi")}
            values = [c.table, c.key, json.dumps(current, ensure_ascii=False),
                      json.dumps(c.proposed, ensure_ascii=False), f"{c.source}: {', '.join(c.evidence)}", c.reason]
            for j, v in enumerate(values):
                self.conflict_table.setItem(i, j, _item(v, editable=False))

    def _resolve(self, accept: bool) -> None:
        row = self.conflict_table.currentRow()
        if row < 0 or not self._editable():
            return
        conflict = self._conflicts[row]
        manager = self.services.manager()
        run_async(lambda: manager.resolve_conflict(conflict.id, accept), lambda _: self._load_conflicts(),
                  lambda exc: show_error(self, self.tr("Conflicts"), exc))

    # -- history ------------------------------------------------------------------------------------

    def _history_tab(self) -> QWidget:
        self.history_tab = QWidget()
        layout = QVBoxLayout(self.history_tab)
        split = QSplitter(Qt.Orientation.Vertical)
        self.commits = QTableWidget(0, 3)
        self.commits.setHorizontalHeaderLabels([self.tr("Date"), self.tr("Message"), self.tr("Changes")])
        self.commits.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.commits.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.commits.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.commits.itemSelectionChanged.connect(self._show_diff)
        split.addWidget(self.commits)
        self.diff_view = QTextBrowser()
        split.addWidget(self.diff_view)
        layout.addWidget(split)
        row = QHBoxLayout()
        row.addStretch(1)
        self.rollback_btn = QPushButton(self.tr("Roll back to this version…"))
        self.rollback_btn.clicked.connect(self._rollback)
        row.addWidget(self.rollback_btn)
        layout.addLayout(row)
        return self.history_tab

    def _load_history(self) -> None:
        manager = self.services.manager()
        run_async(lambda: manager.history(200), self._fill_history,
                  lambda exc: show_error(self, self.tr("History"), exc))

    def _fill_history(self, commits) -> None:
        self._commits = commits
        self.commits.setRowCount(len(commits))
        for i, c in enumerate(commits):
            for j, v in enumerate((c.date.replace("T", " ")[:19], c.message, c.changes if c.changes is not None else "")):
                self.commits.setItem(i, j, _item(v, editable=False))

    def _show_diff(self) -> None:
        row = self.commits.currentRow()
        if row < 0:
            return
        sha = self._commits[row].sha
        manager = self.services.manager()
        run_async(lambda: manager.diff(sha), self._render_diff, lambda exc: self.diff_view.setPlainText(str(exc)))

    def _render_diff(self, d) -> None:
        parts = []
        labels = {"added": self.tr("Added"), "changed": self.tr("Changed"), "removed": self.tr("Removed")}
        for table, td in d.tables.items():
            parts.append(f"<h3>{html.escape(table)}</h3>")
            for kind in ("added", "changed", "removed"):
                rows = getattr(td, kind)
                if not rows:
                    continue
                parts.append(f"<b>{html.escape(labels[kind])} ({len(rows)})</b><ul>")
                for r in rows:
                    if kind == "changed":
                        before, after = r
                        changed = {k: (before.get(k), v) for k, v in after.items()
                                   if before.get(k) != v and k != "updated_at"}
                        text = "; ".join(f"{k}: {b} → {a}" for k, (b, a) in changed.items())
                        parts.append(f"<li>{html.escape(row_key(table, after))}: {html.escape(text)}</li>")
                    else:
                        shown = {k: v for k, v in r.items() if k not in ("updated_at",)}
                        parts.append(f"<li>{html.escape(json.dumps(shown, ensure_ascii=False))}</li>")
                parts.append("</ul>")
        if d.text_diff.strip():
            parts.append(f"<h3>{html.escape(self.tr('Text files'))}</h3><pre>{html.escape(d.text_diff)}</pre>")
        self.diff_view.setHtml("".join(parts) or html.escape(self.tr("No changes in this version.")))

    def _rollback(self) -> None:
        row = self.commits.currentRow()
        if row < 0 or not self._editable():
            return
        c = self._commits[row]
        if not confirm(self, self.tr("Roll back memory"), self.tr(
                "Restore memory to the version of {date} (“{message}”)?\n\nA new version is created; nothing is "
                "lost, and this rollback can itself be undone from the history.").format(
                    date=c.date.replace("T", " ")[:19], message=c.message)):
            return
        manager = self.services.manager()
        run_async(lambda: manager.rollback(c.sha), lambda _: self._load_history(),
                  lambda exc: show_error(self, self.tr("Roll back memory"), exc))

    def show_entry_history(self, table: str, key: str) -> None:
        entries = self.services.manager().entry_history(table, key)
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("History of {key}").format(key=key))
        dialog.resize(760, 360)
        layout = QVBoxLayout(dialog)
        view = QTableWidget(len(entries), 5)
        view.setHorizontalHeaderLabels([self.tr("Date"), self.tr("Change"), self.tr("Source"), self.tr("Details"),
                                        self.tr("Version")])
        view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for i, e in enumerate(entries):
            detail = e.reason or ""
            if e.after_json:
                after = json.loads(e.after_json)
                detail = ", ".join(f"{k}={v}" for k, v in after.items()
                                   if k not in ("updated_at", "locked") and v not in (None, ""))
            for j, v in enumerate((e.ts.replace("T", " ")[:19], e.op, e.source, detail, (e.commit_sha or "")[:8])):
                view.setItem(i, j, _item(v, editable=False))
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
