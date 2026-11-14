"""Formations: edit a formation's layout and members, and create new units in formation."""

from __future__ import annotations

import copy
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                             QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ...model.formations import NM_PER, PRESETS, apply_formation, preset, stations
from ...model.project import Formation, Unit, new_id
from ..formation_widgets import FormationPreview, PresetCombo, TemplateParams, fmt_dist
from ..widgets import CoordEdit, IdCombo, PickerDialog, hint_label
from .base import AppContext, Binder, Page

DOMAIN_FOR_TYPE = {"Ship": "Naval", "Submarine": "Naval", "Aircraft": "Air", "Facility": "Ground",
                   "GroundUnit": "Ground"}
DEFAULT_PRESET = {"Naval": "circular_screen", "Air": "finger_four", "Ground": "ground_wedge"}


def default_preset_for(units: list[Unit]) -> str:
    domain = DOMAIN_FOR_TYPE.get(units[0].type, "Naval") if units else "Naval"
    return DEFAULT_PRESET[domain]


class SpacingEdit(QWidget):
    """Spacing value with a unit selector; stores nautical miles."""

    def __init__(self, on_change: Callable[[float], None], parent=None):
        super().__init__(parent)
        self.on_change = on_change
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.value = QDoubleSpinBox()
        self.value.setRange(0.001, 100000)
        self.value.setDecimals(3)
        self.unit = QComboBox()
        self.unit.addItems(["nm", "km", "m"])
        lay.addWidget(self.value, 1)
        lay.addWidget(self.unit)
        self._nm = 1.0
        self.value.valueChanged.connect(self._changed)
        self.unit.currentTextChanged.connect(lambda *_: self.set_nm(self._nm))

    def set_nm(self, nm: float) -> None:
        self._nm = nm
        u = self.unit.currentText()
        self.value.blockSignals(True)
        self.value.setDecimals(0 if u == "m" else 3)
        self.value.setSingleStep(50 if u == "m" else 0.1)
        self.value.setValue(nm / NM_PER[u])
        self.value.blockSignals(False)

    def nm(self) -> float:
        return self.value.value() * NM_PER[self.unit.currentText()]

    def _changed(self, *_):
        self._nm = self.nm()
        self.on_change(self._nm)


class FormationsPage(Page):
    title = "Formations"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.fid = ""
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        # ------------------------------------------------ list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._pick)
        ll.addWidget(self.list)
        create = QPushButton("Create units in formation...")
        create.setProperty("primary", True)
        create.setToolTip("Build a new group from database entries (e.g. 1 carrier + 6 escorts) in any layout")
        create.clicked.connect(self.open_creator)
        ll.addWidget(create)
        row = QHBoxLayout()
        for text, fn in (("From units...", self._from_units), ("Duplicate", self._duplicate),
                         ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        ll.addWidget(hint_label("A formation is a lead plus members kept on stations. With 'keep on station' "
                                "ticked, moving the lead (or any member) on the map moves the whole group. "
                                "In CMO it becomes a group with formation stations."))
        split.addWidget(left)

        # ------------------------------------------------ editor
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        b = self.b = Binder(self, self._f, "formations", self._attr_changed)

        g = QGroupBox("Formation")
        f = QFormLayout(g)
        self.name = b.line(QLineEdit(), "name")
        self.name.setToolTip("Also the name of the group in CMO")
        f.addRow("Name / group:", self.name)
        self.side_label = QLabel("")
        f.addRow("Side:", self.side_label)
        self.preset = PresetCombo()
        self.preset.currentIndexChanged.connect(self._preset_changed)
        f.addRow("Layout:", self.preset)
        self.lead = IdCombo()
        self.lead.currentIndexChanged.connect(self._lead_changed)
        f.addRow("Lead (guide):", self.lead)
        v.addWidget(g)

        g = QGroupBox("Geometry")
        f = QFormLayout(g)
        self.spacing = SpacingEdit(lambda nm: self._geom("spacing_nm", nm))
        f.addRow("Spacing:", self.spacing)
        self.heading = QDoubleSpinBox()
        self.heading.setRange(0, 359.9)
        self.heading.setWrapping(True)
        self.heading.setSuffix("°")
        self.heading.valueChanged.connect(lambda val: self._geom("heading", float(val)))
        f.addRow("Orientation (heading):", self.heading)
        self.alt_step = QDoubleSpinBox()
        self.alt_step.setRange(-5001, 5000)
        self.alt_step.setSpecialValueText("layout default")
        self.alt_step.setSuffix(" m")
        self.alt_step.setSingleStep(50)
        self.alt_step.valueChanged.connect(
            lambda val: self._geom("alt_step_m", None if val == self.alt_step.minimum() else float(val)))
        f.addRow("Altitude step per aircraft:", self.alt_step)
        row = QHBoxLayout()
        self.mirror = QCheckBox("Mirror left/right")
        self.mirror.toggled.connect(lambda on: self._geom("mirror", bool(on)))
        row.addWidget(self.mirror)
        row.addStretch()
        f.addRow("", row)
        row = QHBoxLayout()
        self.jitter = QDoubleSpinBox()
        self.jitter.setRange(0, 2)
        self.jitter.setSingleStep(0.05)
        self.jitter.setToolTip("Random offset of every station, in spacing units (0 = exact)")
        self.jitter.valueChanged.connect(lambda val: self._geom("jitter", float(val)))
        self.seed = QSpinBox()
        self.seed.setRange(0, 99999)
        self.seed.setToolTip("Random seed for jitter / dispersal")
        self.seed.valueChanged.connect(lambda val: self._geom("seed", int(val)))
        row.addWidget(self.jitter)
        row.addWidget(QLabel("seed"))
        row.addWidget(self.seed)
        f.addRow("Jitter (spacing units):", row)
        v.addWidget(g)

        self.params_box = QGroupBox("Layout settings")
        pl = QVBoxLayout(self.params_box)
        self.params = TemplateParams()
        self.params.paramsChanged.connect(lambda d: self._geom("params", d))
        pl.addWidget(self.params)
        v.addWidget(self.params_box)

        g = QGroupBox("Members (station order)")
        gl = QVBoxLayout(g)
        self.members = QListWidget()
        self.members.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.members.setMaximumHeight(170)
        gl.addWidget(self.members)
        row = QHBoxLayout()
        for text, fn in (("Add...", self._add_members), ("Remove", self._remove_members),
                         ("Up", lambda: self._move_member(-1)), ("Down", lambda: self._move_member(1)),
                         ("Make lead", self._make_lead)):
            btn = QPushButton(text)
            btn.clicked.connect(fn)
            row.addWidget(btn)
        row.addStretch()
        gl.addLayout(row)
        v.addWidget(g)

        g = QGroupBox("Behaviour")
        f = QFormLayout(g)
        f.addRow(b.check(QCheckBox("Keep members on station (move with the lead, follow setting changes)"),
                         "keep_on_station"))
        f.addRow(b.check(QCheckBox("Give every unit the formation heading"), "set_heading"))
        f.addRow(b.check(QCheckBox("Build as a CMO group with formation stations"), "group_in_cmo"))
        self.stype = QComboBox()
        self.stype.addItem("Rotating - stations turn with the group's course", "Rotating")
        self.stype.addItem("Fixed - stations keep their true bearing", "Fixed")
        b.combo(self.stype, "station_type")
        f.addRow("Stations:", self.stype)
        f.addRow(b.check(QCheckBox("Sprint and drift (ASW escorts)"), "sprint_drift"))
        self.notes = b.text(QPlainTextEdit(), "notes")
        self.notes.setMaximumHeight(60)
        self.notes.setPlaceholderText("Notes (not exported)")
        f.addRow("Notes:", self.notes)
        v.addWidget(g)
        row = QHBoxLayout()
        apply_btn = QPushButton("Put members on station now")
        apply_btn.clicked.connect(self._apply_now)
        show = QPushButton("Show on map")
        show.clicked.connect(self._show_on_map)
        row.addWidget(apply_btn)
        row.addWidget(show)
        row.addStretch()
        v.addLayout(row)
        v.addStretch()
        split.addWidget(scroll)

        # ------------------------------------------------ preview + stations
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.preview = FormationPreview()
        rl.addWidget(self.preview, 3)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Unit", "Rel. brg", "True brg", "Distance"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rl.addWidget(self.table, 2)
        split.addWidget(right)
        split.setSizes([260, 520, 520])

    # ------------------------------------------------------------------ helpers
    def _f(self) -> Optional[Formation]:
        return self.project.formation(self.fid)

    def _edit_formation(self, label: str, fn, merge: Optional[str] = None) -> None:
        f = self._f()
        if f is None:
            return
        with self.edit(label, "formations", merge=merge):
            fn(f)
            if f.keep_on_station:
                apply_formation(self.project, f)
        self._show_geometry()

    def _geom(self, attr: str, value) -> None:
        f = self._f()
        if f is None or getattr(f, attr) == value or getattr(self, "_loading", False):
            return
        self._edit_formation(f"Formation {attr}", lambda ff: setattr(ff, attr, value), merge=f"{f.id}.{attr}")

    def _attr_changed(self, attr: str) -> None:
        if attr == "name":
            self._refresh_list()
        if attr == "keep_on_station":
            f = self._f()
            if f and f.keep_on_station:
                self._apply_now()

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        if not self._f():
            self.fid = self.project.formations[0].id if self.project.formations else ""
        self._refresh_list()
        self._load()

    def _refresh_list(self):
        p = self.project
        self.list.blockSignals(True)
        self.list.clear()
        for f in p.formations:
            it = QListWidgetItem(f"{f.name}\n    {preset(f.preset).label} · {len(f.members) + 1} units · "
                                 f"{p.side_name(f.side)}")
            it.setData(Qt.ItemDataRole.UserRole, f.id)
            side = p.side(f.side)
            if side:
                it.setForeground(QColor(side.color))
            self.list.addItem(it)
            if f.id == self.fid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    def _load(self):
        f = self._f()
        p = self.project
        self._loading = True
        try:
            self.b.load()
            for w in (self.name, self.preset, self.lead, self.spacing, self.heading, self.alt_step, self.mirror,
                      self.jitter, self.seed, self.members, self.params_box, self.stype, self.notes):
                w.setEnabled(f is not None)
            if f is None:
                self.side_label.setText("")
                self.preview.show_formation(None)
                self.table.setRowCount(0)
                self.members.clear()
                return
            self.side_label.setText(p.side_name(f.side))
            self.preset.set_key(f.preset)
            leads = [(f"{u.display_name()}  [{u.type}]", u.id) for u in p.units
                     if u.side == f.side and not u.host and (u.id == f.lead or u.id in f.members or
                                                             not self._in_other_formation(u.id, f))]
            self.lead.set_items(leads, blank="(none)", keep=False)
            self.lead.set_current_id(f.lead)
            self.spacing.set_nm(f.spacing_nm)
            for w, val in ((self.heading, f.heading), (self.jitter, f.jitter), (self.seed, f.seed)):
                w.blockSignals(True)
                w.setValue(val)
                w.blockSignals(False)
            self.alt_step.blockSignals(True)
            self.alt_step.setValue(self.alt_step.minimum() if f.alt_step_m is None else f.alt_step_m)
            self.alt_step.blockSignals(False)
            self.mirror.blockSignals(True)
            self.mirror.setChecked(f.mirror)
            self.mirror.blockSignals(False)
            self.params.build(f)
            self.members.clear()
            for i, uid in enumerate(f.members):
                u = p.unit(uid)
                it = QListWidgetItem(f"{i + 1}. {u.display_name() if u else '(missing)'}" +
                                     (f"  -  {u.db_name}" if u and u.db_name else ""))
                it.setData(Qt.ItemDataRole.UserRole, uid)
                self.members.addItem(it)
        finally:
            self._loading = False
        self._show_geometry()

    def _show_geometry(self):
        f = self._f()
        p = self.project
        if f is None:
            return
        side = p.side(f.side)
        names = [(p.unit(uid).name if p.unit(uid) else "?") for uid in f.members]
        self.preview.unit = self.spacing.unit.currentText()
        self.preview.show_formation(f, color=side.color if side else "", labels=names)
        lead = p.unit(f.lead)
        sts = stations(f, lead.lat if lead else 0.0, lead.lon if lead else 0.0)
        self.table.setRowCount(len(sts))
        unit = self.spacing.unit.currentText()
        for r, st in enumerate(sts):
            u = p.unit(st.unit_id)
            vals = [str(r + 1), u.name if u else "?", f"{st.rel_bearing:05.1f}°", f"{st.true_bearing:05.1f}°",
                    fmt_dist(st.distance_nm, unit) + (f"  {st.alt_offset_m:+.0f} m" if st.alt_offset_m else "")]
            for c, val in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(val))

    def _in_other_formation(self, uid: str, f: Formation) -> bool:
        return any(o.id != f.id and (o.lead == uid or uid in o.members) for o in self.project.formations)

    # ------------------------------------------------------------------ list actions
    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.fid = cur.data(Qt.ItemDataRole.UserRole)
            self._load()

    def select_formation(self, fid: str) -> None:
        self.fid = fid
        self.refresh()

    def _from_units(self):
        p = self.project
        free = [u for u in p.units if not u.host and not any(f.lead == u.id or u.id in f.members
                                                               for f in p.formations)]
        items = [(f"{u.display_name()}  ({p.side_name(u.side)}, {u.type})", u.id) for u in free]
        dlg = PickerDialog("Units for the new formation (first one selected becomes the lead)", items, parent=self)
        if dlg.exec() and dlg.selected_ids():
            self.create_from_units(dlg.selected_ids())

    def create_from_units(self, ids: list[str]) -> Optional[Formation]:
        p = self.project
        units = [p.unit(i) for i in ids if p.unit(i)]
        if not units:
            return None
        lead = units[0]
        units = [u for u in units if u.side == lead.side and not u.host]
        key = default_preset_for(units)
        f = Formation(name=self._unique_name(f"{lead.name} group"), side=lead.side, preset=key, lead=lead.id,
                      members=[u.id for u in units[1:]], spacing_nm=PRESETS[key].spacing_nm,
                      heading=float(lead.heading or 0.0))
        with self.edit("New formation", "formations"):
            p.formations.append(f)
            apply_formation(p, f)
        self.fid = f.id
        self.refresh()
        return f

    def _unique_name(self, base: str) -> str:
        names = {f.name for f in self.project.formations}
        if base not in names:
            return base
        i = 2
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def _duplicate(self):
        f = self._f()
        if not f:
            return
        d = copy.deepcopy(f)
        d.id = new_id("f")
        d.name = self._unique_name(f.name + " (copy)")
        d.lead, d.members = "", []          # units can only be in one formation
        with self.edit("Duplicate formation", "formations"):
            self.project.formations.append(d)
        self.fid = d.id
        self.refresh()

    def _delete(self):
        f = self._f()
        if not f:
            return
        if QMessageBox.question(self, "Delete formation", f"Delete formation '{f.name}'? The units stay where "
                                                          f"they are.") != QMessageBox.StandardButton.Yes:
            return
        with self.edit("Delete formation", "formations"):
            self.project.formations = [x for x in self.project.formations if x.id != f.id]
        self.fid = ""
        self.refresh()

    # ------------------------------------------------------------------ editor actions
    def _preset_changed(self, *_):
        key = self.preset.key()
        f = self._f()
        if not f or not key or key == f.preset or self._loading:
            return

        def change(ff):
            ff.preset = key
            ff.params = {}
            ff.alt_step_m = None
            ff.spacing_nm = PRESETS[key].spacing_nm
        self._edit_formation("Change formation layout", change)
        self._load()
        self._refresh_list()

    def _lead_changed(self, *_):
        f = self._f()
        new = self.lead.current_id()
        if not f or self._loading or new == f.lead:
            return

        def change(ff):
            old = ff.lead
            ff.members = [m for m in ff.members if m != new]
            if old:
                ff.members.insert(0, old)
            ff.lead = new
        self._edit_formation("Change formation lead", change)
        self._load()

    def _add_members(self):
        f = self._f()
        if not f:
            return
        p = self.project
        items = [(f"{u.display_name()}  [{u.type}]  -  {u.db_name}", u.id) for u in p.units
                 if u.side == f.side and not u.host and u.id != f.lead and u.id not in f.members
                 and not self._in_other_formation(u.id, f)]
        dlg = PickerDialog("Add members", items, parent=self)
        if dlg.exec() and dlg.selected_ids():
            self._edit_formation("Add formation members", lambda ff: ff.members.extend(dlg.selected_ids()))
            self._load()
            self._refresh_list()

    def _selected_members(self) -> list[str]:
        return [it.data(Qt.ItemDataRole.UserRole) for it in self.members.selectedItems()]

    def _remove_members(self):
        gone = set(self._selected_members())
        if gone:
            self._edit_formation("Remove formation members",
                                 lambda ff: setattr(ff, "members", [m for m in ff.members if m not in gone]))
            self._load()
            self._refresh_list()

    def _move_member(self, d: int):
        f = self._f()
        row = self.members.currentRow()
        if not f or not (0 <= row < len(f.members)) or not (0 <= row + d < len(f.members)):
            return

        def change(ff):
            ff.members[row], ff.members[row + d] = ff.members[row + d], ff.members[row]
        self._edit_formation("Reorder formation", change)
        self._load()
        self.members.setCurrentRow(row + d)

    def _make_lead(self):
        sel = self._selected_members()
        if sel:
            self.lead.set_current_id(sel[0])
            self._lead_changed()

    def _apply_now(self):
        f = self._f()
        if f:
            with self.edit("Put formation on station", "formations"):
                n = apply_formation(self.project, f)
            self._show_geometry()
            self.ctx.status(f"{f.name}: {n} unit(s) moved to their stations.")

    def _show_on_map(self):
        f = self._f()
        lead = self.project.unit(f.lead) if f else None
        if lead and self.ctx.window:
            self.ctx.window.show_on_map(lead.lat, lead.lon)
            self.doc.select(lead.id)

    # ------------------------------------------------------------------ creator
    def open_creator(self):
        dlg = FormationCreator(self.ctx, self)
        if dlg.exec() and dlg.created_id:
            self.fid = dlg.created_id
            self.refresh()


class FormationCreator(QDialog):
    """Create new units from database entries, already in formation."""

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.created_id = ""
        self.setWindowTitle("Create units in formation")
        self.resize(1050, 680)
        p = ctx.project
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        g = QGroupBox("Composition (the first unit of the first row is the lead)")
        gl = QVBoxLayout(g)
        self.rows = QTableWidget(0, 4)
        self.rows.setHorizontalHeaderLabels(["Database entry", "Type", "DBID", "Count"])
        self.rows.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rows.verticalHeader().setVisible(False)
        gl.addWidget(self.rows)
        row = QHBoxLayout()
        add = QPushButton("Add the entry selected in the Database panel")
        add.clicked.connect(self._add_entry)
        rem = QPushButton("Remove row")
        rem.clicked.connect(lambda: self.rows.removeRow(self.rows.currentRow()) or self._update())
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch()
        gl.addLayout(row)
        gl.addWidget(hint_label("Select an entry in the Database panel (it stays open beside this window), then "
                                "press Add. Example: one carrier row with count 1, then a destroyer row with "
                                "count 6."))
        left.addWidget(g)

        g = QGroupBox("Formation")
        f = QFormLayout(g)
        self.name = QLineEdit("Task Group 1")
        f.addRow("Name / group:", self.name)
        self.side = IdCombo()
        self.side.set_items([(s.name, s.id) for s in p.sides])
        w = ctx.window
        if w and hasattr(w, "map_page"):
            self.side.set_current_id(w.map_page.current_side())
        f.addRow("Side:", self.side)
        self.preset = PresetCombo()
        self.preset.set_key("circular_screen")
        self.preset.currentIndexChanged.connect(self._preset_changed)
        f.addRow("Layout:", self.preset)
        self.help = hint_label("")
        f.addRow("", self.help)
        self.coords = CoordEdit()
        lat, lon = (w.map_page.map.center() if w and hasattr(w, "map_page") else (0.0, 0.0))
        self.lat, self.lon = lat, lon
        self.coords.set_coords(lat, lon)
        self.coords.coordsEdited.connect(self._coords)
        f.addRow("Lead position:", self.coords)
        self.spacing = SpacingEdit(lambda nm: self._update())
        f.addRow("Spacing:", self.spacing)
        self.heading = QDoubleSpinBox()
        self.heading.setRange(0, 359.9)
        self.heading.setWrapping(True)
        self.heading.setSuffix("°")
        self.heading.valueChanged.connect(self._update)
        f.addRow("Orientation:", self.heading)
        self.alt = QDoubleSpinBox()
        self.alt.setRange(30, 25000)
        self.alt.setValue(9000)
        self.alt.setSuffix(" m")
        f.addRow("Altitude (aircraft):", self.alt)
        left.addWidget(g)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok = bb.addButton("Create", QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok.setProperty("primary", True)
        bb.accepted.connect(self._create)
        bb.rejected.connect(self.reject)
        left.addWidget(bb)
        lay.addLayout(left, 3)
        self.preview = FormationPreview()
        lay.addWidget(self.preview, 2)
        self._preset_changed()
        if ctx.window is not None and getattr(ctx.window, "db_browser", None) and ctx.window.db_browser.current:
            self._add_entry()

    def _formation(self) -> Formation:
        return Formation(preset=self.preset.key() or "line_ahead", spacing_nm=self.spacing.nm(),
                         heading=float(self.heading.value()), members=[""] * max(0, self._total() - 1))

    def _total(self) -> int:
        n = 0
        for r in range(self.rows.rowCount()):
            w = self.rows.cellWidget(r, 3)
            n += w.value() if w else 0
        return n

    def _preset_changed(self, *_):
        pre = preset(self.preset.key() or "line_ahead")
        self.help.setText(pre.help)
        self.spacing.set_nm(pre.spacing_nm)
        self.spacing.unit.setCurrentText("m" if pre.spacing_nm < 0.2 else "nm")
        self._update()

    def _coords(self, lat, lon):
        self.lat, self.lon = lat, lon

    def _update(self, *_):
        self.preview.unit = self.spacing.unit.currentText()
        side = self.ctx.project.side(self.side.current_id())
        self.preview.show_formation(self._formation(), color=side.color if side else "")
        self.ok.setEnabled(self._total() >= 1)

    def _add_entry(self):
        w = self.ctx.window
        e = w.db_browser.current if w is not None else None
        if e is None or e.type not in DOMAIN_FOR_TYPE:
            QMessageBox.information(self, "Composition", "Select a unit (aircraft, ship, submarine, facility or "
                                                         "ground unit) in the Database panel first.")
            return
        r = self.rows.rowCount()
        self.rows.insertRow(r)
        item = QTableWidgetItem(e.name)
        item.setData(Qt.ItemDataRole.UserRole, e)
        self.rows.setItem(r, 0, item)
        self.rows.setItem(r, 1, QTableWidgetItem(e.type))
        self.rows.setItem(r, 2, QTableWidgetItem(str(e.id)))
        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setValue(1 if r == 0 else 4)
        spin.valueChanged.connect(self._update)
        self.rows.setCellWidget(r, 3, spin)
        if r == 0:
            domain = DOMAIN_FOR_TYPE[e.type]
            self.preset.set_key(DEFAULT_PRESET[domain])
            self._preset_changed()
        self._update()

    def _create(self):
        p = self.ctx.project
        sid = self.side.current_id()
        if not sid or self._total() < 1:
            return
        db = self.ctx.db
        units: list[Unit] = []
        taken = {u.name for u in p.units if u.side == sid}
        for r in range(self.rows.rowCount()):
            e = self.rows.item(r, 0).data(Qt.ItemDataRole.UserRole)
            n = self.rows.cellWidget(r, 3).value()
            for i in range(n):
                name = base = e.name if n == 1 else f"{e.name} {i + 1}"
                k = 2
                while name in taken:
                    name, k = f"{base} ({k})", k + 1
                taken.add(name)
                u = Unit(side=sid, type=e.type, dbid=e.id, db_name=e.name, name=name, lat=self.lat, lon=self.lon)
                if e.type == "Aircraft":
                    u.altitude = float(self.alt.value())
                    los = db.loadouts(e.id, combat_only=True) if db else []
                    u.loadout = los[0].id if los else None
                units.append(u)
        f = self._formation()
        f.name = self.name.text().strip() or "Task Group"
        f.side = sid
        f.lead = units[0].id
        f.members = [u.id for u in units[1:]]
        with self.ctx.doc.modify("Create units in formation", "formations"):
            p.units.extend(units)
            p.formations.append(f)
            apply_formation(p, f)
        self.created_id = f.id
        self.ctx.doc.select(units[0].id)
        self.ctx.status(f"Created {len(units)} unit(s) in formation '{f.name}'.")
        self.accept()
