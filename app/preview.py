"""Live preview with libmpv (6.5): the masked source video with the draft ASS rendered by libass.

If libmpv cannot load, the widget shows how to fix it and every other feature keeps working.
"""

from __future__ import annotations

import contextlib
import locale
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

_MPV = None
_MPV_ERROR = ""


def load_mpv():
    """Import python-mpv, looking for libmpv-2.dll beside the app first (Windows)."""
    global _MPV, _MPV_ERROR
    if _MPV is not None or _MPV_ERROR:
        return _MPV
    root = Path(__file__).resolve().parent.parent
    names = ("libmpv-2.dll", "mpv-2.dll", "mpv-1.dll")   # builds use different names; python-mpv accepts all
    for folder in (root, root / "app", Path(sys.executable).parent):
        if any((folder / name).is_file() for name in names):
            os.environ["PATH"] = f"{folder}{os.pathsep}{os.environ.get('PATH', '')}"
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(folder))
    try:
        import mpv  # type: ignore[import-not-found]

        _MPV = mpv
    except (ImportError, OSError) as exc:
        _MPV_ERROR = str(exc)
        log.warning("libmpv not available: %s", exc)
    return _MPV


def fmt_time(ms: int) -> str:
    s, ms = divmod(max(0, int(ms)), 1000)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}.{ms // 100}"


class TimelineSlider(QSlider):
    """A slider that jumps to where you click (a plain QSlider only moves one page per click)."""

    jumped = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            style = self.style()
            handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)
            if not handle.contains(event.position().toPoint()):
                groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                              QStyle.SubControl.SC_SliderGroove, self)
                span = max(1, groove.width() - handle.width())
                x = int(event.position().x() - groove.x() - handle.width() / 2)
                value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), x, span)
                self.setValue(value)
                self.jumped.emit(value)
        super().mousePressEvent(event)


class PreviewWidget(QWidget):
    position_changed = Signal(int)          # ms, emitted on the UI thread
    _pos_from_mpv = Signal(float)
    _duration_from_mpv = Signal(float)

    def __init__(self, parent: QWidget | None = None, *, controls: bool = True, line_controls: bool = True):
        super().__init__(parent)
        self.player = None
        self._end_ms: int | None = None
        self._loop = False
        self._range: tuple[int, int] | None = None
        self._pos_ms = 0
        self._duration_ms = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video = QWidget(self)
        # Only this widget may be a native window (mpv draws into its HWND). Without both flags Qt also turns
        # its ancestors and siblings (player buttons, the review table) into native windows, which stay painted
        # over other screens after the page is switched.
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
        self.video.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video.setMinimumHeight(180)
        self.video.setStyleSheet("background: black;")
        self.message = QLabel(self)
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.hide()
        layout.addWidget(self.video, 1)
        layout.addWidget(self.message, 1)

        self.controls = QWidget(self)
        rows = QVBoxLayout(self.controls)
        rows.setContentsMargins(0, 0, 0, 0)
        timeline = QHBoxLayout()
        self.slider = TimelineSlider()
        self.slider.setRange(0, 0)
        self.slider.setToolTip(self.tr("Click or drag to move through the video"))
        self.time_label = QLabel("0:00.0 / 0:00.0")
        timeline.addWidget(self.slider, 1)
        timeline.addWidget(self.time_label)
        rows.addLayout(timeline)
        row = QHBoxLayout()
        self.frame_back_btn = QPushButton("◀|")
        self.frame_back_btn.setToolTip(self.tr("Previous frame"))
        self.back_btn = QPushButton("−5 s")
        self.back_btn.setToolTip(self.tr("Back 5 seconds"))
        self.play_btn = QPushButton(self.tr("Play / pause"))
        self.fwd_btn = QPushButton("+5 s")
        self.fwd_btn.setToolTip(self.tr("Forward 5 seconds"))
        self.frame_fwd_btn = QPushButton("|▶")
        self.frame_fwd_btn.setToolTip(self.tr("Next frame"))
        self.replay_btn = QPushButton(self.tr("Replay line"))
        self.loop_btn = QPushButton(self.tr("Loop line"))
        self.loop_btn.setCheckable(True)
        self.speed_btn = QPushButton("1×")
        self.speed_btn.setCheckable(True)
        for w in (self.frame_back_btn, self.back_btn, self.play_btn, self.fwd_btn, self.frame_fwd_btn,
                  self.replay_btn, self.loop_btn, self.speed_btn):
            row.addWidget(w)
        row.addStretch(1)
        rows.addLayout(row)
        layout.addWidget(self.controls)
        self.controls.setVisible(controls)
        self.replay_btn.setVisible(line_controls)
        self.loop_btn.setVisible(line_controls)
        self.play_btn.clicked.connect(self.toggle_pause)
        self.back_btn.clicked.connect(lambda: self.seek_relative(-5000))
        self.fwd_btn.clicked.connect(lambda: self.seek_relative(5000))
        self.frame_back_btn.clicked.connect(lambda: self.frame_step(-1))
        self.frame_fwd_btn.clicked.connect(lambda: self.frame_step(1))
        self.replay_btn.clicked.connect(self.replay)
        self.loop_btn.toggled.connect(self.set_loop)
        self.speed_btn.toggled.connect(lambda slow: self.set_speed(0.5 if slow else 1.0))
        self.slider.sliderMoved.connect(lambda ms: self.seek(ms, exact=False))   # dragging: fast keyframe seeks
        self.slider.sliderReleased.connect(lambda: self.seek(self.slider.value()))
        self.slider.sliderPressed.connect(self._manual)
        self.slider.jumped.connect(lambda ms: (self._manual(), self.seek(ms)))
        self._pos_from_mpv.connect(self._on_pos)
        self._duration_from_mpv.connect(self._on_duration)

        self._watch = QTimer(self)
        self._watch.setInterval(50)
        self._watch.timeout.connect(self._check_end)
        self._init_player()

    @property
    def available(self) -> bool:
        return self.player is not None

    def _init_player(self) -> None:
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.platformName() in ("offscreen", "minimal"):
            # no real windows to draw into (tests, headless runs): mpv would crash embedding into a fake one
            self._unavailable(self.tr("Preview unavailable on this display platform."))
            return
        mpv = load_mpv()
        if mpv is None:
            if sys.platform == "win32":
                hint = self.tr(
                    "Preview unavailable: libmpv could not be loaded ({error}).\n"
                    "Download libmpv for Windows (mpv-dev-x86_64 from the mpv website), put libmpv-2.dll next to "
                    "the app (project folder), and restart. Review works without the preview.")
            else:
                hint = self.tr(
                    "Preview unavailable: libmpv could not be loaded ({error}).\n"
                    "Install libmpv (Ubuntu / Debian: sudo apt install libmpv2) and restart. "
                    "Review works without the preview.")
            self._unavailable(hint.format(error=_MPV_ERROR))
            return
        # Qt applies the system locale on Linux; libmpv refuses to start unless numbers use the C locale
        locale.setlocale(locale.LC_NUMERIC, "C")
        extra: dict[str, str] = {}
        if sys.platform.startswith("linux") and QGuiApplication.platformName() == "xcb":
            # with WAYLAND_DISPLAY set mpv picks its Wayland backend, which ignores wid and draws in its own surface
            extra["gpu_context"] = "x11egl"
        try:
            self.player = mpv.MPV(wid=str(int(self.video.winId())), keep_open="yes", idle="yes", osc="no",
                                  input_default_bindings=False, input_vo_keyboard=False, sub_auto="no",
                                  hr_seek="yes", log_handler=lambda level, prefix, text: log.debug("mpv %s: %s", prefix, text),
                                  **extra)
            self.player.observe_property("time-pos", lambda _name, value: self._pos_from_mpv.emit(value or 0.0))
            self.player.observe_property("duration", lambda _name, value: self._duration_from_mpv.emit(value or 0.0))
        except Exception as exc:  # noqa: BLE001 - any libmpv failure disables the preview only
            self.player = None
            self._unavailable(self.tr("Preview unavailable: {error}").format(error=exc))

    def _unavailable(self, text: str) -> None:
        self.video.hide()
        self.controls.setEnabled(False)
        self.message.setText(text)
        self.message.show()

    # -- media --------------------------------------------------------------------------------------

    def open(self, video: Path, *, vf: str | None = None, subtitles: Path | None = None,
             fonts_dir: Path | None = None) -> None:
        if not self.player:
            return
        p = self.player
        try:
            p["sub-files"] = [str(subtitles)] if subtitles else []
            if fonts_dir:
                p["sub-fonts-dir"] = str(fonts_dir)
            p["vf"] = f'lavfi=graph="{vf}"' if vf else ""
        except Exception as exc:  # noqa: BLE001
            log.warning("mpv option failed: %s", exc)
        p.loadfile(str(video))
        p.pause = True

    def close_media(self) -> None:
        if self.player:
            self.player.command("stop")

    def reload_subtitles(self) -> None:
        if self.player:
            try:
                self.player.command("sub-reload")
            except Exception as exc:  # noqa: BLE001 - nothing loaded yet
                log.debug("sub-reload: %s", exc)

    def seek(self, ms: int, *, exact: bool = True) -> None:
        if self.player:
            try:
                self.player.seek(max(0, ms) / 1000, reference="absolute", precision="exact" if exact else "keyframes")
            except Exception as exc:  # noqa: BLE001
                log.debug("seek: %s", exc)

    def _manual(self) -> None:
        """The user took control: stop the automatic "pause at the end of the line"."""
        self._end_ms = None
        self._watch.stop()

    def seek_relative(self, delta_ms: int) -> None:
        self._manual()
        target = self._pos_ms + delta_ms
        if self._duration_ms:
            target = min(target, self._duration_ms)
        self.seek(max(0, target))

    def frame_step(self, direction: int) -> None:
        """One frame forward or back (pauses), for exact in/out marks."""
        if not self.player:
            return
        self._manual()
        try:
            self.player.command("frame-step" if direction > 0 else "frame-back-step")
        except Exception as exc:  # noqa: BLE001
            log.debug("frame step: %s", exc)

    def play(self) -> None:
        if self.player:
            self.player.pause = False

    def pause(self) -> None:
        if self.player:
            self.player.pause = True

    def toggle_pause(self) -> None:
        if self.player:
            self.player.pause = not self.player.pause

    def set_speed(self, speed: float) -> None:
        self.speed_btn.setText("0.5×" if speed < 1 else "1×")
        if self.player:
            self.player.speed = speed

    def set_loop(self, on: bool) -> None:
        self._loop = on
        if self.loop_btn.isChecked() != on:
            self.loop_btn.setChecked(on)
        if self._range:
            self.play_line(*self._range)

    def play_line(self, start_ms: int, end_ms: int) -> None:
        """Seek to 0.5 s before the line, play it once (or loop it)."""
        self._range = (start_ms, end_ms)
        if not self.player:
            return
        lead = int(QSettings().value("review/lead_ms", 500))
        a, b = max(0, start_ms - lead), end_ms
        try:
            if self._loop:
                self.player["ab-loop-a"] = a / 1000
                self.player["ab-loop-b"] = b / 1000
                self._end_ms = None
            else:
                self.player["ab-loop-a"] = "no"
                self.player["ab-loop-b"] = "no"
                self._end_ms = b
        except Exception as exc:  # noqa: BLE001
            log.debug("ab-loop: %s", exc)
        self.seek(a)
        self.play()
        self._watch.start()

    def replay(self) -> None:
        if self._range:
            self.play_line(*self._range)

    def current_ms(self) -> int:
        return self._pos_ms

    def _on_pos(self, seconds: float) -> None:
        self._pos_ms = int(seconds * 1000)
        if not self.slider.isSliderDown():
            self.slider.setValue(self._pos_ms)
        self.time_label.setText(f"{fmt_time(self._pos_ms)} / {fmt_time(self._duration_ms)}")
        self.position_changed.emit(self._pos_ms)

    def _on_duration(self, seconds: float) -> None:
        self._duration_ms = int(seconds * 1000)
        self.slider.setRange(0, self._duration_ms)
        self.slider.setPageStep(5000)
        self.time_label.setText(f"{fmt_time(self._pos_ms)} / {fmt_time(self._duration_ms)}")

    def _check_end(self) -> None:
        if self._end_ms is not None and self._pos_ms >= self._end_ms:
            self.pause()
            self._end_ms = None
            self._watch.stop()

    def hideEvent(self, event) -> None:  # noqa: N802
        """Stop playback and hide the native video window when the page is hidden.

        Qt does not reliably hide a native child window when a non-native ancestor (the stacked page) is
        hidden, so mpv's picture would stay on top of other screens.
        """
        self.pause()
        self._end_ms = None
        self._watch.stop()
        if self.player:
            self.video.hide()
        super().hideEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        if self.player:
            self.video.show()
        super().showEvent(event)

    def shutdown(self) -> None:
        if self.player:
            with contextlib.suppress(Exception):
                self.player.terminate()
            self.player = None
