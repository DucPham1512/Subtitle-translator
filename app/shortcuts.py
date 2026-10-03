"""Review shortcuts: defaults from 6.4, remappable in Settings (stored in QSettings)."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtGui import QKeySequence

DEFAULTS = {
    "approve_next": "Ctrl+Return",
    "next_line": "Ctrl+Down",
    "prev_line": "Ctrl+Up",
    "replay": "Ctrl+R",
    "play_pause": "Ctrl+Space",
    "toggle_loop": "Ctrl+L",
    "focus_vi": "Ctrl+E",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "search": "Ctrl+F",
    "delete_line": "Ctrl+Delete",
}


def label(action: str) -> str:
    return {
        "approve_next": QCoreApplication.translate("Shortcuts", "Approve and next"),
        "next_line": QCoreApplication.translate("Shortcuts", "Next line"),
        "prev_line": QCoreApplication.translate("Shortcuts", "Previous line"),
        "replay": QCoreApplication.translate("Shortcuts", "Replay line"),
        "play_pause": QCoreApplication.translate("Shortcuts", "Play / pause"),
        "toggle_loop": QCoreApplication.translate("Shortcuts", "Toggle loop"),
        "focus_vi": QCoreApplication.translate("Shortcuts", "Focus Vietnamese field"),
        "undo": QCoreApplication.translate("Shortcuts", "Undo (line)"),
        "redo": QCoreApplication.translate("Shortcuts", "Redo (line)"),
        "search": QCoreApplication.translate("Shortcuts", "Search"),
        "delete_line": QCoreApplication.translate("Shortcuts", "Delete / restore line"),
    }.get(action, action)


def sequence(action: str) -> QKeySequence:
    value = QSettings().value(f"shortcuts/{action}", DEFAULTS[action])
    return QKeySequence(str(value))


def save(action: str, seq: QKeySequence) -> None:
    QSettings().setValue(f"shortcuts/{action}", seq.toString())


def reset_all() -> None:
    s = QSettings()
    for action in DEFAULTS:
        s.remove(f"shortcuts/{action}")
