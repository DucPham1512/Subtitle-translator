"""Navigation shell (6.2): sidebar, stacked screens, status bar with job, cost vs budget and device."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
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


class StyleDialog(QDialog):
    """A new translation style: id, name, the pronoun words the rule check looks for, and the translator's
    instructions (saved as prompts/registers/<id>.md, shared by every series)."""

    def __init__(self, parent: QWidget, root):
        super().__init__(parent)
        from subagent.settings.registers import TEMPLATE

        self.root = root
        self.saved: str | None = None
        self.setWindowTitle(self.tr("New translation style"))
        self.resize(720, 560)
        form = QFormLayout(self)
        self.style_id = QLineEdit()
        self.style_id.setPlaceholderText(self.tr("short id, e.g. hien_dai"))
        self.style_name = QLineEdit()
        self.style_name.setPlaceholderText(self.tr("e.g. Hiện đại"))
        self.style_name.textChanged.connect(self._name_changed)
        self.terms = QLineEdit()
        self.terms.setPlaceholderText(self.tr("e.g. tôi, bạn, anh, em, chị, mày, tao"))
        self.body = QPlainTextEdit()
        self.body.setPlainText(TEMPLATE.format(name="…"))
        self._template = self.body.toPlainText()
        form.addRow(self.tr("Id"), self.style_id)
        form.addRow(self.tr("Name"), self.style_name)
        form.addRow(self.tr("Pronoun words"), self.terms)
        form.addRow(QLabel(self.tr("Instructions for the translator (setting, names and terms, pronoun system, "
                                   "tone). They replace the register section of the translator prompt.")))
        form.addRow(self.body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _name_changed(self, name: str) -> None:
        from subagent.settings.registers import TEMPLATE

        if self.body.toPlainText() == self._template:          # untouched template: follow the name
            self.body.setPlainText(TEMPLATE.format(name=name.strip() or "…"))
            self._template = self.body.toPlainText()

    def _save(self) -> None:
        from subagent.settings.registers import save_register, split_terms

        rid = self.style_id.text().strip()
        try:
            save_register(self.root, rid, self.style_name.text(), self.body.toPlainText(),
                          split_terms(self.terms.text()))
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        self.saved = rid
        self.accept()


class NewSeriesDialog(QDialog):
    """Slug, display name, translation register, how pronouns are decided (character identification, or one
    default pronoun pair, 5.11a) and (optional) work folder of a new series."""

    def __init__(self, parent: QWidget, root):
        super().__init__(parent)
        self.root = root
        self.setWindowTitle(self.tr("New series"))
        form = QFormLayout(self)
        self.slug = QLineEdit()
        self.slug.setPlaceholderText(self.tr("short id, e.g. my-show"))
        self.name = QLineEdit()
        self.register = QComboBox()
        self._fill_styles()
        new_style = QPushButton(self.tr("New style…"))
        new_style.clicked.connect(self._new_style)
        style_row = QHBoxLayout()
        style_row.addWidget(self.register, 1)
        style_row.addWidget(new_style)
        self.work = QLineEdit()
        self.work.setPlaceholderText(self.tr("default: a subfolder of the shared work folder"))
        browse = QPushButton(self.tr("Choose…"))
        browse.clicked.connect(self._pick_work)
        work_row = QHBoxLayout()
        work_row.addWidget(self.work, 1)
        work_row.addWidget(browse)
        self.identify = QCheckBox(self.tr("Identify characters (speaker and listener per line)"))
        self.identify.setToolTip(self.tr(
            "On: voices and pictures find who speaks to whom, and the pronoun matrix decides xưng hô per pair. "
            "Off: no character identification; every line uses the default pronoun pair below."))
        self.self_term = QLineEdit()
        self.self_term.setPlaceholderText(self.tr("how the speaker says \"I\", e.g. ta"))
        self.address_term = QLineEdit()
        self.address_term.setPlaceholderText(self.tr("how the speaker says \"you\", e.g. ngươi"))
        pair_row = QHBoxLayout()
        pair_row.addWidget(self.self_term, 1)
        pair_row.addWidget(QLabel("/"))
        pair_row.addWidget(self.address_term, 1)
        self.pair_note = QLabel()
        self.pair_note.setWordWrap(True)
        self.identify.toggled.connect(self._identify_changed)
        form.addRow(self.tr("Id"), self.slug)
        form.addRow(self.tr("Name"), self.name)
        form.addRow(self.tr("Translation style"), style_row)
        form.addRow(self.tr("Pronouns"), self.identify)
        form.addRow(self.tr("Default pronoun pair"), pair_row)
        form.addRow("", self.pair_note)
        form.addRow(self.tr("Work folder"), work_row)
        self._identify_changed(False)
        form.addRow(QLabel(self.tr("After creating it, the Bootstrap screen opens: calibrate the subtitles, write the "
                                   "cast and add voice clips, as for the first series.")))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._check)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _identify_changed(self, on: bool) -> None:
        self.pair_note.setText(self.tr(
            "Used only if you turn character identification off later (Settings).") if on else self.tr(
            "Required: every line of this series uses this pair."))

    def _pick_work(self) -> None:
        """Choose the series' work folder; starts at the typed folder, else the shared work folder."""
        start = self.work.text().strip() or str(self._shared_work())
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder"), start)
        if folder:
            self.work.setText(str(Path(folder)))

    def _shared_work(self) -> Path:
        import yaml

        try:
            data = yaml.safe_load((Path(self.root) / "config.yaml").read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return Path(self.root)
        work = Path((data.get("paths") or {}).get("work_dir") or "work")
        return work if work.is_absolute() else Path(self.root) / work

    def _fill_styles(self, select: str | None = None) -> None:
        from subagent.settings.registers import list_registers

        self.register.clear()
        for style in list_registers(self.root):
            self.register.addItem(f"{style.name} ({style.id})", style.id)
        if select:
            self.register.setCurrentIndex(max(0, self.register.findData(select)))

    def _new_style(self) -> None:
        dialog = StyleDialog(self, self.root)
        if dialog.exec() and dialog.saved:
            self._fill_styles(select=dialog.saved)

    def _check(self) -> None:
        from subagent.settings import series as sr

        try:
            sr.check_slug(self.slug.text().strip())
        except Exception as exc:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, self.tr("New series"), str(exc))
            return
        if not self.register.currentData():
            QMessageBox.warning(self, self.tr("New series"), self.tr("Choose a translation style, or create one."))
            return
        if not self.identify.isChecked() and not (self.self_term.text().strip() and self.address_term.text().strip()):
            QMessageBox.warning(self, self.tr("New series"), self.tr(
                "Without character identification every line uses the default pronoun pair: fill in both words."))
            (self.address_term if self.self_term.text().strip() else self.self_term).setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str, str, str | None]:
        slug = self.slug.text().strip()
        return slug, self.name.text().strip() or slug, self.register.currentData(), self.work.text().strip() or None

    def pronouns(self) -> dict:
        """series.add keywords: the identification mode and the default pronoun pair."""
        return {"identify": self.identify.isChecked(), "self_term": self.self_term.text().strip(),
                "address_term": self.address_term.text().strip()}


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
        from subagent.settings.config import list_series

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
                from subagent.settings import series as sr

                try:
                    sr.add(self.services.root, *dialog.values(), **dialog.pronouns())
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
        from subagent.settings import series as sr

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
        from subagent.infra.device import describe

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
