"""Make an event from a recipe: pick one, answer a few questions, get a finished event."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QSpinBox, QSplitter,
                             QVBoxLayout, QWidget)

from ..model.enums import UNIT_TYPES
from ..model.event_recipes import RECIPES, Recipe, missing_answers, recipe
from ..model.project import Event
from .widgets import IdCombo, hint_label


class RecipeDialog(QDialog):
    def __init__(self, ctx, recipe_id: str = "", parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.event: Optional[Event] = None
        self.inputs: dict[str, QWidget] = {}
        self.setWindowTitle("New event from a recipe")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        for cat in dict.fromkeys(r.category for r in RECIPES):
            head = QListWidgetItem(cat)
            f = head.font()
            f.setBold(True)
            head.setFont(f)
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(head)
            for r in (x for x in RECIPES if x.category == cat):
                it = QListWidgetItem("    " + r.name)
                it.setData(Qt.ItemDataRole.UserRole, r.id)
                self.list.addItem(it)
        self.list.currentItemChanged.connect(lambda cur, _p: cur and cur.data(Qt.ItemDataRole.UserRole) and
                                             self._show(recipe(cur.data(Qt.ItemDataRole.UserRole))))
        split.addWidget(self.list)
        right = QWidget()
        self.rl = QVBoxLayout(right)
        self.rl.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel()
        self.title.setProperty("heading", True)
        self.rl.addWidget(self.title)
        self.desc = hint_label("")
        self.rl.addWidget(self.desc)
        self.box = QGroupBox("Fill in")
        self.form = QFormLayout(self.box)
        self.rl.addWidget(self.box, 1)
        split.addWidget(right)
        split.setSizes([300, 600])
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok = bb.addButton("Create event", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.accepted.connect(self._create)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.current: Optional[Recipe] = None
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) and (not recipe_id or it.data(Qt.ItemDataRole.UserRole) == recipe_id):
                self.list.setCurrentItem(it)
                break

    # ------------------------------------------------------------------ the form
    def _widget(self, kind: str, value):
        p = self.ctx.project
        if kind in ("side", "own_side", "enemy_side"):
            w = IdCombo()
            w.set_items([(s.name, s.id) for s in p.sides], blank="(all sides)" if kind == "side" else None)
            w.set_current_id(value or "")
            return w
        if kind in ("unit", "reserve_unit"):
            w = IdCombo()
            w.set_items([(f"{u.display_name()}  [{p.side_name(u.side)}, {u.type}]", u.id) for u in p.units],
                        blank="(choose a unit)")
            w.set_current_id(value or "")
            return w
        if kind == "zone":
            w = IdCombo()
            w.set_items([(z.name, z.id) for z in p.zones], blank="(choose an area)")
            w.set_current_id(value or "")
            return w
        if kind == "mission":
            w = IdCombo()
            w.set_items([(f"{m.name}  [{p.side_name(m.side)}]", m.id) for m in p.missions], blank="(choose a mission)")
            w.set_current_id(value or "")
            return w
        if kind == "unittype":
            w = IdCombo()
            w.set_items([(t, t) for t in UNIT_TYPES], blank="(any type)")
            w.set_current_id(value or "")
            return w
        if kind == "int":
            w = QSpinBox()
            w.setRange(-100000, 100000)
            w.setValue(int(value or 0))
            return w
        if kind == "html":
            w = QPlainTextEdit(value or "")
            w.setMaximumHeight(90)
            return w
        w = QLineEdit(value or "")
        return w

    @staticmethod
    def _value(w):
        if isinstance(w, IdCombo):
            return w.current_id()
        if isinstance(w, QSpinBox):
            return w.value()
        if isinstance(w, QPlainTextEdit):
            return w.toPlainText()
        return w.text()

    def _show(self, r: Optional[Recipe]):
        self.current = r
        while self.form.rowCount():
            self.form.removeRow(0)
        self.inputs.clear()
        if r is None:
            return
        self.title.setText(r.name)
        self.desc.setText(r.description)
        defaults = r.defaults(self.ctx.project)
        for a in r.asks:
            w = self._widget(a.kind, defaults.get(a.key))
            if a.help:
                w.setToolTip(a.help)
            self.inputs[a.key] = w
            self.form.addRow(a.label + ":", w)

    def values(self) -> dict:
        return {k: self._value(w) for k, w in self.inputs.items()}

    def set_value(self, key: str, value) -> None:
        w = self.inputs[key]
        if isinstance(w, IdCombo):
            w.set_current_id(value)
        elif isinstance(w, QSpinBox):
            w.setValue(int(value))
        elif isinstance(w, QPlainTextEdit):
            w.setPlainText(value)
        else:
            w.setText(value)

    def _create(self):
        r = self.current
        if r is None:
            return
        v = self.values()
        missing = missing_answers(r, v)
        if missing:
            QMessageBox.information(self, r.name, "Please fill in: " + ", ".join(missing) + ".")
            return
        with self.ctx.doc.modify(f"New event: {r.name}", "events"):
            e = r.build(self.ctx.project, v)
            self.ctx.project.events.append(e)
        self.event = e
        if r.then:
            self.ctx.status(r.then)
        self.accept()


__all__ = ["RecipeDialog"]
