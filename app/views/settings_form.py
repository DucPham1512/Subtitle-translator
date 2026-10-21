"""Advanced settings as a form (6.9): every config field with a control that fits it.

Choices → dropdown, lists → tags (add with Enter, remove with ×; suggestions when known), numbers → number box,
on/off → checkbox, text → text box, paths → text box + Choose…; LLM providers and prices as a group and a table.
Each field shows whether it is saved for this series or shared, and its help (the comment on its line in the
YAML file, then the note in config.py). Saving writes only the changed values, in place (comments stay).
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.widgets import show_error
from subagent.settings import schema as ss

ROLES = ("translator", "evaluator", "utility")
PROVIDER_FIELDS = ("base_url", "api_key_env", "model")
PRICE_FIELDS = ("input", "input_cached", "output")


# -- tags ------------------------------------------------------------------------------------------

class FlowLayout(QLayout):
    """Lays widgets out left to right, wrapping to the next line (the tag chips)."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 4):
        super().__init__(parent)
        self._items: list = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:  # noqa: N802 - Qt API
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._place(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._place(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _place(self, rect: QRect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        gap = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() and line > 0:
                x, y, line = rect.x(), y + line + gap, 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + gap
            line = max(line, hint.height())
        return y + line - rect.y()


class TagEditor(QWidget):
    """A list as removable chips plus an input: Enter (or comma) adds, × removes, Backspace on an empty input
    removes the last one. `numeric`: only numbers are accepted."""

    changed = Signal()

    def __init__(self, suggestions: list[str] | None = None, numeric: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.numeric = numeric
        self._values: list = []
        self.flow = FlowLayout(self)
        self.input = QLineEdit()
        self.input.setPlaceholderText(self.tr("add…"))
        self.input.setMinimumWidth(120)
        self.input.returnPressed.connect(self._add_typed)
        self.input.textEdited.connect(self._maybe_split)
        self.input.installEventFilter(self)
        if suggestions:
            completer = QCompleter(suggestions, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.activated.connect(lambda text: (self.add(text), self.input.clear()))
            self.input.setCompleter(completer)
        self.flow.addWidget(self.input)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt API
        from PySide6.QtCore import QEvent

        if obj is self.input and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Backspace \
                and not self.input.text() and self._values:
            self.remove(len(self._values) - 1)
            return True
        return super().eventFilter(obj, event)

    def _maybe_split(self, text: str) -> None:
        if "," in text:
            for part in text.split(",")[:-1]:
                self.add(part)
            self.input.setText(text.split(",")[-1])

    def _add_typed(self) -> None:
        self.add(self.input.text())
        self.input.clear()

    def _parse(self, text: str):
        text = text.strip()
        if not text:
            return None
        if self.numeric:
            try:
                number = float(text)
            except ValueError:
                return None
            return int(number) if number.is_integer() and "." not in text else number
        return text

    def add(self, text) -> None:
        value = self._parse(str(text))
        if value is None or value in self._values:
            return
        self._values.append(value)
        self._rebuild()
        self.changed.emit()

    def remove(self, index: int) -> None:
        del self._values[index]
        self._rebuild()
        self.changed.emit()

    def values(self) -> list:
        return list(self._values)

    def set_values(self, values: list) -> None:
        self._values = list(values or [])
        self._rebuild()

    def _rebuild(self) -> None:
        while self.flow.count() > 1:
            item = self.flow.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.flow.takeAt(0)                        # the input goes back at the end
        for n, value in enumerate(self._values):
            chip = QFrame()
            chip.setObjectName("tag")
            chip.setStyleSheet("#tag { border: 1px solid palette(mid); border-radius: 10px; }")
            row = QHBoxLayout(chip)
            row.setContentsMargins(8, 1, 2, 1)
            row.setSpacing(2)
            row.addWidget(QLabel(str(value)))
            close = QToolButton()
            close.setText("×")
            close.setAutoRaise(True)
            close.setToolTip(self.tr("Remove"))
            close.clicked.connect(lambda _=False, i=n: self.remove(i))
            row.addWidget(close)
            self.flow.addWidget(chip)
        self.flow.addWidget(self.input)
        self.updateGeometry()


# -- LLM tables ------------------------------------------------------------------------------------

class ProvidersEditor(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        self.edits: dict[str, dict[str, QLineEdit]] = {}
        for role in ROLES:
            box = QGroupBox(role)
            form = QFormLayout(box)
            self.edits[role] = {}
            for name in PROVIDER_FIELDS:
                edit = QLineEdit()
                edit.textEdited.connect(lambda _=None: self.changed.emit())
                form.addRow(name, edit)
                self.edits[role][name] = edit
            col.addWidget(box)

    def set_values(self, value: dict) -> None:
        for role in ROLES:
            for name in PROVIDER_FIELDS:
                self.edits[role][name].setText(str(((value or {}).get(role) or {}).get(name) or ""))

    def values(self) -> dict:
        return {role: {name: self.edits[role][name].text().strip() for name in PROVIDER_FIELDS} for role in ROLES}


class PricesEditor(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([self.tr("Model"), *PRICE_FIELDS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(lambda _: self.changed.emit())
        col.addWidget(self.table)
        row = QHBoxLayout()
        add = QPushButton(self.tr("Add row"))
        remove = QPushButton(self.tr("Remove row"))
        add.clicked.connect(self._add_row)
        remove.clicked.connect(self._remove_row)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        col.addLayout(row)
        col.addWidget(QLabel(self.tr("USD per 1M tokens.")))

    def _add_row(self) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(4):
            self.table.setItem(r, c, QTableWidgetItem("" if c == 0 else "0"))
        self.table.editItem(self.table.item(r, 0))
        self.changed.emit()

    def _remove_row(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        if rows:
            self.changed.emit()

    def set_values(self, value: dict) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for model, price in (value or {}).items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(model))
            for c, name in enumerate(PRICE_FIELDS, start=1):
                self.table.setItem(r, c, QTableWidgetItem(_num_text((price or {}).get(name, 0))))
        self.table.blockSignals(False)

    def values(self) -> dict:
        out: dict = {}
        for r in range(self.table.rowCount()):
            model = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            if not model:
                continue
            row = {}
            for c, name in enumerate(PRICE_FIELDS, start=1):
                text = self.table.item(r, c).text().strip() if self.table.item(r, c) else "0"
                try:
                    row[name] = float(text) if text else 0.0
                except ValueError as exc:
                    raise ValueError(self.tr("Price for {model}: '{text}' is not a number").format(
                        model=model, text=text)) from exc
            out[model] = row
        return out


def _num_text(value) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _decimals(*values) -> int:
    best = 2
    for v in values:
        if isinstance(v, float) and not math.isnan(v):
            text = f"{v:.10f}".rstrip("0")
            best = max(best, len(text.split(".")[1]) if "." in text else 0)
    return min(best, 6)


# -- the form --------------------------------------------------------------------------------------

class Field:
    """One field's control: get / set the value as the config holds it."""

    def __init__(self, spec: ss.FieldSpec, widget: QWidget, get, set_):
        self.spec, self.widget, self.get, self.set = spec, widget, get, set_
        self.row: QWidget | None = None
        self.initial = None


class SettingsForm(QWidget):
    """Section list (with search) on the left, the selected section's fields on the right."""

    def __init__(self, services, parent: QWidget | None = None):
        super().__init__(parent)
        self.services = services
        self.fields: list[Field] = []
        layout = QVBoxLayout(self)
        split = QSplitter()
        left = QWidget()
        left_col = QVBoxLayout(left)
        left_col.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Search settings…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.sections = QListWidget()
        self.sections.currentRowChanged.connect(lambda r: self.pages.setCurrentIndex(max(r, 0)))
        left_col.addWidget(self.search)
        left_col.addWidget(self.sections, 1)
        left.setMaximumWidth(220)
        self.pages = QStackedWidget()
        split.addWidget(left)
        split.addWidget(self.pages)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        row = QHBoxLayout()
        self.status = QLabel()
        raw = QPushButton(self.tr("Edit as YAML…"))
        raw.clicked.connect(self._raw)
        revert = QPushButton(self.tr("Discard changes"))
        revert.clicked.connect(self.load)
        save = QPushButton(self.tr("Save changes"))
        save.clicked.connect(self.save)
        row.addWidget(self.status, 1)
        row.addWidget(raw)
        row.addWidget(revert)
        row.addWidget(save)
        layout.addLayout(row)
        self._built = False

    # building

    def _build(self) -> None:
        paths = self.services.paths
        specs = ss.with_known_sets(ss.fields(self.services.config), paths.root, paths.work)
        texts = {"shared": paths.config_file.read_text(encoding="utf-8") if paths.config_file.is_file() else "",
                 "series": paths.series_file.read_text(encoding="utf-8")
                 if paths.series_file and paths.series_file.is_file() else ""}
        by_section: dict[str, list[ss.FieldSpec]] = {}
        for spec in specs:
            by_section.setdefault(spec.section, []).append(spec)
        for section, items in by_section.items():
            page = QWidget()
            col = QVBoxLayout(page)
            for spec in items:
                field = self._field(spec)
                where = ss.target(paths.root, spec.path, paths.series)
                help_text = " · ".join(t for t in (ss.file_comment(texts[where], spec.path), spec.help) if t)
                field.row = self._row(spec, field.widget, where, help_text)
                col.addWidget(field.row)
                self.fields.append(field)
            col.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
            item = QListWidgetItem(section)
            item.setData(Qt.ItemDataRole.UserRole, section)
            self.sections.addItem(item)
        self.sections.setCurrentRow(0)
        self._built = True

    def _row(self, spec: ss.FieldSpec, widget: QWidget, where: str, help_text: str) -> QWidget:
        row = QWidget()
        col = QVBoxLayout(row)
        col.setContentsMargins(0, 4, 0, 6)
        top = QHBoxLayout()
        name = QLabel(".".join(spec.path[1:]) or spec.path[0])
        name.setMinimumWidth(220)
        name.setToolTip(spec.key)
        tag = QLabel(self.tr("this series") if where == "series" else self.tr("shared"))
        tag.setStyleSheet("color: palette(mid); font-size: 11px;")
        tag.setToolTip(self.tr("Saved in series.yaml (this series only)") if where == "series"
                       else self.tr("Saved in config.yaml (every series)"))
        top.addWidget(name)
        top.addWidget(widget, 1)
        top.addWidget(tag)
        col.addLayout(top)
        if help_text:
            note = QLabel(help_text)
            note.setWordWrap(True)
            note.setStyleSheet("color: palette(placeholder-text); font-size: 11px;")
            col.addWidget(note)
        row.setProperty("search_text", f"{spec.key} {help_text}".lower())
        return row

    def _field(self, spec: ss.FieldSpec) -> Field:
        kind = spec.kind
        if kind == "choice":
            box = QComboBox()
            box.setEditable(spec.editable)
            for c in spec.choices:
                box.addItem(c, c)
            box.currentTextChanged.connect(self._dirty)

            def get_choice(b=box):
                text = b.currentText().strip()
                return None if text in (ss.NONE, "") else text

            def set_choice(v, b=box):
                text = ss.NONE if v is None else str(v)
                if b.findText(text) < 0:
                    b.addItem(text, text)
                b.setCurrentText(text)
            return Field(spec, box, get_choice, set_choice)
        if kind == "bool":
            check = QCheckBox()
            check.toggled.connect(self._dirty)
            return Field(spec, check, check.isChecked, lambda v, c=check: c.setChecked(bool(v)))
        if kind == "int":
            spin = QSpinBox()
            spin.setRange(-10**9, 10**9)
            spin.valueChanged.connect(self._dirty)
            return Field(spec, spin, spin.value, lambda v, s=spin: s.setValue(int(v or 0)))
        if kind == "float":
            spin = QDoubleSpinBox()
            spin.setRange(-1e9, 1e9)
            spin.valueChanged.connect(self._dirty)

            def set_float(v, s=spin, d=spec.default):
                s.setDecimals(_decimals(v, d))
                s.setSingleStep(10 ** -min(_decimals(v, d), 2))
                s.setValue(float(v or 0))
            return Field(spec, spin, lambda s=spin: round(s.value(), s.decimals()), set_float)
        if kind == "list":
            tags = TagEditor(spec.choices, spec.numeric)
            tags.changed.connect(self._dirty)
            return Field(spec, tags, tags.values, tags.set_values)
        if kind == "path":
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            edit.textEdited.connect(self._dirty)
            choose = QPushButton(self.tr("Choose…"))
            choose.clicked.connect(lambda _=False, e=edit: self._pick(e))
            row.addWidget(edit, 1)
            row.addWidget(choose)
            optional = spec.default is None
            return Field(spec, holder, lambda e=edit, o=optional: (e.text().strip() or (None if o else "")),
                         lambda v, e=edit: e.setText("" if v is None else str(v)))
        if kind == "providers":
            ed = ProvidersEditor()
            ed.changed.connect(self._dirty)
            return Field(spec, ed, ed.values, ed.set_values)
        if kind == "prices":
            ed = PricesEditor()
            ed.changed.connect(self._dirty)
            return Field(spec, ed, ed.values, ed.set_values)
        edit = QLineEdit()
        edit.textEdited.connect(self._dirty)
        optional = kind == "optional_text"
        return Field(spec, edit, lambda e=edit, o=optional: (e.text().strip() or None) if o else e.text(),
                     lambda v, e=edit: e.setText("" if v is None else str(v)))

    def _pick(self, edit: QLineEdit) -> None:
        start = edit.text().strip() or str(self.services.paths.root)
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder"), start)
        if folder:
            edit.setText(str(Path(folder)))
            self._dirty()

    # values

    def load(self) -> None:
        if not self._built:
            self._build()
        config = self.services.config
        self._loading = True
        for f in self.fields:
            value = ss.value_at(config, f.spec.path)
            f.set(value)
            f.initial = f.get()
        self._loading = False
        self.status.setText("")

    def _dirty(self, *_args) -> None:
        if not getattr(self, "_loading", False):
            self.status.setText(self.tr("Unsaved changes"))

    def changes(self) -> list[tuple[list[str], object]]:
        return [(f.spec.path, value) for f in self.fields if (value := f.get()) != f.initial]

    def save(self) -> bool:
        from subagent.settings.config import save_settings

        try:
            changes = self.changes()
        except ValueError as exc:
            show_error(self, self.tr("Settings"), exc)
            return False
        if not changes:
            self.status.setText(self.tr("Nothing to save"))
            return False
        try:
            save_settings(self.services.root, changes)
            self.services.reload()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            show_error(self, self.tr("Settings"), exc)
            return False
        self.load()
        self.status.setText(self.tr("Saved {n} changes.").format(n=len(changes)))
        return True

    def _filter(self, text: str) -> None:
        q = text.strip().lower()
        first = None
        for n in range(self.sections.count()):
            section = self.sections.item(n).data(Qt.ItemDataRole.UserRole)
            rows = [f.row for f in self.fields if f.spec.section == section]
            hits = 0
            for row in rows:
                show = not q or q in row.property("search_text") or q in section
                row.setVisible(show)
                hits += show
            self.sections.item(n).setHidden(bool(q) and hits == 0)
            if hits and first is None:
                first = n
        if q and first is not None and self.sections.item(self.sections.currentRow()).isHidden():
            self.sections.setCurrentRow(first)

    def _raw(self) -> None:
        dialog = RawYamlDialog(self, self.services)
        if dialog.exec():
            self.load()


class RawYamlDialog(QDialog):
    """The raw editor for config.yaml or the series' series.yaml (anything the form does not show)."""

    def __init__(self, parent: QWidget, services):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle(self.tr("Edit as YAML"))
        self.resize(900, 700)
        col = QVBoxLayout(self)
        top = QHBoxLayout()
        self.yaml_file = QComboBox()
        self.yaml_file.addItem(self.tr("config.yaml (shared by every series)"), "shared")
        if services.paths.series:
            self.yaml_file.addItem(self.tr("series.yaml (this series: {slug})").format(slug=services.paths.series),
                                   "series")
        self.yaml_file.currentIndexChanged.connect(lambda _: self._load())
        top.addWidget(self.yaml_file)
        top.addWidget(QLabel(self.tr("Validated before saving; comments are kept. A series' series.yaml overrides "
                                     "config.yaml for that series.")), 1)
        col.addLayout(top)
        self.yaml = QPlainTextEdit()
        self.yaml.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        col.addWidget(self.yaml, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        col.addWidget(buttons)
        self._load()

    def _load(self) -> None:
        paths = self.services.paths
        path = paths.series_file if self.yaml_file.currentData() == "series" else paths.config_file
        self.yaml.setPlainText(path.read_text(encoding="utf-8") if path and path.is_file() else "")

    def _save(self) -> None:
        from subagent.settings.config import save_config_text

        try:
            save_config_text(self.services.root, self.yaml.toPlainText(),
                             series_file=self.yaml_file.currentData() == "series")
            self.services.reload()
        except Exception as exc:  # noqa: BLE001
            show_error(self, self.windowTitle(), exc)
            return
        QMessageBox.information(self, self.windowTitle(), self.tr("Saved."))
        self.accept()
