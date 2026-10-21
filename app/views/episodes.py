"""Episodes screen (6.3): table, add files / folders / drag and drop, run actions, relink, run panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.messages import agent_label, stage_label, status_label
from app.views.common import choose_batch_on_exists, choose_on_exists, job_busy
from app.views.run import RunPanel
from app.widgets import confirm, show_error
from app.workers import run_async
from subagent.kernel import SubagentError
from subagent.pipeline import STAGES
from subagent.workspace import AddCandidate


class DropTable(QTableWidget):
    paths_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()


class AddDialog(QDialog):
    """File → detected episode number (editable). Nothing is registered until confirmed (5.21)."""

    def __init__(self, main, candidates: list[AddCandidate], parent: QWidget | None = None):
        super().__init__(parent)
        self.main = main
        self.candidates = candidates
        self.setWindowTitle(self.tr("Add episodes"))
        self.resize(760, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Check the episode numbers. Memory builds up in episode order, so a wrong "
                                        "number matters.")))
        self.table = QTableWidget(len(candidates), 3)
        self.table.setHorizontalHeaderLabels([self.tr("File"), self.tr("Episode"), self.tr("Note")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i, c in enumerate(candidates):
            name = QTableWidgetItem(Path(c.path).name)
            name.setToolTip(c.path)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            number = QTableWidgetItem("" if c.number is None else str(c.number))
            note = QTableWidgetItem(self._note(c))
            note.setFlags(note.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if c.problem:
                number.setFlags(number.flags() & ~Qt.ItemFlag.ItemIsEditable)
                for item in (name, number, note):
                    item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(i, 0, name)
            self.table.setItem(i, 1, number)
            self.table.setItem(i, 2, note)
        layout.addWidget(self.table)
        self.errors = QLabel()
        self.errors.setStyleSheet("color: #c0392b;")
        self.errors.setWordWrap(True)
        layout.addWidget(self.errors)
        buttons = QDialogButtonBox()
        self.ok = buttons.addButton(self.tr("Register"), QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._register)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _note(self, c: AddCandidate) -> str:
        if c.problem == "duplicate":
            return self.tr("Duplicate of {id}; skipped").format(id=c.duplicate_of)
        if c.problem == "no_video_stream":
            return self.tr("No video stream; skipped")
        if c.number is None:
            return self.tr("No number detected: enter it")
        return ""

    def _register(self) -> None:
        for i, c in enumerate(self.candidates):
            text = self.table.item(i, 1).text().strip()
            c.number = int(text) if text.isdigit() else None
        reg = self.main.services.registry
        errors = reg.validate_numbers(self.candidates)
        if errors:
            self.errors.setText("\n".join(errors))
            return
        try:
            reg.register(self.candidates)
        except SubagentError as exc:
            self.errors.setText(str(exc))
            return
        self.accept()


class EpisodesView(QWidget):
    COLS = ["id", "file", "progress", "status", "flags", "cost"]

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        self.rows = []
        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        add_files = QPushButton(self.tr("Add files…"))
        add_folder = QPushButton(self.tr("Add folder…"))
        self.recursive = QCheckBox(self.tr("Include subfolders"))
        refresh = QPushButton(self.tr("Refresh"))
        add_files.clicked.connect(self._add_files)
        add_folder.clicked.connect(self._add_folder)
        refresh.clicked.connect(self.refresh)
        for w in (add_files, add_folder, self.recursive):
            bar.addWidget(w)
        bar.addStretch(1)
        bar.addWidget(QLabel(self.tr("Drop video files or folders on the table to add them.")))
        bar.addWidget(refresh)
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self.table = DropTable()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels([self.tr("Episode"), self.tr("File"), self.tr("Stages"),
                                              self.tr("Status"), self.tr("Flags"), self.tr("Cost")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)   # several: a batch
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.paths_dropped.connect(lambda paths: self._prepare(paths, self.recursive.isChecked()))
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.doubleClicked.connect(lambda _: self._review())
        top_layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for key, label, slot in [
            ("run_auto", self.tr("Run (auto)"), lambda: self._run("auto")),
            ("run_human", self.tr("Run (human review)"), lambda: self._run("human")),
            ("resume", self.tr("Resume"), self._resume),
            ("rerun", self.tr("Rerun from stage…"), self._rerun),
            ("review", self.tr("Review"), self._review),
            ("render", self.tr("Render"), self._render),
            ("relink", self.tr("Relink…"), self._relink),
            ("output", self.tr("Open output folder"), self._open_output),
            ("report", self.tr("Open report"), self._open_report),
            ("clean", self.tr("Clean temporary files"), self._clean),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            actions.addWidget(b)
            self.buttons[key] = b
        actions.addStretch(1)
        top_layout.addLayout(actions)
        splitter.addWidget(top)
        self.run_panel = RunPanel(main)
        splitter.addWidget(self.run_panel)
        splitter.setSizes([480, 320])
        layout.addWidget(splitter)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._schedule_refresh)
        self.watcher.directoryChanged.connect(self._schedule_refresh)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.refresh)
        main.jobs.finished.connect(lambda *a: self.refresh())
        main.jobs.progress.connect(lambda p: self._schedule_refresh() if p.get("status") in ("done", "error") else None)
        self._update_buttons()
        self.refresh()

    def activate(self) -> None:
        self.refresh()

    # -- data ---------------------------------------------------------------------------------------

    def _schedule_refresh(self, *_: object) -> None:
        self._timer.start()

    def refresh(self) -> None:
        run_async(self.services.episode_rows, self._fill, lambda exc: show_error(self, self.tr("Episodes"), exc))

    def _fill(self, rows) -> None:
        selected = self.current_id()
        self.rows = rows
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            cost = f"${r.cost:.3f}" + (" + ?" if r.unpriced_models else "")
            values = [r.episode.id, Path(r.episode.source_path).name, f"{r.stages_done} / {r.stages_total}",
                      status_label(r.status), str(r.flags), cost]
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                if j == 1:
                    item.setToolTip(r.episode.source_path)
                if j == 3 and r.status in ("failed", "missing", "interrupted"):
                    item.setForeground(Qt.GlobalColor.red)
                if j == 5 and r.cost_by_agent:
                    item.setToolTip("\n".join(f"{agent_label(t)}: ${c:.4f}" for t, c in
                                               sorted(r.cost_by_agent.items(), key=lambda kv: -kv[1])))
                if j == 5 and r.unpriced_models:
                    item.setForeground(Qt.GlobalColor.darkYellow)
                    item.setToolTip(self.tr("Incomplete: no price set for {models} (Settings > Advanced, llm.prices)")
                                    .format(models=", ".join(r.unpriced_models)))
                self.table.setItem(i, j, item)
            if r.episode.id == selected:
                self.table.selectRow(i)
        self._watch()
        self._update_buttons()

    def _watch(self) -> None:
        paths = self.services.paths
        wanted = [str(paths.episodes_index)] if paths.episodes_index.is_file() else []
        for r in self.rows:
            state = paths.episode_dir(r.episode.id) / "state.json"
            if state.is_file():
                wanted.append(str(state))
        current = set(self.watcher.files())
        missing = [p for p in wanted if p not in current]
        if missing:
            self.watcher.addPaths(missing)

    def current_row(self):
        idx = self.table.currentRow()
        return self.rows[idx] if 0 <= idx < len(self.rows) else None

    def current_id(self) -> str | None:
        row = self.current_row()
        return row.episode.id if row else None

    def selected_ids(self) -> list[str]:
        """Selected episodes in episode order (the current one when nothing else is selected)."""
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        picked = [self.rows[r] for r in rows if 0 <= r < len(self.rows)]
        if not picked and self.current_row() is not None:
            picked = [self.current_row()]
        return [r.episode.id for r in sorted(picked, key=lambda r: r.episode.number)]

    def _update_buttons(self) -> None:
        row = self.current_row()
        has = row is not None
        status = row.status if row else ""
        missing = status == "missing"
        for b in self.buttons.values():
            b.setEnabled(has and not missing)
        self.buttons["relink"].setEnabled(has)
        self.buttons["review"].setEnabled(has and status in ("awaiting_review", "done"))
        self.buttons["output"].setEnabled(has and bool(row.episode.output_path))
        self.buttons["report"].setEnabled(has and self.services.report_path(row.episode.id).is_file())
        self.buttons["render"].setEnabled(has and not missing and
                                          (self.services.paths.episode_dir(row.episode.id) / "approved.jsonl").is_file())

    # -- adding -------------------------------------------------------------------------------------

    def _add_files(self) -> None:
        exts = " ".join(f"*{e}" for e in self.services.config.episodes.video_extensions)
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Add video files"), "",
                                                self.tr("Videos ({exts})").format(exts=exts))
        if files:
            self._prepare([Path(f) for f in files], False)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Add a folder of videos"))
        if folder:
            self._prepare([Path(folder)], self.recursive.isChecked())

    def _prepare(self, paths: list[Path], recursive: bool) -> None:
        self.main.job_label.setText(self.tr("Checking videos…"))

        def done(cands: list[AddCandidate]) -> None:
            self.main.job_label.setText("")
            if not cands:
                QMessageBox.information(self, self.tr("Add episodes"), self.tr("No video files found."))
                return
            if AddDialog(self.main, cands, self).exec():
                self.refresh()

        run_async(lambda: self.services.prepare_add(paths, recursive), done,
                  lambda exc: show_error(self, self.tr("Add episodes"), exc))

    # -- actions ------------------------------------------------------------------------------------

    def _order_ok(self, ep_id: str) -> bool:
        earlier = self.services.earlier_not_done(ep_id)
        if not earlier:
            return True
        return confirm(self, self.tr("Episode order"), self.tr(
            "Earlier episodes are not done yet: {ids}.\nMemory builds up episode by episode, so translating out "
            "of order may use less context. Continue anyway?").format(ids=", ".join(earlier)))

    def _start(self, name: str, args: list[str]) -> None:
        if not self.main.jobs.start(name, args):
            job_busy(self, self.main)

    def _run(self, mode: str, extra: list[str] | None = None, *, rerun: bool = True) -> None:
        """Run / Run (human review): always processes the episode again (`--rerun`), also when it is done or
        waiting for review. Resume passes rerun=False and only does what is missing."""
        selected = self.selected_ids()
        if len(selected) > 1 and not extra:
            self._run_batch(selected, mode)
            return
        ep = self.current_id()
        if not ep or job_busy(self, self.main) or not self._order_ok(ep):
            return
        row = self.current_row()
        if (rerun and not extra and row is not None and row.status in ("done", "awaiting_review")
                and not self._confirm_rerun([ep])):
            return
        args = ["run", ep, "--mode", mode, *(extra or [])]
        if rerun and not extra:
            args.append("--rerun")
        if mode == "auto":
            on_exists = choose_on_exists(self, self.main, ep)
            if on_exists is None:
                return
            args += ["--on-exists", on_exists]
        self._start(f"{ep} ({mode})", args)

    def _run_batch(self, ids: list[str], mode: str) -> None:
        """Several selected episodes: one batch job, in episode order (6.3)."""
        if job_busy(self, self.main):
            return
        status = {r.episode.id: r.status for r in self.rows}
        todo = list(ids)
        again = [e for e in todo if status.get(e) in ("done", "awaiting_review")]
        earlier = sorted({e for ep in todo for e in self.services.earlier_not_done(ep)} - set(todo))
        text = self.tr("Run {n} episodes in episode order ({mode}): {ids}").format(
            n=len(todo), mode=self.tr("auto") if mode == "auto" else self.tr("human review"), ids=", ".join(todo))
        if again:
            text += "\n\n" + self.tr("Run again with today's memory (done or waiting for review): {ids}. Their "
                                       "translations and review drafts are replaced; a review in progress is "
                                       "lost.").format(ids=", ".join(again))
        if earlier:
            text += "\n\n" + self.tr("Earlier episodes not done and not selected: {ids}. Memory builds up episode by "
                                      "episode.").format(ids=", ".join(earlier))
        text += "\n\n" + (self.tr("Auto mode stops at the first failed episode; finished episodes stay done.")
                           if mode == "auto" else
                           self.tr("Each episode stops at review; a failed episode does not stop the others."))
        if not confirm(self, self.tr("Run several episodes"), text):
            return
        args = ["batch", *todo, "--mode", mode, "--rerun"]
        if mode == "auto":
            existing = [e for e in todo if self.services.output_exists(e)]
            if existing:
                choice = choose_batch_on_exists(self, existing)
                if choice is None:
                    return
                args += ["--on-exists", choice]
            else:
                args += ["--on-exists", "fail"]
        self._start(self.tr("{n} episodes ({mode})").format(n=len(todo), mode=mode), args)

    def _mode_for(self, ep_id: str) -> str:
        from subagent.workspace import load_state

        return load_state(self.services.paths.episode_dir(ep_id), ep_id).mode or self.services.config.review.mode

    def _confirm_rerun(self, ids: list[str]) -> bool:
        from subagent.pipeline import RERUN_FROM

        ep = ids[0]
        files = self.services.discarded_by_rerun(ep, RERUN_FROM)
        text = self.tr("{ep} is already done or waiting for review. Run it again with today's memory?\n\n"
                       "From OCR correction on, every step runs again; its translation and review draft are "
                       "replaced (a review in progress is lost). Memory and the finished video change only when "
                       "the new run is finished.\n\nReplaced: {files}").format(ep=ep, files=", ".join(files) or "-")
        return confirm(self, self.tr("Run again"), text)

    def _resume(self) -> None:
        row = self.current_row()
        if row is None:
            return
        if row.status == "awaiting_review":
            self._review()
            return
        self._run(self._mode_for(row.episode.id), rerun=False)

    def _rerun(self) -> None:
        ep = self.current_id()
        if not ep:
            return
        labels = [stage_label(s.name) for s in STAGES]
        choice, ok = QInputDialog.getItem(self, self.tr("Rerun from stage"), self.tr("Stage:"), labels, 0, False)
        if not ok:
            return
        stage = STAGES[labels.index(choice)].name
        discarded = self.services.discarded_by_rerun(ep, stage)
        text = self.tr("Rerun {ep} from “{stage}”? These results will be replaced:\n\n{files}").format(
            ep=ep, stage=choice, files="\n".join(discarded) or self.tr("(none yet)"))
        if confirm(self, self.tr("Rerun from stage"), text):
            self._run(self._mode_for(ep), ["--from", stage])

    def _review(self) -> None:
        ep = self.current_id()
        if ep:
            self.main.show_review(ep)

    def _render(self) -> None:
        ep = self.current_id()
        if not ep or job_busy(self, self.main):
            return
        on_exists = choose_on_exists(self, self.main, ep)
        if on_exists is not None:
            self._start(f"{ep} (render)", ["render", ep, "--on-exists", on_exists])

    def _relink(self) -> None:
        ep = self.current_id()
        if not ep:
            return
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Find the video for {ep}").format(ep=ep))
        if not path:
            return
        try:
            _, matches = self.services.registry.relink(ep, Path(path))
        except SubagentError as exc:
            show_error(self, self.tr("Relink"), exc)
            return
        if not matches:
            box = QMessageBox(QMessageBox.Icon.Warning, self.tr("Different file?"), self.tr(
                "This file does not match the original video's fingerprint. It may be a different file, and "
                "existing results may not line up."), parent=self)
            keep = box.addButton(self.tr("Keep results"), QMessageBox.ButtonRole.AcceptRole)
            rerun = box.addButton(self.tr("Rerun from the start"), QMessageBox.ButtonRole.DestructiveRole)
            box.exec()
            if box.clickedButton() is rerun:
                self._run(self._mode_for(ep), ["--from", "ingest"])
            del keep
        self.refresh()

    def _open_output(self) -> None:
        from subagent.output import reveal_in_explorer

        row = self.current_row()
        if row and row.episode.output_path:
            path = Path(row.episode.output_path)
            if path.exists():
                reveal_in_explorer(path)
            elif path.parent.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _open_report(self) -> None:
        ep = self.current_id()
        if ep:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.services.report_path(ep))))

    def _clean(self) -> None:
        ep = self.current_id()
        if ep and not job_busy(self, self.main) and confirm(self, self.tr("Clean temporary files"), self.tr(
                "Delete {ep}'s temporary files (frame crops, audio, preview, render leftovers)? The script, edits "
                "and reports are kept.").format(ep=ep)):
            self._start(f"{ep} (clean)", ["clean", ep])
