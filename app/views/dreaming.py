"""Dreaming screen (6.8): run dreaming as a job, review proposals, apply the accepted ones in one commit."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.memory import dreaming
from app.widgets import confirm, show_error
from app.workers import run_async

EVIDENCE = Qt.ItemDataRole.UserRole + 1


class DreamingView(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.services = main.services
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.run_btn = QPushButton(self.tr("Run dreaming"))
        self.run_btn.clicked.connect(self._run)
        self.info = QLabel()
        self.forget_btn = QPushButton(self.tr("Forget rejected proposals…"))
        self.forget_btn.setToolTip(self.tr("Proposals you rejected are never proposed again; this clears that list"))
        self.forget_btn.clicked.connect(self._forget)
        row.addWidget(self.run_btn)
        row.addWidget(self.info, 1)
        row.addWidget(self.forget_btn)
        layout.addLayout(row)
        layout.addWidget(QLabel(self.tr(
            "Checked proposals are applied; unchecked ones are rejected and not proposed again. Proposals that "
            "change locked entries are unchecked and highlighted. Double-click evidence to open the line.")))
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels([self.tr("Proposal"), self.tr("Before"), self.tr("After"), self.tr("Reason"),
                                   self.tr("Evidence")])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemDoubleClicked.connect(self._open_evidence)
        layout.addWidget(self.tree, 1)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.apply_btn = QPushButton(self.tr("Apply checked proposals…"))
        self.apply_btn.clicked.connect(self._apply)
        bottom.addWidget(self.apply_btn)
        layout.addLayout(bottom)
        main.jobs.finished.connect(self._job_finished)

    def activate(self) -> None:
        self._load()

    def _run(self) -> None:
        if not self.main.jobs.start("dream", ["dream"]):
            show_error(self, self.tr("Dreaming"), self.tr("Another job is running."))
        else:
            self.info.setText(self.tr("Dreaming…"))

    def _job_finished(self, name: str, code: int, error: dict) -> None:
        if name != "dream":
            return
        if code != 0:
            from app.messages import error_message

            show_error(self, self.tr("Dreaming"), error_message(error.get("error_code"), error.get("message", "")))
        self._load()

    def _load(self) -> None:
        run_async(lambda: dreaming.load_proposals(self.services.paths), self._fill,
                  lambda exc: show_error(self, self.tr("Dreaming"), exc))

    def _fill(self, out) -> None:
        self.tree.clear()
        if out is None or not out.items:
            self.info.setText(self.tr("No proposals. Run dreaming after finishing an episode."))
            self.apply_btn.setEnabled(False)
            return
        self.apply_btn.setEnabled(True)
        text = self.tr("{n} proposals from {date}").format(n=len(out.items),
                                                           date=out.generated_at.replace("T", " ")[:19])
        hidden = out.inputs.get("previously_rejected", 0)
        if hidden:
            text += " · " + self.tr("{n} you rejected before were left out").format(n=hidden)
        self.info.setText(text)
        kinds = {"glossary": self.tr("Glossary"), "pronoun_pair": self.tr("Pronoun pairs"),
                 "style_rule": self.tr("Style rules"), "briefing": self.tr("Briefings")}
        groups: dict[str, QTreeWidgetItem] = {}
        for item in out.items:
            kind = item.proposal.kind
            if kind not in groups:
                groups[kind] = QTreeWidgetItem(self.tree, [kinds.get(kind, kind)])
                groups[kind].setExpanded(True)
            before = _summary(item.before)
            after = _summary(item.proposal.payload)
            node = QTreeWidgetItem(groups[kind], [item.key, before, after, item.reason, ", ".join(item.proposal.evidence)])
            node.setData(0, Qt.ItemDataRole.UserRole, item.id)
            node.setData(4, EVIDENCE, item.proposal.evidence)
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked if item.preselected == "accept" else Qt.CheckState.Unchecked)
            if item.touches_locked:
                for col in range(5):
                    node.setBackground(col, QBrush(QColor(255, 200, 120, 90)))
                node.setToolTip(0, self.tr("Changes a locked entry (confirmed by a person)"))
        for col in range(4):
            self.tree.resizeColumnToContents(col)

    def _checked(self) -> set[str]:
        ids = set()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                node = group.child(j)
                if node.checkState(0) == Qt.CheckState.Checked:
                    ids.add(node.data(0, Qt.ItemDataRole.UserRole))
        return ids

    def _apply(self) -> None:
        ids = self._checked()
        if self.main.jobs.is_running() or self.services.jobs_running():
            show_error(self, self.tr("Dreaming"), self.tr("Wait for the running job to finish."))
            return
        if not confirm(self, self.tr("Apply proposals"), self.tr(
                "Apply {n} proposals to memory in one version? Unchecked proposals are discarded.").format(n=len(ids))):
            return
        config, paths = self.services.config, self.services.paths

        def done(result) -> None:
            self.info.setText(self.tr("Applied {n} changes; {c} went to Conflicts.").format(
                n=result.writes, c=len(result.conflicts)))
            self.tree.clear()
            self.apply_btn.setEnabled(False)

        run_async(lambda: dreaming.apply_dream(config, paths, ids), done,
                  lambda exc: show_error(self, self.tr("Apply proposals"), exc))

    def _forget(self) -> None:
        n = len(dreaming.load_rejections(self.services.paths))
        if not n:
            self.info.setText(self.tr("No rejected proposals are remembered."))
            return
        if self.main.jobs.is_running() or self.services.jobs_running():
            show_error(self, self.tr("Dreaming"), self.tr("Wait for the running job to finish."))
            return
        if not confirm(self, self.tr("Forget rejected proposals"), self.tr(
                "Forget the {n} proposals you rejected? Dreaming may propose them again.").format(n=n)):
            return
        config, paths = self.services.config, self.services.paths
        run_async(lambda: dreaming.forget_rejections(config, paths),
                  lambda k: self.info.setText(self.tr("Forgot {n} rejected proposals.").format(n=k)),
                  lambda exc: show_error(self, self.tr("Dreaming"), exc))

    def _open_evidence(self, node: QTreeWidgetItem, col: int) -> None:
        evidence = node.data(4, EVIDENCE) or []
        for ev in evidence:
            parts = ev.split(":")
            if len(parts) >= 2 and parts[0].startswith("ep"):
                self.main.show_review(parts[0], event_id=f"{parts[0]}:{parts[1]}", read_only=True)
                return


def _summary(d: dict | None) -> str:
    if not d:
        return ""
    keep = {k: v for k, v in d.items() if k in ("vi", "self_term", "address_term", "context", "rule", "example",
                                                "action", "file") and v}
    if "content" in d:
        keep["content"] = str(d["content"])[:80] + "…"
    return json.dumps(keep, ensure_ascii=False)
