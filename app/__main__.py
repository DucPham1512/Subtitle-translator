"""python -m app: the desktop app."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

APP_DIR = Path(__file__).resolve().parent


def install_fonts(root: Path) -> None:
    """Bundle Noto Sans + Noto Sans SC as the app font with fallback (NFR-UX6)."""
    families: list[str] = []
    for folder in (root / "fonts", APP_DIR / "fonts"):
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                fid = QFontDatabase.addApplicationFont(str(f))
                families += QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
    preferred = [f for f in ("Noto Sans", "Noto Sans SC") if f in families or f in QFontDatabase.families()]
    fallback = ["Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei"]
    font = QApplication.font()
    font.setFamilies(preferred + fallback)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    QApplication.setFont(font)


def install_translator(app: QApplication) -> None:
    lang = str(QSettings().value("ui/language", "vi" if QLocale.system().name().startswith("vi") else "en"))
    translator = QTranslator(app)
    if translator.load(str(APP_DIR / "i18n" / f"app_{lang}.qm")):
        app.installTranslator(translator)
    qt_translator = QTranslator(app)
    if qt_translator.load(f"qtbase_{lang}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_translator)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setOrganizationName("SubtitleAgent")
    app.setApplicationName("Subtitle Agent")
    app.setStyle("Fusion")   # Fusion follows the Windows light / dark setting in Qt 6
    install_translator(app)

    from subagent.config import find_root
    from subagent.errors import SubagentError

    root = find_root(APP_DIR.parent)
    install_fonts(root)
    try:
        from app.services import Services

        services = Services(root)
    except SubagentError as exc:
        QMessageBox.critical(None, app.translate("App", "Subtitle Agent"),
                             app.translate("App", "The settings could not be loaded:\n{error}").format(error=exc))
        return 1

    from app.main_window import MainWindow

    window = MainWindow(services)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
