"""Dialog to create a new character from the review screen (id and pinyin suggested from the Chinese name)."""

from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from subagent.memory.bootstrap import name_pinyin, slugify
from subagent.models import MemoryProposal
from subagent.textutil import is_han

_ID = re.compile(r"^[a-z0-9_]+$")


def character_proposals(data: dict) -> list[MemoryProposal]:
    """The character, and (optionally) its name in the glossary, as human proposals."""
    props = [MemoryProposal(kind="character", source="human", payload={
        "id": data["id"], "name_zh": data["name_zh"], "name_vi": data["name_vi"],
        "description": data.get("description") or None})]
    if data.get("glossary"):
        props.append(MemoryProposal(kind="glossary", source="human", payload={
            "zh": data["name_zh"], "vi": data["name_vi"], "pinyin": data.get("pinyin") or None, "type": "name"}))
    return props


def validate(data: dict, existing_ids: set[str]) -> list[str]:
    errors = []
    if not data["name_zh"] or not any(is_han(ch) for ch in data["name_zh"]):
        errors.append("chinese")
    if not data["name_vi"]:
        errors.append("vietnamese")
    if not _ID.match(data["id"] or ""):
        errors.append("id_format")
    elif data["id"] in existing_ids:
        errors.append("id_taken")
    return errors


class NewCharacterDialog(QDialog):
    ROLES = ("speaker", "listener", None)

    def __init__(self, parent: QWidget, existing_ids: set[str], name_zh: str = ""):
        super().__init__(parent)
        self.existing_ids = existing_ids
        self._id_edited = False
        self._pinyin_edited = False
        self.setWindowTitle(self.tr("New character"))
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_zh = QLineEdit(name_zh)
        self.pinyin = QLineEdit()
        self.name_vi = QLineEdit()
        self.name_vi.setPlaceholderText(self.tr("Hán-Việt reading, e.g. Lâm Uyên"))
        self.char_id = QLineEdit()
        self.char_id.setPlaceholderText(self.tr("lowercase letters, digits and _"))
        self.description = QLineEdit()
        self.description.setPlaceholderText(self.tr("Who they are, in one line (optional)"))
        self.role = QComboBox()
        self.role.addItem(self.tr("Speaker of this line"), "speaker")
        self.role.addItem(self.tr("Listener of this line"), "listener")
        self.role.addItem(self.tr("Don't assign"), None)
        self.glossary = QCheckBox(self.tr("Also add the name to the glossary"))
        self.glossary.setChecked(True)
        form.addRow(self.tr("Chinese name"), self.name_zh)
        form.addRow(self.tr("Pinyin"), self.pinyin)
        form.addRow(self.tr("Vietnamese name"), self.name_vi)
        form.addRow(self.tr("Id"), self.char_id)
        form.addRow(self.tr("Description"), self.description)
        form.addRow(self.tr("Set as"), self.role)
        form.addRow("", self.glossary)
        layout.addLayout(form)
        layout.addWidget(QLabel(self.tr("The character is saved to memory now, locked as your edit.")))
        self.error = QLabel()
        self.error.setStyleSheet("color: #c0392b;")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.name_zh.textChanged.connect(self._suggest)
        self.char_id.textEdited.connect(lambda _: setattr(self, "_id_edited", True))
        self.pinyin.textEdited.connect(lambda _: setattr(self, "_pinyin_edited", True))
        self._suggest(name_zh)
        (self.name_vi if name_zh else self.name_zh).setFocus()

    def _suggest(self, zh: str) -> None:
        """Pinyin and id follow the Chinese name until the user edits them."""
        zh = zh.strip()
        py = name_pinyin(zh) if zh else ""
        if not self._pinyin_edited:
            self.pinyin.setText(py)
        if not self._id_edited:
            candidate = slugify(py) if py else ""
            base, n = candidate, 2
            while candidate and candidate in self.existing_ids:
                candidate = f"{base}_{n}"
                n += 1
            self.char_id.setText(candidate)

    def data(self) -> dict:
        return {
            "id": self.char_id.text().strip(), "name_zh": self.name_zh.text().strip(),
            "name_vi": self.name_vi.text().strip(), "pinyin": self.pinyin.text().strip(),
            "description": self.description.text().strip(), "glossary": self.glossary.isChecked(),
            "role": self.role.currentData(),
        }

    def _accept(self) -> None:
        messages = {
            "chinese": self.tr("Enter the Chinese name."),
            "vietnamese": self.tr("Enter the Vietnamese name."),
            "id_format": self.tr("The id may only contain lowercase letters, digits and _."),
            "id_taken": self.tr("This id is already used by another character."),
        }
        errors = validate(self.data(), self.existing_ids)
        if errors:
            self.error.setText("\n".join(messages[e] for e in errors))
            return
        self.accept()
