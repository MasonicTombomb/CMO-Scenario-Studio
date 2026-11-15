"""Events: triggers, conditions and actions, with templates and a live preview of the generated Lua."""

from __future__ import annotations

import copy
from typing import Any, Optional

from PyQt6.QtCore import QDateTime, Qt, QTimeZone, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton, QSpinBox, QSplitter,
                             QTabWidget, QVBoxLayout, QWidget)

from ...export.compiler import CompileError, compile_event
from ...model.enums import ACTION_TYPES, CONDITION_TYPES, REGULAR_INTERVALS, TRIGGER_TYPES
from ...model.project import Action, Condition, Event, Trigger, new_id
from ..widgets import CodeEditor, IdCombo, hint_label
from .base import AppContext, Binder, Page

TARGET_TYPES = ["", "Aircraft", "Ship", "Submarine", "Facility"]


class ParamForm(QWidget):
    """Builds a form for a [(name, kind)] spec and edits a params dict."""

    paramsChanged = pyqtSignal(dict)

    def __init__(self, page: Page, parent=None):
        super().__init__(parent)
        self.page = page
        self.lay = QFormLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.params: dict[str, Any] = {}
        self.spec: list[tuple[str, str]] = []

    def build(self, spec: list[tuple[str, str]], params: dict) -> None:
        while self.lay.rowCount():
            self.lay.removeRow(0)
        self.spec, self.params = spec, dict(params)
        p = self.page.project
        if not spec:
            self.lay.addRow(hint_label("No settings for this type."))
        for name, kind in spec:
            val = self.params.get(name)
            w: QWidget
            if kind in ("side", "unit", "zone", "mission"):
                w = IdCombo()
                if kind == "side":
                    items = [(s.name, s.id) for s in p.sides]
                elif kind == "unit":
                    items = [(f"{u.display_name()}  ({p.side_name(u.side)})" + ("  [reinforcement]" if u.reserve
                                                                                 else ""), u.id) for u in p.units]
                elif kind == "zone":
                    items = [(f"{z.name}  ({p.side_name(z.side)})", z.id) for z in p.zones]
                else:
                    items = [(f"{m.name}  ({p.side_name(m.side)})", m.id) for m in p.missions]
                w.set_items(items, blank="(any)" if kind in ("side", "unit") else "(choose)", keep=False)
                w.set_current_id(val or "")
                w.currentIndexChanged.connect(lambda _i, n=name, cw=w: self._set(n, cw.current_id()))
            elif kind == "script":
                w = QComboBox()
                w.addItems([""] + [s.name for s in p.scripts])
                w.setCurrentText(val or "")
                w.currentTextChanged.connect(lambda t, n=name: self._set(n, t))
            elif kind == "unittype":
                w = QComboBox()
                for t in TARGET_TYPES:
                    w.addItem(t or "(any)", t)
                w.setCurrentIndex(max(0, w.findData(val or "")))
                w.currentIndexChanged.connect(lambda _i, n=name, cw=w: self._set(n, cw.currentData()))
            elif kind == "interval":
                w = QComboBox()
                w.addItems(REGULAR_INTERVALS)
                w.setCurrentIndex(int(val) if isinstance(val, (int, float)) else 4)
                if val is None:
                    self.params[name] = 4
                w.currentIndexChanged.connect(lambda i, n=name: self._set(n, i))
            elif kind == "int":
                w = QSpinBox()
                w.setRange(-1000000, 1000000)
                w.setValue(int(val or 0))
                w.valueChanged.connect(lambda v, n=name: self._set(n, v))
            elif kind == "bool":
                w = QCheckBox()
                w.setChecked(bool(val) if val is not None else (name == "Active"))
                if val is None and name == "Active":
                    self.params[name] = True
                w.toggled.connect(lambda v, n=name: self._set(n, v))
            elif kind == "datetime":
                w = QDateTimeEdit()
                w.setDisplayFormat("yyyy-MM-dd HH:mm:ss 'Z'")
                w.setTimeZone(QTimeZone.utc())
                w.setCalendarPopup(True)
                iso = val or p.clock.start
                dt = QDateTime.fromString(iso.replace("Z", ""), Qt.DateFormat.ISODate)
                dt.setTimeZone(QTimeZone.utc())
                w.setDateTime(dt)
                if val is None:
                    self.params[name] = iso
                w.dateTimeChanged.connect(lambda d, n=name: self._set(
                    n, d.toTimeZone(QTimeZone.utc()).toString("yyyy-MM-ddTHH:mm:ss")))
            elif kind.startswith("choice:"):
                w = QComboBox()
                opts = kind.split(":", 1)[1].split("|")
                w.addItems(opts)
                w.setCurrentText(val or opts[0])
                if val is None:
                    self.params[name] = opts[0]
                w.currentTextChanged.connect(lambda t, n=name: self._set(n, t))
            elif kind in ("lua", "raw", "html"):
                w = CodeEditor("html" if kind == "html" else "lua")
                w.setMinimumHeight(140 if kind != "raw" else 90)
                w.setPlainText(str(val or ("{ type = '' }" if kind == "raw" else "")))
                w.textChanged.connect(lambda n=name, cw=w: self._set(n, cw.toPlainText()))
                if kind == "raw":
                    self.lay.addRow(hint_label("A Lua table passed to ScenEdit_SetTrigger / SetCondition / "
                                               "SetAction (mode and name are added for you)."))
                if kind == "html":
                    self.lay.addRow(hint_label("HTML shown in a message box. Leave the side blank to message "
                                               "every side."))
            else:
                w = QLineEdit(str(val or ""))
                if name == "Duration":
                    w.setPlaceholderText("d:h:m:s, e.g. 0:0:30:0")
                if name == "Expression":
                    w.setPlaceholderText("Lua, e.g. StudioScore('Blue') > 100")
                w.textChanged.connect(lambda t, n=name: self._set(n, t))
            self.lay.addRow(name + ":", w)

    def _set(self, name: str, value: Any) -> None:
        self.params[name] = value
        self.paramsChanged.emit(dict(self.params))


class ItemList(QWidget):
    """List of triggers / conditions / actions with an 'Add' type menu."""

    def __init__(self, title: str, types: dict, parent=None):
        super().__init__(parent)
        self.types = types
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setMaximumHeight(130)
        lay.addWidget(self.list)
        row = QHBoxLayout()
        self.add = QPushButton(f"Add {title} ▾")
        menu = QMenu(self)
        for key, (label, _spec) in types.items():
            menu.addAction(label).setData(key)
        self.add.setMenu(menu)
        self.menu = menu
        self.remove = QPushButton("Remove")
        self.up = QPushButton("↑")
        self.down = QPushButton("↓")
        for b in (self.add, self.remove, self.up, self.down):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)


class EventsPage(Page):
    title = "Events"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.eid = ""
        self.sel: tuple[str, int] = ("", -1)     # ('triggers'|'conditions'|'actions', index)
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._pick)
        ll.addWidget(self.list)
        row = QHBoxLayout()
        new = QPushButton("New ▾")
        menu = QMenu(self)
        menu.addAction("Blank event", lambda: self._new(None))
        menu.addSeparator()
        for key, label in TEMPLATES:
            menu.addAction(label, lambda k=key: self._new(k))
        new.setMenu(menu)
        row.addWidget(new)
        for text, fn in (("Duplicate", self._dup), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        b = self.b = Binder(self, lambda: self._ev(), "events", self._attr_changed)
        g = QGroupBox("Event")
        f = QFormLayout(g)
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        flags = QHBoxLayout()
        self.rep = b.check(QCheckBox("Repeatable"), "repeatable")
        self.act = b.check(QCheckBox("Active"), "active")
        self.shown = b.check(QCheckBox("Shown in event log"), "shown")
        for w in (self.rep, self.act, self.shown):
            flags.addWidget(w)
        flags.addStretch()
        f.addRow(flags)
        self.prob = b.spin(QSpinBox(), "probability")
        self.prob.setRange(0, 100)
        self.prob.setSuffix(" %")
        f.addRow("Probability:", self.prob)
        ml.addWidget(g)

        self.lists = {}
        for key, title, types in (("triggers", "trigger", TRIGGER_TYPES), ("conditions", "condition",
                                                                             CONDITION_TYPES),
                                  ("actions", "action", ACTION_TYPES)):
            g = QGroupBox(title.capitalize() + "s" + (" (all must be true)" if key == "conditions" else
                                                      " (any fires the event)" if key == "triggers" else
                                                      " (run in order)"))
            gl = QVBoxLayout(g)
            il = ItemList(title, types)
            il.menu.triggered.connect(lambda a, k=key: self._add_item(k, a.data()))
            il.remove.clicked.connect(lambda _c, k=key: self._remove_item(k))
            il.up.clicked.connect(lambda _c, k=key: self._move_item(k, -1))
            il.down.clicked.connect(lambda _c, k=key: self._move_item(k, 1))
            il.list.currentRowChanged.connect(lambda r, k=key: self._pick_item(k, r))
            gl.addWidget(il)
            self.lists[key] = il
            ml.addWidget(g)
        split.addWidget(mid)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget()
        editor = QWidget()
        el = QVBoxLayout(editor)
        self.item_title = QLabel("Select a trigger, condition or action")
        self.item_title.setProperty("heading", True)
        el.addWidget(self.item_title)
        self.params = ParamForm(self)
        self.params.paramsChanged.connect(self._params_changed)
        el.addWidget(self.params)
        el.addStretch()
        tabs.addTab(editor, "Settings")
        self.preview = CodeEditor("lua")
        self.preview.setReadOnly(True)
        tabs.addTab(self.preview, "Generated Lua")
        rl.addWidget(tabs)
        rl.addWidget(hint_label("Conditions, probability and date/time triggers become guards at the top of the "
                                "event's Lua action, so a one-shot event only counts as fired when its actions "
                                "actually run."))
        split.addWidget(right)
        split.setSizes([260, 430, 520])

    # ------------------------------------------------------------------ helpers
    def _ev(self) -> Optional[Event]:
        return next((e for e in self.project.events if e.id == self.eid), None)

    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for e in self.project.events:
            trig = ", ".join(TRIGGER_TYPES.get(t.type, (t.type,))[0] for t in e.triggers) or "no trigger"
            it = QListWidgetItem(f"{'' if e.active else '[off] '}{e.name}\n    {trig}")
            it.setData(Qt.ItemDataRole.UserRole, e.id)
            self.list.addItem(it)
            if e.id == self.eid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if not self._ev() and self.project.events:
            self.eid = self.project.events[0].id
            self.list.setCurrentRow(0)
        self._load()

    def _load(self):
        e = self._ev()
        self.b.load()
        for key, il in self.lists.items():
            il.list.blockSignals(True)
            il.list.clear()
            types = {"triggers": TRIGGER_TYPES, "conditions": CONDITION_TYPES, "actions": ACTION_TYPES}[key]
            for item in (getattr(e, key) if e else []):
                il.list.addItem(f"{types.get(item.type, (item.type,))[0]}{self._summary(item)}")
            il.list.blockSignals(False)
            il.setEnabled(e is not None)
        for w in (self.name, self.rep, self.act, self.shown, self.prob):
            w.setEnabled(e is not None)
        kind, idx = self.sel
        if e and kind and 0 <= idx < len(getattr(e, kind)):
            self.lists[kind].list.blockSignals(True)
            self.lists[kind].list.setCurrentRow(idx)
            self.lists[kind].list.blockSignals(False)
            self._show_item(kind, idx)
        else:
            self.sel = ("", -1)
            self.item_title.setText("Select a trigger, condition or action")
            self.params.build([], {})
        self._update_preview()

    def _summary(self, item) -> str:
        p, prm = self.project, item.params
        bits = []
        for k in ("TargetSide", "Side", "DetectorSide"):
            if prm.get(k):
                bits.append(p.side_name(prm[k]))
        for k in ("SpecificUnit", "Unit"):
            u = p.unit(prm.get(k, "")) if prm.get(k) else None
            if u:
                bits.append(u.name)
        if prm.get("Area") and p.zone(prm["Area"]):
            bits.append(p.zone(prm["Area"]).name)
        if prm.get("Mission") and p.mission(prm["Mission"]):
            bits.append(p.mission(prm["Mission"]).name)
        for k in ("Minutes", "Time", "Change", "Percent", "Key", "Script", "TargetType"):
            if prm.get(k) not in (None, ""):
                bits.append(f"{k} {prm[k]}")
        if item.type == "RegularTime":
            iv = prm.get("Interval", 4)
            bits.append(REGULAR_INTERVALS[int(iv)] if isinstance(iv, int) and iv < len(REGULAR_INTERVALS) else "")
        return ("  —  " + ", ".join(b for b in bits if b)) if bits else ""

    def _update_preview(self):
        e = self._ev()
        if not e:
            self.preview.setPlainText("")
            return
        try:
            c = compile_event(self.project, e)
        except (CompileError, ValueError) as exc:
            self.preview.setPlainText(f"-- cannot compile: {exc}")
            return
        lines = [f"-- Event '{c['name']}'  repeatable={c['repeatable']}  active={c['active']}"]
        for t in c["triggers"]:
            extra = (f"  unit={t['unit']}" if t.get("unit") else "") + (f"  area={t['area']}" if t.get("area") else "")
            lines.append(f"-- trigger '{t['name']}': {t['spec']}{extra}")
        for x in c["conditions"]:
            lines.append(f"-- native condition '{x['name']}': {x['spec']}")
        for x in c["actions"]:
            lines.append(f"-- native action '{x['name']}': {x['spec']}")
        lines += ["", c["script"] or "-- (no Lua action)"]
        self.preview.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ list
    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.eid = cur.data(Qt.ItemDataRole.UserRole)
            self.sel = ("", -1)
            self._load()

    def _attr_changed(self, attr):
        if attr in ("name", "active"):
            self.refresh()
        else:
            self._update_preview()

    def _new(self, template: Optional[str]):
        e = make_template(self.project, template) if template else Event(name=f"Event {len(self.project.events) + 1}")
        with self.edit("New event", "events"):
            self.project.events.append(e)
        self.eid = e.id
        self.sel = ("", -1)
        self.refresh()

    def _dup(self):
        e = self._ev()
        if not e:
            return
        d = copy.deepcopy(e)
        d.id = new_id("e")
        d.name = e.name + " (copy)"
        with self.edit("Duplicate event", "events"):
            self.project.events.append(d)
        self.eid = d.id
        self.refresh()

    def _delete(self):
        if not self._ev():
            return
        with self.edit("Delete event", "events"):
            self.project.events = [x for x in self.project.events if x.id != self.eid]
        self.eid = ""
        self.refresh()

    # ------------------------------------------------------------------ items
    def _add_item(self, key: str, typ: str):
        e = self._ev()
        if not e:
            return
        cls = {"triggers": Trigger, "conditions": Condition, "actions": Action}[key]
        with self.edit(f"Add {key[:-1]}", "events"):
            getattr(e, key).append(cls(type=typ, params={}))
        self.sel = (key, len(getattr(e, key)) - 1)
        self._load()

    def _remove_item(self, key: str):
        e = self._ev()
        row = self.lists[key].list.currentRow()
        if e and 0 <= row < len(getattr(e, key)):
            with self.edit(f"Remove {key[:-1]}", "events"):
                getattr(e, key).pop(row)
            self.sel = ("", -1)
            self._load()
            self.refresh()

    def _move_item(self, key: str, d: int):
        e = self._ev()
        row = self.lists[key].list.currentRow()
        items = getattr(e, key) if e else []
        j = row + d
        if e and 0 <= row < len(items) and 0 <= j < len(items):
            with self.edit("Reorder", "events"):
                items[row], items[j] = items[j], items[row]
            self.sel = (key, j)
            self._load()

    def _pick_item(self, key: str, row: int):
        if row < 0:
            return
        for k, il in self.lists.items():
            if k != key:
                il.list.blockSignals(True)
                il.list.clearSelection()
                il.list.setCurrentRow(-1)
                il.list.blockSignals(False)
        self.sel = (key, row)
        self._show_item(key, row)

    def _show_item(self, key: str, row: int):
        e = self._ev()
        if not e or row >= len(getattr(e, key)):
            return
        item = getattr(e, key)[row]
        types = {"triggers": TRIGGER_TYPES, "conditions": CONDITION_TYPES, "actions": ACTION_TYPES}[key]
        label, spec = types.get(item.type, (item.type, []))
        self.item_title.setText(f"{key[:-1].capitalize()}: {label}")
        self.params.build(spec, item.params)
        if self.params.params != item.params:          # defaults filled in by the form
            item.params.update(self.params.params)

    def _params_changed(self, params: dict):
        e = self._ev()
        key, row = self.sel
        if not e or not key or row >= len(getattr(e, key)):
            return
        item = getattr(e, key)[row]
        with self.edit("Edit event settings", "events", merge=f"{e.id}.{key}.{row}"):
            item.params = params
        il = self.lists[key].list
        types = {"triggers": TRIGGER_TYPES, "conditions": CONDITION_TYPES, "actions": ACTION_TYPES}[key]
        if il.item(row):
            il.item(row).setText(f"{types.get(item.type, (item.type,))[0]}{self._summary(item)}")
        self._update_preview()


# =============================================================================== templates
TEMPLATES = [
    ("welcome", "Welcome message at start"),
    ("score_kill", "Score when enemy units are destroyed"),
    ("victory", "End scenario when a side reaches a score"),
    ("timeout", "Message + end scenario at a date/time"),
    ("reinforce", "Reinforcements arrive after a delay"),
    ("area", "Message when units enter an area"),
    ("tick", "Run a script every minute"),
]


def make_template(p, key: str) -> Event:
    sides = p.sides
    a = sides[0].id if sides else ""
    b = sides[1].id if len(sides) > 1 else a
    if key == "welcome":
        return Event(name="Welcome", triggers=[Trigger("StudioAfterDelay", {"Minutes": 1})],
                     actions=[Action("Message", {"Side": "", "Text": "<P>The scenario has begun.</P>"})])
    if key == "score_kill":
        return Event(name=f"{p.side_name(b)} unit destroyed", repeatable=True,
                     triggers=[Trigger("UnitDestroyed", {"TargetSide": b, "TargetType": t}) for t in
                               ("Aircraft", "Ship", "Submarine", "Facility")],
                     actions=[Action("Score", {"Side": a, "Change": 10, "Reason": "Enemy unit destroyed"})])
    if key == "victory":
        return Event(name=f"{p.side_name(a)} victory",
                     triggers=[Trigger("Points", {"Side": a, "PointValue": 500, "ReachDirection": "GreaterThan"})],
                     actions=[Action("Message", {"Side": "", "Text": "<P>Victory conditions met.</P>"}),
                              Action("EndScenario", {})])
    if key == "timeout":
        end = p.clock.start_dt()
        from datetime import timedelta
        end += timedelta(days=p.clock.duration_days, hours=p.clock.duration_hours) - timedelta(minutes=5)
        return Event(name="Time running out", triggers=[Trigger("StudioAtTime", {"Time": end.strftime(
            "%Y-%m-%dT%H:%M:%S")})], actions=[Action("Message", {"Side": "", "Text": "<P>Five minutes remain.</P>"})])
    if key == "reinforce":
        reserve = next((u for u in p.units if u.reserve), None)
        return Event(name="Reinforcements arrive", triggers=[Trigger("StudioAfterDelay", {"Minutes": 120})],
                     actions=[Action("SpawnUnit", {"Unit": reserve.id if reserve else ""}),
                              Action("Message", {"Side": reserve.side if reserve else a,
                                                 "Text": "<P>Reinforcements have arrived.</P>"})])
    if key == "area":
        z = p.zones[0].id if p.zones else ""
        return Event(name="Area entered", triggers=[Trigger("UnitEntersArea", {"TargetSide": b, "Area": z})],
                     actions=[Action("Message", {"Side": a, "Text": "<P>Enemy forces have entered the area.</P>"})])
    if key == "tick":
        return Event(name="Clock tick", repeatable=True, triggers=[Trigger("RegularTime", {"Interval": 4})],
                     actions=[Action("RunScript", {"Script": p.scripts[0].name if p.scripts else ""})])
    return Event()
