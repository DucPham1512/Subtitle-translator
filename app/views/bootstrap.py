"""Bootstrap wizard (6.6): calibrate, cast, voice clips, sprites, generate seed, review seed.

The app writes only bootstrap inputs here (cast.md, clips, sprites, seed_draft.json) and config; memory is
written by the `bootstrap --approve` job through the Memory Manager.
"""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.preview import PreviewWidget
from app.services.bootstrap import seed as bs
from app.services.bootstrap import voice_clips
from app.widgets import ClipPlayer, FrameSelector, confirm, fmt_ms, show_error, to_qimage
from app.workers import run_async
from subagent.kernel import atomic_write_text

SEED_TABLES = {
    "characters": ["id", "name_zh", "name_vi", "description"],
    "pronoun_pairs": ["speaker_id", "listener_id", "self_term", "address_term", "context"],
    "glossary": ["zh", "vi", "pinyin", "type", "notes"],
}


class BootstrapView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        self.player = ClipPlayer()
        self._mark_in: int | None = None
        self._mark_out: int | None = None
        self._job = ""
        layout = QHBoxLayout(self)
        self.steps = QListWidget()
        self.steps.setMaximumWidth(220)
        for label in (self.tr("1. Calibrate"), self.tr("2. Cast and synopsis"), self.tr("3. Voice clips"),
                      self.tr("4. Sprites"), self.tr("5. Generate seed"), self.tr("6. Review seed")):
            self.steps.addItem(label)
        layout.addWidget(self.steps)
        right = QVBoxLayout()
        # shared episode picker + preview for steps 1, 3 and 4
        pick = QHBoxLayout()
        pick.addWidget(QLabel(self.tr("Episode:")))
        self.episode_box = QComboBox()
        self.episode_box.currentIndexChanged.connect(self._episode_changed)
        pick.addWidget(self.episode_box, 1)
        self.picker = QWidget()
        self.picker.setLayout(pick)
        right.addWidget(self.picker)
        self.preview = PreviewWidget(line_controls=False)   # no subtitle line to replay here
        self.preview.setMinimumHeight(260)
        right.addWidget(self.preview, 2)
        self.pages = QStackedWidget()
        for page in (self._calibrate_page(), self._cast_page(), self._voice_page(), self._sprite_page(),
                     self._generate_page(), self._seed_page()):
            self.pages.addWidget(page)
        right.addWidget(self.pages, 3)
        layout.addLayout(right, 1)
        self.steps.currentRowChanged.connect(self._step)
        main.jobs.log_line.connect(self._job_log)
        main.jobs.finished.connect(self._job_finished)

    def activate(self) -> None:
        self._fill_episodes()
        if self.steps.currentRow() < 0:
            self.steps.setCurrentRow(0)
        else:
            self._step(self.steps.currentRow())

    def shutdown(self) -> None:
        self.preview.shutdown()

    def _step(self, row: int) -> None:
        self.pages.setCurrentIndex(row)
        self.picker.setVisible(row in (0, 2, 3))
        self.preview.setVisible(row in (2, 3))
        if row == 0:
            self._show_style()
        elif row == 1:
            self._load_cast()
        elif row == 2:
            self._fill_characters(self.voice_char)
            self._load_clips()
        elif row == 3:
            self.sprite_note.setVisible(not self.services.config.sprite.enabled)
            self._fill_characters(self.sprite_char)
            self._load_sprites()
        elif row == 5:
            self._load_seed()

    # -- shared -------------------------------------------------------------------------------------

    def _fill_episodes(self) -> None:
        current = self.episode_box.currentData()
        self.episode_box.blockSignals(True)
        self.episode_box.clear()
        for ep in self.services.registry.load():
            self.episode_box.addItem(f"{ep.id} — {Path(ep.source_path).name}", ep.id)
        if current:
            self.episode_box.setCurrentIndex(max(0, self.episode_box.findData(current)))
        self.episode_box.blockSignals(False)
        self._episode_changed()

    def _source(self) -> Path | None:
        ep_id = self.episode_box.currentData()
        if not ep_id:
            return None
        path = Path(self.services.registry.get(ep_id).source_path)
        return path if path.is_file() else None

    def _episode_changed(self, *_: object) -> None:
        self._show_style()
        source = self._source()
        if source is None:
            return
        if self.preview.available:
            self.preview.open(source)
        ep_id = self.episode_box.currentData()
        run_async(lambda: self.services.video_info(ep_id), self._video_loaded)

    def _video_loaded(self, info) -> None:
        self._video = info
        self.cal_slider.setRange(0, max(0, info.duration_ms))
        self.cal_slider.setValue(info.duration_ms // 3)
        self._load_frame()

    def _characters(self) -> list[str]:
        ids = {c.id for c in self.services.store.characters()}
        with contextlib.suppress(Exception):   # no seed yet
            ids |= {c.id for c in bs.load_seed(self.services.paths).characters}
        ids |= set(voice_clips(self.services.paths))
        return sorted(ids)

    def _fill_characters(self, box: QComboBox) -> None:
        current = box.currentText()
        box.clear()
        box.addItems(self._characters())
        if current:
            box.setCurrentText(current)

    # -- 1. calibrate -------------------------------------------------------------------------------

    def _calibrate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(self.tr("Drag a rectangle over the subtitle line, then save. Subtitles are centred, "
                                        "so the band widens to be symmetric around the middle of the frame. The "
                                        "position is the same in every episode, so this is done once.")))
        self.selector = FrameSelector()
        self.selector.selection_changed.connect(self._center_band)
        layout.addWidget(self.selector, 1)
        row = QHBoxLayout()
        self.cal_slider = QSlider(Qt.Orientation.Horizontal)
        self.cal_slider.sliderReleased.connect(self._load_frame)
        self.cal_time = QLabel()
        save = QPushButton(self.tr("Save subtitle band"))
        save.clicked.connect(self._save_band)
        row.addWidget(self.cal_slider, 1)
        row.addWidget(self.cal_time)
        row.addWidget(save)
        layout.addLayout(row)
        # the series' subtitle style, learned once for OCR segmentation (5.4a)
        style_box = QGroupBox(self.tr("Subtitle style (OCR segmentation)"))
        style_layout = QVBoxLayout(style_box)
        style_layout.addWidget(QLabel(self.tr(
            "Learns the subtitle's colours, outline and letter size from the episode above, inside the saved band. "
            "Done once per series; learning it again re-reads the subtitles of every episode run afterwards.")))
        self.style_info = QLabel()
        self.style_info.setWordWrap(True)
        self.style_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        style_layout.addWidget(self.style_info)
        style_row = QHBoxLayout()
        self.style_btn = QPushButton(self.tr("Learn subtitle style from this episode"))
        self.style_btn.clicked.connect(self._learn_style)
        self.style_preview_btn = QPushButton(self.tr("Show style preview"))
        self.style_preview_btn.clicked.connect(self._show_style_preview)
        style_row.addWidget(self.style_btn)
        style_row.addWidget(self.style_preview_btn)
        style_row.addStretch(1)
        style_layout.addLayout(style_row)
        layout.addWidget(style_box)
        self._show_style()
        return page

    def _show_style(self) -> None:
        from app.services.bootstrap import load_style

        try:
            style = load_style(self.services.paths.bootstrap)
        except Exception as exc:  # noqa: BLE001 - a damaged file is shown, not raised
            self.style_info.setText(self.tr("The saved subtitle style cannot be read: {error}").format(error=exc))
            style = None
        else:
            if style is None:
                note = (self.tr("OCR segmentation is on, so learn the style before running episodes.")
                        if self.services.config.ocr.preprocess == "segment" else
                        self.tr("Only needed when OCR pre-processing is set to segmentation."))
                self.style_info.setText(self.tr("No subtitle style learned yet.") + " " + note)
            else:
                outline = (str(style.outline_level) if style.outline_level is not None else self.tr("none"))
                self.style_info.setText(self.tr(
                    "Learned from {episode} on {date}: {polarity} text, fill grey {fill_min}–{fill_max}, outline "
                    "{outline}, stroke {stroke:.3f} and letter height {height:.2f} of the band.").format(
                    episode=style.calibrated_from or "?", date=style.calibrated_at[:10] or "?",
                    polarity=self.tr("light") if style.polarity == "light" else self.tr("dark"),
                    fill_min=style.fill_min, fill_max=style.fill_max, outline=outline, stroke=style.stroke,
                    height=style.letter_height))
        self.style_preview_btn.setEnabled(self._style_preview_path() is not None)

    def _style_preview_path(self) -> Path | None:
        """The preview made by the last calibration on the selected episode, else on the episode the style
        was learned from (deleted by that episode's cleanup)."""
        from app.services.bootstrap import load_style

        ids = [self.episode_box.currentData()]
        with contextlib.suppress(Exception):
            style = load_style(self.services.paths.bootstrap)
            ids.append(style.calibrated_from if style else None)
        for ep_id in ids:
            if ep_id:
                path = self.services.paths.episode_dir(ep_id) / "calibration" / "style.png"
                if path.is_file():
                    return path
        return None

    def _learn_style(self) -> None:
        ep_id = self.episode_box.currentData()
        if not ep_id:
            return
        from app.services.bootstrap import load_style

        with contextlib.suppress(Exception):
            if load_style(self.services.paths.bootstrap) is not None and not confirm(
                    self, self.tr("Subtitle style"),
                    self.tr("Replace the saved subtitle style with one learned from {episode}? Episodes run "
                            "afterwards read their subtitles again with the new style.").format(episode=ep_id)):
                return
        self._job = "calibrate --style"
        if not self.main.jobs.start("calibrate --style", ["calibrate", ep_id, "--style"]):
            show_error(self, self.tr("Subtitle style"), self.tr("Another job is running."))
            return
        self.style_btn.setEnabled(False)
        self.style_info.setText(self.tr("Learning the subtitle style from {episode}…").format(episode=ep_id))

    def _show_style_preview(self) -> None:
        path = self._style_preview_path()
        if path is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Subtitle style preview"))
        dialog.resize(900, 640)
        box = QVBoxLayout(dialog)
        box.addWidget(QLabel(self.tr("Each pair: the subtitle band, then what segmentation keeps for OCR.")))
        image = QLabel()
        image.setPixmap(QPixmap(str(path)))
        scroll = QScrollArea()
        scroll.setWidget(image)
        box.addWidget(scroll, 1)
        dialog.exec()

    def _center_band(self, sel: QRectF) -> None:
        """The drawn band snaps to be symmetric around the frame's centre line (the side closer to the centre
        grows); top and bottom stay as drawn."""
        from app.services.bootstrap import Band

        b = Band(top=sel.top(), bottom=sel.bottom(), left=sel.left(), right=sel.right()).centered()
        self.selector.set_selection(QRectF(b.left, b.top, b.right - b.left, b.bottom - b.top))

    def _band_rect(self) -> QRectF:
        b = self.services.config.video.subtitle_band
        return QRectF(b.left, b.top, b.right - b.left, b.bottom - b.top)

    def _load_frame(self) -> None:
        source = self._source()
        if source is None or not hasattr(self, "_video"):
            return
        from app.services.bootstrap import extract_frame

        t, info = self.cal_slider.value(), self._video
        self.cal_time.setText(fmt_ms(t))

        def done(frame) -> None:
            self.selector.set_frame(frame)
            self.selector.set_selection(self._band_rect())

        run_async(lambda: extract_frame(source, t, size=(info.width, info.height)), done,
                  lambda exc: show_error(self, self.tr("Calibrate"), exc))

    def _save_band(self) -> None:
        sel = self.selector.sel
        if sel is None:
            return
        from app.services.bootstrap import update_config_values

        band = {"top": round(sel.top(), 4), "bottom": round(sel.bottom(), 4), "left": round(sel.left(), 4),
                "right": round(sel.right(), 4)}
        try:
            update_config_values(self.services.root, {"video.subtitle_band": band})
            self.services.reload()
        except Exception as exc:  # noqa: BLE001
            show_error(self, self.tr("Calibrate"), exc)
            return
        QMessageBox.information(self, self.tr("Calibrate"), self.tr("Subtitle band saved."))

    # -- 2. cast ------------------------------------------------------------------------------------

    def _cast_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(self.tr("List the characters (Chinese name, who they are), their relationships and "
                                        "how they address each other, and a short synopsis.")))
        self.cast = QPlainTextEdit()
        layout.addWidget(self.cast, 1)
        row = QHBoxLayout()
        imp = QPushButton(self.tr("Import file…"))
        save = QPushButton(self.tr("Save"))
        imp.clicked.connect(self._import_cast)
        save.clicked.connect(self._save_cast)
        row.addStretch(1)
        row.addWidget(imp)
        row.addWidget(save)
        layout.addLayout(row)
        return page

    def _cast_path(self) -> Path:
        return self.services.paths.bootstrap / "cast.md"

    def _load_cast(self) -> None:
        p = self._cast_path()
        self.cast.setPlainText(p.read_text(encoding="utf-8") if p.is_file() else "")

    def _import_cast(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Import cast list"), "",
                                              self.tr("Text (*.md *.txt);;All files (*)"))
        if path:
            self.cast.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))

    def _save_cast(self) -> None:
        atomic_write_text(self._cast_path(), self.cast.toPlainText())
        QMessageBox.information(self, self.tr("Cast"), self.tr("Saved."))

    # -- 3. voices ----------------------------------------------------------------------------------

    def _voice_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Character id:")))
        self.voice_char = QComboBox()
        self.voice_char.setEditable(True)
        self.voice_char.currentTextChanged.connect(lambda _: self._load_clips())
        row.addWidget(self.voice_char, 1)
        self.clip_count = QLabel()
        row.addWidget(self.clip_count)
        layout.addLayout(row)
        marks = QHBoxLayout()
        mark_in = QPushButton(self.tr("Mark in"))
        mark_out = QPushButton(self.tr("Mark out"))
        self.marks = QLabel()
        save = QPushButton(self.tr("Save clip"))
        imp = QPushButton(self.tr("Import WAV files…"))
        mark_in.clicked.connect(lambda: self._mark("in"))
        mark_out.clicked.connect(lambda: self._mark("out"))
        save.clicked.connect(self._save_clip)
        imp.clicked.connect(self._import_clips)
        for w in (mark_in, mark_out, self.marks, save):
            marks.addWidget(w)
        marks.addStretch(1)
        marks.addWidget(imp)
        layout.addLayout(marks)
        self.clips = QListWidget()
        self.clips.itemDoubleClicked.connect(lambda item: self.player.play(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.clips, 1)
        row2 = QHBoxLayout()
        play = QPushButton(self.tr("Play"))
        delete = QPushButton(self.tr("Delete clip"))
        play.clicked.connect(lambda: self.clips.currentItem() and self.player.play(
            self.clips.currentItem().data(Qt.ItemDataRole.UserRole)))
        delete.clicked.connect(self._delete_clip)
        row2.addStretch(1)
        row2.addWidget(play)
        row2.addWidget(delete)
        layout.addLayout(row2)
        return page

    def _char_id(self, box: QComboBox) -> str | None:
        text = box.currentText().strip()
        return bs.slugify(text) if text else None

    def _mark(self, which: str) -> None:
        t = self.preview.current_ms()
        if which == "in":
            self._mark_in = t
        else:
            self._mark_out = t
        self.marks.setText(self.tr("in {a} · out {b}").format(
            a=fmt_ms(self._mark_in) if self._mark_in is not None else "—",
            b=fmt_ms(self._mark_out) if self._mark_out is not None else "—"))

    def _save_clip(self) -> None:
        char, source = self._char_id(self.voice_char), self._source()
        if not char or source is None or self._mark_in is None or self._mark_out is None:
            QMessageBox.information(self, self.tr("Voice clips"), self.tr(
                "Choose a character, then mark the start and end of a line spoken only by that character."))
            return
        a, b = self._mark_in, self._mark_out
        config, paths = self.services.config, self.services.paths
        run_async(lambda: bs.save_clip(config, paths, char, source, a, b), lambda _: self._load_clips(),
                  lambda exc: show_error(self, self.tr("Voice clips"), exc))

    def _import_clips(self) -> None:
        char = self._char_id(self.voice_char)
        if not char:
            return
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Import voice clips"), "",
                                                self.tr("Audio (*.wav *.mp3 *.flac *.m4a *.ogg)"))
        folder = self.services.paths.bootstrap / "voices" / char
        folder.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, folder / Path(f).name)
        self._load_clips()

    def _load_clips(self) -> None:
        char = self._char_id(self.voice_char)
        self.clips.clear()
        files = voice_clips(self.services.paths).get(char or "", [])
        for f in files:
            item = QListWidgetItem(f.name)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.clips.addItem(item)
        self.clip_count.setText(self.tr("{n} clips (3–5 recommended)").format(n=len(files)))

    def _delete_clip(self) -> None:
        item = self.clips.currentItem()
        if item and confirm(self, self.tr("Delete clip"), self.tr("Delete {name}?").format(name=item.text())):
            Path(item.data(Qt.ItemDataRole.UserRole)).unlink(missing_ok=True)
            self._load_clips()

    # -- 4. sprites ---------------------------------------------------------------------------------

    def _sprite_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.sprite_note = QLabel(self.tr("The sprite check is turned off in Settings; templates are not used."))
        layout.addWidget(self.sprite_note)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Character id:")))
        self.sprite_char = QComboBox()
        self.sprite_char.setEditable(True)
        self.sprite_char.currentTextChanged.connect(lambda _: self._load_sprites())
        row.addWidget(self.sprite_char, 1)
        grab = QPushButton(self.tr("Grab paused frame"))
        grab.clicked.connect(self._grab)
        save = QPushButton(self.tr("Save template"))
        save.clicked.connect(self._save_sprite)
        row.addWidget(grab)
        row.addWidget(save)
        layout.addLayout(row)
        body = QHBoxLayout()
        self.sprite_selector = FrameSelector()
        body.addWidget(self.sprite_selector, 2)
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListView.ViewMode.IconMode)
        self.thumbs.setIconSize(QSize(96, 96))
        body.addWidget(self.thumbs, 1)
        layout.addLayout(body, 1)
        return page

    def _grab(self) -> None:
        source = self._source()
        if source is None:
            return
        from app.services.bootstrap import extract_frame

        self.preview.pause()
        t = self.preview.current_ms()
        run_async(lambda: extract_frame(source, t), self.sprite_selector.set_frame,
                  lambda exc: show_error(self, self.tr("Sprites"), exc))

    def _save_sprite(self) -> None:
        from app.services.bootstrap import save_template

        char = self._char_id(self.sprite_char)
        crop = self.sprite_selector.crop()
        if not char or crop is None:
            QMessageBox.information(self, self.tr("Sprites"), self.tr(
                "Grab a frame, drag a rectangle around the character, and choose the character id."))
            return
        existing = len(list((self.services.paths.bootstrap / "sprites" / char).glob("*.png")))
        save_template(self.services.paths, char, crop, f"template_{existing + 1:02d}")
        self._load_sprites()

    def _load_sprites(self) -> None:
        char = self._char_id(self.sprite_char)
        self.thumbs.clear()
        folder = self.services.paths.bootstrap / "sprites" / (char or "")
        if not char or not folder.is_dir():
            return
        from app.services.bootstrap import imread

        for f in sorted(folder.glob("*.png")):
            item = QListWidgetItem(QIcon(QPixmap.fromImage(to_qimage(imread(f)))), f.stem)
            self.thumbs.addItem(item)

    # -- 5. generate --------------------------------------------------------------------------------

    def _generate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(self.tr("Drafts characters (Hán-Việt names), pronoun pairs and glossary terms from the "
                                        "cast list, and computes the voice bank from the clips. Nothing is written "
                                        "to memory until you approve the seed in step 6.")))
        run = QPushButton(self.tr("Generate seed"))
        run.clicked.connect(self._generate)
        layout.addWidget(run, 0, Qt.AlignmentFlag.AlignLeft)
        self.gen_log = QPlainTextEdit()
        self.gen_log.setReadOnly(True)
        layout.addWidget(self.gen_log, 1)
        return page

    def _generate(self) -> None:
        if not self._cast_path().is_file():
            QMessageBox.information(self, self.tr("Generate seed"), self.tr("Write the cast list first (step 2)."))
            return
        self.gen_log.clear()
        self._job = "bootstrap"
        if not self.main.jobs.start("bootstrap", ["bootstrap"]):
            show_error(self, self.tr("Generate seed"), self.tr("Another job is running."))

    def _job_log(self, line: str) -> None:
        if self.main.jobs.name in ("bootstrap", "bootstrap --approve"):
            self.gen_log.appendPlainText(line)

    def _job_finished(self, name: str, code: int, error: dict) -> None:
        from app.messages import error_message

        if name == "calibrate --style":
            self.style_btn.setEnabled(True)
            self._show_style()
            if code != 0:
                show_error(self, self.tr("Subtitle style"),
                           error_message(error.get("error_code"), error.get("message", "")))
            else:
                self._show_style_preview()
            return
        if name not in ("bootstrap", "bootstrap --approve"):
            return

        if code != 0:
            show_error(self, self.tr("Bootstrap"), error_message(error.get("error_code"), error.get("message", "")))
            return
        if name == "bootstrap":
            self.gen_log.appendPlainText(self.tr("Seed ready. Review it in step 6."))
            self.steps.setCurrentRow(5)
        else:
            QMessageBox.information(self, self.tr("Bootstrap"), self.tr("Memory seeded. You can run episode 1 now."))

    # -- 6. review seed -----------------------------------------------------------------------------

    def _seed_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.seed_tabs = QTabWidget()
        self.seed_grids: dict[str, QTableWidget] = {}
        titles = {"characters": self.tr("Characters"), "pronoun_pairs": self.tr("Pronoun pairs"),
                  "glossary": self.tr("Glossary")}
        for key, cols in SEED_TABLES.items():
            grid = QTableWidget(0, len(cols))
            grid.setHorizontalHeaderLabels(cols)
            grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.seed_grids[key] = grid
            w = QWidget()
            v = QVBoxLayout(w)
            v.addWidget(grid)
            row = QHBoxLayout()
            add = QPushButton(self.tr("Add row"))
            rem = QPushButton(self.tr("Remove row"))
            add.clicked.connect(lambda _=False, g=grid: g.insertRow(g.rowCount()))
            rem.clicked.connect(lambda _=False, g=grid: g.removeRow(g.currentRow()) if g.currentRow() >= 0 else None)
            row.addStretch(1)
            row.addWidget(add)
            row.addWidget(rem)
            v.addLayout(row)
            self.seed_tabs.addTab(w, titles[key])
        self.confusable = QTableWidget(0, 3)
        self.confusable.setHorizontalHeaderLabels([self.tr("Character A"), self.tr("Character B"),
                                                   self.tr("Similarity")])
        self.confusable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.confusable.cellDoubleClicked.connect(self._play_pair)
        cw = QWidget()
        cv = QVBoxLayout(cw)
        cv.addWidget(QLabel(self.tr("Voices that sound alike (read-only). Double-click a name to hear a clip.")))
        cv.addWidget(self.confusable)
        self.seed_tabs.addTab(cw, self.tr("Confusable voices"))
        layout.addWidget(self.seed_tabs, 1)
        self.seed_warnings = QLabel()
        self.seed_warnings.setWordWrap(True)
        self.seed_warnings.setStyleSheet("color: #b35c00;")
        layout.addWidget(self.seed_warnings)
        row = QHBoxLayout()
        save = QPushButton(self.tr("Save draft"))
        approve = QPushButton(self.tr("Approve and write to memory…"))
        approve.setStyleSheet("font-weight: bold;")
        save.clicked.connect(lambda: self._save_seed(quiet=False))
        approve.clicked.connect(self._approve)
        row.addStretch(1)
        row.addWidget(save)
        row.addWidget(approve)
        layout.addLayout(row)
        return page

    def _load_seed(self) -> None:
        try:
            draft = bs.load_seed(self.services.paths)
        except Exception:  # noqa: BLE001
            self.seed_warnings.setText(self.tr("No seed draft yet. Generate it in step 5."))
            return
        self._draft = draft
        for key, cols in SEED_TABLES.items():
            grid = self.seed_grids[key]
            rows = getattr(draft, key)
            grid.setRowCount(len(rows))
            for i, r in enumerate(rows):
                d = r.model_dump()
                for j, c in enumerate(cols):
                    grid.setItem(i, j, QTableWidgetItem("" if d.get(c) is None else str(d.get(c))))
        self.confusable.setRowCount(len(draft.confusable_pairs))
        for i, p in enumerate(draft.confusable_pairs):
            for j, v in enumerate((p.a, p.b, f"{p.similarity:.2f}")):
                self.confusable.setItem(i, j, QTableWidgetItem(v))
        self.seed_warnings.setText("\n".join(draft.warnings))

    def _play_pair(self, row: int, col: int) -> None:
        if col > 1:
            return
        char = self.confusable.item(row, col).text()
        clips = voice_clips(self.services.paths).get(char, [])
        if clips:
            self.player.play(clips[0])

    def _save_seed(self, quiet: bool = True) -> bool:
        if not hasattr(self, "_draft"):
            return False
        data = self._draft.model_dump()
        for key, cols in SEED_TABLES.items():
            grid = self.seed_grids[key]
            rows = []
            for i in range(grid.rowCount()):
                d = {c: (grid.item(i, j).text().strip() if grid.item(i, j) else "") for j, c in enumerate(cols)}
                if any(d.values()):
                    rows.append({k: (v or None) if k in ("pinyin", "type", "notes") else v for k, v in d.items()})
            data[key] = rows
        try:
            draft = bs.SeedDraft.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            show_error(self, self.tr("Seed"), exc)
            return False
        bs.save_seed(self.services.paths, draft)
        self._draft = draft
        if not quiet:
            QMessageBox.information(self, self.tr("Seed"), self.tr("Draft saved."))
        return True

    def _approve(self) -> None:
        if not self._save_seed() or not confirm(self, self.tr("Approve seed"), self.tr(
                "Write these characters, pronoun pairs, glossary terms and voices to memory? They are locked "
                "(only you can change them later).")):
            return
        if not self.main.jobs.start("bootstrap --approve", ["bootstrap", "--approve"]):
            show_error(self, self.tr("Approve seed"), self.tr("Another job is running."))
