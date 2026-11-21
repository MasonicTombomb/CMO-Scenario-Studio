"""The briefing pack window: edit a side's operation order and intelligence summary, preview it, print it to PDF."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from ..model.briefing_pack import DEFAULT_BANNER, cmo_briefing_html, default_mission, opord_html
from .widgets import IdCombo, hint_label

TEXT_FIELDS = (
    # (tab, key, label, hint)
    ("Orders", "situation", "Background", "The political and military background, added to the generated situation."),
    ("Orders", "mission", "Mission", ""),
    ("Orders", "intent", "Commander's intent", "Purpose, method and end state. Blank: a generic one."),
    ("Orders", "concept", "Concept of operations", "How the operation will unfold, phase by phase."),
    ("Intelligence", "enemy_assessment", "Enemy assessment", "What the enemy is trying to do and how it is "
                                                            "postured."),
    ("Intelligence", "mlcoa", "Most likely enemy course of action", ""),
    ("Intelligence", "mdcoa", "Most dangerous enemy course of action", ""),
    ("Support and signal", "roe", "Rules of engagement (additional)", "Added under the weapon control states."),
    ("Support and signal", "sustainment", "Sustainment", "Logistics, fuel, tankers, medical: added to the bases."),
    ("Support and signal", "command", "Command", "Who commands, where, succession. Blank: generated."),
)


class BriefingPackDialog(QDialog):
    def __init__(self, ctx, side_id: str = "", parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Briefing pack (operation order and intelligence summary)")
        self.resize(1300, 860)
        self._loading = False
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.side = IdCombo()
        self.side.set_items([(s.name, s.id) for s in ctx.project.sides])
        if side_id:
            self.side.set_current_id(side_id)
        self.side.currentIndexChanged.connect(self._load)
        top.addWidget(hint_label("Side:"))
        top.addWidget(self.side)
        top.addWidget(hint_label("Everything left blank is written for you from the scenario: forces, missions, "
                                 "courses, times on target, codewords, weather and doctrine."), 1)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        head = QFormLayout()
        self.operation = QLineEdit()
        self.originator = QLineEdit()
        self.classification = QLineEdit()
        self.classification.setPlaceholderText(DEFAULT_BANNER)
        for w in (self.operation, self.originator, self.classification):
            w.textEdited.connect(self._edited)
        head.addRow("Operation:", self.operation)
        head.addRow("Issued by:", self.originator)
        head.addRow("Banner:", self.classification)
        ll.addLayout(head)
        tabs = QTabWidget()
        self.fields: dict[str, QPlainTextEdit] = {}
        forms: dict[str, QFormLayout] = {}
        for tab, key, label, tip in TEXT_FIELDS:
            if tab not in forms:
                page = QWidget()
                forms[tab] = QFormLayout(page)
                tabs.addTab(page, tab)
            ed = QPlainTextEdit()
            ed.setMinimumHeight(70)
            ed.setToolTip(tip)
            ed.textChanged.connect(self._edited)
            self.fields[key] = ed
            forms[tab].addRow(label + ":", ed)
        self.exact = QCheckBox("Give exact enemy positions in the intelligence summary")
        self.exact.setToolTip("Off: approximate (nearest named area or whole degree), as an intelligence estimate")
        self.exact.toggled.connect(self._edited)
        forms["Intelligence"].addRow("", self.exact)
        ll.addWidget(tabs, 1)
        btns = QHBoxLayout()
        for text, fn, tip in (("Save PDF...", self.save_pdf, "Print this side's pack to a PDF file"),
                              ("PDFs for every side...", self.save_all, "One PDF per side into a folder"),
                              ("Use as CMO briefing", self.to_cmo, "Replace the side's in-game briefing with the "
                                                                    "situation, mission, execution and schedule")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        ll.addLayout(btns)
        split.addWidget(left)
        self.preview = QTextBrowser()
        split.addWidget(self.preview)
        split.setSizes([560, 740])
        lay.addWidget(split, 1)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._render)
        self._load()

    # ------------------------------------------------------------------ data
    @property
    def sid(self) -> str:
        return self.side.current_id()

    def _load(self, *_):
        s = self.ctx.project.side(self.sid)
        if s is None:
            return
        o = s.orders
        self._loading = True
        self.operation.setText(o.operation)
        self.operation.setPlaceholderText(f"OPERATION {self.ctx.project.meta.title.upper()}")
        self.originator.setText(o.originator)
        self.originator.setPlaceholderText(f"{s.name} Joint Force Headquarters")
        self.classification.setText(o.classification)
        for key, ed in self.fields.items():
            ed.setPlainText(getattr(o, key))
        self.fields["mission"].setPlaceholderText(default_mission(self.ctx.project, self.sid))
        self.exact.setChecked(o.exact_positions)
        self._loading = False
        self._render()

    def _edited(self, *_):
        if self._loading:
            return
        s = self.ctx.project.side(self.sid)
        if s is None:
            return
        new = {"operation": self.operation.text(), "originator": self.originator.text(),
               "classification": self.classification.text(), "exact_positions": self.exact.isChecked(),
               **{k: ed.toPlainText() for k, ed in self.fields.items()}}
        if any(getattr(s.orders, k) != v for k, v in new.items()):
            with self.ctx.doc.modify(f"Edit {s.name} briefing pack", "sides", merge=f"orders.{s.id}"):
                for k, v in new.items():
                    setattr(s.orders, k, v)
        self._timer.start()

    def html(self, sid: Optional[str] = None) -> str:
        return opord_html(self.ctx.project, sid or self.sid, self.ctx.db)

    def _render(self):
        self.preview.setHtml(self.html())

    # ------------------------------------------------------------------ output
    def _default_name(self, sid: str) -> str:
        p = self.ctx.project
        s = p.side(sid)
        return f"{p.meta.prefix()}_{s.file_tag()}_OPORD.pdf"

    def save_pdf(self):
        from ..export.pdf import html_to_pdf
        path, _ = QFileDialog.getSaveFileName(self, "Save briefing pack", str(Path.home() / self._default_name(
            self.sid)), "PDF (*.pdf)")
        if not path:
            return
        how = html_to_pdf(self.html(), path)
        self.ctx.status(f"Saved {path}" + ("" if how == "browser" else " (simple layout: Edge or Chrome not found)"))
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def save_all(self):
        from ..export.pdf import html_to_pdf
        folder = QFileDialog.getExistingDirectory(self, "Folder for the briefing packs", str(Path.home()))
        if not folder:
            return
        done = []
        for s in self.ctx.project.sides:
            if not s.export_briefing:
                continue
            out = Path(folder) / self._default_name(s.id)
            html_to_pdf(self.html(s.id), out)
            done.append(out.name)
        QMessageBox.information(self, "Briefing packs", "Saved:\n" + "\n".join(done) if done else
                                "No sides have briefings switched on (Sides tab).")

    def to_cmo(self):
        s = self.ctx.project.side(self.sid)
        if s is None:
            return
        if s.briefing_html.strip() and QMessageBox.question(
                self, "Use as CMO briefing", f"Replace {s.name}'s in-game briefing with the briefing pack?") \
                != QMessageBox.StandardButton.Yes:
            return
        with self.ctx.doc.modify(f"Briefing pack into {s.name}'s CMO briefing", "sides"):
            s.briefing_html = cmo_briefing_html(self.ctx.project, s.id, self.ctx.db)
        self.ctx.status(f"{s.name}'s in-game briefing now holds the operation order (Briefings tab).")


__all__ = ["BriefingPackDialog"]
