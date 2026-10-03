"""Navigation shell (6.2): sidebar, stacked screens, status bar with job, cost vs budget and device."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from app.jobs import JobRunner
from app.messages import stage_label
from app.services import Services
from app.workers import run_async


class MainWindow(QMainWindow):
    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.jobs = JobRunner(services.root, self)
        self.setWindowTitle(self.tr("Subtitle Agent"))
        self.resize(1400, 860)

        from app.views.audit import AuditView
        from app.views.bootstrap import BootstrapView
        from app.views.dreaming import DreamingView
        from app.views.episodes import EpisodesView
        from app.views.memory import MemoryView
        from app.views.review import ReviewView
        from app.views.settings import SettingsView

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(170)
        self.stack = QStackedWidget()
        self.views = {
            "episodes": EpisodesView(self),
            "review": ReviewView(self),
            "memory": MemoryView(self),
            "bootstrap": BootstrapView(self),
            "dreaming": DreamingView(self),
            "audit": AuditView(self),
            "settings": SettingsView(self),
        }
        labels = {
            "episodes": self.tr("Episodes"), "review": self.tr("Review"), "memory": self.tr("Memory"),
            "bootstrap": self.tr("Bootstrap"), "dreaming": self.tr("Dreaming"), "audit": self.tr("Audit"),
            "settings": self.tr("Settings"),
        }
        for key, view in self.views.items():
            item = QListWidgetItem(labels[key])
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar.addItem(item)
            self.stack.addWidget(view)
        self.sidebar.currentRowChanged.connect(self._navigate)

        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter()
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        row.addWidget(splitter)
        self.setCentralWidget(central)

        self.job_label = QLabel(self.tr("No job running"))
        self.cost_label = QLabel()
        self.device_label = QLabel(self.tr("Device: …"))
        sb = self.statusBar()
        sb.addWidget(self.job_label, 1)
        sb.addPermanentWidget(self.cost_label)
        sb.addPermanentWidget(self.device_label)
        self._update_cost(0.0)
        self.jobs.started.connect(lambda name: self.job_label.setText(self.tr("Running: {job}").format(job=name)))
        self.jobs.progress.connect(self._on_progress)
        self.jobs.finished.connect(self._on_job_finished)
        self._detect_device()

        geometry = QSettings().value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.sidebar.setCurrentRow(0)

    def _navigate(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        view = self.stack.currentWidget()
        if hasattr(view, "activate"):
            view.activate()

    def go(self, key: str) -> QWidget:
        keys = list(self.views)
        self.sidebar.setCurrentRow(keys.index(key))
        return self.views[key]

    def show_review(self, episode_id: str, event_id: str | None = None, read_only: bool | None = None, *,
                    audit: bool = False) -> None:
        view = self.go("review")
        view.open_episode(episode_id, event_id=event_id, read_only=read_only, audit=audit)

    def _detect_device(self) -> None:
        from subagent.device import describe

        config = self.services.config
        run_async(lambda: describe(config),
                  lambda label: self.device_label.setText(self.tr("Device: {device}").format(device=label)))

    def _update_cost(self, cost: float) -> None:
        budget = self.services.config.budget.max_cost_per_episode
        self.cost_label.setText(self.tr("Cost ${cost} / ${budget}").format(cost=f"{cost:.3f}", budget=f"{budget:.2f}"))

    def _on_progress(self, payload: dict) -> None:
        self._update_cost(float(payload.get("cost") or 0.0))
        stage = payload.get("stage", "")
        self.job_label.setText(self.tr("Running: {job} — {stage}").format(job=self.jobs.name, stage=stage_label(stage)))

    def _on_job_finished(self, name: str, code: int, error: dict) -> None:
        if code == 0:
            self.job_label.setText(self.tr("Finished: {job}").format(job=name))
        else:
            self.job_label.setText(self.tr("Failed: {job}").format(job=name))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.jobs.is_running():
            answer = QMessageBox.question(
                self, self.tr("Job running"),
                self.tr("A job is running ({job}). Cancel it and close? It can be resumed later.").format(job=self.jobs.name))
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.jobs.cancel()
        for view in self.views.values():
            if hasattr(view, "shutdown"):
                view.shutdown()
        QSettings().setValue("window/geometry", self.saveGeometry())
        event.accept()
