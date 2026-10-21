"""Audit (6.11): accuracy measured on a sample of finished episodes.

AuditView lists finished episodes with their sample and marking progress, draws samples, opens an episode in
the review screen's audit mode and shows the report. AuditBar is the marking strip the review screen shows in
audit mode: ✓ / ✗ / n/a per aspect, a note, "all correct, next".
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.widgets import show_error
from app.workers import run_async
from subagent.audit import NO_ID_YET
from subagent.kernel.models import AUDIT_ASPECTS, AuditMark, AuditSample

VALUES = (("ok", True), ("wrong", False), ("na", None))


class AuditBar(QWidget):
    """Marks for one sampled line. Emits `changed(AuditMark)`; `all_correct` asks for ✓ everywhere + next."""

    changed = Signal(object)
    all_correct = Signal()
    next_unmarked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        row = QHBoxLayout()
        names = {"speaker": self.tr("Speaker"), "ocr": self.tr("OCR"), "translation": self.tr("Translation"),
                 "pronouns": self.tr("Pronouns")}
        texts = {"ok": "✓", "wrong": "✗", "na": self.tr("n/a")}
        self.groups: dict[str, QButtonGroup] = {}
        self.buttons: dict[tuple[str, str], QToolButton] = {}
        for aspect in AUDIT_ASPECTS:
            row.addWidget(QLabel(names[aspect]))
            group = QButtonGroup(self)
            group.setExclusive(False)        # clicking the checked button clears it
            for key, _ in VALUES:
                b = QToolButton()
                b.setText(texts[key])
                b.setCheckable(True)
                b.setMinimumWidth(30)
                b.clicked.connect(lambda on, a=aspect, k=key: self._clicked(a, k, on))
                group.addButton(b)
                self.buttons[(aspect, key)] = b
                row.addWidget(b)
            self.groups[aspect] = group
            row.addSpacing(10)
        row.addStretch(1)
        layout.addLayout(row)
        answer = QHBoxLayout()
        self.correct_label = QLabel(self.tr("Who really speaks:"))
        self.correct = QComboBox()
        self.correct.setToolTip(self.tr("Pick the right speaker: your answers make a test set that scores later "
                                         "versions automatically (Audit → Benchmark)"))
        self.correct.currentIndexChanged.connect(lambda _: None if self._loading else self._emit())
        answer.addWidget(self.correct_label)
        answer.addWidget(self.correct, 1)
        layout.addLayout(answer)
        row2 = QHBoxLayout()
        self.note = QLineEdit()
        self.note.setPlaceholderText(self.tr("Note (optional)"))
        self.note.textEdited.connect(lambda _: self._emit())
        self.all_btn = QPushButton(self.tr("All correct, next"))
        self.all_btn.setToolTip(self.tr("Mark every aspect correct and go to the next sampled line (Ctrl+Enter)"))
        self.all_btn.clicked.connect(self.all_correct.emit)
        self.next_btn = QPushButton(self.tr("Next unmarked"))
        self.next_btn.clicked.connect(self.next_unmarked.emit)
        row2.addWidget(self.note, 1)
        row2.addWidget(self.all_btn)
        row2.addWidget(self.next_btn)
        layout.addLayout(row2)
        self._mark: AuditMark | None = None
        self._loading = False
        self._names: dict[str, str] = {}
        self._show_answer(False)

    def set_characters(self, names: dict[str, str]) -> None:
        if names == self._names:
            return
        self._names = dict(names)
        self._loading = True
        self.correct.clear()
        self.correct.addItem(self.tr("(choose)"), None)
        self.correct.addItem(self.tr("— nobody known: an NPC or a new character without an id (blank is right)"), NO_ID_YET)
        for cid, name in sorted(names.items(), key=lambda kv: kv[1]):
            self.correct.addItem(f"{name} ({cid})", cid)
        self._loading = False

    def _show_answer(self, on: bool) -> None:
        self.correct_label.setVisible(on)
        self.correct.setVisible(on)

    def show_mark(self, mark: AuditMark | None, sample: AuditSample | None, progress: str) -> None:
        self._mark = mark
        kind = ""
        if sample is not None:
            kind = self.tr("random sample") if sample.kind == "random" else self.tr("signals disagree")
            if sample.disagreement:
                kind += " · " + ", ".join(sample.disagreement)
        self.info.setText(f"<b>{self.tr('Audit')}</b> · {progress} · {kind}")
        for aspect in AUDIT_ASPECTS:
            value = getattr(mark, aspect) if mark else None
            self.buttons[(aspect, "ok")].setChecked(value is True)
            self.buttons[(aspect, "wrong")].setChecked(value is False)
            self.buttons[(aspect, "na")].setChecked(bool(mark and aspect in mark.na))
        self.note.setText(mark.note if mark else "")
        self._loading = True
        self.correct.setCurrentIndex(max(0, self.correct.findData(mark.correct_speaker if mark else None)))
        self._loading = False
        self._show_answer(bool(mark and mark.speaker is False))
        self.setEnabled(sample is not None)

    def _clicked(self, aspect: str, key: str, on: bool) -> None:
        for k, _ in VALUES:
            if k != key:
                self.buttons[(aspect, k)].setChecked(False)
        self._emit()

    def current(self, event_id: str) -> AuditMark:
        values = {a: (True if self.buttons[(a, "ok")].isChecked() else False if self.buttons[(a, "wrong")].isChecked()
                      else None) for a in AUDIT_ASPECTS}
        na = [a for a in AUDIT_ASPECTS if self.buttons[(a, "na")].isChecked()]
        correct = self.correct.currentData() if values["speaker"] is False else None
        self._show_answer(values["speaker"] is False)
        return AuditMark(event_id=event_id, note=self.note.text().strip(), na=na, correct_speaker=correct, **values)

    def _emit(self) -> None:
        self.changed.emit(None)


class AuditView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        layout = QVBoxLayout(self)
        intro = QLabel(self.tr(
            "Measure accuracy without checking every line: each finished episode gets a small random sample "
            "(flagged and unflagged lines in proportion) plus the lines where voice, picture and speaker disagree. "
            "Mark the sampled lines; the report estimates accuracy for all lines. Marks change no output and teach "
            "no memory."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([self.tr("Episode"), self.tr("Mode"), self.tr("Lines"),
                                              self.tr("Sampled"), self.tr("Marked"), self.tr("Errors so far")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(lambda _: self._open())
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        self.sample_btn = QPushButton(self.tr("Draw samples for finished episodes"))
        self.sample_btn.clicked.connect(self._sample)
        self.open_btn = QPushButton(self.tr("Audit selected episode"))
        self.open_btn.clicked.connect(self._open)
        self.report_btn = QPushButton(self.tr("Report…"))
        self.report_btn.clicked.connect(self._report)
        self.bench_btn = QPushButton(self.tr("Benchmark…"))
        self.bench_btn.setToolTip(self.tr(
            "Re-run speaker decisions of the audited episodes with today's code and memory in a sandbox, and score "
            "them against your audit answers. Changes nothing; costs a few cents of translation per episode."))
        self.bench_btn.clicked.connect(self._benchmark)
        self.history_btn = QPushButton(self.tr("Benchmark history…"))
        self.history_btn.clicked.connect(self._history)
        for b in (self.sample_btn, self.open_btn, self.report_btn, self.bench_btn, self.history_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def activate(self) -> None:
        self._load()

    def _benchmark(self) -> None:
        label, ok = QInputDialog.getText(self, self.tr("Benchmark"), self.tr("A name for this run (optional):"))
        if not ok:
            return
        args = ["audit", "benchmark"] + (["--label", label.strip()] if label.strip() else [])
        if not self.main.jobs.start("benchmark", args):
            show_error(self, self.tr("Benchmark"), self.tr("Another job is running."))
            return
        self.main.go("episodes")    # the run panel shows the progress

    def _history(self) -> None:
        def done(result) -> None:
            text, _ = result
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("Benchmark history"))
            dialog.resize(820, 600)
            box = QVBoxLayout(dialog)
            view = QTextBrowser()
            view.setMarkdown(text)
            box.addWidget(view)
            dialog.exec()

        run_async(self.services.benchmark_history, done, lambda exc: show_error(self, self.tr("Benchmark"), exc))

    def _load(self) -> None:
        run_async(self.services.audit_overview, self._fill, lambda exc: show_error(self, self.tr("Audit"), exc))

    def _fill(self, rows: list[dict]) -> None:
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            errors = (f"{r['errors'] * 100:.0f}% ({r['checked']})" if r["checked"] else "–")
            marked = f"{r['marked']} / {r['sampled']}" if r["sampled"] else "–"
            if r.get("missing"):
                marked += " · " + self.tr("{n} answers missing").format(n=r["missing"])
            values = [r["episode"], r["mode"], r["lines"], r["sampled"] or "–", marked, errors]
            if not r["auditable"]:
                values[3:] = [self.tr("not audited: reviewed by hand"), "", ""]
            for col, v in enumerate(values):
                item = QTableWidgetItem(str(v))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, r["episode"])
                    item.setData(Qt.ItemDataRole.UserRole + 1, r["auditable"])
                if not r["auditable"]:
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setToolTip(self.tr("Human-reviewed: the output is your corrected script, and its edit list "
                                            "already records every machine error. Set audit.include_human to audit "
                                            "it anyway."))
                self.table.setItem(i, col, item)

    def _selected(self) -> str | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _sample(self) -> None:
        run_async(self.services.draw_audit_samples, lambda _: self._load(),
                  lambda exc: show_error(self, self.tr("Audit"), exc))

    def _open(self) -> None:
        ep = self._selected()
        row = self.table.currentRow()
        if ep and self.table.item(row, 0).data(Qt.ItemDataRole.UserRole + 1):
            self.main.show_review(ep, audit=True)

    def _report(self) -> None:
        def done(result) -> None:
            text, path = result
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("Audit report"))
            dialog.resize(760, 560)
            box = QVBoxLayout(dialog)
            view = QTextBrowser()
            view.setMarkdown(text)
            box.addWidget(view)
            box.addWidget(QLabel(self.tr("Saved: {path}").format(path=path)))
            dialog.exec()

        run_async(self.services.audit_report, done, lambda exc: show_error(self, self.tr("Audit"), exc))
