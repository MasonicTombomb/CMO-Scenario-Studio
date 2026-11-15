"""Area library: browse predefined sea and air patrol areas by region, add them to the scenario (optionally with
a mission), edit the library, and save scenario areas into it."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QItemSelectionModel, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from ..geo import format_latlon
from ..model.area_library import (KIND_COLORS, KIND_LABELS, KINDS, AreaEntry, AreaLibrary, add_area, area_from_zone,
                                  default_library, load_library, mission_label, suggested_mission, zone_name)
from ..model.project import Project, Zone
from .map.map_widget import MapWidget
from .map.tiles import TileCache
from .widgets import IdCombo, hint_label

AREA_ROLE = Qt.ItemDataRole.UserRole
MISSION_CHOICES: list[tuple[str, Optional[tuple[str, str]]]] = [
    ("Suggested for each area", None),
    ("Patrol - AAW (CAP)", ("patrol", "aaw")),
    ("Patrol - ASW", ("patrol", "asw")),
    ("Patrol - ASuW (naval)", ("patrol", "naval")),
    ("Patrol - land", ("patrol", "land")),
    ("Patrol - mixed", ("patrol", "mixed")),
    ("Patrol - SEAD", ("patrol", "sead")),
    ("Support (AEW / tanker orbit)", ("support", "")),
]


def library_path(ctx) -> Path:
    return ctx.settings.data_dir() / "areas.json"


def current_library(ctx) -> tuple[AreaLibrary, str]:
    return load_library(library_path(ctx))


def _tiles(ctx, owner) -> TileCache:
    w = ctx.window
    if w is not None and hasattr(w, "map_page"):
        return w.map_page.tiles
    return TileCache(ctx.settings.cache_dir() / "tiles", owner)


def _size_text(a: AreaEntry) -> str:
    ew, ns = a.extent_nm()
    return f"{ew:.0f} x {ns:.0f} nm"


class AreaPreview(MapWidget):
    """The slippy map showing library areas (sea blue, air orange); the chosen one is highlighted."""

    def __init__(self, tiles: TileCache, parent=None):
        super().__init__(tiles, parent)
        self.setMinimumSize(380, 300)
        self.set_project(Project())
        self.zoom = 3
        self._fit_pts: list[tuple[float, float]] = []

    def showEvent(self, e):
        super().showEvent(e)
        if self._fit_pts:     # fit again once the widget has its real size
            QTimer.singleShot(0, lambda: self.fit(self._fit_pts))

    def show_areas(self, areas: list[AreaEntry], selected: str = "", fit: Optional[list[AreaEntry]] = None) -> None:
        self.project.zones = [Zone(id=a.id, name=a.name, points=[list(p) for p in a.points],
                                   color=KIND_COLORS.get(a.kind, "#cccccc")) for a in areas if a.points]
        self.selected = selected
        if fit:
            self._fit_pts = [(p[0], p[1]) for a in fit for p in a.points]
            self.fit(self._fit_pts)
        self.update()


def _fill_tree(tree: QTreeWidget, areas: list[AreaEntry], regions: list[str], keep: set[str],
               columns: int = 2) -> None:
    """Region > Sea / Air > areas."""
    tree.blockSignals(True)
    tree.clear()
    for reg in regions:
        in_reg = [a for a in areas if a.region == reg]
        if not in_reg:
            continue
        head = QTreeWidgetItem([reg, str(len(in_reg))][:columns])
        f = head.font(0)
        f.setBold(True)
        head.setFont(0, f)
        tree.addTopLevelItem(head)
        for kind in KINDS:
            items = [a for a in in_reg if a.kind == kind]
            if not items:
                continue
            kh = QTreeWidgetItem([f"{KIND_LABELS[kind]} areas", str(len(items))][:columns])
            kh.setForeground(0, QColor(KIND_COLORS[kind]))
            head.addChild(kh)
            for a in sorted(items, key=lambda x: (x.subregion, x.name)):
                it = QTreeWidgetItem([a.name, _size_text(a)][:columns])
                it.setData(0, AREA_ROLE, a.id)
                it.setToolTip(0, f"{a.subregion}\n{a.description}".strip())
                kh.addChild(it)
                if a.id in keep:
                    it.setSelected(True)
                    tree.setCurrentItem(it, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
            kh.setExpanded(True)
        head.setExpanded(True)
    tree.blockSignals(False)


def _find_item(tree: QTreeWidget, aid: str) -> Optional[QTreeWidgetItem]:
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        if it.data(0, AREA_ROLE) == aid:
            return it
        stack.extend(it.child(k) for k in range(it.childCount()))
    return None


# =============================================================================== browse and add
class AreaBrowserDialog(QDialog):
    def __init__(self, ctx, parent=None, select: str = ""):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Area library - predefined patrol areas")
        self.resize(1450, 820)
        self.lib, self.source = current_library(ctx)
        self.added_zone_ids: list[str] = []
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search areas (e.g. Biscay, GIUK, Hormuz, CAP, tanker)...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._fill)
        ll.addWidget(self.filter)
        row = QHBoxLayout()
        self.region = QComboBox()
        self.region.addItem("All regions", "")
        for r in self.lib.all_regions():
            self.region.addItem(r, r)
        self.region.currentIndexChanged.connect(self._fill)
        self.kind = QComboBox()
        self.kind.addItem("Sea and air", "")
        for k in KINDS:
            self.kind.addItem(f"{KIND_LABELS[k]} only", k)
        self.kind.currentIndexChanged.connect(self._fill)
        row.addWidget(self.region, 1)
        row.addWidget(self.kind, 1)
        ll.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Area", "Size"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemSelectionChanged.connect(self._pick)
        self.tree.itemDoubleClicked.connect(lambda it, _c: it.data(0, AREA_ROLE) and self._add())
        ll.addWidget(self.tree, 1)
        self.count = hint_label("")
        ll.addWidget(self.count)
        edit = QPushButton("Edit area library...")
        edit.clicked.connect(self._edit_library)
        ll.addWidget(edit)
        ll.addWidget(hint_label(f"Library: {self.source}"))
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.preview = AreaPreview(_tiles(ctx, self))
        self.preview.objectClicked.connect(self._map_clicked)
        rl.addWidget(self.preview, 1)
        self.title = QLabel("")
        self.title.setProperty("heading", True)
        self.title.setWordWrap(True)
        rl.addWidget(self.title)
        self.desc = hint_label("")
        rl.addWidget(self.desc)

        g = QFormLayout()
        self.side = IdCombo()
        self.side.set_items([(s.name, s.id) for s in ctx.project.sides])
        w = ctx.window
        if w is not None and hasattr(w, "map_page"):
            self.side.set_current_id(w.map_page.current_side())
        g.addRow("Side:", self.side)
        self.name = QLineEdit()
        self.name.setToolTip("Exported as reference points NAME-1, NAME-2, ... (one area selected)")
        g.addRow("Area name:", self.name)
        self.all_sides = QCheckBox("Create the reference points on every side")
        g.addRow("", self.all_sides)
        self.colour = QCheckBox("Colour sea areas blue and air areas orange on the map (else the side colour)")
        self.colour.setChecked(True)
        g.addRow("", self.colour)
        mrow = QHBoxLayout()
        self.make_mission = QCheckBox("Create a mission on it:")
        self.make_mission.setChecked(True)
        self.mission = QComboBox()
        for label, _v in MISSION_CHOICES:
            self.mission.addItem(label)
        self.make_mission.toggled.connect(self.mission.setEnabled)
        self.make_mission.toggled.connect(lambda *_: self._pick())
        self.mission.currentIndexChanged.connect(lambda *_: self._pick())
        mrow.addWidget(self.make_mission)
        mrow.addWidget(self.mission, 1)
        g.addRow("Mission:", mrow)
        self.mission_hint = hint_label("")
        g.addRow("", self.mission_hint)
        rl.addLayout(g)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.add_btn = bb.addButton("Add to scenario", QDialogButtonBox.ButtonRole.AcceptRole)
        self.add_btn.setProperty("primary", True)
        bb.accepted.connect(self._add)
        bb.rejected.connect(self.reject)
        rl.addWidget(bb)
        split.addWidget(right)
        split.setSizes([460, 990])
        self._fill()
        if select and self.lib.area(select):
            self.select_area(select)

    # ------------------------------------------------------------------ list
    def _visible_areas(self) -> list[AreaEntry]:
        return self.lib.filtered(self.filter.text(), self.region.currentData() or "", self.kind.currentData() or "")

    def selected_areas(self) -> list[AreaEntry]:
        ids = [it.data(0, AREA_ROLE) for it in self.tree.selectedItems() if it.data(0, AREA_ROLE)]
        return [a for a in (self.lib.area(i) for i in ids) if a]

    def select_area(self, aid: str) -> None:
        it = _find_item(self.tree, aid)
        if it is not None:
            self.tree.clearSelection()
            it.setSelected(True)
            self.tree.setCurrentItem(it)
            self.tree.scrollToItem(it)

    def _fill(self, *_):
        keep = {a.id for a in self.selected_areas()}
        areas = self._visible_areas()
        _fill_tree(self.tree, areas, self.lib.all_regions(), keep)
        words = self.filter.text().lower().split()
        if words:       # prefer an area whose name matches the search
            hit = next((a for a in areas if all(w in a.name.lower() for w in words)), None)
            if hit:
                keep = {hit.id}
                self.select_area(hit.id)
        if not keep & {a.id for a in areas} and areas:
            self.select_area(sorted(areas, key=lambda a: (self.lib.all_regions().index(a.region), a.kind,
                                                          a.subregion, a.name))[0].id)
        n_sea = sum(a.kind == "sea" for a in areas)
        self.count.setText(f"{len(areas)} areas shown ({n_sea} sea, {len(areas) - n_sea} air) of "
                           f"{len(self.lib.areas)}. Ctrl/Shift-click to add several at once.")
        self._pick()

    def _pick(self):
        sel = self.selected_areas()
        self.add_btn.setEnabled(bool(sel))
        self.name.setEnabled(len(sel) == 1)
        shown = self._visible_areas()
        if len(sel) == 1:
            a = sel[0]
            self.title.setText(f"{a.name}  ·  {a.region} · {KIND_LABELS[a.kind]}"
                               + (f" · {a.subregion}" if a.subregion else ""))
            c = a.centre()
            self.desc.setText(f"{a.description}\n{len(a.points)} corners · about {_size_text(a)} · centre "
                              f"{format_latlon(*c)}" + (f" · tags: {', '.join(a.tags)}" if a.tags else ""))
            if not self.name.isModified():
                self.name.setText(zone_name(a.id))
        elif sel:
            self.title.setText(f"{len(sel)} areas selected")
            self.desc.setText(", ".join(a.name for a in sel))
            self.name.setText("(named after each area)")
        else:
            self.title.setText("Select an area")
            self.desc.setText("")
        self.mission_hint.setText(self._mission_text(sel))
        self.preview.show_areas(shown, sel[0].id if len(sel) == 1 else "", fit=sel or None)

    def _mission_for(self, a: AreaEntry) -> Optional[tuple[str, str]]:
        if not self.make_mission.isChecked():
            return None
        return MISSION_CHOICES[self.mission.currentIndex()][1] or suggested_mission(a)

    def _mission_text(self, sel: list[AreaEntry]) -> str:
        if not self.make_mission.isChecked() or not sel:
            return ""
        kinds = []
        for a in sel[:4]:
            mc, st = self._mission_for(a)
            kinds.append(f"'{a.name} {mission_label(mc, st)}'")
        more = f" and {len(sel) - 4} more" if len(sel) > 4 else ""
        return f"Creates {', '.join(kinds)}{more} with no units assigned - add aircraft or ships on the " \
               f"Missions tab."

    def _map_clicked(self, oid: str):
        if oid and self.lib.area(oid):
            self.select_area(oid)

    # ------------------------------------------------------------------ add
    def _add(self):
        sel = self.selected_areas()
        sid = self.side.current_id()
        if not sel:
            return
        if not sid:
            QMessageBox.information(self, "Area library", "Add a side to the scenario first (Sides tab).")
            return
        single = self.name.text().strip() if len(sel) == 1 else ""
        zones, missions = [], []
        label = sel[0].name if len(sel) == 1 else f"{len(sel)} areas"
        with self.ctx.doc.modify(f"Add {label} from the area library", "zones"):
            for a in sel:
                res = add_area(self.ctx.project, a, sid, name=single, all_sides=self.all_sides.isChecked(),
                               mission=self._mission_for(a),
                               color=KIND_COLORS.get(a.kind, "") if self.colour.isChecked() else "")
                zones.append(res.zone)
                if res.mission:
                    missions.append(res.mission)
        self.added_zone_ids = [z.id for z in zones]
        msg = f"Added {len(zones)} area(s)" + (f" and {len(missions)} mission(s)" if missions else "") + \
              f": {', '.join(z.name for z in zones[:6])}{'...' if len(zones) > 6 else ''}"
        self.ctx.status(msg)
        self.ctx.doc.select(zones[0].id)
        self.accept()

    def _edit_library(self):
        dlg = AreaLibraryDialog(self.ctx, self)
        dlg.exec()
        self.lib, self.source = current_library(self.ctx)
        self._fill()


# =============================================================================== library editor
class AreaLibraryDialog(QDialog):
    def __init__(self, ctx, parent=None, select: str = ""):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Area library")
        self.resize(1450, 820)
        self.path = library_path(ctx)
        self.lib = current_library(ctx)[0].clone()
        self.aid = select
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
        self.filter.setPlaceholderText("Filter areas...")
        self.filter.textChanged.connect(lambda *_: self._fill())
        ll.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Area"])
        self.tree.currentItemChanged.connect(self._pick)
        ll.addWidget(self.tree)
        row = QHBoxLayout()
        for text, fn in (("New", self._new), ("Duplicate", self._dup), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        f = QFormLayout()
        self.name = QLineEdit()
        self.name.editingFinished.connect(self._fields)
        f.addRow("Name:", self.name)
        self.region = QComboBox()
        self.region.setEditable(True)
        self.region.lineEdit().editingFinished.connect(self._fields)
        self.region.activated.connect(lambda *_: self._fields())
        f.addRow("Region:", self.region)
        self.kind = QComboBox()
        for k in KINDS:
            self.kind.addItem(KIND_LABELS[k], k)
        self.kind.activated.connect(lambda *_: self._fields())
        f.addRow("Kind:", self.kind)
        self.subregion = QLineEdit()
        self.subregion.setPlaceholderText("e.g. North Atlantic, Baltic, South China Sea")
        self.subregion.editingFinished.connect(self._fields)
        f.addRow("Sub-region:", self.subregion)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("comma separated, e.g. ASW, chokepoint (AEW / tanker make support missions)")
        self.tags.editingFinished.connect(self._fields)
        f.addRow("Tags:", self.tags)
        self.description = QPlainTextEdit()
        self.description.setMaximumHeight(70)
        self.description.textChanged.connect(self._fields)
        f.addRow("Description:", self.description)
        ml.addLayout(f)
        self.points = QTableWidget(0, 2)
        self.points.setHorizontalHeaderLabels(["Latitude", "Longitude"])
        self.points.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.points.itemChanged.connect(self._point_edited)
        ml.addWidget(QLabel("Corners (or drag the white squares on the map):"))
        ml.addWidget(self.points, 1)
        row = QHBoxLayout()
        for text, fn in (("Add corner", self._add_point), ("Remove corner", self._remove_point),
                         ("Reverse", self._reverse)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        ml.addLayout(row)
        split.addWidget(mid)
        self.preview = AreaPreview(_tiles(ctx, self))
        self.preview.zonePointMoved.connect(self._vertex_moved)
        self.preview.objectClicked.connect(lambda oid: oid and self.lib.area(oid) and self._go(oid))
        split.addWidget(self.preview)
        split.setSizes([330, 520, 600])
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
    def _a(self) -> Optional[AreaEntry]:
        return self.lib.area(self.aid)

    def _touch(self):
        self.dirty = True
        self._label()

    def _label(self):
        where = str(self.path) if self.path.is_file() else f"{self.path} (not created yet - Save writes it)"
        n_sea = sum(a.kind == "sea" for a in self.lib.areas)
        self.file_label.setText(f"Your area file: {where}{'  ·  unsaved changes' if self.dirty else ''}\n"
                                f"{len(self.lib.areas)} areas ({n_sea} sea, {len(self.lib.areas) - n_sea} air) in "
                                f"{len(self.lib.all_regions())} regions")

    def _go(self, aid: str):
        self.aid = aid
        it = _find_item(self.tree, aid)
        if it is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(it)
            self.tree.blockSignals(False)
        self._load(fit=False)

    def _fill(self):
        areas = self.lib.filtered(self.filter.text())
        _fill_tree(self.tree, areas, self.lib.all_regions(), {self.aid}, columns=1)
        self.region.blockSignals(True)
        self.region.clear()
        self.region.addItems(self.lib.all_regions())
        self.region.blockSignals(False)
        if not self._a() and areas:
            self.aid = areas[0].id
            it = _find_item(self.tree, self.aid)
            if it is not None:
                self.tree.blockSignals(True)
                self.tree.setCurrentItem(it)
                self.tree.blockSignals(False)
        self._load()

    def _pick(self, cur, _prev=None):
        aid = cur.data(0, AREA_ROLE) if cur else None
        if aid:
            self.aid = aid
            self._load()

    def _load(self, fit: bool = True):
        a = self._a()
        for w in (self.name, self.region, self.kind, self.subregion, self.tags, self.description, self.points):
            w.setEnabled(a is not None)
        if a is None:
            self.preview.show_areas([], "")
            return
        for w, v in ((self.name, a.name), (self.subregion, a.subregion), (self.tags, ", ".join(a.tags))):
            w.blockSignals(True)
            w.setText(v)
            w.blockSignals(False)
        self.region.blockSignals(True)
        self.region.setCurrentText(a.region)
        self.region.blockSignals(False)
        self.kind.setCurrentIndex(max(0, self.kind.findData(a.kind)))
        self.description.blockSignals(True)
        self.description.setPlainText(a.description)
        self.description.blockSignals(False)
        self._fill_points()
        self._show(fit)

    def _show(self, fit: bool = False):
        a = self._a()
        if a is None:
            return
        near = [x for x in self.lib.areas if x.region == a.region]
        self.preview.show_areas(near, a.id, fit=[a] if fit else None)

    def _fill_points(self):
        a = self._a()
        self.points.blockSignals(True)
        self.points.setRowCount(0)
        for lat, lon in (a.points if a else []):
            r = self.points.rowCount()
            self.points.insertRow(r)
            self.points.setItem(r, 0, QTableWidgetItem(f"{lat:.4f}"))
            self.points.setItem(r, 1, QTableWidgetItem(f"{lon:.4f}"))
        self.points.blockSignals(False)

    def _fields(self, *_):
        a = self._a()
        if not a:
            return
        new = (self.name.text().strip() or a.name, self.region.currentText().strip() or a.region,
               self.kind.currentData() or a.kind, self.subregion.text().strip(),
               [x.strip() for x in self.tags.text().split(",") if x.strip()], self.description.toPlainText())
        old = (a.name, a.region, a.kind, a.subregion, a.tags, a.description)
        if new != old:
            regroup = new[:3] != old[:3]
            a.name, a.region, a.kind, a.subregion, a.tags, a.description = new
            self._touch()
            if regroup:
                self._fill()

    def _point_edited(self, item: QTableWidgetItem):
        a = self._a()
        r, c = item.row(), item.column()
        if not a or r >= len(a.points):
            return
        try:
            v = float(item.text().replace(",", "."))
        except ValueError:
            self._fill_points()
            return
        lim = 90.0 if c == 0 else 180.0
        a.points[r][c] = max(-lim, min(lim, v))
        self._touch()
        self._show()

    def _vertex_moved(self, zid: str, idx: int, lat: float, lon: float):
        a = self.lib.area(zid)
        if a is None or not (0 <= idx < len(a.points)):
            return
        a.points[idx] = [round(lat, 4), round(lon, 4)]
        self.aid = a.id
        self._fill_points()
        self._touch()
        self._show()

    def _add_point(self):
        a = self._a()
        if not a:
            return
        r = self.points.currentRow()
        if len(a.points) >= 2:
            i = r if 0 <= r < len(a.points) else len(a.points) - 1
            p, q = a.points[i], a.points[(i + 1) % len(a.points)]
            a.points.insert(i + 1, [round((p[0] + q[0]) / 2, 4), round((p[1] + q[1]) / 2, 4)])
        else:
            lat, lon = self.preview.center()
            a.points.append([round(lat, 4), round(lon, 4)])
        self._fill_points()
        self._touch()
        self._show()

    def _remove_point(self):
        a = self._a()
        r = self.points.currentRow()
        if a and 0 <= r < len(a.points) and len(a.points) > 3:
            a.points.pop(r)
            self._fill_points()
            self._touch()
            self._show()

    def _reverse(self):
        a = self._a()
        if a:
            a.points.reverse()
            self._fill_points()
            self._touch()
            self._show()

    # ------------------------------------------------------------------ areas
    def _new(self):
        name, ok = QInputDialog.getText(self, "New area", "Area name:")
        if not (ok and name.strip()):
            return
        w = self.ctx.window
        lat, lon = w.map_page.map.center() if w is not None and hasattr(w, "map_page") else self.preview.center()
        d = 1.0
        cur = self._a()
        a = AreaEntry(id=self.lib.unique_id(name), name=name.strip(), region=cur.region if cur else "Europe",
                      kind=cur.kind if cur else "sea",
                      points=[[round(lat + d, 4), round(lon - d, 4)], [round(lat + d, 4), round(lon + d, 4)],
                              [round(lat - d, 4), round(lon + d, 4)], [round(lat - d, 4), round(lon - d, 4)]])
        self.lib.areas.append(a)
        self.aid = a.id
        self._fill()
        self._touch()

    def _dup(self):
        a = self._a()
        if a:
            d = copy.deepcopy(a)
            d.name += " (copy)"
            d.id = self.lib.unique_id(d.name)
            self.lib.areas.insert(self.lib.areas.index(a) + 1, d)
            self.aid = d.id
            self._fill()
            self._touch()

    def _delete(self):
        a = self._a()
        if a and QMessageBox.question(self, "Delete", f"Delete area '{a.name}'?") == QMessageBox.StandardButton.Yes:
            self.lib.areas.remove(a)
            self.aid = ""
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
        self.ctx.status(f"Area library saved to {self.path}")
        return True

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import area library", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            self.lib = AreaLibrary.load(path)
        except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
            QMessageBox.critical(self, "Import", f"Not a valid area library:\n{exc}")
            return
        self.aid = ""
        self._fill()
        self._touch()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export area library", str(Path.home() / "areas.json"),
                                              "JSON (*.json)")
        if path:
            self.lib.save(path)

    def _show_file(self):
        if not self.path.is_file():
            if QMessageBox.question(self, "Show file", "Your area file does not exist yet. Save it now so you can "
                                                       "edit it by hand?") != QMessageBox.StandardButton.Yes:
                return
            if not self.save():
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.parent)))

    def _reset(self):
        if QMessageBox.question(self, "Reset", "Replace the library with the built-in areas? (Save to keep the "
                                               "change.)") == QMessageBox.StandardButton.Yes:
            self.lib = default_library()
            self.aid = ""
            self._fill()
            self._touch()

    def closeEvent(self, e):
        if self.dirty:
            r = QMessageBox.question(self, "Area library", "Save changes to your area library?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                     QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel or (r == QMessageBox.StandardButton.Save and not self.save()):
                e.ignore()
                return
        super().closeEvent(e)

    def reject(self):
        self.close()


def save_zone_to_library(ctx, zone_id: str, parent=None) -> Optional[AreaEntry]:
    """Ask for a name, region and kind, then add the scenario area to the user's area library."""
    z = ctx.project.zone(zone_id)
    if z is None:
        return None
    if len(z.points) < 3:
        QMessageBox.warning(parent, "Save to area library", "An area needs at least three corners.")
        return None
    lib = current_library(ctx)[0].clone()
    name, ok = QInputDialog.getText(parent, "Save to area library", "Area name:",
                                    text=z.name.replace("_", " ").title())
    if not ok or not name.strip():
        return None
    regions = lib.all_regions()
    lat = sum(p[0] for p in z.points) / len(z.points)
    lon = sum(p[1] for p in z.points) / len(z.points)
    region, ok = QInputDialog.getItem(parent, "Save to area library", "Region (or type a new one):", regions,
                                      max(0, regions.index(guess_region(lat, lon))
                                          if guess_region(lat, lon) in regions else 0), True)
    if not ok:
        return None
    kinds = [KIND_LABELS[k] for k in KINDS]
    kind, ok = QInputDialog.getItem(parent, "Save to area library", "Kind:", kinds, 0, False)
    if not ok:
        return None
    entry = area_from_zone(z, lib, name=name.strip(), region=region.strip() or "Europe",
                           kind=KINDS[kinds.index(kind)])
    lib.areas.append(entry)
    lib.save(library_path(ctx))
    ctx.status(f"Area '{entry.name}' saved to {library_path(ctx)}")
    return entry


def guess_region(lat: float, lon: float) -> str:
    """A rough region for a position (used to preselect the region when saving an area)."""
    if lat >= 66:
        return "Arctic"
    if 49.8 <= lat <= 61.0 and -10.5 <= lon <= 2.0 and not (lat < 51.0 and lon > -2.0):
        return "United Kingdom"
    if -170 <= lon <= -30:
        return "North America" if lat >= 12 else "South America"
    if (lon > 110 and lat < -5) or lon > 150 or lon < -170 or (lon > 140 and lat < 20):
        return "Oceania"
    if 25 <= lon <= 63 and 12 <= lat <= 42 and not (lon < 36 and lat > 34):
        return "Middle East"
    if lat < 36 and -20 <= lon < 52:
        return "Africa"
    if lon < 45:
        return "Europe"
    return "Asia"
