"""Navigation shell (6.2): sidebar, stacked screens, status bar with job, cost vs budget and device."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.jobs import JobRunner
from app.messages import stage_label
from app.services import Services
from app.workers import run_async

_WINDOWS: list = []      # windows opened by a series switch (kept alive; the first one is held by main())


class NewSeriesDialog(QDialog):
    """Slug, display name, translation register and (optional) work folder of a new series."""

    def __init__(self, parent: QWidget, root):
        super().__init__(parent)
        from subagent import series as sr

        self.setWindowTitle(self.tr("New series"))
        form = QFormLayout(self)
        self.slug = QLineEdit()
        self.slug.setPlaceholderText(self.tr("short id, e.g. my-show"))
        self.name = QLineEdit()
        self.register = QComboBox()
        for reg in sr.registers(root) or ["co_trang_tien_hiep"]:
            self.register.addItem(reg, reg)
        self.work = QLineEdit()
        self.work.setPlaceholderText(self.tr("default: a subfolder of the shared work folder"))
        form.addRow(self.tr("Id"), self.slug)
        form.addRow(self.tr("Name"), self.name)
        form.addRow(self.tr("Translation style"), self.register)
        form.addRow(self.tr("Work folder"), self.work)
        form.addRow(QLabel(self.tr("After creating it, the Bootstrap screen opens: calibrate the subtitles, write the "
                                   "cast and add voice clips, as for the first series.")))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _check(self) -> None:
        from subagent import series as sr

        try:
            sr.check_slug(self.slug.text().strip())
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, self.tr("New series"), str(exc))
            return
        self.accept()

    def values(self) -> tuple[str, str, str, str | None]:
        slug = self.slug.text().strip()
        return slug, self.name.text().strip() or slug, self.register.currentData(), self.work.text().strip() or None


class MainWindow(QMainWindow):
    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.jobs = JobRunner(services.root, self, services.paths.series)
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
        left = QWidget()
        left_col = QVBoxLayout(left)
        left_col.setContentsMargins(0, 0, 0, 0)
        self.series_box = self._series_picker()
        left_col.addWidget(self.series_box)
        left_col.addWidget(self.sidebar, 1)
        left.setFixedWidth(170)
        splitter.addWidget(left)
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

    # -- series ---------------------------------------------------------------------------------------

    NEW_SERIES = "__new__"

    def _series_picker(self) -> QComboBox:
        """The series this window shows; hidden in the single-series layout (no data/series/ yet)."""
        from subagent.config import list_series

        box = QComboBox()
        box.setToolTip(self.tr("The series (show) you are working on"))
        names = list_series(self.services.root)
        current = self.services.paths.series
        for slug in names:
            box.addItem(slug, slug)
        box.addItem(self.tr("New series…"), self.NEW_SERIES)
        if current in names:
            box.setCurrentIndex(names.index(current))
        box.setVisible(bool(names))
        box.activated.connect(self._series_chosen)
        return box

    def _series_chosen(self, index: int) -> None:
        slug = self.series_box.itemData(index)
        if slug == self.services.paths.series:
            return
        if slug == self.NEW_SERIES:
            dialog = NewSeriesDialog(self, self.services.root)
            if dialog.exec():
                from subagent import series as sr

                try:
                    sr.add(self.services.root, *dialog.values())
                except Exception as exc:  # noqa: BLE001 - shown to the user
                    from app.widgets import show_error

                    show_error(self, self.tr("New series"), exc)
                    self._reset_series_box()
                    return
                self.switch_series(dialog.values()[0], then="bootstrap")
                return
            self._reset_series_box()
            return
        self.switch_series(slug)

    def _reset_series_box(self) -> None:
        current = self.series_box.findData(self.services.paths.series)
        self.series_box.setCurrentIndex(max(0, current))

    def switch_series(self, slug: str, then: str | None = None) -> None:
        """Make `slug` the default series and rebuild the window around it (every screen reloads)."""
        from subagent import series as sr

        if self.jobs.is_running() or self.services.jobs_running():
            QMessageBox.information(self, self.tr("Series"),
                                    self.tr("A job is running. Switch series when it has finished."))
            self._reset_series_box()
            return
        sr.set_default(self.services.root, slug)
        window = MainWindow(Services(self.services.root))
        window.show()
        if then:
            window.go(then)
        _WINDOWS.append(window)
        self._switching = True
        self.close()

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
        if self in _WINDOWS and getattr(self, "_switching", False):
            _WINDOWS.remove(self)
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
