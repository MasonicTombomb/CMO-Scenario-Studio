"""Map page: the map with its toolbar, layers, and an inspector for the selected object."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QGuiApplication
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QInputDialog, QLabel, QMenu, QSplitter,
                             QStackedWidget, QToolBar, QToolButton, QVBoxLayout, QWidget)

from ...db.database import DBEntry
from ...geo import format_latlon
from ...model.project import ReferencePoint, Unit, Zone
from ...settings import TILE_SOURCES
from ..forms import RPForm, UnitForm, ZoneForm
from ..map.map_widget import MapWidget, Tool
from ..map.tiles import TileCache
from ..widgets import IdCombo, hint_label
from .base import AppContext, Page


class MapPage(Page):
    title = "Map"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        self.place_entry: Optional[DBEntry] = None
        self.tiles = TileCache(ctx.settings.cache_dir() / "tiles", self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        tb = QToolBar()
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        group = QActionGroup(self)
        self.tool_actions = {}
        for tool, text, tip in ((Tool.SELECT, "Select / move", "Select objects; drag units and points to move them"),
                                (Tool.PLACE, "Place unit", "Place the unit chosen in the DB browser"),
                                (Tool.RP, "Reference point", "Click to add reference points"),
                                (Tool.ZONE, "Draw area", "Draw a patrol / trigger area"),
                                (Tool.MEASURE, "Measure", "Measure distance and bearing"),
                                (Tool.COURSE, "Plot course", "Select a unit, then click waypoints for the route it "
                                                             "should fly or sail")):
            a = QAction(text, self, checkable=True)
            a.setToolTip(tip)
            a.triggered.connect(lambda _c, t=tool: self.set_tool(t))
            group.addAction(a)
            tb.addAction(a)
            self.tool_actions[tool] = a
        self.tool_actions[Tool.SELECT].setChecked(True)
        tb.addSeparator()
        tb.addWidget(QLabel(" New objects on: "))
        self.side_combo = IdCombo()
        self.side_combo.setMinimumWidth(110)
        tb.addWidget(self.side_combo)
        tb.addSeparator()
        tpl = QAction("Templates...", self)
        tpl.setToolTip("Place a pre-grouped site (airfield, command post, barracks...) at the map centre (Ctrl+T)")
        tpl.triggered.connect(lambda: self.ctx.window and self.ctx.window.place_template())
        tb.addAction(tpl)
        areas = QAction("Patrol areas...", self)
        areas.setToolTip("Add predefined sea and air patrol areas (Biscay, GIUK gap, Hormuz...) by region "
                         "(Ctrl+Shift+A)")
        areas.triggered.connect(lambda: self.ctx.window and self.ctx.window.add_library_area())
        tb.addAction(areas)
        tb.addSeparator()
        fit = QAction("Fit all", self)
        fit.triggered.connect(lambda: self.map.fit_project())
        tb.addAction(fit)
        # what the map shows: layers and sides, in one drop-down to keep the toolbar short
        self.show_menu = QMenu(self)
        self.show_menu.setToolTipsVisible(True)
        self.show_menu.addSection("Layers")

        def layer(text: str, on: bool, tip: str = "") -> QAction:
            a = self.show_menu.addAction(text)
            a.setCheckable(True)
            a.setChecked(on)
            if tip:
                a.setToolTip(tip)
            a.toggled.connect(self._layers)
            return a
        self.labels = layer("Labels", True, "Unit, area and reference point names")
        self.zones_cb = layer("Areas", True)
        self.rps_cb = layer("Ref points", True)
        self.courses_cb = layer("Courses", True, "The plotted courses of units")
        self.grid_cb = layer("Grid", False, "A latitude / longitude grid")
        self.show_menu.addSection("Sides")
        self._side_actions: list[QAction] = []
        self.show_menu.aboutToShow.connect(self._fill_side_actions)
        self.show_btn = QToolButton()
        self.show_btn.setText("Show ▾")
        self.show_btn.setToolTip("Show or hide labels, areas, reference points, courses, the grid and each side's "
                                 "units")
        self.show_btn.setMenu(self.show_menu)
        self.show_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.show_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        tb.addWidget(self.show_btn)
        tb.addSeparator()
        tb.addWidget(QLabel(" Map: "))
        self.tile_combo = QComboBox()
        self.tile_combo.addItems(list(TILE_SOURCES) + ["Custom"])
        self.tile_combo.setCurrentText(ctx.settings.tile_source)
        self.tile_combo.currentTextChanged.connect(self._tile_source)
        tb.addWidget(self.tile_combo)
        lay.addWidget(tb)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.map = MapWidget(self.tiles)
        split.addWidget(self.map)
        self.inspector = QStackedWidget()
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.addWidget(hint_label(
            "<b>Getting started</b><br><br>"
            "1. Find a unit in the <b>Database</b> panel and press <i>Place on map</i>, then click the map.<br>"
            "2. To build an airbase: place an airfield facility, select it, then pick an aircraft and press "
            "<i>Add to selected base</i>.<br>"
            "3. Use <i>Draw area</i> for patrol zones and <i>Reference point</i> for markers.<br>"
            "4. Right-click the map for more.<br><br>"
            "Scroll to zoom, drag to pan, Delete removes the selection, Esc cancels a tool."))
        el.addStretch()
        self.inspector.addWidget(empty)
        self.unit_form = UnitForm(ctx)
        self.rp_form = RPForm(ctx)
        self.zone_form = ZoneForm(ctx)
        for w in (self.unit_form, self.rp_form, self.zone_form):
            self.inspector.addWidget(w)
            w.centerRequested.connect(lambda lat, lon: self.map.center_on(lat, lon))
        self.inspector.setMinimumWidth(330)
        split.addWidget(self.inspector)
        split.setStretchFactor(0, 1)
        split.setSizes([900, 360])
        lay.addWidget(split, 1)

        m = self.map
        m.objectClicked.connect(lambda oid: self.doc.select(oid, self))
        m.objectMoved.connect(self._moved)
        m.zonePointMoved.connect(self._vertex_moved)
        m.placeRequested.connect(self._place)
        m.rpRequested.connect(self._add_rp)
        m.zoneFinished.connect(self._add_zone)
        m.courseFinished.connect(self._add_waypoints)
        m.waypointMoved.connect(self._waypoint_moved)
        m.contextRequested.connect(self._context)
        m.deleteRequested.connect(self._delete)
        m.cursorMoved.connect(lambda lat, lon: ctx.window and ctx.window.set_cursor_text(format_latlon(lat, lon)))
        m.message.connect(lambda t: ctx.status(t, 8000))
        self.doc.selected.connect(self._selected)
        self._tile_source(self.tile_combo.currentText())

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self.map.set_project(self.project)
        cur = self.side_combo.current_id()
        self.side_combo.set_items([(s.name, s.id) for s in self.project.sides], keep=False)
        if cur and self.project.side(cur):
            self.side_combo.set_current_id(cur)
        if self.doc.selection and not self.project.find(self.doc.selection):
            self.doc.select("")
        self.map.update()

    def _on_changed(self, kind, source):
        # Always repaint the map (cheap); the inspector forms refresh themselves.
        self.map.set_project(self.project)
        if kind in ("sides", "") or source is not self:
            super()._on_changed(kind, source)

    def _on_reset(self):
        self.map.set_project(self.project)
        super()._on_reset()

    def current_side(self) -> str:
        sid = self.side_combo.current_id()
        if not sid and self.project.sides:
            sid = self.project.sides[0].id
        return sid

    # ------------------------------------------------------------------ tools
    def set_tool(self, tool: Tool, label: str = "") -> None:
        if tool == Tool.COURSE:
            u = self.project.unit(self.doc.selection) if self.doc.selection else None
            if u is None:
                self.ctx.status("Select a unit first, then press 'Plot course' and click its waypoints.")
                self.tool_actions[Tool.SELECT].setChecked(True)
                self.map.set_tool(Tool.SELECT)
                return
            self.plot_course(u.id)
            return
        self.tool_actions[tool].setChecked(True)
        if tool == Tool.PLACE and not self.place_entry:
            self.ctx.status("Choose a unit in the Database panel first, then press 'Place on map'.")
            self.tool_actions[Tool.SELECT].setChecked(True)
            tool = Tool.SELECT
        self.map.set_tool(tool, label or (self.place_entry.name if self.place_entry else ""))
        self.map.setFocus()

    def start_place(self, entry: DBEntry) -> None:
        self.place_entry = entry
        self.set_tool(Tool.PLACE, entry.name)

    def plot_course(self, unit_id: str) -> None:
        """Course tool for this unit: each click adds a waypoint to the end of its course."""
        u = self.project.unit(unit_id)
        if u is None:
            return
        self.tool_actions[Tool.COURSE].setChecked(True)
        self.map.start_course(u.id, u.name)
        self.map.setFocus()

    def _add_waypoints(self, unit_id: str, pts: list) -> None:
        from ...model.project import Course, Waypoint
        u = self.project.unit(unit_id)
        self.tool_actions[Tool.SELECT].setChecked(True)
        if u is None or not pts:
            return
        with self.edit(f"Plot course for {u.name}", "units"):
            if u.course is None:
                u.course = Course()
            u.course.waypoints.extend(Waypoint(round(a, 6), round(b, 6)) for a, b in pts)
        self.doc.select(u.id, None)
        self.ctx.status(f"{u.name}: {len(u.course.waypoints)} waypoint(s). Set its departure and what it does at "
                        f"the end in the inspector.")

    def _waypoint_moved(self, unit_id: str, i: int, lat: float, lon: float) -> None:
        u = self.project.unit(unit_id)
        if u is None or u.course is None or not (0 <= i < len(u.course.waypoints)):
            return
        with self.edit("Move waypoint", "units"):
            u.course.waypoints[i].lat, u.course.waypoints[i].lon = round(lat, 6), round(lon, 6)

    def _clear_course(self, unit_id: str) -> None:
        u = self.project.unit(unit_id)
        if u is not None and u.course is not None:
            with self.edit(f"Clear course of {u.name}", "units"):
                u.course = None

    def _layers(self, *_):
        self.map.show_courses = self.courses_cb.isChecked()
        self.map.show_labels = self.labels.isChecked()
        self.map.show_zones = self.zones_cb.isChecked()
        self.map.show_rps = self.rps_cb.isChecked()
        self.map.show_grid = self.grid_cb.isChecked()
        self.map.update()

    def _fill_side_actions(self):
        for a in self._side_actions:
            self.show_menu.removeAction(a)
        self._side_actions = []
        for s in self.project.sides:
            a = self.show_menu.addAction(s.name)
            a.setCheckable(True)
            a.setChecked(s.id not in self.map.hidden_sides)
            a.toggled.connect(lambda on, sid=s.id: self._toggle_side(sid, on))
            self._side_actions.append(a)

    def _toggle_side(self, sid: str, on: bool):
        if on:
            self.map.hidden_sides.discard(sid)
        else:
            self.map.hidden_sides.add(sid)
        self.map.update()

    def _tile_source(self, name: str):
        s = self.ctx.settings
        s.tile_source = name
        if name == "Custom":
            url = s.custom_tile_url
            if not url:
                url, ok = QInputDialog.getText(self, "Custom tiles", "XYZ tile URL template ({z}/{x}/{y}):",
                                               text="https://")
                if not ok or "{z}" not in url:
                    self.tile_combo.setCurrentText("None (offline grid)")
                    return
                s.custom_tile_url = url
            self.tiles.set_source(url, 19)
            self.map.attribution = "Custom tiles"
        else:
            url, attrib, maxz = TILE_SOURCES.get(name, TILE_SOURCES["None (offline grid)"])
            self.tiles.set_source(url, maxz)
            self.map.attribution = attrib
        self.map.zoom = min(self.map.zoom, self.tiles.max_zoom)
        self.map.update()

    # ------------------------------------------------------------------ selection
    def _selected(self, oid: str, source):
        self.map.select(oid)
        obj = self.project.find(oid) if oid else None
        if isinstance(obj, Unit):
            if obj.host:
                self.map.select(obj.host)     # hosted units are drawn at their base
            self.unit_form.set_unit(oid)
            self.inspector.setCurrentWidget(self.unit_form)
            if source is not self and not obj.host and (obj.lat or obj.lon):
                self._ensure_visible(obj.lat, obj.lon)
        elif isinstance(obj, ReferencePoint):
            self.rp_form.set_rp(oid)
            self.inspector.setCurrentWidget(self.rp_form)
            if source is not self:
                self._ensure_visible(obj.lat, obj.lon)
        elif isinstance(obj, Zone):
            self.zone_form.set_zone(oid)
            self.inspector.setCurrentWidget(self.zone_form)
            if source is not self and obj.points:
                self.map.fit([(a, b) for a, b in obj.points])
        else:
            self.inspector.setCurrentIndex(0)

    def _ensure_visible(self, lat, lon):
        q = self.map.to_screen(lat, lon)
        if not self.map.rect().adjusted(40, 40, -40, -40).contains(q.toPoint()):
            self.map.center_on(lat, lon)

    # ------------------------------------------------------------------ edits from the map
    def _moved(self, oid: str, lat: float, lon: float):
        obj = self.project.find(oid)
        if obj is None:
            return
        from ...model.formations import move_with_formation
        moved_group = False
        with self.edit("Move " + getattr(obj, "name", "object"), "units" if isinstance(obj, Unit) else "rps"):
            if isinstance(obj, Unit):
                moved_group = move_with_formation(self.project, obj.id, lat, lon)
                for u in self.project.units:
                    host = self.project.unit(u.host) if u.host else None
                    if host is not None:
                        u.lat, u.lon = host.lat, host.lon
            else:
                obj.lat, obj.lon = lat, lon
        if moved_group:
            self.ctx.status("Moved the whole formation (untick 'keep on station' to move one unit).")
        self.doc.select(oid, self)

    def _vertex_moved(self, zid: str, idx: int, lat: float, lon: float):
        z = self.project.zone(zid)
        if z and 0 <= idx < len(z.points):
            with self.edit("Move area corner", "zones"):
                z.points[idx] = [lat, lon]
            self.zone_form.refresh()

    def _place(self, lat: float, lon: float):
        e = self.place_entry
        sid = self.current_side()
        if not e or not sid:
            self.ctx.status("Add a side first (Sides tab).")
            return
        self.add_unit_from_entry(e, sid, lat, lon)

    def add_unit_from_entry(self, e: DBEntry, sid: str, lat: float, lon: float, host: str = "",
                            count: int = 1) -> Unit:
        name = self.project.unique_unit_name(e.name, sid)
        u = Unit(side=sid, type=e.type, dbid=e.id, db_name=e.name, name=name, lat=lat, lon=lon, host=host,
                 count=count)
        if e.type == "Aircraft":
            if not host:
                u.altitude = 9000.0
            u.loadout = self._default_loadout(e.id)
        with self.edit(f"Add {e.name}", "units"):
            self.project.units.append(u)
        self.doc.select(u.id, self)
        self.ctx.status(f"Added {name}. Click again to place another, Esc to stop.")
        return u

    def _default_loadout(self, aircraft_id: int) -> Optional[int]:
        db = self.ctx.db
        if not db:
            return None
        los = db.loadouts(aircraft_id, combat_only=True)
        return los[0].id if los else None

    def _add_rp(self, lat: float, lon: float):
        sid = self.current_side()
        if not sid:
            return
        n = len(self.project.reference_points) + 1
        rp = ReferencePoint(side=sid, name=f"RP-{n}", lat=lat, lon=lon)
        with self.edit("Add reference point", "rps"):
            self.project.reference_points.append(rp)
        self.doc.select(rp.id, self)

    def _add_zone(self, pts: list):
        sid = self.current_side()
        if not sid:
            return
        n = len(self.project.zones) + 1
        name, ok = QInputDialog.getText(self, "New area", "Area name (reference points become NAME-1, NAME-2...):",
                                        text=f"AREA_{n}")
        if not ok or not name.strip():
            return
        z = Zone(side=sid, name=name.strip().replace(" ", "_"), points=[list(p) for p in pts])
        with self.edit("Draw area", "zones"):
            self.project.zones.append(z)
        self.set_tool(Tool.SELECT)
        self.doc.select(z.id, self)

    def _delete(self, oid: str):
        obj = self.project.find(oid)
        if isinstance(obj, Unit):
            self.unit_form.set_unit(oid)
            self.unit_form._delete()
        elif isinstance(obj, ReferencePoint):
            with self.edit("Delete reference point", "rps"):
                self.project.reference_points = [r for r in self.project.reference_points if r.id != oid]
            self.doc.select("")
        elif isinstance(obj, Zone):
            with self.edit("Delete area", "zones"):
                self.project.remove_zone(oid)
            self.doc.select("")

    def _context(self, lat: float, lon: float, oid: str, gpos):
        menu = QMenu(self)
        obj = self.project.find(oid) if oid else None
        if obj is not None:
            menu.addAction(f"Select '{getattr(obj, 'name', oid)}'", lambda: self.doc.select(oid, self))
            if isinstance(obj, Unit):
                menu.addAction("Duplicate", lambda: (self.unit_form.set_unit(oid), self.unit_form._duplicate()))
                menu.addAction("Plot course..." if not (obj.course and obj.course.waypoints) else
                               "Add waypoints to course...", lambda: (self.doc.select(oid, self),
                                                                      self.plot_course(oid)))
                if obj.course and obj.course.waypoints:
                    menu.addAction("Clear course", lambda: self._clear_course(oid))
                from ...model.formations import formation_of
                fm = formation_of(self.project, oid)
                if self.ctx.window is not None:
                    if fm is not None:
                        menu.addAction(f"Edit formation '{fm.name}'", lambda: self.ctx.window.open_formation(fm.id))
                    else:
                        menu.addAction("Make formation from this unit...",
                                       lambda: self.ctx.window.make_formation([oid]))
            if isinstance(obj, Zone) and self.ctx.window is not None:
                menu.addAction("Save area to library...", lambda: self.ctx.window.save_zone_to_library(oid))
            menu.addAction("Delete", lambda: self._delete(oid))
            menu.addSeparator()
        if self.place_entry:
            menu.addAction(f"Place {self.place_entry.name} here", lambda: self._place(lat, lon))
        menu.addAction("Add reference point here", lambda: self._add_rp(lat, lon))
        if self.ctx.window is not None:
            menu.addAction("Place unit template here...", lambda: self.ctx.window.place_template(lat, lon))
            menu.addAction("Add patrol area from library...", lambda: self.ctx.window.add_library_area())
        menu.addAction("Draw area from here", lambda: (self.set_tool(Tool.ZONE), self.map._draft.append([lat, lon])))
        menu.addAction("Measure from here", lambda: (self.set_tool(Tool.MEASURE),
                                                      self.map._measure.append((lat, lon))))
        menu.addSeparator()
        menu.addAction(f"Copy coordinates  ({format_latlon(lat, lon)})",
                       lambda: QGuiApplication.clipboard().setText(format_latlon(lat, lon)))
        menu.addAction("Centre here", lambda: self.map.center_on(lat, lon))
        menu.exec(gpos)
