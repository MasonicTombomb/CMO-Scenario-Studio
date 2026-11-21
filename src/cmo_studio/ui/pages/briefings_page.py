"""Description and briefing pages: HTML editor, formatting helpers, OOB generator, live preview."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QPushButton,
                             QSplitter, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from ...export import html as H
from ...model.project import DEFAULT_BRIEFING, DEFAULT_DESCRIPTION
from ..widgets import CodeEditor, hint_label
from .base import AppContext, Page

PREVIEW_CSS = H.BRIEFING_CSS.replace("background-color: #383838;", "")


class BriefingsPage(Page):
    title = "Briefings"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.target = ("desc", "")     # ('desc', '') | ('side', id) | ('variant', id)
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._pick)
        ll.addWidget(self.list)
        ll.addWidget(hint_label("Pages are exported to Scenarios\\<Folder>\\ and loaded in CMO with "
                                "[LOADDOC]file.html[/LOADDOC] (the build report prints the exact lines)."))
        split.addWidget(left)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.page_title = QLabel("")
        self.page_title.setProperty("heading", True)
        bar.addWidget(self.page_title)
        bar.addStretch()
        for text, tag, tip in (("H1", "h1", "Heading"), ("H2", "h2", "Sub-heading"), ("H4", "h4", "Small heading"),
                               ("P", "p", "Paragraph"), ("B", "b", "Bold"), ("I", "i", "Italic")):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c, t=tag: self._wrap(t))
            bar.addWidget(b)
        lst = QToolButton()
        lst.setText("• List")
        lst.clicked.connect(self._list)
        bar.addWidget(lst)
        ins = QPushButton("Insert ▾")
        menu = QMenu(self)
        menu.addAction("Order of battle: this side", lambda: self._oob(own=True))
        menu.addAction("Order of battle: enemy sides", lambda: self._oob(own=False))
        menu.addAction("Flight schedule: this side", self._schedule)
        menu.addAction("Briefing skeleton (OPORD)", lambda: self.editor.insertPlainText(DEFAULT_BRIEFING))
        menu.addAction("Image (from the scenario folder)", lambda: self.editor.insertPlainText(
            '<img src="picture.jpg" width="600">\n'))
        menu.addAction("Table", lambda: self.editor.insertPlainText(
            "<table>\n\t<tr><th>Unit</th><th>Task</th></tr>\n\t<tr><td></td><td></td></tr>\n</table>\n"))
        ins.setMenu(menu)
        bar.addWidget(ins)
        self.pack_btn = QPushButton("Briefing pack (PDF)...")
        self.pack_btn.setToolTip("A NATO-style operation order with an intelligence summary, air tasking schedule "
                                 "and weather annex for this side, printed to PDF")
        self.pack_btn.clicked.connect(self._pack)
        bar.addWidget(self.pack_btn)
        ml.addLayout(bar)
        self.auto = QCheckBox("Prepend automatic header (author, date, location, sides, duration, ratings)")
        self.auto.toggled.connect(self._auto)
        ml.addWidget(self.auto)
        self.editor = CodeEditor("html")
        self.editor.textChanged.connect(self._text)
        ml.addWidget(self.editor, 1)
        split.addWidget(mid)

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.document().setDefaultStyleSheet(PREVIEW_CSS)
        self.preview.setStyleSheet("QTextBrowser { background: #383838; color: whitesmoke; }")
        split.addWidget(self.preview)
        split.setSizes([220, 560, 520])
        self._timer = QTimer(self, singleShot=True, interval=300)
        self._timer.timeout.connect(self._render)
        self._loading = False

    # ------------------------------------------------------------------ list
    def refresh(self) -> None:
        p = self.project
        pages = [("desc", "", "Scenario description")]
        pages += [("side", s.id, f"Briefing: {s.name}") for s in p.sides]
        pages += [("variant", v.id, f"Variant text: {v.name}") for v in p.variants]
        self.list.blockSignals(True)
        self.list.clear()
        for kind, oid, label in pages:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, (kind, oid))
            self.list.addItem(it)
            if (kind, oid) == self.target:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if self.list.currentItem() is None:
            self.target = ("desc", "")
            self.list.setCurrentRow(0)
        self._load()

    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.target = tuple(cur.data(Qt.ItemDataRole.UserRole))
            self._load()

    def _get(self) -> str:
        kind, oid = self.target
        p = self.project
        if kind == "desc":
            return p.meta.description_html
        if kind == "side":
            s = p.side(oid)
            return s.briefing_html if s else ""
        v = next((x for x in p.variants if x.id == oid), None)
        return v.description_html if v else ""

    def _load(self):
        kind, oid = self.target
        p = self.project
        self._loading = True
        self.editor.set_text_keep(self._get())
        self._loading = False
        self.auto.setVisible(kind == "desc")
        self.auto.blockSignals(True)
        self.auto.setChecked(p.meta.auto_header)
        self.auto.blockSignals(False)
        names = {"desc": f"{p.meta.prefix()}_Desc.html"}
        if kind == "side" and p.side(oid):
            names["side"] = f"{p.meta.prefix()}_Briefing_{p.side(oid).file_tag()}.html"
        if kind == "variant":
            v = next((x for x in p.variants if x.id == oid), None)
            names["variant"] = (f"{p.meta.prefix()}_Desc_{v.key}.html  (appended to the description)" if v else "")
        self.page_title.setText(names.get(kind, ""))
        self._render()

    # ------------------------------------------------------------------ edits
    def _text(self):
        if self._loading:
            return
        kind, oid = self.target
        text = self.editor.toPlainText()
        p = self.project
        with self.edit("Edit page", "briefings", merge=f"brief.{kind}.{oid}"):
            if kind == "desc":
                p.meta.description_html = text
            elif kind == "side" and p.side(oid):
                p.side(oid).briefing_html = text
            else:
                v = next((x for x in p.variants if x.id == oid), None)
                if v:
                    v.description_html = text
        self._timer.start()

    def _auto(self, on: bool):
        with self.edit("Automatic header", "meta"):
            self.project.meta.auto_header = on
        self._render()

    def _render(self):
        kind, oid = self.target
        p = self.project
        if kind == "desc":
            body = p.meta.description_html
            if p.meta.auto_header:
                body = H.description_header(p) + "\n" + body
        elif kind == "variant":
            v = next((x for x in p.variants if x.id == oid), None)
            body = (H.description_header(p, v) if p.meta.auto_header and v else "") + "\n" + \
                p.meta.description_html + "\n" + (v.description_html if v else "")
        else:
            body = self._get()
        self.preview.setHtml(f"<html><body>{body}</body></html>")

    def _wrap(self, tag: str):
        cur = self.editor.textCursor()
        sel = cur.selectedText().replace(" ", "\n")
        block = tag in ("h1", "h2", "h4", "p")
        if not sel:
            sel = "text"
        text = f"<{tag}>{sel}</{tag}>" + ("\n" if block else "")
        cur.insertText(text)

    def _list(self):
        cur = self.editor.textCursor()
        sel = cur.selectedText().replace(" ", "\n")
        items = [s.strip() for s in sel.split("\n") if s.strip()] or ["item"]
        cur.insertText("<ul>\n" + "".join(f"\t<li>{re.sub('<[^>]+>', '', i)}</li>\n" for i in items) + "</ul>\n")

    def _schedule(self):
        from ...model.briefing_pack import flight_schedule_html
        kind, oid = self.target
        sides = [oid] if kind == "side" else [s.id for s in self.project.sides]
        out = [(f"<h3>{self.project.side_name(sid)}</h3>\n" if kind != "side" else "") +
               flight_schedule_html(self.project, sid, self.ctx.db, title=kind == "side") for sid in sides]
        self.editor.insertPlainText("\n".join(out) + "\n")

    def _pack(self):
        from ..briefing_pack_dialog import BriefingPackDialog
        kind, oid = self.target
        BriefingPackDialog(self.ctx, oid if kind == "side" else "", self).exec()
        self.refresh()

    def _oob(self, own: bool):
        kind, oid = self.target
        p = self.project
        if kind == "side":
            sides = [oid] if own else [s.id for s in p.sides if s.id != oid and p.side(oid) and
                                       p.side(oid).postures.get(s.id) in ("H", "U")]
        else:
            sides = [s.id for s in p.sides]
        out = []
        for sid in sides:
            block = H.oob_html(p, sid)
            if block:
                out.append(f"<h3>{p.side_name(sid)}</h3>\n{block}")
        self.editor.insertPlainText("\n".join(out) + "\n" if out else "<p>(no units yet)</p>\n")


__all__ = ["BriefingsPage", "DEFAULT_DESCRIPTION"]
