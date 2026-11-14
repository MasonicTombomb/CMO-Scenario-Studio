"""Formation preview drawing, preset picker and template-parameter form (shared by the page and the creator)."""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView,
                             QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..model.formations import BASES, DOMAINS, NM_PER, PRESETS_LIST, effective_params, offsets, preset
from .widgets import hint_label

UNIT_LABELS = {"nm": "nm", "km": "km", "m": "m"}


def fmt_dist(nm: float, unit: str) -> str:
    v = nm / NM_PER[unit]
    return f"{v:,.0f} {unit}" if unit == "m" else f"{v:,.2f} {unit}"


class PresetCombo(QComboBox):
    """Presets grouped under Naval / Air / Ground / Any headings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        model = QStandardItemModel(self)
        for domain in DOMAINS:
            head = QStandardItem(f"— {domain} —")
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            f = QFont()
            f.setBold(True)
            head.setFont(f)
            model.appendRow(head)
            for p in PRESETS_LIST:
                if p.domain == domain:
                    it = QStandardItem("    " + p.label)
                    it.setData(p.key, Qt.ItemDataRole.UserRole)
                    it.setToolTip(p.help)
                    model.appendRow(it)
        self.setModel(model)
        self.setMaxVisibleItems(30)

    def key(self) -> str:
        return self.currentData() or ""

    def set_key(self, key: str) -> None:
        i = self.findData(key)
        self.blockSignals(True)
        self.setCurrentIndex(max(1, i))
        self.blockSignals(False)


class FormationPreview(QWidget):
    """North-up plan of the stations: lead, numbered members, range rings, heading arrow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.formation = None
        self.count = None          # number of members to draw (defaults to len(members))
        self.unit = "nm"
        self.color = QColor("#3d8bfd")
        self.labels: list[str] = []

    def show_formation(self, f, count=None, color: str = "", labels=None) -> None:
        self.formation, self.count = f, count
        if color:
            self.color = QColor(color)
        self.labels = labels or []
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#141a22"))
        f = self.formation
        if f is None:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No formation")
            return
        n = len(f.members) if self.count is None else self.count
        offs = offsets(f, n)
        h = math.radians(f.heading)
        pts = []
        for x, y, dz in offs:   # rotate (x right, y ahead) by heading into east/north
            e = x * math.cos(h) + y * math.sin(h)
            nn = -x * math.sin(h) + y * math.cos(h)
            pts.append((e, nn, dz))
        extent = max([abs(a) for a, _, _ in pts] + [abs(b) for _, b, _ in pts] + [f.spacing_nm])
        margin = 26
        size = min(self.width(), self.height()) / 2 - margin
        scale = size / (extent * 1.1)
        c = QPointF(self.width() / 2, self.height() / 2)

        def to_px(e, nn):
            return QPointF(c.x() + e * scale, c.y() - nn * scale)

        # range rings at multiples of the spacing (at most 6)
        step = f.spacing_nm
        while extent / step > 6:
            step *= 2
        p.setPen(QPen(QColor(90, 120, 150, 90), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = step
        while r <= extent * 1.1:
            p.drawEllipse(c, r * scale, r * scale)
            r += step
        # north marker and heading arrow
        p.setPen(QColor("#8a8f99"))
        p.drawText(QRectF(c.x() - 20, 2, 40, 16), Qt.AlignmentFlag.AlignCenter, "N")
        arrow_len = size * 0.9
        tip = QPointF(c.x() + math.sin(h) * arrow_len, c.y() - math.cos(h) * arrow_len)
        p.setPen(QPen(QColor(255, 209, 102, 160), 2))
        p.drawLine(c, tip)
        a1 = QPointF(tip.x() - 9 * math.sin(h - 0.4), tip.y() + 9 * math.cos(h - 0.4))
        a2 = QPointF(tip.x() - 9 * math.sin(h + 0.4), tip.y() + 9 * math.cos(h + 0.4))
        p.setBrush(QBrush(QColor(255, 209, 102, 200)))
        p.drawPolygon(QPolygonF([tip, a1, a2]))
        # members
        font = p.font()
        font.setPointSize(7)
        p.setFont(font)
        p.setPen(QPen(QColor(self.color).lighter(130), 1, Qt.PenStyle.DotLine))
        for e, nn, _ in pts:
            p.drawLine(c, to_px(e, nn))
        for i, (e, nn, dz) in enumerate(pts):
            q = to_px(e, nn)
            p.setPen(QPen(QColor("#0b0b0b"), 1))
            p.setBrush(QBrush(self.color))
            p.drawEllipse(q, 6, 6)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(q.x() - 8, q.y() - 7, 16, 14), Qt.AlignmentFlag.AlignCenter, str(i + 1))
            label = self.labels[i] if i < len(self.labels) else ""
            if dz:
                label = (label + " " if label else "") + f"{dz:+.0f} m"
            if label:
                p.setPen(QColor("#c8ccd4"))
                p.drawText(QPointF(q.x() + 9, q.y() + 4), label)
        # lead
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.setBrush(QBrush(QColor("#ffd166")))
        p.drawPolygon(QPolygonF([QPointF(c.x(), c.y() - 9), QPointF(c.x() + 8, c.y() + 6),
                                 QPointF(c.x() - 8, c.y() + 6)]))
        p.setPen(QColor("#8a8f99"))
        p.drawText(QRectF(4, self.height() - 18, self.width() - 8, 16), Qt.AlignmentFlag.AlignLeft,
                   f"rings every {fmt_dist(step, self.unit)}   ·   heading {f.heading:03.0f}°   ·   {n + 1} units")
        p.end()


class TemplateParams(QWidget):
    """Editor for the preset's base-generator parameters. Emits paramsChanged(dict of overrides)."""

    paramsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        self._values: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {}

    def build(self, f) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        pre = preset(f.preset)
        base = BASES[pre.base]
        eff = effective_params(f)
        self._defaults = {k: spec[2] for k, spec in base.params.items()}
        self._defaults.update(pre.params)
        self._values = dict(eff)
        self.form.addRow(hint_label(pre.help))
        if not base.params:
            self.form.addRow(hint_label("This layout has no extra settings - use spacing and heading."))
        for key, (label, kind, _default, lo, hi) in base.params.items():
            val = eff.get(key)
            if kind == "float":
                w = QDoubleSpinBox()
                w.setRange(lo, hi)
                w.setDecimals(2)
                w.setSingleStep(0.1 if hi <= 20 else 5)
                w.setValue(float(val))
                w.valueChanged.connect(lambda v, k=key: self._set(k, float(v)))
            elif kind == "int":
                w = QSpinBox()
                w.setRange(int(lo), int(hi))
                w.setValue(int(val))
                w.valueChanged.connect(lambda v, k=key: self._set(k, int(v)))
            elif kind == "bool":
                w = QCheckBox()
                w.setChecked(bool(val))
                w.toggled.connect(lambda v, k=key: self._set(k, bool(v)))
            elif kind.startswith("choice:"):
                w = QComboBox()
                w.addItems(kind.split(":", 1)[1].split("|"))
                w.setCurrentText(str(val))
                w.currentTextChanged.connect(lambda t, k=key: self._set(k, t))
            else:   # stations
                w = self._stations_editor(key, val or [], len(f.members))
            self.form.addRow(label + ":", w)

    def _stations_editor(self, key: str, stations: list, members: int) -> QWidget:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        t = QTableWidget(max(members, len(stations)), 2)
        t.setHorizontalHeaderLabels(["Rel. bearing (°)", "Distance (spacing units)"])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setMaximumHeight(170)
        for r in range(t.rowCount()):
            b, d = (stations[r] if r < len(stations) else (180.0, float(r + 1)))
            t.setItem(r, 0, QTableWidgetItem(f"{float(b):g}"))
            t.setItem(r, 1, QTableWidgetItem(f"{float(d):g}"))

        def changed(*_):
            out = []
            for r in range(t.rowCount()):
                try:
                    out.append([float(t.item(r, 0).text()), float(t.item(r, 1).text())])
                except (AttributeError, ValueError):
                    out.append([180.0, float(r + 1)])
            self._set(key, out)
        t.itemChanged.connect(changed)
        v.addWidget(t)
        row = QHBoxLayout()
        add = QPushButton("Add station")
        add.clicked.connect(lambda: (t.insertRow(t.rowCount()), t.setItem(t.rowCount() - 1, 0, QTableWidgetItem("180")),
                                     t.setItem(t.rowCount() - 1, 1, QTableWidgetItem(str(t.rowCount())))))
        row.addWidget(add)
        row.addStretch()
        v.addLayout(row)
        v.addWidget(hint_label("Row n is member n. Bearing is relative to the formation heading (0 = ahead, "
                               "90 = right)."))
        return box

    def _set(self, key: str, value: Any) -> None:
        self._values[key] = value
        overrides = {k: v for k, v in self._values.items() if self._defaults.get(k) != v}
        self.paramsChanged.emit(overrides)
