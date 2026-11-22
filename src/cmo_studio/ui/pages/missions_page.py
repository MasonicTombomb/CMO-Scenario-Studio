"""Missions: class/type, area, assigned units, strike targets and ScenEdit_SetMission options."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QListWidget,
                             QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter,
                             QVBoxLayout, QWidget)

from ...model.enums import MISSION_CLASS_LABELS, MISSION_CLASSES, MISSION_NEEDS_ZONE, MISSION_OPTIONS
from ...model.project import Mission
from ..intercept_form import InterceptForm
from ..widgets import IdCombo, IdListEditor, KeyValueTable, hint_label
from .base import AppContext, Binder, Page


class MissionsPage(Page):
    title = "Missions"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.mid = ""
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.side_filter = IdCombo()
        self.side_filter.currentIndexChanged.connect(lambda *_: self._refresh_list())
        ll.addWidget(self.side_filter)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._pick)
        ll.addWidget(self.list)
        row = QHBoxLayout()
        for text, fn in (("New mission", self._new), ("Duplicate", self._dup), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        v = QVBoxLayout(body)
        b = self.b = Binder(self, lambda: self.project.mission(self.mid), "missions", self._changed_attr)

        g = QGroupBox("Mission")
        f = QFormLayout(g)
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        self.side = IdCombo()
        b.combo(self.side, "side")
        f.addRow("Side:", self.side)
        self.mclass = QComboBox()
        for k, label in MISSION_CLASS_LABELS.items():
            self.mclass.addItem(label, k)
        b.combo(self.mclass, "mclass")
        f.addRow("Class:", self.mclass)
        self.subtype = QComboBox()
        self.subtype.currentIndexChanged.connect(self._subtype)
        f.addRow("Type:", self.subtype)
        self.zone = IdCombo()
        self.zone.currentIndexChanged.connect(lambda *_: self._set("zone", self.zone.current_id()))
        f.addRow("Area:", self.zone)
        self.pzone = IdCombo()
        self.pzone.currentIndexChanged.connect(lambda *_: self._set("prosecution_zone", self.pzone.current_id()))
        f.addRow("Prosecution area:", self.pzone)
        self.dest = IdCombo()
        self.dest.currentIndexChanged.connect(lambda *_: self._set("destination", self.dest.current_id()))
        f.addRow("Destination:", self.dest)
        v.addWidget(g)

        self.intercept = InterceptForm()
        self.intercept.edited.connect(self._intercept)
        self.intercept.presetChosen.connect(self._intercept_preset)
        self.intercept.baseTicked.connect(self._intercept_base)
        v.addWidget(self.intercept)

        g = QGroupBox("Options")
        f = QFormLayout(g)
        self.opt_widgets = {}
        for key, (label, kind) in MISSION_OPTIONS.items():
            if kind == "bool":
                w = QComboBox()
                w.addItem("(default)", None)
                w.addItem("Yes", True)
                w.addItem("No", False)
                w.currentIndexChanged.connect(lambda _i, k=key, cw=w: self._opt(k, cw.currentData()))
            elif kind == "int":
                w = QSpinBox()
                w.setRange(0, 99)
                w.setSpecialValueText("(default)")
                w.valueChanged.connect(lambda val, k=key: self._opt(k, val or None))
            else:
                w = QLineEdit()
                w.editingFinished.connect(lambda k=key, lw=w: self._opt(k, lw.text().strip() or None))
            self.opt_widgets[key] = w
            f.addRow(label + ":", w)
        v.addWidget(g)
        g = QGroupBox("Other ScenEdit_SetMission fields")
        gv = QVBoxLayout(g)
        self.extra = KeyValueTable("Field", "Value")
        self.extra.setMaximumHeight(130)
        self.extra.dataChanged.connect(self._extra)
        gv.addWidget(self.extra)
        gv.addWidget(hint_label("Anything ScenEdit_SetMission accepts, e.g. TransitThrottleAircraft = 'Cruise'. "
                                "Unknown fields are reported in the build report, not fatal."))
        v.addWidget(g)

        row = QHBoxLayout()
        g = QGroupBox("Assigned units")
        gv = QVBoxLayout(g)
        self.units = IdListEditor("Assign units")
        self.units.set_source(self._unit_choices)
        self.units.idsChanged.connect(lambda ids: self._set("units", ids))
        gv.addWidget(self.units)
        row.addWidget(g)
        self.tgt_box = QGroupBox("Strike targets")
        gv = QVBoxLayout(self.tgt_box)
        self.targets = IdListEditor("Add targets")
        self.targets.set_source(self._target_choices)
        self.targets.idsChanged.connect(lambda ids: self._set("targets", ids))
        gv.addWidget(self.targets)
        row.addWidget(self.tgt_box)
        v.addLayout(row)
        self.notes = b.text(QPlainTextEdit(), "notes")
        self.notes.setPlaceholderText("Notes (not exported)")
        self.notes.setMaximumHeight(70)
        v.addWidget(self.notes)
        v.addStretch()
        split.addWidget(scroll)
        split.setSizes([300, 800])

    # ------------------------------------------------------------------ helpers
    def _m(self) -> Mission | None:
        return self.project.mission(self.mid)

    def _unit_choices(self):
        m = self._m()
        p = self.project
        return [(f"{u.display_name()}  -  {u.db_name}" + ("  [reinforcement]" if u.reserve else ""), u.id)
                for u in p.units if m and u.side == m.side and (m.mclass != "intercept" or u.type == "Aircraft")]

    def _target_choices(self):
        m = self._m()
        p = self.project
        return [(f"{u.display_name()}  ({p.side_name(u.side)})  -  {u.db_name}", u.id)
                for u in p.units if m and u.side != m.side]

    def _set(self, attr, value):
        m = self._m()
        if m is None or getattr(m, attr) == value:
            return
        with self.edit(f"Mission {attr}", "missions"):
            setattr(m, attr, value)
        self._load()

    # ------------------------------------------------------------------ intercepts
    def _intercept(self, attr, value):
        from ...model.intercept import intercept_of
        m = self._m()
        if m is None or getattr(intercept_of(m), attr) == value:
            return
        with self.edit("Intercept conditions", "missions", merge=f"ic.{m.id}.{attr}"):
            setattr(intercept_of(m), attr, value)
        self.intercept.load(self.project, m)

    def _intercept_preset(self, key):
        from ...model.intercept import PRESETS, apply_preset
        m = self._m()
        if m is not None:
            with self.edit(f"Intercept preset: {PRESETS[key][0]}", "missions"):
                apply_preset(m, key)
            self._load()

    def _intercept_base(self, base, on, move):
        from ...model.intercept import put_base_on_call
        m = self._m()
        if m is not None:
            with self.edit(f"{base} {'on' if on else 'off'} call", "missions"):
                put_base_on_call(self.project, m, base, on, move)
            self._refresh_list()
            self._load()

    def _opt(self, key, value):
        m = self._m()
        if m is None or m.options.get(key) == value:
            return
        with self.edit("Mission option", "missions", merge=f"opt.{key}"):
            if value is None:
                m.options.pop(key, None)
            else:
                m.options[key] = value

    def _extra(self, data):
        m = self._m()
        if not m:
            return
        with self.edit("Mission fields", "missions", merge="mextra"):
            for k in list(m.options):
                if k not in MISSION_OPTIONS:
                    m.options.pop(k)
            m.options.update(data)

    def _changed_attr(self, attr):
        if attr in ("mclass", "side", "name"):
            m = self._m()
            if attr == "mclass" and m:
                subs = MISSION_CLASSES.get(m.mclass, ())
                if subs and m.subtype not in subs:
                    with self.edit("Mission type", "missions"):
                        m.subtype = subs[0]
            self._refresh_list()
            self._load()

    def _subtype(self, *_):
        val = self.subtype.currentData()
        if val is not None:
            self._set("subtype", val)

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self.side_filter.set_items([(s.name, s.id) for s in self.project.sides], blank="All sides")
        self._refresh_list()
        self._load()

    def _refresh_list(self):
        p = self.project
        sid = self.side_filter.current_id()
        self.list.blockSignals(True)
        self.list.clear()
        for m in p.missions:
            if sid and m.side != sid:
                continue
            sub = f"/{m.subtype}" if MISSION_CLASSES.get(m.mclass) else ""
            it = QListWidgetItem(f"{m.name}   [{m.mclass}{sub}, {len(m.units)} unit(s)]")
            it.setData(Qt.ItemDataRole.UserRole, m.id)
            side = p.side(m.side)
            if side:
                it.setForeground(QColor(side.color))
            self.list.addItem(it)
            if m.id == self.mid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)

    def _load(self):
        p = self.project
        m = self._m()
        self.side.set_items([(s.name, s.id) for s in p.sides], keep=False)
        self.b.load()
        enabled = m is not None
        if not enabled:
            self.intercept.setVisible(False)
        for w in (self.name, self.side, self.mclass, self.subtype, self.zone, self.pzone, self.dest, self.units,
                  self.targets, self.extra, self.notes, *self.opt_widgets.values()):
            w.setEnabled(enabled)
        if not m:
            return
        subs = MISSION_CLASSES.get(m.mclass, ())
        self.subtype.blockSignals(True)
        self.subtype.clear()
        for s in subs:
            self.subtype.addItem(s.upper(), s)
        self.subtype.setEnabled(bool(subs))
        if subs:
            self.subtype.setCurrentIndex(max(0, self.subtype.findData(m.subtype)))
        self.subtype.blockSignals(False)
        zones = [(f"{z.name}  ({len(z.points)} pts, {'all sides' if z.all_sides else p.side_name(z.side)})", z.id)
                 for z in p.zones if z.side == m.side or z.all_sides]
        self.zone.set_items(zones, blank="(none)", keep=False)
        self.zone.set_current_id(m.zone)
        self.zone.setEnabled(m.mclass in MISSION_NEEDS_ZONE or m.mclass in ("strike", "intercept"))
        self.pzone.set_items(zones, blank="(none)", keep=False)
        self.pzone.set_current_id(m.prosecution_zone)
        self.pzone.setEnabled(m.mclass == "patrol")
        hosts = [(f"{u.name}  [{u.type}]", u.id) for u in p.units if u.side == m.side and u.type in
                 ("Facility", "Ship")]
        self.dest.set_items(hosts, blank="(none)", keep=False)
        self.dest.set_current_id(m.destination)
        self.dest.setEnabled(m.mclass == "ferry")
        for key, w in self.opt_widgets.items():
            val = m.options.get(key)
            w.blockSignals(True)
            if isinstance(w, QComboBox):
                w.setCurrentIndex(0 if val is None else (1 if val else 2))
            elif isinstance(w, QSpinBox):
                w.setValue(int(val or 0))
            else:
                w.setText("" if val is None else str(val))
            w.blockSignals(False)
        self.extra.set_data({k: v for k, v in m.options.items() if k not in MISSION_OPTIONS})
        labels = {u.id: f"{u.display_name()}  -  {u.db_name}" for u in p.units}
        self.units.set_ids(m.units, labels)
        tl = {u.id: f"{u.display_name()}  ({p.side_name(u.side)})" for u in p.units}
        self.targets.set_ids(m.targets, tl)
        self.tgt_box.setVisible(m.mclass == "strike")
        self.intercept.setVisible(m.mclass == "intercept")
        if m.mclass == "intercept":
            self.intercept.load(p, m)

    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.mid = cur.data(Qt.ItemDataRole.UserRole)
            self._load()

    def _new(self):
        p = self.project
        sid = self.side_filter.current_id() or (p.sides[0].id if p.sides else "")
        if not sid:
            return
        m = Mission(side=sid, name=f"Mission {len(p.missions) + 1}")
        zones = [z for z in p.zones if z.side == sid]
        if zones:
            m.zone = zones[0].id
        with self.edit("New mission", "missions"):
            p.missions.append(m)
        self.mid = m.id
        self.refresh()
        self.name.setFocus()
        self.name.selectAll()

    def _dup(self):
        import copy
        from ...model.project import new_id
        m = self._m()
        if not m:
            return
        d = copy.deepcopy(m)
        d.id = new_id("m")
        d.name = m.name + " (copy)"
        with self.edit("Duplicate mission", "missions"):
            self.project.missions.append(d)
        self.mid = d.id
        self.refresh()

    def _delete(self):
        m = self._m()
        if not m:
            return
        with self.edit("Delete mission", "missions"):
            self.project.missions = [x for x in self.project.missions if x.id != m.id]
        self.mid = ""
        self.refresh()
