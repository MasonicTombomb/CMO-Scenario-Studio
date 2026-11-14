"""Edit many units at once: tick the fields to change, leave the rest as they are."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget)

from ..model.enums import HOST_TYPES, PROFICIENCY
from ..model.project import Project, Unit
from .widgets import IdCombo, hint_label, parse_lua_scalar

YES_NO = (("Yes", True), ("No", False))


def rename(pattern: str, u: Unit, n: int, p: Project) -> str:
    """Pattern placeholders: {name} current name, {n} running number, {nn} zero-padded, {class}, {side}, {type}."""
    try:
        return pattern.format(name=u.name, n=n, nn=f"{n:02d}", cls=u.db_name, side=p.side_name(u.side),
                              type=u.type, **{"class": u.db_name}).strip() or u.name
    except (KeyError, IndexError, ValueError):
        return u.name


def change_side(p: Project, u: Unit, sid: str) -> None:
    """Move a unit to another side, dropping links that only make sense on the old side."""
    if u.side == sid:
        return
    u.side = sid
    host = p.unit(u.host) if u.host else None
    if host is not None and host.side != sid:
        u.host = ""
    for m in p.missions:
        if m.side != sid and u.id in m.units:
            m.units.remove(u.id)
        if m.side == sid and u.id in m.targets:
            m.targets.remove(u.id)
    for f in p.formations:
        if f.side != sid:
            if u.id in f.members:
                f.members.remove(u.id)
            if f.lead == u.id:
                f.lead = f.members.pop(0) if f.members else ""


class BulkEditDialog(QDialog):
    def __init__(self, ctx, unit_ids: list[str], parent=None):
        super().__init__(parent)
        self.ctx = ctx
        p = ctx.project
        self.units = [p.unit(i) for i in unit_ids if p.unit(i)]
        self.setWindowTitle(f"Edit {len(self.units)} units")
        self.resize(640, 640)
        self.fields: list[tuple[QCheckBox, Callable[[Project, Unit, int], None]]] = []
        lay = QVBoxLayout(self)
        types = sorted({u.type for u in self.units})
        sides = sorted({p.side_name(u.side) for u in self.units})
        lay.addWidget(QLabel(f"<b>{len(self.units)} units</b> · {', '.join(types)} · {', '.join(sides)}"))
        lay.addWidget(hint_label("Tick a field to change it on every selected unit; unticked fields are left as "
                                 "they are. One undo step reverts everything."))

        # ------------------------------------------------ identity
        g = QGroupBox("Identity")
        self.grid_identity = QGridLayout(g)
        self._row = 0
        self.rename = QLineEdit("{name}")
        self.rename.setToolTip("{name} current name, {n} running number, {nn} 01, 02..., {class} DB class, "
                               "{side}, {type}")
        self.start_n = QSpinBox()
        self.start_n.setRange(0, 9999)
        self.start_n.setValue(1)
        box = QWidget()
        bl = QHBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(self.rename, 1)
        bl.addWidget(QLabel("first {n}:"))
        bl.addWidget(self.start_n)
        self._add(self.grid_identity, "Rename", box, lambda p, u, i: setattr(u, "name", rename(
            self.rename.text(), u, self.start_n.value() + i, p)))
        self.side = IdCombo()
        self.side.set_items([(s.name, s.id) for s in p.sides])
        if self.units:
            self.side.set_current_id(self.units[0].side)
        self._add(self.grid_identity, "Side", self.side, lambda p, u, i: change_side(p, u, self.side.current_id()))
        self.group = QLineEdit()
        self.group.setPlaceholderText("blank clears the group tag")
        self._add(self.grid_identity, "Group tag", self.group, lambda p, u, i: setattr(u, "group",
                                                                                       self.group.text().strip()))
        self.count = QSpinBox()
        self.count.setRange(1, 500)
        self._add(self.grid_identity, "Count", self.count, lambda p, u, i: setattr(u, "count", self.count.value()))
        lay.addWidget(g)

        # ------------------------------------------------ behaviour
        g = QGroupBox("Behaviour")
        grid = QGridLayout(g)
        self._row = 0
        self.prof = QComboBox()
        self.prof.addItem("(side default)", "")
        for x in PROFICIENCY:
            self.prof.addItem(x, x)
        self._add(grid, "Proficiency", self.prof, lambda p, u, i: setattr(u, "proficiency", self.prof.currentData()))
        for attr, label in (("radar_active", "Radar active"), ("sonar_active", "Sonar active"),
                            ("hold_position", "Hold position"), ("autodetectable", "Auto-detectable"),
                            ("reserve", "Reinforcement (spawned by event)")):
            cb = QComboBox()
            for text, val in YES_NO:
                cb.addItem(text, val)
            self._add(grid, label, cb, lambda p, u, i, a=attr, w=cb: setattr(u, a, bool(w.currentData())))
        lay.addWidget(g)

        # ------------------------------------------------ movement
        g = QGroupBox("Movement and position")
        grid = QGridLayout(g)
        self._row = 0
        self.heading = self._opt_spin(0, 359.9, "°", wrap=True)
        self._add(grid, "Heading", self.heading, lambda p, u, i: setattr(u, "heading", self._opt(self.heading)))
        self.speed = self._opt_spin(0, 3000, " kt")
        self._add(grid, "Speed", self.speed, lambda p, u, i: setattr(u, "speed", self._opt(self.speed)))
        self.alt = self._opt_spin(0, 30000, " m")
        self._add(grid, "Altitude (airborne aircraft)", self.alt,
                  lambda p, u, i: u.type == "Aircraft" and not u.host and setattr(u, "altitude", self._opt(self.alt)))
        self.depth = self._opt_spin(0, 3000, " m")
        self._add(grid, "Depth (submarines)", self.depth,
                  lambda p, u, i: u.type == "Submarine" and setattr(u, "depth", self._opt(self.depth)))
        self.host = IdCombo()
        first_side = self.units[0].side if self.units else ""
        self.host.set_items([(f"{h.name}  [{h.type}]", h.id) for h in p.units if h.side == first_side and
                             h.type in HOST_TYPES and not h.host and h.id not in unit_ids], blank="(own position)")
        self._add(grid, "Starts at (same side only)", self.host, self._apply_host)
        lay.addWidget(g)

        # ------------------------------------------------ aircraft
        same_aircraft = len({u.dbid for u in self.units}) == 1 and self.units and self.units[0].type == "Aircraft"
        g = QGroupBox("Aircraft loadout" + ("" if same_aircraft else " (select aircraft of one type)"))
        grid = QGridLayout(g)
        self._row = 0
        self.loadout = QComboBox()
        self.loadout.addItem(f"(reserve - loadout {p.build.default_loadout})", None)
        db = ctx.db
        if same_aircraft and db:
            for lo in db.loadouts(int(self.units[0].dbid)):
                self.loadout.addItem(f"{lo.id}  [{lo.role}]  {lo.name}", lo.id)
        self._add(grid, "Loadout", self.loadout, lambda p, u, i: setattr(u, "loadout", self.loadout.currentData()))
        g.setEnabled(bool(same_aircraft))
        lay.addWidget(g)

        # ------------------------------------------------ extra fields
        g = QGroupBox("Extra ScenEdit_SetUnit field")
        grid = QGridLayout(g)
        self._row = 0
        box = QWidget()
        bl = QHBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        self.extra_key = QLineEdit()
        self.extra_key.setPlaceholderText("field, e.g. fuel")
        self.extra_val = QLineEdit()
        self.extra_val.setPlaceholderText("value (blank removes the field)")
        bl.addWidget(self.extra_key)
        bl.addWidget(self.extra_val)
        self._add(grid, "Set field", box, self._apply_extra)
        lay.addWidget(g)

        lay.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok = bb.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok.setProperty("primary", True)
        bb.accepted.connect(self._apply)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.changed = 0

    # ------------------------------------------------------------------ building
    def _add(self, grid: QGridLayout, label: str, editor: QWidget, fn: Callable[[Project, Unit, int], Any]) -> None:
        cb = QCheckBox(label)
        editor.setEnabled(False)
        cb.toggled.connect(editor.setEnabled)
        grid.addWidget(cb, self._row, 0)
        grid.addWidget(editor, self._row, 1)
        grid.setColumnStretch(1, 1)
        self._row += 1
        self.fields.append((cb, fn))

    @staticmethod
    def _opt_spin(lo: float, hi: float, suffix: str, wrap: bool = False) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo - 1, hi)
        w.setSpecialValueText("default")
        w.setSuffix(suffix)
        w.setWrapping(wrap)
        w.setValue(lo - 1)
        return w

    @staticmethod
    def _opt(w: QDoubleSpinBox):
        return None if w.value() == w.minimum() else float(w.value())

    # ------------------------------------------------------------------ apply
    def _apply_host(self, p: Project, u: Unit, i: int) -> None:
        hid = self.host.current_id()
        h = p.unit(hid) if hid else None
        if h is None:
            u.host = ""
        elif h.side == u.side and u.id != h.id:
            u.host = h.id
            u.lat, u.lon = h.lat, h.lon

    def _apply_extra(self, p: Project, u: Unit, i: int) -> None:
        key = self.extra_key.text().strip()
        if not key:
            return
        if self.extra_val.text().strip() == "":
            u.extra.pop(key, None)
        else:
            u.extra[key] = parse_lua_scalar(self.extra_val.text())

    def selected_fields(self) -> list[str]:
        return [cb.text() for cb, _ in self.fields if cb.isChecked()]

    def apply_to_project(self) -> int:
        """Apply the ticked fields (inside the caller's undo step). Returns the number of units changed."""
        p = self.ctx.project
        todo = [fn for cb, fn in self.fields if cb.isChecked()]
        for i, uid in enumerate([u.id for u in self.units]):
            u = p.unit(uid)
            if u is None:
                continue
            for fn in todo:
                fn(p, u, i)
        return len(self.units) if todo else 0

    def _apply(self) -> None:
        if not self.selected_fields():
            self.reject()
            return
        with self.ctx.doc.modify(f"Edit {len(self.units)} units", "units"):
            self.units = [self.ctx.project.unit(u.id) for u in self.units]
            self.changed = self.apply_to_project()
        self.ctx.status(f"Changed {', '.join(self.selected_fields()).lower()} on {self.changed} unit(s).")
        self.accept()
