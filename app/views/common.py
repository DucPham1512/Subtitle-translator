"""Helpers shared by screens: output-folder and output-conflict checks before a render (5.22)."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox, QWidget

from subagent.kernel.errors import SubagentError


def choose_batch_on_exists(parent: QWidget, existing: list[str]) -> str | None:
    """One choice for every episode of a batch whose output already exists; None cancels the batch."""
    box = QMessageBox(QMessageBox.Icon.Question, QCoreApplication.translate("Output", "Output files exist"),
                      QCoreApplication.translate("Output", "The output video already exists for: {ids}.").format(
                          ids=", ".join(existing)), parent=parent)
    overwrite = box.addButton(QCoreApplication.translate("Output", "Overwrite"), QMessageBox.ButtonRole.DestructiveRole)
    keep = box.addButton(QCoreApplication.translate("Output", "Keep both"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    if box.clickedButton() is overwrite:
        return "overwrite"
    if box.clickedButton() is keep:
        return "keep-both"
    return None


def choose_on_exists(parent: QWidget, window, episode_id: str) -> str | None:
    """Returns the CLI --on-exists value, or None when the user cancels or no output folder is set."""
    try:
        target = window.services.output_target(episode_id)
    except SubagentError as exc:
        box = QMessageBox(QMessageBox.Icon.Warning, QCoreApplication.translate("Output", "Output folder"),
                          QCoreApplication.translate("Output", "Rendering needs an output folder.\n\n{error}").format(error=exc), parent=parent)
        open_settings = box.addButton(QCoreApplication.translate("Output", "Open Settings"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is open_settings:
            window.go("settings").show_tab("files")
        return None
    if not target.exists():
        return "fail"
    box = QMessageBox(QMessageBox.Icon.Question, QCoreApplication.translate("Output", "Output file exists"),
                      QCoreApplication.translate("Output", "{name} already exists in the output folder.").format(name=target.name), parent=parent)
    overwrite = box.addButton(QCoreApplication.translate("Output", "Overwrite"), QMessageBox.ButtonRole.DestructiveRole)
    keep = box.addButton(QCoreApplication.translate("Output", "Keep both"), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    if box.clickedButton() is overwrite:
        return "overwrite"
    if box.clickedButton() is keep:
        return "keep-both"
    return None


def job_busy(parent: QWidget, window) -> bool:
    if window.jobs.is_running():
        QMessageBox.information(parent, QCoreApplication.translate("Output", "Job running"),
                                QCoreApplication.translate("Output", "Another job is running ({job}). Wait for it to finish or cancel it.").format(
                                    job=window.jobs.name))
        return True
    return False
