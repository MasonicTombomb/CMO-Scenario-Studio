"""Interactive Web-Mercator map: tiles + units, reference points and areas from the project.

Tools: select/move, place unit, add reference point, draw area, measure.
The widget never edits the project itself; it emits signals that the map page
turns into undoable edits.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QCursor, QFont, QPainter, QPainterPath, QPen, QPixmap, QPolygonF)
from PyQt6.QtWidgets import QWidget

from ...geo import TILE, bearing_deg, distance_km, from_world, to_world, world_size
from ...model.project import Project
from .tiles import TileCache


class Tool(Enum):
    SELECT = "select"
    PLACE = "place"
    RP = "rp"
    ZONE = "zone"
    MEASURE = "measure"


HIT_PX = 11


class MapWidget(QWidget):
    objectClicked = pyqtSignal(str)                    # unit / rp / zone id ('' = nothing)
    objectMoved = pyqtSignal(str, float, float)        # id, lat, lon (unit or rp)
    zonePointMoved = pyqtSignal(str, int, float, float)
    placeRequested = pyqtSignal(float, float)
    rpRequested = pyqtSignal(float, float)
    zoneFinished = pyqtSignal(list)                    # [[lat, lon], ...]
    contextRequested = pyqtSignal(float, float, str, object)   # lat, lon, hit id, global QPoint
    cursorMoved = pyqtSignal(float, float)
    deleteRequested = pyqtSignal(str)
    message = pyqtSignal(str)
    viewChanged = pyqtSignal()

    def __init__(self, tiles: TileCache, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(300, 200)
        self.tiles = tiles
        tiles.tileReady.connect(self.update)
        self.project: Optional[Project] = None
        self.zoom = 5
        self.cx, self.cy = to_world(57.5, 20.0, self.zoom)   # world pixel at the centre
        self.tool = Tool.SELECT
        self.selected = ""
        self.hidden_sides: set[str] = set()
        self.show_labels = True
        self.show_zones = True
        self.show_rps = True
        self.show_grid = False
        self.attribution = ""
        self.place_label = ""
        self._drag_start: Optional[QPointF] = None
        self._drag_mode = ""              # 'pan' | 'move' | 'vertex'
        self._drag_id = ""
        self._drag_vertex = -1
        self._drag_pos: Optional[tuple[float, float]] = None
        self._moved = False
        self._draft: list[list[float]] = []
        self._measure: list[tuple[float, float]] = []
        self._mouse: Optional[QPointF] = None

    # ------------------------------------------------------------------ public
    def set_project(self, project: Project) -> None:
        self.project = project
        self.update()

    def set_tool(self, tool: Tool, label: str = "") -> None:
        self.tool = tool
        self.place_label = label
        self._draft.clear()
        self._measure.clear()
        cursors = {Tool.SELECT: Qt.CursorShape.ArrowCursor, Tool.PLACE: Qt.CursorShape.CrossCursor,
                   Tool.RP: Qt.CursorShape.CrossCursor, Tool.ZONE: Qt.CursorShape.CrossCursor,
                   Tool.MEASURE: Qt.CursorShape.CrossCursor}
        self.setCursor(QCursor(cursors[tool]))
        hints = {
            Tool.SELECT: "Select: click to select, drag a unit/point to move it, drag the map to pan.",
            Tool.PLACE: f"Place: click the map to place {label or 'the unit'}. Esc to stop.",
            Tool.RP: "Reference point: click to add. Esc to stop.",
            Tool.ZONE: "Draw area: click to add corners, double-click or Enter to finish, Backspace to undo, Esc cancels.",
            Tool.MEASURE: "Measure: click points to measure a route. Esc clears.",
        }
        self.message.emit(hints[tool])
        self.update()

    def center_on(self, lat: float, lon: float, zoom: Optional[int] = None) -> None:
        if zoom is not None:
            self.zoom = max(1, min(self.tiles.max_zoom, int(zoom)))
        self.cx, self.cy = to_world(lat, lon, self.zoom)
        self.update()
        self.viewChanged.emit()

    def center(self) -> tuple[float, float]:
        return from_world(self.cx, self.cy, self.zoom)

    def fit(self, points: list[tuple[float, float]]) -> None:
        if not points:
            return
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        for z in range(min(self.tiles.max_zoom, 14), 1, -1):
            x0, y0 = to_world(max(lats), min(lons), z)
            x1, y1 = to_world(min(lats), max(lons), z)
            if abs(x1 - x0) < self.width() * 0.85 and abs(y1 - y0) < self.height() * 0.85:
                break
        self.zoom = z
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.update()
        self.viewChanged.emit()

    def fit_project(self) -> None:
        if not self.project:
            return
        pts = [(u.lat, u.lon) for u in self.project.units if not u.host and (u.lat or u.lon)]
        pts += [(r.lat, r.lon) for r in self.project.reference_points]
        for z in self.project.zones:
            pts += [(p[0], p[1]) for p in z.points]
        self.fit(pts)

    def select(self, oid: str) -> None:
        self.selected = oid
        self.update()

    # ------------------------------------------------------------------ coordinates
    def to_screen(self, lat: float, lon: float) -> QPointF:
        x, y = to_world(lat, lon, self.zoom)
        return QPointF(x - self.cx + self.width() / 2, y - self.cy + self.height() / 2)

    def to_latlon(self, p: QPointF) -> tuple[float, float]:
        x = p.x() - self.width() / 2 + self.cx
        y = p.y() - self.height() / 2 + self.cy
        lat, lon = from_world(x, y, self.zoom)
        lon = ((lon + 180) % 360) - 180
        return lat, lon

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0f1720"))
        self._paint_tiles(p)
        if self.show_grid or not self.tiles.url:
            self._paint_grid(p)
        if self.project:
            if self.show_zones:
                self._paint_zones(p)
            if self.show_rps:
                self._paint_rps(p)
            self._paint_formations(p)
            self._paint_units(p)
        self._paint_draft(p)
        self._paint_measure(p)
        self._paint_scale(p)
        if self.attribution:
            p.setPen(QColor(220, 220, 220, 170))
            f = p.font()
            f.setPointSize(7)
            p.setFont(f)
            p.drawText(self.rect().adjusted(0, 0, -6, -4), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                       self.attribution)
        p.end()

    def _paint_tiles(self, p: QPainter) -> None:
        if not self.tiles.url:
            return
        z = self.zoom
        n = 2 ** z
        left = self.cx - self.width() / 2
        top = self.cy - self.height() / 2
        tx0, ty0 = int(math.floor(left / TILE)), int(math.floor(top / TILE))
        tx1, ty1 = int(math.floor((left + self.width()) / TILE)), int(math.floor((top + self.height()) / TILE))
        wanted = set()
        for ty in range(max(0, ty0), min(n - 1, ty1) + 1):
            for tx in range(tx0, tx1 + 1):
                wx = tx % n
                wanted.add((z, wx, ty))
                sx, sy = tx * TILE - left, ty * TILE - top
                pm = self.tiles.tile(z, wx, ty)
                if pm is not None:
                    p.drawPixmap(QRectF(sx, sy, TILE, TILE), pm, QRectF(pm.rect()))
                else:
                    self._paint_parent_tile(p, z, wx, ty, sx, sy)
        self.tiles.cancel_outside(wanted)

    def _paint_parent_tile(self, p: QPainter, z: int, x: int, y: int, sx: float, sy: float) -> None:
        """While a tile loads, stretch the cached tile from a lower zoom level."""
        for up in range(1, 5):
            pz = z - up
            if pz < 0:
                return
            px, py = x >> up, y >> up
            key = (self.tiles.url, pz, px, py)
            pm: Optional[QPixmap] = self.tiles._mem.get(key)
            if pm is not None:
                frac = TILE / (2 ** up)
                src = QRectF((x - (px << up)) * frac, (y - (py << up)) * frac, frac, frac)
                p.drawPixmap(QRectF(sx, sy, TILE, TILE), pm, src)
                return

    def _paint_grid(self, p: QPainter) -> None:
        lat0, lon0 = self.to_latlon(QPointF(0, self.height()))
        lat1, lon1 = self.to_latlon(QPointF(self.width(), 0))
        span = max(abs(lon1 - lon0), 0.01)
        step = next(s for s in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 45, 90) if span / s < 14)
        p.setPen(QPen(QColor(120, 150, 180, 70), 1))
        f = p.font()
        f.setPointSize(7)
        p.setFont(f)
        lon = math.floor(lon0 / step) * step
        while lon <= lon1:
            pt = self.to_screen(0, lon)
            p.drawLine(QPointF(pt.x(), 0), QPointF(pt.x(), self.height()))
            p.drawText(QPointF(pt.x() + 2, 12), f"{lon:g}°")
            lon += step
        lat = math.floor(lat0 / step) * step
        while lat <= lat1:
            pt = self.to_screen(lat, 0)
            p.drawLine(QPointF(0, pt.y()), QPointF(self.width(), pt.y()))
            p.drawText(QPointF(2, pt.y() - 2), f"{lat:g}°")
            lat += step

    def _side_color(self, sid: str) -> QColor:
        s = self.project.side(sid) if self.project else None
        return QColor(s.color if s else "#cccccc")

    def _visible(self, sid: str, all_sides: bool = False) -> bool:
        return all_sides or sid not in self.hidden_sides

    def _paint_zones(self, p: QPainter) -> None:
        for z in self.project.zones:
            if not z.points or not self._visible(z.side, z.all_sides):
                continue
            col = QColor(z.color) if z.color else self._side_color(z.side)
            pts = [self.to_screen(a, b) for a, b in z.points]
            if self._drag_mode == "vertex" and self._drag_id == z.id and self._drag_pos:
                pts[self._drag_vertex] = self.to_screen(*self._drag_pos)
            sel = z.id == self.selected
            fill = QColor(col)
            fill.setAlpha(55 if sel else 28)
            pen = QPen(col, 2.2 if sel else 1.4)
            if z.all_sides:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QBrush(fill))
            if len(pts) >= 3:
                p.drawPolygon(QPolygonF(pts))
            elif len(pts) == 2:
                p.drawLine(pts[0], pts[1])
            if sel or self.zoom >= 9:
                p.setBrush(QBrush(QColor("#ffffff") if sel else col))
                for q in pts:
                    p.drawRect(QRectF(q.x() - 3, q.y() - 3, 6, 6))
            if self.show_labels and pts:
                cx = sum(q.x() for q in pts) / len(pts)
                cy = sum(q.y() for q in pts) / len(pts)
                self._label(p, QPointF(cx, cy), z.name, col, center=True)

    def _paint_rps(self, p: QPainter) -> None:
        for r in self.project.reference_points:
            if not self._visible(r.side, r.all_sides):
                continue
            pos = (self._drag_pos if (self._drag_mode == "move" and self._drag_id == r.id and self._drag_pos)
                   else (r.lat, r.lon))
            q = self.to_screen(*pos)
            col = QColor("#ffd166") if r.highlighted else self._side_color(r.side)
            sel = r.id == self.selected
            p.setPen(QPen(QColor("#ffffff") if sel else QColor("#111111"), 1.5 if sel else 1))
            p.setBrush(QBrush(col))
            d = 6 if sel else 5
            p.drawPolygon(QPolygonF([QPointF(q.x(), q.y() - d), QPointF(q.x() + d, q.y()),
                                     QPointF(q.x(), q.y() + d), QPointF(q.x() - d, q.y())]))
            if self.show_labels:
                self._label(p, QPointF(q.x() + 8, q.y() + 4), r.name, col)

    def _paint_formations(self, p: QPainter) -> None:
        """Thin dashed links from each formation lead to its members."""
        for f in getattr(self.project, "formations", []):
            lead = self.project.unit(f.lead)
            if lead is None or lead.host or not self._visible(lead.side):
                continue
            col = QColor(self._side_color(lead.side))
            col.setAlpha(150 if f.id == self.selected or f.lead == self.selected else 90)
            pen = QPen(col, 1.2, Qt.PenStyle.DashLine)
            p.setPen(pen)
            a = self.to_screen(lead.lat, lead.lon)
            for uid in f.members:
                u = self.project.unit(uid)
                if u is not None and not u.host:
                    p.drawLine(a, self.to_screen(u.lat, u.lon))

    def _unit_path(self, utype: str, s: float) -> QPainterPath:
        path = QPainterPath()
        if utype == "Aircraft":
            path.moveTo(0, -s)
            path.lineTo(s * 0.9, s * 0.8)
            path.lineTo(0, s * 0.35)
            path.lineTo(-s * 0.9, s * 0.8)
            path.closeSubpath()
        elif utype == "Ship":
            path.addRoundedRect(QRectF(-s * 1.1, -s * 0.55, s * 2.2, s * 1.1), s * 0.5, s * 0.5)
        elif utype == "Submarine":
            path.moveTo(-s * 1.1, 0)
            path.arcTo(QRectF(-s * 1.1, -s * 0.7, s * 2.2, s * 1.4), 180, 180)
            path.closeSubpath()
        elif utype == "GroundUnit":
            path.moveTo(0, -s)
            path.lineTo(s, 0)
            path.lineTo(0, s)
            path.lineTo(-s, 0)
            path.closeSubpath()
        else:
            path.addRect(QRectF(-s * 0.8, -s * 0.8, s * 1.6, s * 1.6))
        return path

    def _paint_units(self, p: QPainter) -> None:
        hosted: dict[str, int] = {}
        for u in self.project.units:
            if u.host:
                hosted[u.host] = hosted.get(u.host, 0) + max(1, u.count)
        font = QFont(p.font())
        font.setPointSize(8)
        p.setFont(font)
        for u in self.project.units:
            if u.host or not self._visible(u.side):
                continue
            pos = (self._drag_pos if (self._drag_mode == "move" and self._drag_id == u.id and self._drag_pos)
                   else (u.lat, u.lon))
            q = self.to_screen(*pos)
            if not (-40 < q.x() < self.width() + 40 and -40 < q.y() < self.height() + 40):
                continue
            col = self._side_color(u.side)
            sel = u.id == self.selected
            size = 8 if sel else 6.5
            path = self._unit_path(u.type, size)
            p.save()
            p.translate(q)
            if u.type in ("Aircraft",) and u.heading is not None:
                p.rotate(u.heading)
            fill = QColor(col)
            if u.reserve:
                fill.setAlpha(90)
            p.setBrush(QBrush(fill))
            pen = QPen(QColor("#ffffff") if sel else QColor("#0b0b0b"), 2 if sel else 1)
            if u.reserve:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawPath(path)
            p.restore()
            if hosted.get(u.id):
                badge = str(hosted[u.id])
                p.setBrush(QBrush(QColor("#111111")))
                p.setPen(QPen(col, 1))
                w = 7 + 6 * len(badge)
                p.drawRoundedRect(QRectF(q.x() + 6, q.y() - 15, w, 12), 5, 5)
                p.setPen(QColor("#ffffff"))
                p.drawText(QRectF(q.x() + 6, q.y() - 15, w, 12), Qt.AlignmentFlag.AlignCenter, badge)
            if u.count > 1:
                p.setPen(QColor("#ffffff"))
                p.drawText(QPointF(q.x() - 4, q.y() + 18), f"x{u.count}")
            if self.show_labels and (self.zoom >= 7 or sel):
                self._label(p, QPointF(q.x() + 10, q.y() + 4), u.name, col)

    def _label(self, p: QPainter, at: QPointF, text: str, col: QColor, center: bool = False) -> None:
        fm = p.fontMetrics()
        w = fm.horizontalAdvance(text)
        pos = QPointF(at.x() - w / 2, at.y()) if center else at
        p.setPen(QColor(0, 0, 0, 200))
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            p.drawText(pos + QPointF(dx, dy), text)
        p.setPen(col.lighter(150))
        p.drawText(pos, text)

    def _paint_draft(self, p: QPainter) -> None:
        if self.tool != Tool.ZONE or not self._draft:
            return
        pts = [self.to_screen(a, b) for a, b in self._draft]
        if self._mouse is not None:
            pts.append(self._mouse)
        p.setPen(QPen(QColor("#ffd166"), 2, Qt.PenStyle.DashLine))
        fill = QColor("#ffd166")
        fill.setAlpha(30)
        p.setBrush(QBrush(fill))
        if len(pts) >= 3:
            p.drawPolygon(QPolygonF(pts))
        else:
            p.drawPolyline(QPolygonF(pts))
        p.setBrush(QBrush(QColor("#ffd166")))
        for q in pts[:len(self._draft)]:
            p.drawEllipse(q, 3.5, 3.5)

    def _paint_measure(self, p: QPainter) -> None:
        if self.tool != Tool.MEASURE or not self._measure:
            return
        pts = list(self._measure)
        if self._mouse is not None:
            pts.append(self.to_latlon(self._mouse))
        p.setPen(QPen(QColor("#00e0ff"), 2))
        total = 0.0
        for a, b in zip(pts, pts[1:]):
            qa, qb = self.to_screen(*a), self.to_screen(*b)
            p.drawLine(qa, qb)
            d = distance_km(a[0], a[1], b[0], b[1])
            total += d
            brg = bearing_deg(a[0], a[1], b[0], b[1])
            mid = (qa + qb) / 2
            self._label(p, mid + QPointF(6, -6), f"{d:.1f} km / {d / 1.852:.1f} nm  {brg:03.0f}°", QColor("#00e0ff"))
        if len(pts) > 2:
            self._label(p, self.to_screen(*pts[-1]) + QPointF(8, 16),
                        f"total {total:.1f} km / {total / 1.852:.1f} nm", QColor("#00e0ff"))

    def _paint_scale(self, p: QPainter) -> None:
        lat, _ = self.center()
        m_per_px = 40075016.686 * math.cos(math.radians(lat)) / world_size(self.zoom)
        target = 120 * m_per_px / 1000.0   # km in 120 px
        nice = next((v for v in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000) if v >= target * 0.6), 5000)
        px = nice * 1000.0 / m_per_px
        x0, y0 = 12, self.height() - 14
        p.setPen(QPen(QColor("#dddddd"), 2))
        p.drawLine(QPointF(x0, y0), QPointF(x0 + px, y0))
        p.drawLine(QPointF(x0, y0 - 4), QPointF(x0, y0 + 2))
        p.drawLine(QPointF(x0 + px, y0 - 4), QPointF(x0 + px, y0 + 2))
        self._label(p, QPointF(x0 + 2, y0 - 6), f"{nice} km  (zoom {self.zoom})", QColor("#bbbbbb"))

    # ------------------------------------------------------------------ hit testing
    def hit(self, pos: QPointF) -> tuple[str, str, int]:
        """(kind, id, vertex) under the cursor: kind in unit/rp/vertex/zone/''."""
        if not self.project:
            return "", "", -1
        sel_zone = self.project.zone(self.selected) if self.selected else None
        if sel_zone:
            for i, (a, b) in enumerate(sel_zone.points):
                if (self.to_screen(a, b) - pos).manhattanLength() < HIT_PX:
                    return "vertex", sel_zone.id, i
        best, best_d = ("", "", -1), HIT_PX * 1.0
        for u in self.project.units:
            if u.host or not self._visible(u.side):
                continue
            d = (self.to_screen(u.lat, u.lon) - pos).manhattanLength()
            if d < best_d:
                best, best_d = ("unit", u.id, -1), d
        if self.show_rps:
            for r in self.project.reference_points:
                if not self._visible(r.side, r.all_sides):
                    continue
                d = (self.to_screen(r.lat, r.lon) - pos).manhattanLength()
                if d < best_d:
                    best, best_d = ("rp", r.id, -1), d
        if best[0]:
            return best
        if self.show_zones:
            for z in reversed(self.project.zones):
                if len(z.points) >= 3 and self._visible(z.side, z.all_sides):
                    poly = QPolygonF([self.to_screen(a, b) for a, b in z.points])
                    if poly.containsPoint(pos, Qt.FillRule.OddEvenFill):
                        return "zone", z.id, -1
        return "", "", -1

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, e) -> None:
        pos = e.position()
        self._drag_start = pos
        self._moved = False
        if e.button() == Qt.MouseButton.RightButton:
            return
        if e.button() == Qt.MouseButton.MiddleButton or self.tool != Tool.SELECT:
            self._drag_mode = "pan"
            return
        kind, oid, vertex = self.hit(pos)
        if kind in ("unit", "rp"):
            self._drag_mode, self._drag_id = "move", oid
        elif kind == "vertex":
            self._drag_mode, self._drag_id, self._drag_vertex = "vertex", oid, vertex
        else:
            self._drag_mode = "pan"
        self._last = pos

    def mouseMoveEvent(self, e) -> None:
        pos = e.position()
        self._mouse = pos
        lat, lon = self.to_latlon(pos)
        self.cursorMoved.emit(lat, lon)
        if self._drag_start is not None and (pos - self._drag_start).manhattanLength() > 3:
            self._moved = True
        if self._drag_start is not None and e.buttons() != Qt.MouseButton.NoButton and self._moved:
            if self._drag_mode == "pan":
                last = getattr(self, "_last", self._drag_start)
                d = pos - last
                self.cx -= d.x()
                self.cy -= d.y()
                self._last = pos
                self.viewChanged.emit()
            elif self._drag_mode in ("move", "vertex"):
                self._drag_pos = (lat, lon)
        self.update()

    def mouseReleaseEvent(self, e) -> None:
        pos = e.position()
        if e.button() == Qt.MouseButton.RightButton:
            if self.tool == Tool.ZONE and self._draft:
                self._draft.pop()
                self.update()
                return
            lat, lon = self.to_latlon(pos)
            kind, oid, _ = self.hit(pos)
            self.contextRequested.emit(lat, lon, oid, e.globalPosition().toPoint())
            self._drag_start = None
            return
        mode, self._drag_mode = self._drag_mode, ""
        if self._moved and mode in ("move", "vertex") and self._drag_pos:
            lat, lon = self._drag_pos
            if mode == "move":
                self.objectMoved.emit(self._drag_id, lat, lon)
            else:
                self.zonePointMoved.emit(self._drag_id, self._drag_vertex, lat, lon)
        elif not self._moved:
            self._click(pos)
        self._drag_pos = None
        self._drag_start = None
        self.update()

    def _click(self, pos: QPointF) -> None:
        lat, lon = self.to_latlon(pos)
        if self.tool == Tool.SELECT:
            kind, oid, _ = self.hit(pos)
            self.selected = oid
            self.objectClicked.emit(oid)
        elif self.tool == Tool.PLACE:
            self.placeRequested.emit(lat, lon)
        elif self.tool == Tool.RP:
            self.rpRequested.emit(lat, lon)
        elif self.tool == Tool.ZONE:
            self._draft.append([lat, lon])
        elif self.tool == Tool.MEASURE:
            self._measure.append((lat, lon))
        self.update()

    def mouseDoubleClickEvent(self, e) -> None:
        if self.tool == Tool.ZONE:
            self._finish_zone()

    def _finish_zone(self) -> None:
        # the double-click also produced a click at the same point: drop near-duplicates
        pts: list[list[float]] = []
        for pt in self._draft:
            if not pts or (self.to_screen(*pts[-1]) - self.to_screen(*pt)).manhattanLength() > 4:
                pts.append(pt)
        self._draft.clear()
        if len(pts) >= 1:
            self.zoneFinished.emit(pts)
        self.update()

    def wheelEvent(self, e) -> None:
        steps = e.angleDelta().y() / 120
        if not steps:
            return
        new = max(1, min(self.tiles.max_zoom, self.zoom + (1 if steps > 0 else -1)))
        if new == self.zoom:
            return
        pos = e.position()
        lat, lon = self.to_latlon(pos)
        self.zoom = new
        x, y = to_world(lat, lon, new)
        self.cx = x - (pos.x() - self.width() / 2)
        self.cy = y - (pos.y() - self.height() / 2)
        self.update()
        self.viewChanged.emit()

    def keyPressEvent(self, e) -> None:
        k = e.key()
        if k == Qt.Key.Key_Escape:
            if self.tool != Tool.SELECT:
                self.set_tool(Tool.SELECT)
            else:
                self.selected = ""
                self.objectClicked.emit("")
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.tool == Tool.ZONE:
            self._finish_zone()
        elif k == Qt.Key.Key_Backspace and self.tool == Tool.ZONE and self._draft:
            self._draft.pop()
        elif k == Qt.Key.Key_Delete and self.selected:
            self.deleteRequested.emit(self.selected)
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom = min(self.tiles.max_zoom, self.zoom + 1)
            lat, lon = from_world(self.cx, self.cy, self.zoom - 1)
            self.cx, self.cy = to_world(lat, lon, self.zoom)
        elif k == Qt.Key.Key_Minus:
            lat, lon = self.center()
            self.zoom = max(1, self.zoom - 1)
            self.cx, self.cy = to_world(lat, lon, self.zoom)
        else:
            super().keyPressEvent(e)
            return
        self.update()

    def leaveEvent(self, e) -> None:
        self._mouse = None
        self.update()
