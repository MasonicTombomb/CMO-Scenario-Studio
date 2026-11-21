"""Unit templates: browse and place pre-grouped sites, edit the library, save units as a template."""

from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QUrl
from PyQt6.QtGui import QBrush, QColor, QDesktopServices, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..model.templates import (TemplateComponent, TemplateLibrary, UnitTemplate, default_library, load_library,
                               place_template, place_templates, resolve, template_from_units)
from ..geo import format_latlon, parse_latlon
from .widgets import CoordEdit, IdCombo, hint_label


def library_path(ctx) -> Path:
    return ctx.settings.data_dir() / "templates.json"


def current_library(ctx) -> tuple[TemplateLibrary, str]:
    return load_library(library_path(ctx))


def _runway_length(name: str) -> float:
    m = re.search(r"(\d{3,4})m\)", name)
    return float(m.group(1)) if m and "Runway" in name and "Access" not in name else 0.0


class TemplatePreview(QWidget):
    """Plan view of a template: components at their offsets, rotated by the orientation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.tpl: Optional[UnitTemplate] = None
        self.heading = 0.0

    def show_template(self, tpl: Optional[UnitTemplate], heading: float = 0.0) -> None:
        self.tpl, self.heading = tpl, heading
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#141a22"))
        if not self.tpl or not self.tpl.components:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No template")
            return
        h = math.radians(self.heading)

        def rot(x, y):
            return x * math.cos(h) + y * math.sin(h), -x * math.sin(h) + y * math.cos(h)

        def ends(comp, x, y, rl):
            a = math.radians(comp.hdg)
            dx, dy = math.sin(a) * rl / 2, math.cos(a) * rl / 2
            return rot(x + dx, y + dy), rot(x - dx, y - dy)

        pts = []
        for comp in self.tpl.components:
            rl = comp.length or _runway_length(comp.db_name)
            for x, y in comp.positions:
                pts.append(rot(x, y))
                if rl:
                    pts += list(ends(comp, x, y, rl))
        extent = max([abs(a) for a, _ in pts] + [abs(b) for _, b in pts] + [100.0])
        margin = 30
        scale = (min(self.width(), self.height()) / 2 - margin) / (extent * 1.05)
        cx, cy = self.width() / 2, self.height() / 2

        def px(e, n):
            return QPointF(cx + e * scale, cy - n * scale)

        p.setPen(QPen(QColor(90, 120, 150, 70), 1, Qt.PenStyle.DashLine))
        step = next((s for s in (50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000)
                     if extent / s <= 5), 100000)
        r = step
        while r <= extent * 1.05:
            p.drawEllipse(QPointF(cx, cy), r * scale, r * scale)
            r += step
        p.setPen(QColor("#8a8f99"))
        p.drawText(QRectF(cx - 20, 2, 40, 16), Qt.AlignmentFlag.AlignCenter, "N")
        tip = QPointF(cx + math.sin(h) * 40, cy - math.cos(h) * 40)
        p.setPen(QPen(QColor(255, 209, 102, 180), 2))
        p.drawLine(QPointF(cx, cy), tip)
        font = QFont(p.font())
        font.setPointSize(7)
        p.setFont(font)
        colors = ["#3d8bfd", "#30a46c", "#f5a524", "#e5484d", "#8e4ec6", "#12a594", "#d6409f", "#c8ccd4"]
        for k, comp in enumerate(self.tpl.components):
            col = QColor(colors[k % len(colors)])
            rl = comp.length or _runway_length(comp.db_name)
            for i, (x, y) in enumerate(comp.positions):
                e, n = rot(x, y)
                q = px(e, n)
                if rl:
                    a, b = (px(*v) for v in ends(comp, x, y, rl))
                    p.setPen(QPen(QColor("#c8ccd4"), max(3.0, 45 * scale)))
                    p.drawLine(a, b)
                    if comp.length:
                        p.setPen(QColor("#e6e8ec"))
                        p.drawText(QPointF(b.x() + 4, b.y() + 4), comp.label.replace("Runway ", ""))
                    continue
                p.setPen(QPen(QColor("#0b0b0b"), 1))
                p.setBrush(QBrush(col))
                if comp.host:
                    p.drawRect(QRectF(q.x() - 5, q.y() - 5, 10, 10))
                elif comp.hold:
                    p.drawPolygon(QPolygonF([QPointF(q.x(), q.y() - 6), QPointF(q.x() + 6, q.y()),
                                             QPointF(q.x(), q.y() + 6), QPointF(q.x() - 6, q.y())]))
                else:
                    p.drawEllipse(q, 4.5, 4.5)
                if i == 0:
                    p.setPen(col.lighter(140))
                    p.drawText(QPointF(q.x() + 7, q.y() + 4), comp.label)
        p.setPen(QColor("#8a8f99"))
        p.drawText(QRectF(6, self.height() - 18, self.width() - 12, 16), Qt.AlignmentFlag.AlignLeft,
                   f"rings every {step:,} m  ·  {self.tpl.unit_count} units  ·  squares host aircraft/boats, "
                   f"diamonds are mobile units")
        p.end()


# =============================================================================== browse + place
class TemplatePlacerDialog(QDialog):
    def __init__(self, ctx, lat: Optional[float] = None, lon: Optional[float] = None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Place a unit template")
        self.resize(1350, 760)
        self.lib, self.source = current_library(ctx)
        self.placed_ids: list[str] = []
        self.placed_sites = 0
        self.ticked: list[str] = []        # template ids ticked for placing together, in the order ticked
        self._filling = False
        w = ctx.window
        if lat is None or lon is None:
            lat, lon = (w.map_page.map.center() if w is not None and hasattr(w, "map_page") else (0.0, 0.0))
        self.lat, self.lon = lat, lon
        self.free_pos = (lat, lon)         # where a template without a real location goes
        self._last_site_default = ""
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search templates (e.g. airfield, bunker, port)...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._fill)
        ll.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Template", "Units"])
        self.tree.setSortingEnabled(False)
        self.tree.setColumnWidth(0, 300)
        self.tree.currentItemChanged.connect(self._pick)
        self.tree.itemChanged.connect(self._tick_changed)
        self.tree.itemDoubleClicked.connect(lambda it, _c: it.data(0, Qt.ItemDataRole.UserRole) and
                                            self._place(only_current=True))
        ll.addWidget(self.tree)
        trow = QHBoxLayout()
        self.ticked_label = hint_label("Tick several templates (or a whole category) to place them all at once.")
        trow.addWidget(self.ticked_label, 1)
        self.untick_btn = QPushButton("Untick all")
        self.untick_btn.clicked.connect(self._untick_all)
        trow.addWidget(self.untick_btn)
        ll.addLayout(trow)
        lib_btn = QPushButton("Edit template library...")
        lib_btn.clicked.connect(self._edit_library)
        ll.addWidget(lib_btn)
        ll.addWidget(hint_label(f"Library: {self.source}"))
        split.addWidget(left)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("")
        self.title.setProperty("heading", True)
        self.title.setWordWrap(True)
        ml.addWidget(self.title)
        self.desc = hint_label("")
        ml.addWidget(self.desc)
        self.parts = QTableWidget(0, 4)
        self.parts.setHorizontalHeaderLabels(["Component", "Count", "Database entry", "DBID"])
        self.parts.verticalHeader().setVisible(False)
        self.parts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.parts.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        ml.addWidget(self.parts, 1)
        g = QFormLayout()
        self.site = QLineEdit()
        self.site.setPlaceholderText("e.g. Amari - units become 'Amari Control Tower'...")
        g.addRow("Site name:", self.site)
        self.side = IdCombo()
        self.side.set_items([(s.name, s.id) for s in ctx.project.sides])
        if w is not None and hasattr(w, "map_page"):
            self.side.set_current_id(w.map_page.current_side())
        g.addRow("Side:", self.side)
        self.real = QCheckBox("At the real site")
        self.real.setToolTip("Real-world templates: place them at their actual position and orientation")
        self.real.toggled.connect(self._real_toggled)
        self.coords = CoordEdit()
        self.coords.set_coords(lat, lon)
        self.coords.coordsEdited.connect(self._coords)
        prow = QHBoxLayout()
        prow.addWidget(self.coords, 1)
        prow.addWidget(self.real)
        g.addRow("Position:", prow)
        self.heading = QDoubleSpinBox()
        self.heading.setRange(0, 359.9)
        self.heading.setWrapping(True)
        self.heading.setSuffix("°")
        self.heading.setToolTip("Orientation of the site; runways lie along it")
        self.heading.valueChanged.connect(lambda v: self.preview.show_template(self._tpl(), v))
        g.addRow("Orientation / runway heading:", self.heading)
        self.group = QCheckBox("Group the site in CMO and keep it together on the map")
        self.group.setChecked(True)
        g.addRow("", self.group)
        ml.addLayout(g)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.place_btn = bb.addButton("Place", QDialogButtonBox.ButtonRole.AcceptRole)
        self.place_btn.setProperty("primary", True)
        bb.accepted.connect(self._place)
        bb.rejected.connect(self.reject)
        ml.addWidget(bb)
        split.addWidget(mid)

        self.preview = TemplatePreview()
        split.addWidget(self.preview)
        split.setSizes([380, 520, 450])
        self._fill()

    def _tpl(self) -> Optional[UnitTemplate]:
        it = self.tree.currentItem()
        tid = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        return self.lib.template(tid) if tid else None

    def _fill(self, *_):
        words = self.filter.text().lower().split()
        cur = self._tpl().id if self._tpl() else ""
        self._filling = True
        self.tree.clear()
        for cat in self.lib.all_categories():
            items = [t for t in self.lib.templates if t.category == cat and
                     all(w in f"{t.name} {t.site} {t.description} {' '.join(t.tags)} {cat}".lower() for w in words)]
            if not items:
                continue
            head = QTreeWidgetItem([cat, str(len(items))])
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            head.setFlags(head.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            head.setToolTip(0, "Tick to place every template shown in this category")
            self.tree.addTopLevelItem(head)
            for t in items:
                it = QTreeWidgetItem([t.name, str(t.unit_count)])
                it.setData(0, Qt.ItemDataRole.UserRole, t.id)
                it.setToolTip(0, t.description)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Checked if t.id in self.ticked else Qt.CheckState.Unchecked)
                head.addChild(it)
                if t.id == cur:
                    self.tree.setCurrentItem(it)
            head.setExpanded(True)
        if words:   # prefer a template whose name matches the search over one that only mentions it
            for i in range(self.tree.topLevelItemCount()):
                head = self.tree.topLevelItem(i)
                hit = next((head.child(k) for k in range(head.childCount())
                            if all(w in head.child(k).text(0).lower() for w in words)), None)
                if hit is not None:
                    self.tree.setCurrentItem(hit)
                    break
        if self.tree.currentItem() is None or not self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole):
            first = self.tree.topLevelItem(0)
            if first and first.childCount():
                self.tree.setCurrentItem(first.child(0))
        self._filling = False
        self._pick()

    # ------------------------------------------------------------------ ticking several
    def _tick_changed(self, item: QTreeWidgetItem, column: int) -> None:
        tid = item.data(0, Qt.ItemDataRole.UserRole)
        if self._filling or column != 0 or not tid:
            return
        on = item.checkState(0) == Qt.CheckState.Checked
        if on and tid not in self.ticked:
            self.ticked.append(tid)
        elif not on and tid in self.ticked:
            self.ticked.remove(tid)
        self._pick()

    def _untick_all(self) -> None:
        self.ticked.clear()
        self._fill()
        self._pick()

    def to_place(self) -> list[UnitTemplate]:
        """The ticked templates, or the highlighted one when none is ticked."""
        tpls = [t for t in (self.lib.template(i) for i in self.ticked) if t is not None]
        if tpls:
            return tpls
        t = self._tpl()
        return [t] if t is not None else []

    def _multi(self) -> bool:
        """Several templates will be placed (anything but the highlighted one on its own)."""
        t = self._tpl()
        return len(self.ticked) > 1 or (len(self.ticked) == 1 and (t is None or t.id != self.ticked[0]))

    def _update_multi(self) -> None:
        tpls = self.to_place()
        multi = self._multi()
        self.place_btn.setEnabled(bool(tpls))
        self.place_btn.setText(f"Place {len(tpls)} templates" if len(tpls) > 1 else "Place")
        self.site.setEnabled(not multi)
        self.site.setToolTip("Each ticked template keeps its own site name." if multi else "")
        self.untick_btn.setEnabled(bool(self.ticked))
        if not self.ticked:
            self.ticked_label.setText("Tick several templates (or a whole category) to place them all at once.")
            return
        names = ", ".join(t.name for t in tpls[:6]) + (f" and {len(tpls) - 6} more" if len(tpls) > 6 else "")
        real = sum(1 for t in tpls if t.location)
        where = ""
        if multi:
            if real and self.real.isChecked():
                where = (" Real sites go to their own positions" + ("; the others in a row east of the position."
                                                                     if real < len(tpls) else "."))
            else:
                where = " They go in a row east of the position, spaced so they do not overlap."
        self.ticked_label.setText(f"<b>{len(tpls)} ticked</b> ({sum(t.unit_count for t in tpls)} units): {names}."
                                  + where)

    def _pick(self, *_):
        if self._filling:
            return
        t = self._tpl()
        multi = self._multi()
        # 'At the real site': for one template, its own; for several, whether any of them has a real site
        has_real = any(x.location for x in self.to_place()) if multi else bool(t and t.location)
        self.real.blockSignals(True)
        self.real.setEnabled(has_real)
        self.real.setChecked(has_real)
        self.real.blockSignals(False)
        self._sync_position()
        self._update_multi()
        if t is None:
            return
        self.title.setText(f"{t.name}  ({t.unit_count} units)")
        self.desc.setText(t.description + (f"\nReal site: {format_latlon(*t.location)}, layout drawn at "
                                           f"{t.heading:g}°." if t.location else ""))
        if not self.site.isModified() or self.site.text() == self._last_site_default:
            self._last_site_default = t.site or t.name
            self.site.setText(self._last_site_default)
            self.site.setModified(False)
        db = self.ctx.db
        self.parts.setRowCount(0)
        for comp in t.components:
            r = self.parts.rowCount()
            self.parts.insertRow(r)
            res = resolve(db, comp)
            ok = res is not None
            vals = [comp.label + ("  [host]" if comp.host else ""), str(len(comp.positions)),
                    (res.name if ok else f"NOT FOUND: {comp.db_name}") +
                    ("" if not ok or res.how in ("dbid", "unchecked") else f"  (matched by {res.how})"),
                    str(res.dbid) if ok else "-"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if not ok:
                    it.setForeground(QColor("#e5484d"))
                self.parts.setItem(r, c, it)
        self.parts.resizeColumnsToContents()
        self.preview.show_template(t, self.heading.value())

    def _coords(self, lat, lon):
        self.lat, self.lon = lat, lon
        if not self.real.isChecked() or self._multi():
            self.free_pos = (lat, lon)

    def _sync_position(self) -> None:
        """The position box: the real site of one real-world template, else where the others go."""
        t = self._tpl()
        fixed = not self._multi() and self.real.isChecked() and t is not None and bool(t.location)
        if fixed:
            self.lat, self.lon = t.location
            self.heading.setValue(t.heading)
        else:
            self.lat, self.lon = self.free_pos
        self.coords.set_coords(self.lat, self.lon)
        self.coords.setEnabled(not fixed)

    def _real_toggled(self, _on: bool):
        self._sync_position()
        if not self._filling:
            self._update_multi()

    def _place(self, only_current: bool = False):
        if not only_current and self._multi():
            self._place_many()
            return
        t = self._tpl() if only_current or not self.ticked else self.lib.template(self.ticked[0])
        sid = self.side.current_id()
        if t is None or not sid:
            return
        with self.ctx.doc.modify(f"Place {t.name}", "units"):
            res = place_template(self.ctx.project, t, self.ctx.db, sid, self.lat, self.lon,
                                 heading=self.heading.value(), site_name=self.site.text().strip() or t.name,
                                 group=self.group.isChecked())
        self.placed_ids = [u.id for u in res.units]
        self.placed_sites = 1
        msg = f"Placed {len(res.units)} unit(s) of '{t.name}'."
        if res.skipped:
            msg += f" Skipped (not in this database): {', '.join(res.skipped)}"
            QMessageBox.information(self, "Template placed", msg)
        self.ctx.status(msg)
        if res.units:
            self.ctx.doc.select(res.units[0].id)
        self.accept()

    def _place_many(self):
        tpls = self.to_place()
        sid = self.side.current_id()
        if not tpls or not sid:
            return
        with self.ctx.doc.modify(f"Place {len(tpls)} templates", "units"):
            results = place_templates(self.ctx.project, tpls, self.ctx.db, sid, *self.free_pos,
                                      heading=self.heading.value(), real_sites=self.real.isChecked(),
                                      group=self.group.isChecked())
        self.placed_ids = [u.id for _t, res in results for u in res.units]
        self.placed_sites = len(results)
        msg = f"Placed {len(results)} templates, {len(self.placed_ids)} unit(s): " + \
            ", ".join(t.name for t, _r in results) + "."
        skipped = [f"{t.name}: {', '.join(res.skipped)}" for t, res in results if res.skipped]
        if skipped:
            QMessageBox.information(self, "Templates placed",
                                    msg + "\n\nSkipped (not in this database):\n" + "\n".join(skipped))
        self.ctx.status(msg)
        if self.placed_ids:
            self.ctx.doc.select(self.placed_ids[0])
        self.accept()

    def _edit_library(self):
        TemplateLibraryDialog(self.ctx, self).exec()
        self.lib, self.source = current_library(self.ctx)
        self._fill()


# =============================================================================== library editor
COMP_COLS = ["Label", "Type", "Database name", "DBID", "Positions (x,y m; ...)", "Host", "Radar", "Hold", "Search",
             "Heading"]


class TemplateLibraryDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Template library")
        self.resize(1450, 800)
        self.path = library_path(ctx)
        self.lib = current_library(ctx)[0].clone()
        self.tid = ""
        self.dirty = False
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.file_label = QLabel("")
        self.file_label.setProperty("hint", True)
        top.addWidget(self.file_label, 1)
        for text, fn in (("Import...", self._import), ("Export...", self._export), ("Show file", self._show_file),
                         ("Reset to defaults", self._reset)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter templates...")
        self.filter.textChanged.connect(lambda *_: self._fill())
        ll.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Template"])
        self.tree.currentItemChanged.connect(self._pick)
        ll.addWidget(self.tree)
        row = QHBoxLayout()
        for text, fn in (("New", self._new), ("Duplicate", self._dup), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout()
        self.name = QLineEdit()
        self.name.editingFinished.connect(self._fields)
        f.addRow("Name:", self.name)
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.lineEdit().editingFinished.connect(self._fields)
        self.category.activated.connect(lambda *_: self._fields())
        f.addRow("Category:", self.category)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("comma separated search tags")
        self.tags.editingFinished.connect(self._fields)
        f.addRow("Tags:", self.tags)
        self.description = QPlainTextEdit()
        self.description.setMaximumHeight(60)
        self.description.textChanged.connect(self._fields)
        f.addRow("Description:", self.description)
        self.location = QLineEdit()
        self.location.setPlaceholderText("optional: lat, lon of a real site (decimal or DMS); empty = place anywhere")
        self.location.editingFinished.connect(self._location_edited)
        f.addRow("Real location:", self.location)
        rl.addLayout(f)
        row = QHBoxLayout()
        for text, fn in (("Add component", self._add_comp), ("Remove", self._remove_comp),
                         ("Use Database panel entry", self._use_db), ("Up", lambda: self._move_comp(-1)),
                         ("Down", lambda: self._move_comp(1))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        rl.addLayout(row)
        mid = QSplitter(Qt.Orientation.Horizontal)
        self.comps = QTableWidget(0, len(COMP_COLS))
        self.comps.setHorizontalHeaderLabels(COMP_COLS)
        self.comps.verticalHeader().setVisible(False)
        self.comps.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.comps.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.comps.itemChanged.connect(self._comp_edited)
        mid.addWidget(self.comps)
        self.preview = TemplatePreview()
        mid.addWidget(self.preview)
        mid.setSizes([850, 380])
        rl.addWidget(mid, 1)
        rl.addWidget(hint_label("Positions are metres: x to the right of the site's orientation, y ahead of it; "
                                "separate several copies with ';' (e.g. '650,700; 650,820'). 'Use Database panel "
                                "entry' fills type, name and DBID from the entry selected in the Database panel. "
                                "Host marks units that can hold aircraft or boats."))
        split.addWidget(right)
        split.setSizes([330, 1100])
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        save = bb.addButton("Save", QDialogButtonBox.ButtonRole.ApplyRole)
        save.setProperty("primary", True)
        save.clicked.connect(self.save)
        bb.rejected.connect(self.close)
        lay.addWidget(bb)
        self._fill()
        self._label()

    # ------------------------------------------------------------------ helpers
    def _t(self) -> Optional[UnitTemplate]:
        return self.lib.template(self.tid)

    def _touch(self):
        self.dirty = True
        self._label()

    def _label(self):
        where = str(self.path) if self.path.is_file() else f"{self.path} (not created yet - Save writes it)"
        self.file_label.setText(f"Your template file: {where}{'  ·  unsaved changes' if self.dirty else ''}\n"
                                f"{len(self.lib.templates)} templates · "
                                f"{sum(t.unit_count for t in self.lib.templates)} units in all")

    def _fill(self):
        words = self.filter.text().lower().split()
        self.tree.blockSignals(True)
        self.tree.clear()
        for cat in self.lib.all_categories():
            items = [t for t in self.lib.templates if t.category == cat and
                     all(w in f"{t.name} {' '.join(t.tags)} {cat}".lower() for w in words)]
            if not items:
                continue
            head = QTreeWidgetItem([cat])
            self.tree.addTopLevelItem(head)
            for t in items:
                it = QTreeWidgetItem([t.name])
                it.setData(0, Qt.ItemDataRole.UserRole, t.id)
                head.addChild(it)
                if t.id == self.tid:
                    self.tree.setCurrentItem(it)
            head.setExpanded(True)
        self.tree.blockSignals(False)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItems(self.lib.all_categories())
        self.category.blockSignals(False)
        if not self._t() and self.lib.templates:
            self.tid = self.lib.templates[0].id
        self._load()

    def _pick(self, cur, _prev=None):
        tid = cur.data(0, Qt.ItemDataRole.UserRole) if cur else None
        if tid:
            self.tid = tid
            self._load()

    def _load(self):
        t = self._t()
        for w in (self.name, self.category, self.tags, self.description, self.comps, self.location):
            w.setEnabled(t is not None)
        if t is None:
            return
        loc = f"{t.location[0]:.6f}, {t.location[1]:.6f}" if t.location else ""
        for w, v in ((self.name, t.name), (self.tags, ", ".join(t.tags)), (self.location, loc)):
            w.blockSignals(True)
            w.setText(v)
            w.blockSignals(False)
        self.category.blockSignals(True)
        self.category.setCurrentText(t.category)
        self.category.blockSignals(False)
        self.description.blockSignals(True)
        self.description.setPlainText(t.description)
        self.description.blockSignals(False)
        self._fill_comps()

    def _fill_comps(self):
        t = self._t()
        self.comps.blockSignals(True)
        self.comps.setRowCount(0)
        for comp in (t.components if t else []):
            r = self.comps.rowCount()
            self.comps.insertRow(r)
            pos = "; ".join(f"{x:g},{y:g}" for x, y in comp.positions)
            vals = [comp.label, comp.db_type, comp.db_name, str(comp.dbid or ""), pos]
            for c, v in enumerate(vals):
                self.comps.setItem(r, c, QTableWidgetItem(v))
            for c, flag in ((5, comp.host), (6, comp.radar), (7, comp.hold)):
                it = QTableWidgetItem("")
                it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                it.setCheckState(Qt.CheckState.Checked if flag else Qt.CheckState.Unchecked)
                self.comps.setItem(r, c, it)
            self.comps.setItem(r, 8, QTableWidgetItem(comp.search))
            self.comps.setItem(r, 9, QTableWidgetItem(f"{comp.hdg:g}" if comp.hdg else ""))
        self.comps.blockSignals(False)
        self.comps.resizeColumnsToContents()
        self.preview.show_template(t)

    def _fields(self, *_):
        t = self._t()
        if not t:
            return
        new = (self.name.text().strip() or t.name, self.category.currentText().strip() or "Custom",
               [x.strip() for x in self.tags.text().split(",") if x.strip()], self.description.toPlainText())
        if new != (t.name, t.category, t.tags, t.description):
            regroup = new[1] != t.category or new[0] != t.name
            t.name, t.category, t.tags, t.description = new
            self._touch()
            if regroup:
                self._fill()

    def _location_edited(self):
        t = self._t()
        if not t:
            return
        text = self.location.text().strip()
        loc = parse_latlon(text) if text else None
        new_loc = [round(loc[0], 6), round(loc[1], 6)] if loc else None
        if text and loc is None:
            QMessageBox.warning(self, "Real location", "Write the location as 'lat, lon' (decimal or DMS).")
        elif new_loc != (t.location and [round(t.location[0], 6), round(t.location[1], 6)]):
            t.location = new_loc
            self._touch()

    def _comp_edited(self, item: QTableWidgetItem):
        t = self._t()
        r, c = item.row(), item.column()
        if not t or r >= len(t.components):
            return
        comp = t.components[r]
        text = item.text().strip()
        if c == 0:
            comp.label = text or comp.label
        elif c == 1:
            comp.db_type = text or "Facility"
        elif c == 2:
            comp.db_name = text
        elif c == 3:
            comp.dbid = int(text) if text.isdigit() else 0
        elif c == 4:
            pts = []
            for part in text.split(";"):
                nums = re.findall(r"-?\d+(?:\.\d+)?", part)
                if len(nums) >= 2:
                    pts.append([float(nums[0]), float(nums[1])])
            if pts:
                comp.positions = pts
            else:
                QMessageBox.warning(self, "Positions", "Write positions as 'x,y' in metres, several separated "
                                                       "by ';'.")
        elif c in (5, 6, 7):
            setattr(comp, {5: "host", 6: "radar", 7: "hold"}[c], item.checkState() == Qt.CheckState.Checked)
        elif c == 8:
            comp.search = text
        elif c == 9:
            try:
                comp.hdg = float(text or 0) % 360.0
            except ValueError:
                QMessageBox.warning(self, "Heading", "Heading is degrees relative to the site orientation.")
        self._touch()
        self.preview.show_template(t)

    def _add_comp(self):
        t = self._t()
        if t:
            t.components.append(TemplateComponent(label="New component", db_name="Building (Small)", dbid=113))
            self._fill_comps()
            self._touch()

    def _remove_comp(self):
        t = self._t()
        rows = sorted({i.row() for i in self.comps.selectedIndexes()}, reverse=True)
        if t and rows:
            for r in rows:
                if r < len(t.components):
                    t.components.pop(r)
            self._fill_comps()
            self._touch()

    def _move_comp(self, d: int):
        t = self._t()
        r = self.comps.currentRow()
        if t and 0 <= r < len(t.components) and 0 <= r + d < len(t.components):
            t.components[r], t.components[r + d] = t.components[r + d], t.components[r]
            self._fill_comps()
            self.comps.selectRow(r + d)
            self._touch()

    def _use_db(self):
        t = self._t()
        w = self.ctx.window
        e = w.db_browser.current if w is not None else None
        r = self.comps.currentRow()
        if not t or e is None or not (0 <= r < len(t.components)):
            QMessageBox.information(self, "Database entry", "Select a component row here and an entry in the "
                                                            "Database panel first.")
            return
        comp = t.components[r]
        comp.db_type, comp.db_name, comp.dbid = e.type, e.name, e.id
        self._fill_comps()
        self.comps.selectRow(r)
        self._touch()

    # ------------------------------------------------------------------ templates
    def _new(self):
        name, ok = QInputDialog.getText(self, "New template", "Template name:")
        if ok and name.strip():
            t = UnitTemplate(id=self.lib.unique_id(name), name=name.strip(), category="Custom",
                             components=[TemplateComponent(label="Building", db_name="Building (Small)", dbid=113)])
            self.lib.templates.append(t)
            self.tid = t.id
            self._fill()
            self._touch()

    def _dup(self):
        t = self._t()
        if t:
            d = copy.deepcopy(t)
            d.name += " (copy)"
            d.id = self.lib.unique_id(d.name)
            self.lib.templates.insert(self.lib.templates.index(t) + 1, d)
            self.tid = d.id
            self._fill()
            self._touch()

    def _delete(self):
        t = self._t()
        if t and QMessageBox.question(self, "Delete", f"Delete template '{t.name}'?") == \
                QMessageBox.StandardButton.Yes:
            self.lib.templates.remove(t)
            self.tid = ""
            self._fill()
            self._touch()

    # ------------------------------------------------------------------ files
    def save(self) -> bool:
        try:
            self.lib.save(self.path)
        except OSError as exc:
            QMessageBox.critical(self, "Save", str(exc))
            return False
        self.dirty = False
        self._label()
        self.ctx.status(f"Template library saved to {self.path}")
        return True

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import template library", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            self.lib = TemplateLibrary.load(path)
        except (ValueError, OSError) as exc:
            QMessageBox.critical(self, "Import", f"Not a valid template library:\n{exc}")
            return
        self.tid = ""
        self._fill()
        self._touch()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export template library", str(Path.home() / "templates.json"),
                                              "JSON (*.json)")
        if path:
            self.lib.save(path)

    def _show_file(self):
        if not self.path.is_file():
            if QMessageBox.question(self, "Show file", "Your template file does not exist yet. Save it now so you "
                                                       "can edit it by hand?") != QMessageBox.StandardButton.Yes:
                return
            if not self.save():
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.parent)))

    def _reset(self):
        if QMessageBox.question(self, "Reset", "Replace the library with the built-in templates? (Save to keep "
                                               "the change.)") == QMessageBox.StandardButton.Yes:
            self.lib = default_library()
            self.tid = ""
            self._fill()
            self._touch()

    def closeEvent(self, e):
        if self.dirty:
            r = QMessageBox.question(self, "Template library", "Save changes to your template library?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                     QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel or (r == QMessageBox.StandardButton.Save and not self.save()):
                e.ignore()
                return
        super().closeEvent(e)

    def reject(self):
        self.close()


def save_units_as_template(ctx, unit_ids: list[str], parent=None) -> Optional[UnitTemplate]:
    """Ask for a name and category, then add a template made from the units to the user's library."""
    if not unit_ids:
        return None
    lib = current_library(ctx)[0].clone()
    name, ok = QInputDialog.getText(parent, "Save as template", "Template name:")
    if not ok or not name.strip():
        return None
    cats = lib.all_categories()
    cat, ok = QInputDialog.getItem(parent, "Save as template", "Category (or type a new one):",
                                   ["Custom"] + [c for c in cats if c != "Custom"], 0, True)
    if not ok:
        return None
    try:
        tpl = template_from_units(ctx.project, unit_ids, name.strip(), cat.strip() or "Custom", lib=lib)
    except ValueError as exc:
        QMessageBox.warning(parent, "Save as template", str(exc))
        return None
    lib.templates.append(tpl)
    lib.save(library_path(ctx))
    ctx.status(f"Template '{tpl.name}' ({tpl.unit_count} units) saved to {library_path(ctx)}")
    return tpl
