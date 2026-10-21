"""Run panel (6.3): per-stage progress, live log tail, cost vs budget, Cancel, plain-language errors."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.messages import error_message, stage_label
from app.services.episodes import STAGE_NAMES


class RunPanel(QWidget):
    def __init__(self, window, parent: QWidget | None = None):
        super().__init__(parent)
        self.main = window
        self.jobs = window.jobs
        self.last_stage = ""
        layout = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel(self.tr("No job running"))
        self.title.setStyleSheet("font-weight: bold;")
        self.cost = QLabel()
        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.jobs.cancel)
        head.addWidget(self.title, 1)
        head.addWidget(self.cost)
        head.addWidget(self.cancel_btn)
        layout.addLayout(head)

        body = QHBoxLayout()
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        self.bars: dict[str, QProgressBar] = {}
        stages = [s for s in STAGE_NAMES if s != "report"]
        for i, stage in enumerate(stages):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setFormat("")
            self.bars[stage] = bar
            grid.addWidget(QLabel(stage_label(stage)), i % 8, (i // 8) * 2)
            grid.addWidget(bar, i % 8, (i // 8) * 2 + 1)
        body.addWidget(grid_host, 2)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        body.addWidget(self.log, 3)
        layout.addLayout(body)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.error.setStyleSheet("color: #c0392b;")
        self.error.hide()
        layout.addWidget(self.error)

        self.jobs.started.connect(self._started)
        self.jobs.progress.connect(self._progress)
        self.jobs.log_line.connect(self.log.appendPlainText)
        self.jobs.finished.connect(self._finished)

    def _started(self, name: str) -> None:
        self.title.setText(self.tr("Running: {job}").format(job=name))
        self.cancel_btn.setEnabled(True)
        self.error.hide()
        self.log.clear()
        self.last_stage = ""
        for bar in self.bars.values():
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("")

    def _progress(self, p: dict) -> None:
        stage, status = p.get("stage", ""), p.get("status", "")
        if stage == "batch":
            if status == "progress" and p.get("message"):
                self.title.setText(self.tr("Running: {job} · episode {episode}").format(
                    job=self.main.jobs.name, episode=p["message"]))
                for b in self.bars.values():           # a new episode: its stages start over
                    b.setRange(0, 100)
                    b.setValue(0)
                    b.setFormat("")
            if p.get("message") and status in ("info", "done"):
                self.log.appendPlainText(f"[{self.tr('Batch')}] {p['message']}")
            return
        budget = self.main.services.config.budget.max_cost_per_episode
        self.cost.setText(self.tr("Cost ${cost} / ${budget}").format(cost=f"{float(p.get('cost') or 0):.3f}",
                                                                     budget=f"{budget:.2f}"))
        if p.get("message") and status in ("done", "info", "error", "awaiting_review", "finished"):
            self.log.appendPlainText(f"[{stage_label(stage)}] {p['message']}")
        bar = self.bars.get(stage)
        if bar is None:
            return
        if status == "start":
            self.last_stage = stage
            bar.setRange(0, 0)   # busy until counts arrive
        elif status == "progress" and p.get("total"):
            bar.setRange(0, int(p["total"]))
            bar.setValue(int(p.get("done") or 0))
            bar.setFormat("%v / %m")
        elif status in ("done", "skipped"):
            bar.setRange(0, 100)
            bar.setValue(100)
            bar.setFormat(self.tr("skipped") if status == "skipped" else self.tr("done"))
        elif status == "error":
            bar.setRange(0, 100)
            bar.setFormat(self.tr("failed"))

    def _finished(self, name: str, code: int, error: dict) -> None:
        self.cancel_btn.setEnabled(False)
        for bar in self.bars.values():
            if bar.maximum() == 0:
                bar.setRange(0, 100)
        if code == 0:
            self.title.setText(self.tr("Finished: {job}").format(job=name))
            return
        self.title.setText(self.tr("Failed: {job}").format(job=name))
        text = error_message(error.get("error_code"), error.get("message", ""))
        if self.last_stage:
            text += "\n" + self.tr("Resume continues from: {stage}").format(stage=stage_label(self.last_stage))
        self.error.setText(text)
        self.error.show()
