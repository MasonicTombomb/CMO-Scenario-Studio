"""Lua scripts and special actions (both are code editors with a list)."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget)

from ...model.project import Script, SpecialAction
from ...tools.lua_engine import LuaUnavailable, check_syntax, find_lua_dll
from ..widgets import CodeEditor, IdCombo, hint_label
from .base import AppContext, Binder, Page

SNIPPETS = {
    "Message to a side": "StudioMsg('SideName', '<P>Text</P>')",
    "Change score": "StudioAddScore('SideName', 10, 'Reason')",
    "Flag (once only)": "if StudioFlag('MY_FLAG') then return end\nStudioSetFlag('MY_FLAG', true)",
    "Find a unit": "local u = StudioGetUnit({ side = 'SideName', name = 'Unit name' })\nif u then\n  print(u.name, u.latitude, u.longitude)\nend",
    "Loop over a side's units": "local side = VP_GetSide({ side = 'SideName' })\nfor _, ref in ipairs(side.units) do\n  local u = ScenEdit_GetUnit({ guid = ref.guid })\n  -- ...\nend",
    "Add a unit": "ScenEdit_AddUnit({ side = 'SideName', type = 'Ship', dbid = 1234, name = 'New ship',\n                  latitude = 59.0, longitude = 24.0 })",
    "Spawn a reinforcement": "StudioSpawn('u_xxxxxxxx')   -- id of a unit marked 'reinforcement'",
    "Activate a mission": "StudioMissionStatus('SideName', 'Mission name', true)",
    "Random position": "local pos = StudioRandomPosition(58.0, 59.0, 22.0, 24.0)",
    "Elapsed minutes": "local minutes = math.floor(((tonumber(ScenEdit_CurrentTime()) or 0) - STUDIO.START) / 60)",
    "End scenario": "ScenEdit_EndScenario()",
}


def snippet_menu(parent, editor: CodeEditor) -> QMenu:
    menu = QMenu(parent)
    for label, code in SNIPPETS.items():
        menu.addAction(label, lambda c=code: editor.insertPlainText(c + "\n"))
    return menu


def check_lua(ctx, name: str, code: str, parent) -> None:
    dll = find_lua_dll(ctx.settings.cmo_dir)
    if not dll:
        QMessageBox.information(parent, "Check syntax", "CMO's lua54.dll was not found - set the CMO folder in "
                                                        "Settings.")
        return
    try:
        errs = check_syntax(dll, {name: code})
    except LuaUnavailable as exc:
        QMessageBox.warning(parent, "Check syntax", str(exc))
        return
    if errs:
        QMessageBox.warning(parent, "Syntax error", errs[name])
    else:
        ctx.status(f"{name}: no syntax errors (checked with CMO's Lua 5.4).")


class ScriptsPage(Page):
    title = "Scripts"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.sid = ""
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
        for text, fn in (("New", self._new), ("Rename", self._rename), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        ll.addWidget(hint_label(
            "Each script is exported as Lua\\<Folder>\\<name>.lua. Call it from an event with the "
            "'Run project script' action, or tick 'load on init' to run it whenever the scenario loads "
            "(good for shared functions). The studio's helpers (StudioMsg, StudioAddScore, StudioFlag, "
            "StudioSpawn, ...) are always available."))
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        b = self.b = Binder(self, lambda: self.project.script(self.sid) if self.sid else None, "scripts")
        top = QHBoxLayout()
        self.title_lbl = QLabel("")
        self.title_lbl.setProperty("heading", True)
        top.addWidget(self.title_lbl)
        top.addStretch()
        self.init = b.check(QCheckBox("Load on init (run from LuaInit.lua)"), "load_on_init")
        top.addWidget(self.init)
        ins = QPushButton("Insert snippet ▾")
        top.addWidget(ins)
        chk = QPushButton("Check syntax")
        chk.clicked.connect(lambda: check_lua(self.ctx, self.title_lbl.text() or "script", self.editor.toPlainText(),
                                              self))
        top.addWidget(chk)
        rl.addLayout(top)
        self.editor = CodeEditor("lua")
        b.text(self.editor, "content")
        ins.setMenu(snippet_menu(self, self.editor))
        rl.addWidget(self.editor, 1)
        f = QFormLayout()
        self.notes = b.line(QLineEdit(), "notes")
        self.notes.setPlaceholderText("one-line description (written as a comment at the top of the file)")
        f.addRow("Notes:", self.notes)
        rl.addLayout(f)
        split.addWidget(right)
        split.setSizes([260, 900])

    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for s in self.project.scripts:
            it = QListWidgetItem(f"{s.name}.lua" + ("   [init]" if s.load_on_init else ""))
            it.setData(Qt.ItemDataRole.UserRole, s.id)
            self.list.addItem(it)
            if s.id == self.sid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if not self.project.script(self.sid) if self.sid else True:
            self.sid = self.project.scripts[0].id if self.project.scripts else ""
            if self.list.count():
                self.list.setCurrentRow(0)
        self._load()

    def _load(self):
        s = self.project.script(self.sid) if self.sid else None
        self.b.load()
        self.title_lbl.setText(f"{s.name}.lua" if s else "")
        for w in (self.editor, self.init, self.notes):
            w.setEnabled(s is not None)

    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.sid = cur.data(Qt.ItemDataRole.UserRole)
            self._load()

    def _valid(self, name: str) -> bool:
        if not re.match(r"^[A-Za-z0-9_\- ]+$", name or ""):
            QMessageBox.warning(self, "Script", "Use letters, digits, spaces, '_' or '-'.")
            return False
        if name.lower() in ("build_scenario", "luainit", "studio_runtime"):
            QMessageBox.warning(self, "Script", f"'{name}' is generated by the studio.")
            return False
        if any(s.name.lower() == name.lower() and s.id != self.sid for s in self.project.scripts):
            QMessageBox.warning(self, "Script", "A script with that name exists.")
            return False
        return True

    def _new(self):
        name, ok = QInputDialog.getText(self, "New script", "Script name (without .lua):", text="Tick")
        if not ok or not self._valid(name.strip()):
            return
        s = Script(name=name.strip(), content=f"-- {name.strip()}.lua\n")
        with self.edit("New script", "scripts"):
            self.project.scripts.append(s)
        self.sid = s.id
        self.refresh()

    def _rename(self):
        s = self.project.script(self.sid) if self.sid else None
        if not s:
            return
        name, ok = QInputDialog.getText(self, "Rename script", "New name:", text=s.name)
        if ok and name.strip() != s.name and self._valid(name.strip()):
            old = s.name
            with self.edit("Rename script", "scripts"):
                s.name = name.strip()
                for e in self.project.events:
                    for a in e.actions:
                        if a.type == "RunScript" and a.params.get("Script") == old:
                            a.params["Script"] = s.name
            self.refresh()

    def _delete(self):
        s = self.project.script(self.sid) if self.sid else None
        if s and QMessageBox.question(self, "Delete", f"Delete {s.name}.lua?") == QMessageBox.StandardButton.Yes:
            with self.edit("Delete script", "scripts"):
                self.project.scripts = [x for x in self.project.scripts if x.id != s.id]
            self.sid = ""
            self.refresh()


class SpecialActionsPage(Page):
    title = "Special actions"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.aid = ""
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
        for text, fn in (("New", self._new), ("Delete", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        ll.addWidget(hint_label("Special actions are buttons the player can press in CMO (Game > Special "
                                "Actions). They are skipped for computer-controlled sides."))
        split.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        b = self.b = Binder(self, self._sa, "specials", lambda a: self.refresh() if a in ("name", "side") else None)
        f = QFormLayout()
        self.name = b.line(QLineEdit(), "name")
        f.addRow("Name:", self.name)
        self.side = IdCombo()
        b.combo(self.side, "side")
        f.addRow("Side:", self.side)
        self.desc = b.line(QLineEdit(), "description")
        f.addRow("Description:", self.desc)
        flags = QHBoxLayout()
        self.rep = b.check(QCheckBox("Repeatable"), "repeatable")
        self.act = b.check(QCheckBox("Active"), "active")
        flags.addWidget(self.rep)
        flags.addWidget(self.act)
        flags.addStretch()
        ins = QPushButton("Insert snippet ▾")
        chk = QPushButton("Check syntax")
        flags.addWidget(ins)
        flags.addWidget(chk)
        f.addRow(flags)
        rl.addLayout(f)
        self.editor = CodeEditor("lua")
        b.text(self.editor, "script")
        ins.setMenu(snippet_menu(self, self.editor))
        chk.clicked.connect(lambda: check_lua(self.ctx, self.name.text() or "special action",
                                              self.editor.toPlainText(), self))
        rl.addWidget(self.editor, 1)
        split.addWidget(right)
        split.setSizes([260, 900])

    def _sa(self):
        return next((a for a in self.project.special_actions if a.id == self.aid), None)

    def refresh(self) -> None:
        p = self.project
        self.list.blockSignals(True)
        self.list.clear()
        for a in p.special_actions:
            it = QListWidgetItem(f"{a.name}   ({p.side_name(a.side)})")
            it.setData(Qt.ItemDataRole.UserRole, a.id)
            self.list.addItem(it)
            if a.id == self.aid:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        self.side.set_items([(s.name, s.id) for s in p.sides], keep=False)
        self.b.load()
        en = self._sa() is not None
        for w in (self.name, self.side, self.desc, self.rep, self.act, self.editor):
            w.setEnabled(en)

    def _pick(self, cur, _prev=None):
        if cur is not None:
            self.aid = cur.data(Qt.ItemDataRole.UserRole)
            self.refresh()

    def _new(self):
        p = self.project
        if not p.sides:
            return
        a = SpecialAction(side=p.sides[0].id, name=f"Special action {len(p.special_actions) + 1}",
                          script=f"StudioMsg('{p.sides[0].name}', '<P>Special action used.</P>')")
        with self.edit("New special action", "specials"):
            p.special_actions.append(a)
        self.aid = a.id
        self.refresh()

    def _delete(self):
        if self._sa():
            with self.edit("Delete special action", "specials"):
                self.project.special_actions = [x for x in self.project.special_actions if x.id != self.aid]
            self.aid = ""
            self.refresh()
