"""Sides: names, colours, AI, proficiency, doctrine, the posture matrix and build variants."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter,
                             QTableWidget, QVBoxLayout, QWidget)

from ...model.enums import AWARENESS, DOCTRINE_FIELDS, POSTURES, PROFICIENCY
from ...model.project import Variant, new_id
from ..widgets import ColorButton, IdListEditor, hint_label
from .base import AppContext, Binder, Page

PALETTE = ["#3d8bfd", "#e5484d", "#30a46c", "#f5a524", "#8e4ec6", "#12a594", "#d6409f", "#aaaaaa"]


class SidesPage(Page):
    title = "Sides"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.sid = ""
        self.vid = ""
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        # ------------------------------------------------ side list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._pick)
        ll.addWidget(self.list)
        row = QHBoxLayout()
        for text, fn in (("Add side", self._add), ("Remove", self._remove), ("Up", lambda: self._move(-1)),
                         ("Down", lambda: self._move(1))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        # ------------------------------------------------ side form
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        b = self.b = Binder(self, lambda: self.project.side(self.sid), "sides", self._side_changed)
        g = QGroupBox("Side")
        f = QFormLayout(g)
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        self.tag = b.line(QLineEdit(), "tag")
        self.tag.setPlaceholderText("short tag for file names, e.g. NATO")
        f.addRow("Tag:", self.tag)
        self.color = ColorButton()
        self.color.colorChanged.connect(self._color)
        f.addRow("Map colour:", self.color)
        self.aw = QComboBox()
        for a in AWARENESS:
            self.aw.addItem(a, a)
        b.combo(self.aw, "awareness")
        f.addRow("Awareness:", self.aw)
        self.prof = QComboBox()
        for p in PROFICIENCY:
            self.prof.addItem(p, p)
        b.combo(self.prof, "proficiency")
        f.addRow("Proficiency:", self.prof)
        self.ai = b.check(QCheckBox("Computer-controlled only (never playable)"), "computer_only")
        f.addRow("", self.ai)
        sc = b.spin(QSpinBox(), "start_score")
        sc.setRange(-100000, 100000)
        f.addRow("Starting score:", sc)
        self.brief = b.check(QCheckBox("Export a briefing page for this side"), "export_briefing")
        f.addRow("", self.brief)
        ml.addWidget(g)

        g = QGroupBox("Side doctrine (blank = CMO default)")
        f = QFormLayout(g)
        self.doctrine: dict[str, QComboBox] = {}
        for key, (label, _kind, choices) in DOCTRINE_FIELDS.items():
            cb = QComboBox()
            for c in choices:
                cb.addItem(c or "(default)", c)
            cb.currentIndexChanged.connect(lambda _i, k=key, w=cb: self._doctrine(k, w.currentData()))
            self.doctrine[key] = cb
            f.addRow(label + ":", cb)
        ml.addWidget(g)
        ml.addStretch()
        split.addWidget(mid)

        # ------------------------------------------------ postures + variants
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox("Postures (row side's view of the column side)")
        v = QVBoxLayout(g)
        self.matrix = QTableWidget()
        self.matrix.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.matrix)
        sym = QPushButton("Make symmetric (copy row → column)")
        sym.clicked.connect(self._symmetric)
        v.addWidget(sym, 0, Qt.AlignmentFlag.AlignLeft)
        rl.addWidget(g)

        g = QGroupBox("Build variants (single-player versions)")
        v = QVBoxLayout(g)
        v.addWidget(hint_label("Each variant gets its own launcher Build_<KEY>.lua and, optionally, its own "
                               "description page. Use it for 'Play as X' versions where the other side is "
                               "computer-controlled."))
        row = QHBoxLayout()
        self.vlist = QListWidget()
        self.vlist.setMaximumHeight(110)
        self.vlist.currentItemChanged.connect(self._pick_variant)
        row.addWidget(self.vlist, 1)
        col = QVBoxLayout()
        for text, fn in (("Add", self._add_variant), ("Remove", self._remove_variant)):
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            col.addWidget(btn)
        col.addStretch()
        row.addLayout(col)
        v.addLayout(row)
        vb = self.vb = Binder(self, lambda: next((x for x in self.project.variants if x.id == self.vid), None),
                              "variants", lambda a: self._refresh_variants() if a in ("name", "key") else None)
        f = QFormLayout()
        self.vname = vb.line(QLineEdit(), "name")
        f.addRow("Name:", self.vname)
        self.vkey = vb.line(QLineEdit(), "key")
        self.vkey.setToolTip("Lua identifier; the launcher is Build_<KEY>.lua")
        f.addRow("Key:", self.vkey)
        self.vsuffix = vb.line(QLineEdit(), "scen_suffix", strip=False)
        self.vsuffix.setPlaceholderText(" - Play as NATO")
        f.addRow(".scen suffix:", self.vsuffix)
        v.addLayout(f)
        self.vsides = IdListEditor("Computer-controlled sides")
        self.vsides.set_source(lambda: [(s.name, s.id) for s in self.project.sides])
        self.vsides.idsChanged.connect(self._variant_sides)
        self.vsides.setMaximumHeight(120)
        v.addWidget(self.vsides)
        v.addWidget(hint_label("The variant's description text is edited on the Briefings tab."))
        rl.addWidget(g)
        split.addWidget(right)
        split.setSizes([220, 380, 520])

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        p = self.project
        self.list.blockSignals(True)
        self.list.clear()
        for s in p.sides:
            it = QListWidgetItem(("[AI] " if s.computer_only else "") + s.name)
            it.setData(Qt.ItemDataRole.UserRole, s.id)
            it.setForeground(QColor(s.color))
            self.list.addItem(it)
            if s.id == self.sid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if not p.side(self.sid):
            self.sid = p.sides[0].id if p.sides else ""
            if self.list.count():
                self.list.setCurrentRow(0)
        self._load_side()
        self._refresh_matrix()
        self._refresh_variants()

    def _load_side(self):
        s = self.project.side(self.sid)
        self.b.load()
        if s:
            self.color.set_color(s.color)
            for key, cb in self.doctrine.items():
                cb.blockSignals(True)
                cb.setCurrentIndex(max(0, cb.findData(s.doctrine.get(key, ""))))
                cb.blockSignals(False)

    def _refresh_matrix(self):
        p = self.project
        n = len(p.sides)
        self.matrix.blockSignals(True)
        self.matrix.clear()
        self.matrix.setRowCount(n)
        self.matrix.setColumnCount(n)
        self.matrix.setHorizontalHeaderLabels([s.name for s in p.sides])
        self.matrix.setVerticalHeaderLabels([s.name for s in p.sides])
        for r, a in enumerate(p.sides):
            for c, bside in enumerate(p.sides):
                if a.id == bside.id:
                    w = QComboBox()
                    w.addItem("—")
                    w.setEnabled(False)
                else:
                    w = QComboBox()
                    for k, label in POSTURES.items():
                        w.addItem(label, k)
                    w.setCurrentIndex(max(0, w.findData(a.postures.get(bside.id, "N"))))
                    colors = {"H": "#e5484d", "U": "#f5a524", "N": "#c8ccd4", "F": "#30a46c"}
                    w.setStyleSheet(f"color: {colors.get(w.currentData(), '#ccc')};")
                    w.currentIndexChanged.connect(lambda _i, x=a.id, y=bside.id, cb=w: self._posture(x, y, cb))
                self.matrix.setCellWidget(r, c, w)
        self.matrix.blockSignals(False)

    def _refresh_variants(self):
        p = self.project
        self.vlist.blockSignals(True)
        self.vlist.clear()
        for v in p.variants:
            it = QListWidgetItem(f"{v.name}   [Build_{v.key}.lua]")
            it.setData(Qt.ItemDataRole.UserRole, v.id)
            self.vlist.addItem(it)
            if v.id == self.vid:
                self.vlist.setCurrentItem(it)
        self.vlist.blockSignals(False)
        v = next((x for x in p.variants if x.id == self.vid), None)
        self.vb.load()
        for w in (self.vname, self.vkey, self.vsuffix, self.vsides):
            w.setEnabled(v is not None)
        self.vsides.set_ids(v.computer_sides if v else [], {s.id: s.name for s in p.sides})

    # ------------------------------------------------------------------ side edits
    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.sid = cur.data(Qt.ItemDataRole.UserRole)
            self._load_side()

    def _side_changed(self, attr):
        if attr in ("name", "computer_only"):
            self.refresh()

    def _color(self, c):
        s = self.project.side(self.sid)
        if s:
            with self.edit("Side colour", "sides"):
                s.color = c
            self.refresh()

    def _doctrine(self, key, value):
        s = self.project.side(self.sid)
        if not s or s.doctrine.get(key, "") == (value or ""):
            return
        with self.edit("Side doctrine", "sides"):
            if value:
                s.doctrine[key] = value
            else:
                s.doctrine.pop(key, None)

    def _posture(self, a, b, cb):
        s = self.project.side(a)
        if s:
            with self.edit("Change posture", "sides"):
                s.postures[b] = cb.currentData()
            self._refresh_matrix()

    def _symmetric(self):
        p = self.project
        with self.edit("Symmetric postures", "sides"):
            for i, a in enumerate(p.sides):
                for bside in p.sides[i + 1:]:
                    bside.postures[a.id] = a.postures.get(bside.id, "N")
        self._refresh_matrix()

    def _add(self):
        name, ok = QInputDialog.getText(self, "Add side", "Side name:")
        if not ok or not name.strip():
            return
        if self.project.side_by_name(name.strip()):
            QMessageBox.warning(self, "Add side", "A side with that name exists.")
            return
        color = PALETTE[len(self.project.sides) % len(PALETTE)]
        with self.edit("Add side", "sides"):
            s = self.project.add_side(name.strip(), "", color)
            from ...model.project import DEFAULT_BRIEFING
            s.briefing_html = DEFAULT_BRIEFING
        self.sid = s.id
        self.refresh()

    def _remove(self):
        s = self.project.side(self.sid)
        if not s:
            return
        n = len(self.project.units_of_side(s.id))
        if QMessageBox.question(self, "Remove side", f"Remove '{s.name}' and its {n} unit(s), areas, missions and "
                                                     f"special actions?") != QMessageBox.StandardButton.Yes:
            return
        with self.edit("Remove side", "sides"):
            self.project.remove_side(s.id)
        self.sid = ""
        self.refresh()

    def _move(self, d):
        p = self.project
        i = next((k for k, s in enumerate(p.sides) if s.id == self.sid), -1)
        j = i + d
        if i < 0 or not (0 <= j < len(p.sides)):
            return
        with self.edit("Reorder sides", "sides"):
            p.sides[i], p.sides[j] = p.sides[j], p.sides[i]
        self.refresh()

    # ------------------------------------------------------------------ variants
    def _pick_variant(self, cur, _prev=None):
        if cur is not None:
            self.vid = cur.data(Qt.ItemDataRole.UserRole)
            self._refresh_variants()

    def _add_variant(self):
        p = self.project
        playable = [s for s in p.sides if not s.computer_only]
        target = playable[0] if playable else None
        v = Variant(id=new_id("v"))
        if target:
            v.name = f"Play as {target.name}"
            v.key = "PLAY_" + "".join(ch for ch in target.file_tag().upper() if ch.isalnum())
            v.scen_suffix = f" - Play as {target.name}"
            v.computer_sides = [s.id for s in playable if s.id != target.id]
        with self.edit("Add variant", "variants"):
            p.variants.append(v)
        self.vid = v.id
        self._refresh_variants()

    def _remove_variant(self):
        with self.edit("Remove variant", "variants"):
            self.project.variants = [v for v in self.project.variants if v.id != self.vid]
        self.vid = ""
        self._refresh_variants()

    def _variant_sides(self, ids):
        v = next((x for x in self.project.variants if x.id == self.vid), None)
        if v:
            with self.edit("Variant sides", "variants"):
                v.computer_sides = ids
            self._refresh_variants()
