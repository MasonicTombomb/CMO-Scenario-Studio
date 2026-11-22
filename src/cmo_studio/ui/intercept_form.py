"""The launch conditions of an intercept mission: check boxes with their values, and the response."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox,
                             QVBoxLayout, QWidget)

from ..model.intercept import (CONTACT_CONDITIONS, GATES, POSTURES, PRESETS, ROE, aircraft_at, apply_preset,
                               bases_with_aircraft, busy_with, describe, intercept_of)
from .widgets import IdCombo, hint_label


class InterceptForm(QWidget):
    """Edits ``mission.intercept``. Emits :attr:`edited` (attribute, value) and lets the page store it."""
    edited = pyqtSignal(str, object)
    presetChosen = pyqtSignal(str)
    baseTicked = pyqtSignal(str, bool, bool)        # base, on call, move its aircraft from other missions

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.mission = None
        self._loading = False
        self.boxes: dict[str, QCheckBox] = {}
        self.values: dict[str, QWidget] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        top = QGroupBox("Aircraft on call")
        tl = QVBoxLayout(top)
        self.bases = QListWidget()
        self.bases.setMaximumHeight(110)
        self.bases.setToolTip("Tick the air bases whose aircraft are on call for this mission; untick one to take its "
                              "aircraft off. Choose single aircraft under Assigned units.")
        self.bases.itemChanged.connect(self._base_changed)
        tl.addWidget(self.bases)
        tl.addWidget(hint_label("Give each base its own intercept mission: an aircraft can be on call for one only."))
        lay.addWidget(top)

        g = QGroupBox("Launch when a contact...")
        gl = QVBoxLayout(g)
        head = QHBoxLayout()
        self.logic = QComboBox()
        self.logic.addItem("meets ALL the ticked conditions", "all")
        self.logic.addItem("meets ANY of the ticked conditions", "any")
        self.logic.currentIndexChanged.connect(lambda *_: self._emit("logic", self.logic.currentData()))
        head.addWidget(self.logic, 1)
        self.presets = QPushButton("Presets ▾")
        self.presets.setToolTip("Tick a ready-made set of conditions, then change what you like")
        menu = QMenu(self.presets)
        for key, (label, _v) in PRESETS.items():
            menu.addAction(label, lambda k=key: self.presetChosen.emit(k))
        self.presets.setMenu(menu)
        head.addWidget(self.presets)
        gl.addLayout(head)
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        for row, (attr, label, tip) in enumerate(CONTACT_CONDITIONS):
            self._condition(grid, row, attr, label, tip, self._contact_value(attr))
        gl.addLayout(grid)
        self.missiles = self._check("missiles", "Also launch against missiles (cruise missiles), not only aircraft")
        gl.addWidget(self.missiles)
        lay.addWidget(g)

        g = QGroupBox("...and (always required as well)")
        grid = QGridLayout(g)
        grid.setColumnStretch(1, 1)
        for row, (attr, label, tip) in enumerate(GATES):
            self._condition(grid, row, attr, label, tip, self._gate_value(attr))
        lay.addWidget(g)

        g = QGroupBox("Response")
        f = QFormLayout(g)
        f.addRow("Aircraft per contact:", self._spin("per_contact", 1, 12))
        f.addRow("Contacts at once:", self._spin("max_contacts", 1, 24))
        f.addRow("Keep in reserve:", self._spin("reserve", 0, 99))
        self.roe = QComboBox()
        for k, label in ROE.items():
            self.roe.addItem(label, k)
        self.roe.currentIndexChanged.connect(lambda *_: self._emit("roe", self.roe.currentData()))
        f.addRow("Orders:", self.roe)
        f.addRow("Stand down after:", self._dspin("stand_down_min", 0.5, 240, " min"))
        f.addRow("Go home at:", self._spin("bingo_pct", 0, 90, " % fuel", "CMO decides"))
        f.addRow("", self._check("radar", "Radars on once launched"))
        f.addRow("", self._check("message", "Tell the side when aircraft scramble and stand down"))
        f.addRow("Set a flag on launch:", self._line("signal", "optional, e.g. QRA_AIRBORNE"))
        lay.addWidget(g)
        self.summary = hint_label("")
        lay.addWidget(self.summary)

    # ------------------------------------------------------------------ widgets
    def _emit(self, attr, value):
        if not self._loading and self.mission is not None:
            self.edited.emit(attr, value)

    def _check(self, attr, text, tip=""):
        cb = QCheckBox(text)
        cb.setToolTip(tip)
        cb.toggled.connect(lambda on, a=attr: self._emit(a, on))
        self.boxes[attr] = cb
        return cb

    def _spin(self, attr, lo, hi, suffix="", special=""):
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setSuffix(suffix)
        if special:
            w.setSpecialValueText(special)
        w.valueChanged.connect(lambda v, a=attr: self._emit(a, int(v)))
        self.values[attr] = w
        return w

    def _dspin(self, attr, lo, hi, suffix="", step=1.0):
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setDecimals(1 if hi <= 300 else 0)
        w.setSingleStep(step)
        w.setSuffix(suffix)
        w.valueChanged.connect(lambda v, a=attr: self._emit(a, float(v)))
        self.values[attr] = w
        return w

    def _line(self, attr, hint):
        w = QLineEdit()
        w.setPlaceholderText(hint)
        w.textEdited.connect(lambda t, a=attr: self._emit(a, t.strip()))
        self.values[attr] = w
        return w

    @staticmethod
    def _row(*widgets):
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            h.addWidget(QLabel(w) if isinstance(w, str) else w)
        h.addStretch(1)
        return box

    def _condition(self, grid, row, attr, label, tip, value):
        grid.addWidget(self._check(attr, label, tip), row, 0)
        if value is not None:
            grid.addWidget(value, row, 1)

    def _contact_value(self, attr):
        if attr == "in_area":
            self.area = QLabel()
            return self.area
        if attr == "near":
            self.defend = IdCombo()
            self.defend.setMinimumWidth(220)
            self.defend.currentIndexChanged.connect(lambda *_: self._emit("defend", self.defend.current_id()))
            return self._row(self._dspin("near_nm", 1, 2000, " nm", 10), "of", self.defend)
        if attr == "posture":
            self.postures = {}
            for k, name in POSTURES:
                cb = QCheckBox(name)
                cb.toggled.connect(lambda *_: self._emit("postures", [p for p, _n in POSTURES
                                                                      if self.postures[p].isChecked()]))
                self.postures[k] = cb
            return self._row(*self.postures.values())
        if attr == "inbound":
            return self._row("within", self._dspin("inbound_deg", 1, 180, "°", 5), "of it")
        if attr == "altitude":
            return self._row(self._dspin("alt_min", 0, 40000, " m", 500), "and",
                             self._dspin("alt_max", 0, 40000, " m", 500))
        if attr == "speed":
            return self._row(self._dspin("speed_min", 0, 4000, " kn", 25))
        if attr == "tracked":
            return self._row(self._dspin("tracked_min", 0.5, 240, " min"))
        return None

    def _gate_value(self, attr):
        if attr == "raid":
            return self._row(self._spin("raid_min", 1, 50))
        if attr == "window":
            return self._row("from", self._spin("window_from", 0, 60 * 24 * 30, " min", "the start"), "to",
                             self._spin("window_to", 0, 60 * 24 * 30, " min", "the end"))
        if attr == "flag":
            return self._line("flag_key", "e.g. BEAR_PROBE")
        return None

    # ------------------------------------------------------------------ data
    def load(self, project, mission) -> None:
        self.project, self.mission = project, mission
        ic = intercept_of(mission)
        self._loading = True
        self._load_bases()
        self.defend.set_items([(f"{u.name}", u.id) for u in project.units if u.side == mission.side and not u.host
                               and not (u.group and u.type == "Facility")], blank="the aircraft's base", keep=False)
        self.defend.set_current_id(ic.defend)
        for attr, cb in self.boxes.items():
            cb.setChecked(bool(getattr(ic, attr)))
        for attr, w in self.values.items():
            v = getattr(ic, attr)
            if isinstance(w, QLineEdit):
                if w.text() != v:
                    w.setText(v)
            else:
                w.setValue(v)
        for k, cb in self.postures.items():
            cb.setChecked(k in ic.postures)
        for cb, val in ((self.logic, ic.logic), (self.roe, ic.roe)):
            cb.setCurrentIndex(max(0, cb.findData(val)))
        z = project.zone(mission.zone) if mission.zone else None
        self.area.setText(z.name if z else "(choose the Area above)")
        self._enable(ic)
        self.summary.setText(describe(project, mission))
        self._loading = False

    def _enable(self, ic):
        """Grey out the values of unticked conditions."""
        for attr, names in (("near", ["near_nm"]), ("inbound", ["inbound_deg"]), ("altitude", ["alt_min", "alt_max"]),
                            ("speed", ["speed_min"]), ("tracked", ["tracked_min"]), ("raid", ["raid_min"]),
                            ("window", ["window_from", "window_to"]), ("flag", ["flag_key"])):
            for n in names:
                self.values[n].setEnabled(bool(getattr(ic, attr)))
        self.defend.setEnabled(ic.near or ic.inbound)
        self.area.setEnabled(ic.in_area)
        for cb in self.postures.values():
            cb.setEnabled(ic.posture)

    def _load_bases(self):
        """One tick box per base of the side: ticked when its aircraft are on call here, half-ticked when only some are."""
        p, m = self.project, self.mission
        self.bases.blockSignals(True)
        self.bases.clear()
        for key, name, n in bases_with_aircraft(p, m.side):
            ids = aircraft_at(p, m.side, key)
            mine = [x for x in ids if x in m.units]
            other: dict[str, int] = {}
            for x in ids:
                for o in busy_with(p, m, x):
                    other[o.name] = other.get(o.name, 0) + max(1, p.unit(x).count)
            text = f"{name}  ({n} aircraft" + "".join(f", {c} on {o}" for o, c in other.items()) + ")"
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, key)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if ids and len(mine) == len(ids) else
                             Qt.CheckState.PartiallyChecked if mine else Qt.CheckState.Unchecked)
            self.bases.addItem(it)
        if not self.bases.count():
            it = QListWidgetItem("(no aircraft of this side are at a base)")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.bases.addItem(it)
        self.bases.blockSignals(False)

    def _base_changed(self, item: QListWidgetItem):
        key = item.data(Qt.ItemDataRole.UserRole)
        if self._loading or self.mission is None or not key:
            return
        on = item.checkState() != Qt.CheckState.Unchecked
        move = False
        if on:
            p, m = self.project, self.mission
            busy = {p.unit(x).name: busy_with(p, m, x)[0].name for x in aircraft_at(p, m.side, key)
                    if busy_with(p, m, x)}
            if busy:
                names = ", ".join(busy) if len(busy) < 7 else f"{len(busy)} aircraft"
                move = QMessageBox.question(
                    self, "Aircraft on call", f"{names} at {key} are already on {', '.join(dict.fromkeys(busy.values()))}. "
                    "Move them to this mission?") == QMessageBox.StandardButton.Yes
        self.baseTicked.emit(key, on, move)
        self._load_bases()


__all__ = ["InterceptForm", "apply_preset"]
