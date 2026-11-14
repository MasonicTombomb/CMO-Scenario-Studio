"""Areas (reference-point polygons) and single reference points."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QSplitter, QStackedWidget,
                             QTabWidget, QVBoxLayout, QWidget)

from ...model.project import ReferencePoint, Zone
from ..forms import RPForm, ZoneForm
from ..widgets import hint_label
from .base import AppContext, Page


class AreasPage(Page):
    title = "Areas"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.zones = QListWidget()
        self.rps = QListWidget()
        self.tabs.addTab(self.zones, "Areas")
        self.tabs.addTab(self.rps, "Reference points")
        self.zones.currentItemChanged.connect(lambda c, _p=None: c and self.doc.select(c.data(Qt.ItemDataRole.UserRole), self))
        self.rps.currentItemChanged.connect(lambda c, _p=None: c and self.doc.select(c.data(Qt.ItemDataRole.UserRole), self))
        ll.addWidget(self.tabs)
        row = QHBoxLayout()
        b1 = QPushButton("New area (box)")
        b1.setToolTip("Add a 4-corner area at the map centre; reshape it on the map")
        b1.clicked.connect(self._new_zone)
        b2 = QPushButton("New reference point")
        b2.clicked.connect(self._new_rp)
        b3 = QPushButton("From library...")
        b3.setToolTip("Add predefined sea and air patrol areas by region (Ctrl+Shift+A)")
        b3.clicked.connect(lambda: self.ctx.window and self.ctx.window.add_library_area())
        row.addWidget(b1)
        row.addWidget(b2)
        row.addWidget(b3)
        ll.addLayout(row)
        ll.addWidget(hint_label("Tip: drawing on the Map tab ('Draw area') is usually quicker."))
        split.addWidget(left)
        self.stack = QStackedWidget()
        self.stack.addWidget(QWidget())
        self.zone_form = ZoneForm(ctx)
        self.rp_form = RPForm(ctx)
        self.stack.addWidget(self.zone_form)
        self.stack.addWidget(self.rp_form)
        for w in (self.zone_form, self.rp_form):
            w.centerRequested.connect(self._show_on_map)
        split.addWidget(self.stack)
        split.setSizes([320, 700])
        self.doc.selected.connect(self._selected)

    def refresh(self) -> None:
        p = self.project
        for lw, items in ((self.zones, p.zones), (self.rps, p.reference_points)):
            lw.blockSignals(True)
            lw.clear()
            for o in items:
                side = p.side(o.side)
                extra = f"  ({len(o.points)} pts)" if isinstance(o, Zone) else ""
                it = QListWidgetItem(f"{o.name}{extra}  ·  {'all sides' if o.all_sides else p.side_name(o.side)}")
                it.setData(Qt.ItemDataRole.UserRole, o.id)
                if side:
                    it.setForeground(QColor(side.color))
                lw.addItem(it)
                if o.id == self.doc.selection:
                    lw.setCurrentItem(it)
            lw.blockSignals(False)
        self._selected(self.doc.selection, None)

    def _selected(self, oid, source):
        obj = self.project.find(oid) if oid else None
        if isinstance(obj, Zone):
            self.zone_form.set_zone(oid)
            self.stack.setCurrentWidget(self.zone_form)
            self.tabs.setCurrentIndex(0)
        elif isinstance(obj, ReferencePoint):
            self.rp_form.set_rp(oid)
            self.stack.setCurrentWidget(self.rp_form)
            self.tabs.setCurrentIndex(1)

    def _centre(self):
        w = self.ctx.window
        if w and hasattr(w, "map_page"):
            return w.map_page.map.center()
        return 0.0, 0.0

    def _side(self):
        w = self.ctx.window
        if w and hasattr(w, "map_page"):
            return w.map_page.current_side()
        return self.project.sides[0].id if self.project.sides else ""

    def _new_zone(self):
        lat, lon = self._centre()
        d = 0.5
        z = Zone(side=self._side(), name=f"AREA_{len(self.project.zones) + 1}",
                 points=[[lat + d, lon - d], [lat + d, lon + d], [lat - d, lon + d], [lat - d, lon - d]])
        with self.edit("New area", "zones"):
            self.project.zones.append(z)
        self.refresh()
        self.doc.select(z.id, self)

    def _new_rp(self):
        lat, lon = self._centre()
        r = ReferencePoint(side=self._side(), name=f"RP-{len(self.project.reference_points) + 1}", lat=lat, lon=lon)
        with self.edit("New reference point", "rps"):
            self.project.reference_points.append(r)
        self.refresh()
        self.doc.select(r.id, self)

    def _show_on_map(self, lat, lon):
        w = self.ctx.window
        if w:
            w.show_on_map(lat, lon)
