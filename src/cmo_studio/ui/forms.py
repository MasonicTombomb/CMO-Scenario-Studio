"""Editors for single units, reference points and areas (used on the map and on their own pages)."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from ..geo import polygon_centroid
from ..model.enums import HOST_TYPES, PROFICIENCY
from .pages.base import AppContext, Binder, Page
from .widgets import ColorButton, CoordEdit, IdCombo, KeyValueTable, hint_label


def side_items(project) -> list[tuple[str, str]]:
    return [(s.name, s.id) for s in project.sides]


class _Scroll(Page):
    """A Page whose content scrolls."""

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.body = QWidget()
        self.lay = QVBoxLayout(self.body)
        scroll.setWidget(self.body)
        outer.addWidget(scroll)


# =============================================================================== unit
class UnitForm(_Scroll):
    showInBrowser = pyqtSignal(str, int)     # type, dbid
    centerRequested = pyqtSignal(float, float)
    deleted = pyqtSignal()

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.uid = ""
        b = self.b = Binder(self, lambda: self.project.unit(self.uid), "units", self._after_change)
        lay = self.lay

        self.header = QLabel("No unit selected")
        self.header.setProperty("heading", True)
        self.header.setWordWrap(True)
        lay.addWidget(self.header)

        g = QGroupBox("Identity")
        f = QFormLayout(g)
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        self.side = IdCombo()
        b.combo(self.side, "side")
        f.addRow("Side:", self.side)
        row = QHBoxLayout()
        self.db_label = QLabel("")
        self.db_label.setWordWrap(True)
        row.addWidget(self.db_label, 1)
        btn = QPushButton("Show in DB")
        btn.clicked.connect(self._show_db)
        row.addWidget(btn)
        f.addRow("Database:", row)
        self.count = b.spin(QSpinBox(), "count")
        self.count.setRange(1, 500)
        self.count.setToolTip("More than 1 builds '<name> #1', '<name> #2', ...")
        f.addRow("Count:", self.count)
        self.group = b.line(QLineEdit(), "group")
        self.group.setPlaceholderText("free tag, e.g. 'Narva garrison'")
        f.addRow("Group:", self.group)
        lay.addWidget(g)

        g = QGroupBox("Position")
        f = QFormLayout(g)
        self.host = IdCombo()
        self.host.currentIndexChanged.connect(self._host_changed)
        f.addRow("Starts at:", self.host)
        row = QHBoxLayout()
        self.coords = CoordEdit()
        self.coords.coordsEdited.connect(self._coords)
        row.addWidget(self.coords, 1)
        go = QPushButton("Show")
        go.clicked.connect(lambda: (u := self.project.unit(self.uid)) and self.centerRequested.emit(u.lat, u.lon))
        row.addWidget(go)
        f.addRow("Lat, lon:", row)
        self.alt = QDoubleSpinBox()
        self.alt.setRange(-1, 30000)
        self.alt.setSpecialValueText("default (9000 m)")
        self.alt.setSuffix(" m")
        b.opt_spin(self.alt, "altitude")
        self.alt_row = ("Altitude:", self.alt)
        f.addRow(*self.alt_row)
        self.depth = QDoubleSpinBox()
        self.depth.setRange(-1, 3000)
        self.depth.setSpecialValueText("default")
        self.depth.setSuffix(" m")
        b.opt_spin(self.depth, "depth")
        f.addRow("Depth:", self.depth)
        self.heading = QDoubleSpinBox()
        self.heading.setRange(-1, 359)
        self.heading.setSpecialValueText("default")
        self.heading.setSuffix("°")
        b.opt_spin(self.heading, "heading")
        f.addRow("Heading:", self.heading)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(-1, 3000)
        self.speed.setSpecialValueText("default")
        self.speed.setSuffix(" kt")
        b.opt_spin(self.speed, "speed")
        f.addRow("Speed:", self.speed)
        self.pos_form = f
        lay.addWidget(g)

        self.air = QGroupBox("Aircraft")
        f = QFormLayout(self.air)
        self.loadout = QComboBox()
        self.loadout.currentIndexChanged.connect(self._loadout_changed)
        f.addRow("Loadout:", self.loadout)
        self.loadout_info = hint_label("")
        f.addRow("", self.loadout_info)
        lay.addWidget(self.air)

        g = QGroupBox("Behaviour")
        v = QVBoxLayout(g)
        grid = QHBoxLayout()
        self.radar = b.check(QCheckBox("Radar active"), "radar_active")
        self.sonar = b.check(QCheckBox("Sonar active"), "sonar_active")
        self.hold = b.check(QCheckBox("Hold position"), "hold_position")
        self.auto = b.check(QCheckBox("Auto-detectable"), "autodetectable")
        for w in (self.radar, self.sonar, self.hold, self.auto):
            grid.addWidget(w)
        grid.addStretch()
        v.addLayout(grid)
        f = QFormLayout()
        self.prof = QComboBox()
        self.prof.addItem("(side default)", "")
        for p in PROFICIENCY:
            self.prof.addItem(p, p)
        b.combo(self.prof, "proficiency")
        f.addRow("Proficiency:", self.prof)
        v.addLayout(f)
        self.reserve = b.check(QCheckBox("Reinforcement - not built at start; spawned by an event's "
                                         "'Spawn unit' action"), "reserve")
        v.addWidget(self.reserve)
        lay.addWidget(g)

        self.hosted_box = QGroupBox("Hosted units")
        hv = QVBoxLayout(self.hosted_box)
        self.hosted = QListWidget()
        self.hosted.setMaximumHeight(140)
        self.hosted.itemDoubleClicked.connect(lambda it: self.doc.select(it.data(Qt.ItemDataRole.UserRole)))
        hv.addWidget(self.hosted)
        hv.addWidget(hint_label("Select this base, pick an aircraft in the DB browser and press "
                                "'Add to selected base'. Double-click to edit a squadron."))
        lay.addWidget(self.hosted_box)

        g = QGroupBox("Notes and advanced")
        v = QVBoxLayout(g)
        self.notes = b.text(QPlainTextEdit(), "notes")
        self.notes.setMaximumHeight(70)
        self.notes.setPlaceholderText("Designer notes (not exported)")
        v.addWidget(self.notes)
        v.addWidget(hint_label("Extra ScenEdit_SetUnit fields applied after the unit is built "
                               "(e.g. fuel = 50, outOfComms = true):"))
        self.extra = KeyValueTable("Field", "Value")
        self.extra.setMaximumHeight(140)
        self.extra.dataChanged.connect(self._extra)
        v.addWidget(self.extra)
        lay.addWidget(g)

        row = QHBoxLayout()
        dup = QPushButton("Duplicate")
        dup.clicked.connect(self._duplicate)
        dele = QPushButton("Delete unit")
        dele.clicked.connect(self._delete)
        row.addWidget(dup)
        row.addStretch()
        row.addWidget(dele)
        lay.addLayout(row)
        lay.addStretch()
        self.body.setEnabled(False)

    # ------------------------------------------------------------------ load
    def set_unit(self, uid: str) -> None:
        self.uid = uid or ""
        self.refresh()

    def refresh(self) -> None:
        u = self.project.unit(self.uid)
        self.body.setEnabled(u is not None)
        self.side.set_items(side_items(self.project), keep=False)
        if not u:
            self.header.setText("No unit selected")
            self.b.load()
            return
        self.header.setText(f"{u.display_name()}  ·  {u.type}")
        self.db_label.setText(f"DBID {u.dbid} - {u.db_name or '(name unknown)'}")
        hosts = [(f"{h.name}  [{h.type}]", h.id) for h in self.project.units
                 if h.id != u.id and h.type in HOST_TYPES and h.side == u.side and not h.host]
        self.host.set_items(hosts, blank="(own position)", keep=False)
        self.host.set_current_id(u.host)
        self.coords.set_coords(u.lat, u.lon)
        self.coords.setEnabled(not u.host)
        self.b.load()
        self.extra.set_data(u.extra)
        is_air = u.type == "Aircraft"
        self.air.setVisible(is_air)
        self.alt.setEnabled(is_air and not u.host)
        self.depth.setEnabled(u.type == "Submarine")
        self.sonar.setEnabled(u.type in ("Ship", "Submarine"))
        if is_air:
            self._fill_loadouts(u)
        hosted = self.project.hosted_by(u.id)
        self.hosted_box.setVisible(u.type in HOST_TYPES)
        self.hosted.clear()
        for h in hosted:
            it = QListWidgetItem(f"{h.display_name()}  -  {h.db_name}")
            it.setData(Qt.ItemDataRole.UserRole, h.id)
            self.hosted.addItem(it)

    def _fill_loadouts(self, u) -> None:
        self.loadout.blockSignals(True)
        self.loadout.clear()
        self.loadout.addItem(f"(reserve - loadout {self.project.build.default_loadout})", None)
        db = self.ctx.db
        found = False
        if db and u.dbid:
            for lo in db.loadouts(int(u.dbid), combat_only=False):
                self.loadout.addItem(f"{lo.id}  [{lo.role}]  {lo.name}", lo.id)
                found = found or lo.id == u.loadout
        if u.loadout and not found:
            self.loadout.addItem(f"{u.loadout}  (not in the open database)", u.loadout)
        i = self.loadout.findData(u.loadout) if u.loadout else 0
        self.loadout.setCurrentIndex(max(0, i))
        self.loadout.blockSignals(False)
        self._loadout_text(u.loadout)

    def _loadout_text(self, lid) -> None:
        db = self.ctx.db
        if lid and db:
            w = db.loadout_weapons(int(lid))
            self.loadout_info.setText(", ".join(w) if w else "(no weapons)")
        else:
            self.loadout_info.setText("Starts unarmed in reserve; the player arms it." if not lid else "")

    # ------------------------------------------------------------------ edits
    def _after_change(self, attr: str) -> None:
        if attr in ("name", "count", "side", "reserve"):
            self.refresh()

    def _coords(self, lat: float, lon: float) -> None:
        u = self.project.unit(self.uid)
        if not u:
            return
        with self.edit("Move unit", "units"):
            u.lat, u.lon = lat, lon

    def _host_changed(self, *_):
        u = self.project.unit(self.uid)
        hid = self.host.current_id()
        if not u or u.host == hid:
            return
        with self.edit("Change host", "units"):
            u.host = hid
            h = self.project.unit(hid)
            if h:
                u.lat, u.lon = h.lat, h.lon
        self.refresh()

    def _loadout_changed(self, *_):
        u = self.project.unit(self.uid)
        lid = self.loadout.currentData()
        if not u or u.loadout == lid:
            return
        with self.edit("Change loadout", "units"):
            u.loadout = lid
        self._loadout_text(lid)

    def _extra(self, data: dict) -> None:
        u = self.project.unit(self.uid)
        if u and u.extra != data:
            with self.edit("Edit extra fields", "units", merge=f"extra.{u.id}"):
                u.extra = data

    def _show_db(self):
        u = self.project.unit(self.uid)
        if u:
            self.showInBrowser.emit(u.type, int(u.dbid))

    def _duplicate(self):
        with self.edit("Duplicate unit", "units"):
            dup = self.project.duplicate_unit(self.uid)
        if dup:
            self.doc.select(dup.id)

    def _delete(self):
        u = self.project.unit(self.uid)
        if not u:
            return
        hosted = self.project.hosted_by(u.id)
        if hosted and QMessageBox.question(
                self, "Delete unit", f"'{u.name}' hosts {len(hosted)} unit(s). Delete them too?") != \
                QMessageBox.StandardButton.Yes:
            return
        with self.edit("Delete unit", "units"):
            self.project.remove_unit(u.id)
        self.doc.select("")
        self.deleted.emit()


# =============================================================================== reference point
class RPForm(_Scroll):
    centerRequested = pyqtSignal(float, float)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.rid = ""
        b = self.b = Binder(self, lambda: next((r for r in self.project.reference_points if r.id == self.rid), None),
                            "rps", lambda a: self.refresh() if a == "name" else None)
        self.header = QLabel("Reference point")
        self.header.setProperty("heading", True)
        self.lay.addWidget(self.header)
        f = QFormLayout()
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        self.side = IdCombo()
        b.combo(self.side, "side")
        f.addRow("Side:", self.side)
        self.all = b.check(QCheckBox("Create on every side (objective markers)"), "all_sides")
        f.addRow("", self.all)
        self.hl = b.check(QCheckBox("Highlighted"), "highlighted")
        f.addRow("", self.hl)
        row = QHBoxLayout()
        self.coords = CoordEdit()
        self.coords.coordsEdited.connect(self._coords)
        row.addWidget(self.coords, 1)
        go = QPushButton("Show")
        go.clicked.connect(self._show)
        row.addWidget(go)
        f.addRow("Lat, lon:", row)
        self.lay.addLayout(f)
        dele = QPushButton("Delete reference point")
        dele.clicked.connect(self._delete)
        self.lay.addWidget(dele, 0, Qt.AlignmentFlag.AlignRight)
        self.lay.addWidget(hint_label("Reference points can be used in Lua (ScenEdit_GetReferencePoint) and as "
                                      "markers for players. Areas (polygons) are drawn with the area tool."))
        self.lay.addStretch()

    def _rp(self):
        return next((r for r in self.project.reference_points if r.id == self.rid), None)

    def set_rp(self, rid: str) -> None:
        self.rid = rid
        self.refresh()

    def refresh(self) -> None:
        r = self._rp()
        self.body.setEnabled(r is not None)
        self.side.set_items(side_items(self.project), keep=False)
        self.b.load()
        if r:
            self.header.setText(f"Reference point: {r.name}")
            self.coords.set_coords(r.lat, r.lon)

    def _coords(self, lat, lon):
        r = self._rp()
        if r:
            with self.edit("Move reference point", "rps"):
                r.lat, r.lon = lat, lon

    def _show(self):
        r = self._rp()
        if r:
            self.centerRequested.emit(r.lat, r.lon)

    def _delete(self):
        if self._rp():
            with self.edit("Delete reference point", "rps"):
                self.project.reference_points = [x for x in self.project.reference_points if x.id != self.rid]
            self.doc.select("")


# =============================================================================== zone
class ZoneForm(_Scroll):
    centerRequested = pyqtSignal(float, float)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.zid = ""
        b = self.b = Binder(self, lambda: self.project.zone(self.zid), "zones",
                            lambda a: self.refresh() if a in ("name", "side") else None)
        self.header = QLabel("Area")
        self.header.setProperty("heading", True)
        self.lay.addWidget(self.header)
        f = QFormLayout()
        self.name = b.line(QLineEdit(), "name")
        self.name.setToolTip("Exported as reference points NAME-1, NAME-2, ...")
        f.addRow("Name:", self.name)
        self.side = IdCombo()
        b.combo(self.side, "side")
        f.addRow("Side:", self.side)
        self.all = b.check(QCheckBox("Create on every side"), "all_sides")
        f.addRow("", self.all)
        self.color = ColorButton()
        self.color.colorChanged.connect(self._color)
        clear = QPushButton("Side colour")
        clear.clicked.connect(lambda: self._color(""))
        row = QHBoxLayout()
        row.addWidget(self.color)
        row.addWidget(clear)
        row.addStretch()
        f.addRow("Map colour:", row)
        self.lay.addLayout(f)

        self.points = QTableWidget(0, 2)
        self.points.setHorizontalHeaderLabels(["Latitude", "Longitude"])
        self.points.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.points.itemChanged.connect(self._point_edited)
        self.lay.addWidget(QLabel("Corners (drag the white squares on the map to move them):"))
        self.lay.addWidget(self.points)
        row = QHBoxLayout()
        for text, fn in (("Add corner", self._add_point), ("Remove corner", self._remove_point),
                         ("Reverse", self._reverse), ("Show", self._show)):
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            row.addWidget(btn)
        row.addStretch()
        self.lay.addLayout(row)
        self.used = hint_label("")
        self.lay.addWidget(self.used)
        self.notes = b.text(QPlainTextEdit(), "notes")
        self.notes.setPlaceholderText("Notes (not exported)")
        self.notes.setMaximumHeight(60)
        self.lay.addWidget(self.notes)
        dele = QPushButton("Delete area")
        dele.clicked.connect(self._delete)
        self.lay.addWidget(dele, 0, Qt.AlignmentFlag.AlignRight)
        self.lay.addStretch()

    def set_zone(self, zid: str) -> None:
        self.zid = zid
        self.refresh()

    def refresh(self) -> None:
        z = self.project.zone(self.zid)
        self.body.setEnabled(z is not None)
        self.side.set_items(side_items(self.project), keep=False)
        self.b.load()
        self.points.blockSignals(True)
        self.points.setRowCount(0)
        if z:
            self.header.setText(f"Area: {z.name}  ({len(z.points)} corners)")
            self.color.set_color(z.color or (self.project.side(z.side).color if self.project.side(z.side) else ""))
            for i, (lat, lon) in enumerate(z.points):
                self.points.insertRow(i)
                self.points.setItem(i, 0, QTableWidgetItem(f"{lat:.5f}"))
                self.points.setItem(i, 1, QTableWidgetItem(f"{lon:.5f}"))
            users = [m.name for m in self.project.missions if z.id in (m.zone, m.prosecution_zone)]
            trig = [e.name for e in self.project.events if any(t.params.get("Area") == z.id for t in e.triggers)]
            txt = []
            if users:
                txt.append("Missions: " + ", ".join(users))
            if trig:
                txt.append("Events: " + ", ".join(trig))
            self.used.setText("Used by  " + " · ".join(txt) if txt else "Not used by any mission or event yet.")
        self.points.blockSignals(False)

    def _color(self, c: str):
        z = self.project.zone(self.zid)
        if z:
            with self.edit("Area colour", "zones"):
                z.color = c
            self.refresh()

    def _point_edited(self, item: QTableWidgetItem):
        z = self.project.zone(self.zid)
        if not z:
            return
        try:
            v = float(item.text())
        except ValueError:
            self.refresh()
            return
        r, c = item.row(), item.column()
        if r < len(z.points):
            with self.edit("Edit area corner", "zones"):
                z.points[r][c] = v

    def _add_point(self):
        z = self.project.zone(self.zid)
        if not z:
            return
        row = self.points.currentRow()
        with self.edit("Add area corner", "zones"):
            if len(z.points) >= 2 and 0 <= row < len(z.points):
                a, b = z.points[row], z.points[(row + 1) % len(z.points)]
                z.points.insert(row + 1, [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
            else:
                c = polygon_centroid(z.points) if z.points else (0.0, 0.0)
                z.points.append([c[0] + 0.05, c[1] + 0.05])
        self.refresh()

    def _remove_point(self):
        z = self.project.zone(self.zid)
        row = self.points.currentRow()
        if z and 0 <= row < len(z.points):
            with self.edit("Remove area corner", "zones"):
                z.points.pop(row)
            self.refresh()

    def _reverse(self):
        z = self.project.zone(self.zid)
        if z:
            with self.edit("Reverse area", "zones"):
                z.points.reverse()
            self.refresh()

    def _show(self):
        z = self.project.zone(self.zid)
        if z and z.points:
            self.centerRequested.emit(*polygon_centroid(z.points))

    def _delete(self):
        z = self.project.zone(self.zid)
        if not z:
            return
        with self.edit("Delete area", "zones"):
            self.project.remove_zone(z.id)
        self.doc.select("")
