"""Settings screen (6.9): general, files, advanced YAML, API keys, language, shortcuts."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QProcess, QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import shortcuts
from app.widgets import show_error
from app.workers import run_async
from subagent.settings import update_config_values
from subagent.workspace import detect_number


class SettingsView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._tab_keys: list[str] = []
        for key, title, builder in [
            ("general", self.tr("General"), self._general_tab),
            ("files", self.tr("Files"), self._files_tab),
            ("advanced", self.tr("Advanced"), self._advanced_tab),
            ("keys", self.tr("API keys"), self._keys_tab),
            ("language", self.tr("Language"), self._language_tab),
            ("shortcuts", self.tr("Shortcuts"), self._shortcuts_tab),
        ]:
            self.tabs.addTab(builder(), title)
            self._tab_keys.append(key)

    def activate(self) -> None:
        self._load()

    def show_tab(self, key: str) -> None:
        self.tabs.setCurrentIndex(self._tab_keys.index(key))

    def _save_values(self, updates: dict) -> bool:
        try:
            update_config_values(self.services.root, updates)
            self.services.reload()
        except Exception as exc:  # noqa: BLE001
            show_error(self, self.tr("Settings"), exc)
            return False
        self._load()
        QMessageBox.information(self, self.tr("Settings"), self.tr("Saved."))
        return True

    # -- general ------------------------------------------------------------------------------------

    def _general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.mode = QComboBox()
        self.mode.addItem(self.tr("Human review"), "human")
        self.mode.addItem(self.tr("Automatic"), "auto")
        self.device = QComboBox()
        for label, value in ((self.tr("Automatic (GPU when available)"), "auto"), (self.tr("GPU (CUDA)"), "cuda"),
                             (self.tr("CPU"), "cpu")):
            self.device.addItem(label, value)
        self.budget = QDoubleSpinBox()
        self.budget.setRange(0.0, 1000.0)
        self.budget.setDecimals(2)
        self.budget.setPrefix("$ ")
        self.sprite = QCheckBox(self.tr("Use on-screen character art to resolve uncertain speakers"))
        self.encoder = QComboBox()
        for label, value in ((self.tr("Automatic (NVENC when available)"), "auto"), ("NVENC (h264_nvenc)", "h264_nvenc"),
                             ("x264 (CPU)", "libx264")):
            self.encoder.addItem(label, value)
        self.quality = QSpinBox()
        self.quality.setRange(0, 51)
        self.pinyin_size = QDoubleSpinBox()
        self.vi_size = QDoubleSpinBox()
        for s in (self.pinyin_size, self.vi_size):
            s.setRange(8, 200)
            s.setSuffix(" px @1080p")
        form.addRow(self.tr("Default review mode"), self.mode)
        form.addRow(self.tr("Device"), self.device)
        form.addRow(self.tr("Budget per episode"), self.budget)
        form.addRow(self.tr("Sprite check"), self.sprite)
        form.addRow(self.tr("Video encoder"), self.encoder)
        form.addRow(self.tr("Quality (lower = better, 18–23 typical)"), self.quality)
        form.addRow(self.tr("Pinyin font size"), self.pinyin_size)
        form.addRow(self.tr("Vietnamese font size"), self.vi_size)
        save = QPushButton(self.tr("Save"))
        save.clicked.connect(lambda: self._save_values({
            "review.mode": self.mode.currentData(), "device": self.device.currentData(),
            "budget.max_cost_per_episode": round(self.budget.value(), 2), "sprite.enabled": self.sprite.isChecked(),
            "render.encoder": self.encoder.currentData(), "render.quality": self.quality.value(),
            "render.pinyin_font_size": self.pinyin_size.value(), "render.vi_font_size": self.vi_size.value()}))
        form.addRow("", save)
        return w

    # -- files --------------------------------------------------------------------------------------

    def _files_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        out_row = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setPlaceholderText(self.tr("Required before the first render"))
        browse = QPushButton(self.tr("Choose…"))
        browse.clicked.connect(lambda: self._pick_folder(self.output))
        out_row.addWidget(self.output, 1)
        out_row.addWidget(browse)
        self.suffix = QLineEdit()
        work_row = QHBoxLayout()
        self.work_dir = QLineEdit()
        wbrowse = QPushButton(self.tr("Choose…"))
        wbrowse.clicked.connect(lambda: self._pick_folder(self.work_dir))
        work_row.addWidget(self.work_dir, 1)
        work_row.addWidget(wbrowse)
        self.cleanup = QCheckBox(self.tr("Delete temporary files when an episode is done"))
        self.extensions = QLineEdit()
        self.patterns = QPlainTextEdit()
        self.patterns.setFixedHeight(90)
        self.pattern_test = QLineEdit()
        self.pattern_test.setPlaceholderText(self.tr("Type a sample file name, e.g. 仙门第3集.mp4"))
        self.pattern_result = QLabel()
        self.pattern_test.textChanged.connect(self._test_pattern)
        self.patterns.textChanged.connect(self._test_pattern)
        form.addRow(self.tr("Output folder"), out_row)
        form.addRow(self.tr("Output name suffix"), self.suffix)
        form.addRow(self.tr("Working folder"), work_row)
        form.addRow(self.tr("Cleanup"), self.cleanup)
        form.addRow(self.tr("Video extensions"), self.extensions)
        form.addRow(self.tr("Episode number patterns (one per line, tried in order)"), self.patterns)
        form.addRow(self.tr("Test"), self.pattern_test)
        form.addRow("", self.pattern_result)
        save = QPushButton(self.tr("Save"))
        save.clicked.connect(self._save_files)
        form.addRow("", save)
        return w

    def _pick_folder(self, target: QLineEdit) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder"), target.text())
        if folder:
            target.setText(folder)

    def _patterns(self) -> list[str]:
        return [p for p in self.patterns.toPlainText().splitlines() if p.strip()]

    def _test_pattern(self) -> None:
        name = self.pattern_test.text().strip()
        if not name:
            self.pattern_result.clear()
            return
        n = detect_number(name, self._patterns())
        self.pattern_result.setText(self.tr("Detected episode: {n}").format(n=n) if n is not None
                                    else self.tr("No number detected"))

    def _save_files(self) -> None:
        folder = self.output.text().strip() or None
        if folder and not Path(folder).is_dir():
            show_error(self, self.tr("Settings"), self.tr("The output folder does not exist: {path}").format(path=folder))
            return
        exts = [e.strip() if e.strip().startswith(".") else "." + e.strip()
                for e in self.extensions.text().replace(";", ",").split(",") if e.strip()]
        self._save_values({"output.folder": folder, "output.name_suffix": self.suffix.text(),
                           "paths.work_dir": self.work_dir.text().strip() or "work",
                           "cleanup.auto": self.cleanup.isChecked(), "episodes.video_extensions": exts,
                           "episodes.number_patterns": self._patterns()})

    # -- advanced -----------------------------------------------------------------------------------

    def _advanced_tab(self) -> QWidget:
        from app.views.settings_form import SettingsForm

        self.form = SettingsForm(self.services)
        return self.form

    # -- API keys -----------------------------------------------------------------------------------

    def _keys_tab(self) -> QWidget:
        w = QWidget()
        self.keys_form = QFormLayout(w)
        self.key_fields: dict[str, QLineEdit] = {}
        self.keys_status = QLabel()
        self.keys_status.setWordWrap(True)
        return w

    def _build_keys(self) -> None:
        form = self.keys_form
        while form.rowCount():
            form.removeRow(0)
        self.key_fields = {}
        providers = self.services.config.llm.providers
        envs = sorted({p.api_key_env for p in providers.values()})
        for env in envs:
            field = QLineEdit(self.services.env_value(env))
            field.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_fields[env] = field
            roles = ", ".join(r for r, p in providers.items() if p.api_key_env == env)
            form.addRow(f"{env} ({roles})", field)
        save = QPushButton(self.tr("Save keys"))
        save.clicked.connect(self._save_keys)
        form.addRow("", save)
        for role in providers:
            btn = QPushButton(self.tr("Test {role}").format(role=role))
            btn.clicked.connect(lambda _=False, r=role: self._test(r))
            form.addRow("", btn)
        self.keys_status = QLabel()
        self.keys_status.setWordWrap(True)
        form.addRow("", self.keys_status)

    def _save_keys(self) -> None:
        try:
            self.services.save_env({k: f.text().strip() for k, f in self.key_fields.items()})
        except Exception as exc:  # noqa: BLE001
            show_error(self, self.tr("API keys"), exc)
            return
        self.keys_status.setText(self.tr("Keys saved to .env."))

    def _test(self, role: str) -> None:
        from subagent.llm import LLMClient

        self._save_keys()
        client = LLMClient(self.services.config, self.services.paths, use_cache=False)
        self.keys_status.setText(self.tr("Testing {role}…").format(role=role))
        run_async(lambda: client.test_connection(role),
                  lambda reply: self.keys_status.setText(self.tr("{role}: connected (reply: {reply})").format(
                      role=role, reply=reply)),
                  lambda exc: self.keys_status.setText(self.tr("{role}: failed — {error}").format(role=role, error=exc)))

    # -- language -----------------------------------------------------------------------------------

    def _language_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("Tiếng Việt", "vi")
        apply = QPushButton(self.tr("Apply (restarts the app)"))
        apply.clicked.connect(self._apply_language)
        form.addRow(self.tr("Interface language"), self.language)
        form.addRow("", apply)
        form.addRow(self.tr("Theme"), QLabel(self.tr("Follows the Windows light / dark setting.")))
        return w

    def _apply_language(self) -> None:
        lang = self.language.currentData()
        if lang == QSettings().value("ui/language"):
            return
        QSettings().setValue("ui/language", lang)
        answer = QMessageBox.question(self, self.tr("Language"),
                                      self.tr("The language changes after a restart. Restart now?"))
        if answer == QMessageBox.StandardButton.Yes and self.main.close():
            QProcess.startDetached(sys.executable, ["-m", "app"], str(self.services.root))
            QCoreApplication.quit()

    # -- shortcuts ----------------------------------------------------------------------------------

    def _shortcuts_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.shortcut_table = QTableWidget(len(shortcuts.DEFAULTS), 2)
        self.shortcut_table.setHorizontalHeaderLabels([self.tr("Action"), self.tr("Shortcut")])
        self.shortcut_table.horizontalHeader().setStretchLastSection(True)
        self.shortcut_edits: dict[str, QKeySequenceEdit] = {}
        for i, action in enumerate(shortcuts.DEFAULTS):
            self.shortcut_table.setCellWidget(i, 0, QLabel(shortcuts.label(action)))
            edit = QKeySequenceEdit(shortcuts.sequence(action))
            self.shortcut_table.setCellWidget(i, 1, edit)
            self.shortcut_edits[action] = edit
        layout.addWidget(self.shortcut_table)
        row = QHBoxLayout()
        reset = QPushButton(self.tr("Reset to defaults"))
        save = QPushButton(self.tr("Save shortcuts"))
        reset.clicked.connect(self._reset_shortcuts)
        save.clicked.connect(self._save_shortcuts)
        row.addStretch(1)
        row.addWidget(reset)
        row.addWidget(save)
        layout.addLayout(row)
        return w

    def _reset_shortcuts(self) -> None:
        shortcuts.reset_all()
        for action, edit in self.shortcut_edits.items():
            edit.setKeySequence(shortcuts.sequence(action))

    def _save_shortcuts(self) -> None:
        for action, edit in self.shortcut_edits.items():
            shortcuts.save(action, edit.keySequence())
        QMessageBox.information(self, self.tr("Shortcuts"), self.tr("Saved. They apply when you open Review."))

    # -- load ---------------------------------------------------------------------------------------

    def _load(self) -> None:
        c = self.services.config
        self.mode.setCurrentIndex(self.mode.findData(c.review.mode))
        self.device.setCurrentIndex(self.device.findData(c.device))
        self.budget.setValue(c.budget.max_cost_per_episode)
        self.sprite.setChecked(c.sprite.enabled)
        self.encoder.setCurrentIndex(self.encoder.findData(c.render.encoder))
        self.quality.setValue(c.render.quality)
        self.pinyin_size.setValue(c.render.pinyin_font_size)
        self.vi_size.setValue(c.render.vi_font_size)
        self.output.setText(c.output.folder or "")
        self.suffix.setText(c.output.name_suffix)
        self.work_dir.setText(c.paths.work_dir)
        self.cleanup.setChecked(c.cleanup.auto)
        self.extensions.setText(", ".join(c.episodes.video_extensions))
        self.patterns.setPlainText("\n".join(c.episodes.number_patterns))
        self.form.load()
        self.language.setCurrentIndex(max(0, self.language.findData(QSettings().value("ui/language", "en"))))
        self._build_keys()
