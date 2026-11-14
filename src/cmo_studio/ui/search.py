"""Search everything (Ctrl+K): units, sides, missions, events, areas, formations, scripts (including their
lines), special actions, variants and studio commands - type, arrow keys, Enter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from ..model.project import Project

KIND_COLORS = {
    "Unit": "#3d8bfd", "Side": "#c8ccd4", "Mission": "#30a46c", "Event": "#f5a524", "Area": "#12a594",
    "Ref. point": "#12a594", "Formation": "#8e4ec6", "Script": "#d6409f", "Script line": "#d6409f",
    "Special action": "#f5a524", "Variant": "#c8ccd4", "Command": "#9fb3c8",
}


@dataclass
class Hit:
    kind: str
    name: str
    detail: str
    oid: str = ""
    line: int = 0
    action: Optional[Callable[[], None]] = None
    score: float = 0.0


def collect(p: Project) -> list[Hit]:
    """Everything searchable in a project."""
    out: list[Hit] = []
    for u in p.units:
        host = p.unit(u.host) if u.host else None
        bits = [p.side_name(u.side), u.type, u.db_name, f"DBID {u.dbid}"]
        if u.group:
            bits.append(f"group {u.group}")
        if host:
            bits.append(f"at {host.name}")
        if u.reserve:
            bits.append("reinforcement")
        out.append(Hit("Unit", u.display_name(), " · ".join(b for b in bits if b), u.id))
    for s in p.sides:
        out.append(Hit("Side", s.name, ("computer-controlled" if s.computer_only else "playable") +
                       f" · {len(p.units_of_side(s.id))} unit entries", s.id))
    for m in p.missions:
        out.append(Hit("Mission", m.name, f"{p.side_name(m.side)} · {m.mclass}"
                       f"{('/' + m.subtype) if m.subtype else ''} · {len(m.units)} unit(s)", m.id))
    for e in p.events:
        trig = ", ".join(t.type for t in e.triggers)
        acts = ", ".join(a.type for a in e.actions)
        out.append(Hit("Event", e.name, f"{trig} → {acts}" + ("" if e.active else " · inactive"), e.id))
    for z in p.zones:
        out.append(Hit("Area", z.name, f"{p.side_name(z.side)} · {len(z.points)} corners", z.id))
    for r in p.reference_points:
        out.append(Hit("Ref. point", r.name, f"{p.side_name(r.side)} · {r.lat:.3f}, {r.lon:.3f}", r.id))
    for f in p.formations:
        lead = p.unit(f.lead)
        out.append(Hit("Formation", f.name, f"{p.side_name(f.side)} · {f.preset} · lead "
                       f"{lead.name if lead else '-'} · {len(f.members) + 1} units", f.id))
    for a in p.special_actions:
        out.append(Hit("Special action", a.name, f"{p.side_name(a.side)} · {a.description}", a.id))
    for v in p.variants:
        out.append(Hit("Variant", v.name, f"Build_{v.key}.lua", v.id))
    for s in p.scripts:
        out.append(Hit("Script", f"{s.name}.lua", s.notes or f"{len(s.content.splitlines())} lines", s.id))
        for i, line in enumerate(s.content.splitlines(), 1):
            if line.strip() and not line.strip().startswith("--"):
                out.append(Hit("Script line", line.strip()[:100], f"{s.name}.lua line {i}", s.id, line=i))
    return out


def score(hit: Hit, words: list[str], query: str) -> float:
    """0 = no match. Name matches beat detail matches; script lines rank last."""
    name = hit.name.lower()
    hay = f"{name} {hit.detail.lower()} {hit.kind.lower()}"
    if not all(w in hay for w in words):
        if len(words) == 1 and _subsequence(words[0], name):
            return 5.0
        return 0.0
    s = 0.0
    if name == query:
        s = 100
    elif name.startswith(query):
        s = 80
    elif re.search(r"\b" + re.escape(query), name):
        s = 65
    elif query in name:
        s = 50
    elif all(w in name for w in words):
        s = 40
    else:
        s = 20
    if hit.kind == "Script line":
        s -= 15
    if hit.kind == "Command":
        s += 3
    return s - len(name) / 1000


def _subsequence(q: str, text: str) -> bool:
    it = iter(text)
    return all(ch in it for ch in q)


class SearchDialog(QDialog):
    def __init__(self, project: Project, commands: list[tuple[str, str, Callable[[], None]]],
                 on_open: Callable[[Hit], None], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search everything")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setStyleSheet("QDialog { border: 1px solid #3d8bfd; border-radius: 6px; }")
        self.resize(720, 460)
        self.on_open = on_open
        self.hits = collect(project) + [Hit("Command", name, detail, action=fn) for name, detail, fn in commands]
        lay = QVBoxLayout(self)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Search units, missions, events, areas, formations, scripts, commands...")
        f = self.edit.font()
        f.setPointSize(f.pointSize() + 2)
        self.edit.setFont(f)
        self.edit.textChanged.connect(self._search)
        self.edit.installEventFilter(self)
        lay.addWidget(self.edit)
        self.list = QListWidget()
        self.list.itemActivated.connect(self._activate)
        lay.addWidget(self.list, 1)
        self.status = QLabel("")
        self.status.setProperty("hint", True)
        lay.addWidget(self.status)
        self._search("")

    def _search(self, text: str) -> None:
        q = text.strip().lower()
        words = q.split()
        self.list.clear()
        if not q:
            results = [h for h in self.hits if h.kind not in ("Script line",)][:60]
        else:
            scored = []
            for h in self.hits:
                s = score(h, words, q)
                if s > 0:
                    h.score = s
                    scored.append(h)
            scored.sort(key=lambda h: -h.score)
            results = scored[:200]
        for h in results:
            it = QListWidgetItem(f"{h.name}\n    {h.kind}  ·  {h.detail}")
            it.setData(Qt.ItemDataRole.UserRole, h)
            it.setForeground(QColor(KIND_COLORS.get(h.kind, "#e3e5e8")) if h.kind == "Command" else QColor("#e3e5e8"))
            if h.kind == "Command":
                font = QFont(it.font())
                font.setItalic(True)
                it.setFont(font)
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.status.setText(f"{self.list.count()} result(s)  ·  ↑↓ to choose, Enter to open, Esc to close")

    def eventFilter(self, obj, ev) -> bool:
        if obj is self.edit and ev.type() == ev.Type.KeyPress:
            key = ev.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                step = {Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: 10, Qt.Key.Key_PageUp: -10}[key]
                row = max(0, min(self.list.count() - 1, self.list.currentRow() + step))
                self.list.setCurrentRow(row)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                it = self.list.currentItem()
                if it:
                    self._activate(it)
                return True
        return super().eventFilter(obj, ev)

    def _activate(self, it: QListWidgetItem) -> None:
        hit: Hit = it.data(Qt.ItemDataRole.UserRole)
        self.accept()
        self.on_open(hit)
