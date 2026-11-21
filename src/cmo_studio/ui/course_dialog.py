"""The course window: plot a unit's route on a map, set what it does on each leg, and see the flight profile.

It edits a copy of the project; **OK** writes the course back as one undoable change and **Cancel** drops it.
"""

from __future__ import annotations

import copy
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
                             QTableWidgetItem, QToolTip, QVBoxLayout, QWidget)

from ..model.course_plan import LATE_S, CoursePlan, Leg, hms, plan_course, plan_times
from ..model.enums import HOST_TYPES
from ..model.project import COURSE_FINISH, ENGAGE_SETTING, SENSOR_SETTING, WEAPONS_SETTING, Course, Waypoint
from .map.map_widget import MapWidget, Tool
from .widgets import IdCombo, PickerDialog, hint_label

ALT_COL = QColor("#3d8bfd")
SPEED_COL = QColor("#f5a524")
ON_COL, OFF_COL, NONE_COL = QColor("#30a46c"), QColor("#5b6270"), QColor("#2c3038")
WCS_COL = {"free": QColor("#e5484d"), "tight": QColor("#f5a524"), "hold": QColor("#30a46c"), "": NONE_COL}
WCS_TEXT = {"free": "Free", "tight": "Tight", "hold": "Hold", "": "Doctrine"}
FT = 3.28084


def _onoff(v: Optional[bool]) -> str:
    return "On" if v else "Off" if v is False else "-"


# ====================================================================== profile chart
class ProfileChart(QWidget):
    """Altitude (aircraft) and speed along the route, with radar / jammer / weapons strips underneath."""
    legClicked = pyqtSignal(int)            # index into plan.legs

    STRIP_H = 13

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: Optional[CoursePlan] = None
        self.selected = -1
        self.strips: list[tuple[str, callable]] = []
        self.setMinimumHeight(200)
        self.setMouseTracking(True)

    def set_plan(self, plan: Optional[CoursePlan], selected: int = -1, sonar: bool = False) -> None:
        self.plan = plan
        self.selected = selected
        self.strips = [("Radar", lambda lg: ON_COL if lg.radar else OFF_COL if lg.radar is False else NONE_COL),
                       ("Sonar" if sonar else "Jammers",
                        (lambda lg: ON_COL if lg.sonar else OFF_COL if lg.sonar is False else NONE_COL) if sonar else
                        (lambda lg: ON_COL if lg.ecm else OFF_COL if lg.ecm is False else NONE_COL)),
                       ("Weapons", lambda lg: WCS_COL.get(lg.weapons, NONE_COL))]
        self.update()

    # geometry
    def _plot_rect(self) -> QRectF:
        bottom = 18 + len(self.strips) * (self.STRIP_H + 3) + 6
        return QRectF(70, 18, max(50.0, self.width() - 70 - 62), max(40.0, self.height() - 18 - bottom))

    def _xs(self) -> list[float]:
        xs = [0.0]
        for lg in self.plan.legs:
            xs.append(xs[-1] + lg.nm)
        return xs

    def _x(self, nm: float, r: QRectF, total: float) -> float:
        return r.left() + r.width() * (nm / total if total else 0)

    def leg_at(self, x: float) -> int:
        if not self.plan or not self.plan.legs:
            return -1
        r = self._plot_rect()
        xs = self._xs()
        total = xs[-1] or 1.0
        nm = (x - r.left()) / r.width() * total
        for i in range(len(self.plan.legs)):
            if xs[i] <= nm <= xs[i + 1]:
                return i
        return -1

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1b1d22"))
        f = QFont(p.font())
        f.setPointSize(8)
        p.setFont(f)
        plan = self.plan
        if not plan or not plan.legs:
            p.setPen(QColor("#8a8f99"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Add waypoints to see the profile of the route.")
            p.end()
            return
        r = self._plot_rect()
        xs = self._xs()
        total = xs[-1] or 1.0
        X = lambda nm: self._x(nm, r, total)  # noqa: E731
        # selected leg
        if 0 <= self.selected < len(plan.legs):
            p.fillRect(QRectF(X(xs[self.selected]), r.top(), X(xs[self.selected + 1]) - X(xs[self.selected]),
                              r.height()), QColor(255, 255, 255, 18))
        p.setPen(QPen(QColor("#3a3f48"), 1))
        p.drawRect(r)
        # altitude
        if plan.air:
            alts = [lg.alt for lg in plan.legs if lg.alt is not None] + [plan.start_alt or 0.0]
            top = max(alts + [1000.0]) * 1.15
            Y = lambda m: r.bottom() - r.height() * (m / top)  # noqa: E731
            known = any(lg.alt is not None for lg in plan.legs)
            prev = plan.start_alt if plan.start_alt is not None else next(
                (lg.alt for lg in plan.legs if lg.alt is not None), None)
            pts: list[QPointF] = []
            for i, lg in enumerate(plan.legs):
                a = prev if prev is not None else lg.alt
                b = lg.alt if lg.alt is not None else a
                if lg.n == 0 and (plan.hosted or "Lands" in plan.finish):
                    b = 0.0
                if a is None or b is None:
                    continue
                x0, x1 = X(xs[i]), X(xs[i + 1])
                change = (x1 - x0) * (0.75 if lg.n == 0 else 0.2)
                if lg.n == 0:   # stay up, then come down at the end
                    pts += [QPointF(x0, Y(a)), QPointF(x1 - change, Y(a)), QPointF(x1, Y(b))]
                else:
                    pts += [QPointF(x0, Y(a)), QPointF(x0 + change, Y(b)), QPointF(x1, Y(b))]
                prev = b
            if pts and known:
                fill = QColor(ALT_COL)
                fill.setAlpha(45)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(fill))
                p.drawPolygon(QPolygonF([QPointF(pts[0].x(), r.bottom())] + pts + [QPointF(pts[-1].x(), r.bottom())]))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(ALT_COL, 2))
                p.drawPolyline(QPolygonF(pts))
            else:
                p.setPen(QPen(ALT_COL, 1, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
                p.drawText(QPointF(r.left() + 6, r.center().y() - 4), "Altitude: CMO chooses (none set)")
            p.setPen(ALT_COL)
            for m in (0.0, top / 2, top / 1.15):
                p.drawText(QRectF(0, Y(m) - 8, r.left() - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           f"{m:,.0f} m")
            p.drawText(QRectF(0, r.top() - 17, r.left() + 40, 14), Qt.AlignmentFlag.AlignLeft, "Altitude")
        elif plan.sub:
            self._paint_depth(p, plan, r, xs, X)
        # speed
        spd_top = max(lg.speed for lg in plan.legs) * 1.25
        SY = lambda kn: r.bottom() - r.height() * (kn / spd_top)  # noqa: E731
        p.setPen(QPen(SPEED_COL, 1.6, Qt.PenStyle.SolidLine))
        last = None
        for i, lg in enumerate(plan.legs):
            a, b = QPointF(X(xs[i]), SY(lg.speed)), QPointF(X(xs[i + 1]), SY(lg.speed))
            p.setPen(QPen(SPEED_COL, 1.6, Qt.PenStyle.SolidLine if lg.speed_set else Qt.PenStyle.DotLine))
            if last is not None:
                p.drawLine(last, a)
            p.drawLine(a, b)
            last = b
        p.setPen(SPEED_COL)
        for kn in (0.0, spd_top / 2, spd_top / 1.25):
            p.drawText(QRectF(r.right() + 6, SY(kn) - 8, 60, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{kn:,.0f} kn")
        p.drawText(QRectF(r.right() - 40, r.top() - 17, 100, 14), Qt.AlignmentFlag.AlignRight, "Speed")
        # waypoints, waits and signals
        for i, lg in enumerate(plan.legs):
            x = X(xs[i + 1])
            p.setPen(QPen(QColor("#565c66"), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(QColor("#d0d4da"))
            p.drawText(QRectF(x - 30, r.top() - 17, 60, 14), Qt.AlignmentFlag.AlignCenter,
                       str(lg.n) if lg.n else ("base" if lg.label.startswith(("Back", "To ")) else "end"))
            notes = []
            if lg.wait:
                notes.append(f"wait {lg.wait} min")
            if lg.signal:
                notes.append(f"> {lg.signal}")
            if lg.target_s is not None:
                d = lg.diff_s
                notes.append("on time" if abs(d) <= LATE_S else f"{hms(abs(d))} {'late' if d > 0 else 'early'}")
            if notes:
                p.setPen(QColor("#ffd166"))
                p.drawText(QPointF(x + 3, r.top() + 12), ", ".join(notes))
        # where the fuel should run out (aircraft with a loadout), counting fuel used while waiting
        if plan.range_nm is not None and plan.fuel_nm > plan.range_nm:
            left, at = plan.range_nm, None
            for i, lg in enumerate(plan.legs):
                if left <= lg.nm:
                    at = xs[i] + left
                    break
                left -= lg.nm + lg.wait / 60 * lg.speed
                if left <= 0:
                    at = xs[i + 1]
                    break
            if at is not None:
                x = X(at)
                p.setPen(QPen(QColor("#e5484d"), 2, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
                p.setPen(QColor("#e5484d"))
                p.drawText(QPointF(x + 4, r.bottom() - 6), "fuel runs out (est.)")
        # strips
        y = r.bottom() + 6
        for label, colour in self.strips:
            p.setPen(QColor("#9aa0aa"))
            p.drawText(QRectF(0, y - 1, r.left() - 6, self.STRIP_H + 2),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
            for i, lg in enumerate(plan.legs):
                p.fillRect(QRectF(X(xs[i]) + 0.5, y, X(xs[i + 1]) - X(xs[i]) - 1, self.STRIP_H), colour(lg))
            y += self.STRIP_H + 3
        p.setPen(QColor("#9aa0aa"))
        p.drawText(QRectF(r.left(), y, r.width(), 14), Qt.AlignmentFlag.AlignLeft, "0 nm")
        p.drawText(QRectF(r.left(), y, r.width(), 14), Qt.AlignmentFlag.AlignRight, f"{total:,.0f} nm")
        p.drawText(QRectF(r.left(), y, r.width(), 14), Qt.AlignmentFlag.AlignCenter,
                   "green on / grey off / dark unchanged    weapons: red free, amber tight, green hold")
        p.end()

    def _paint_depth(self, p: QPainter, plan: CoursePlan, r: QRectF, xs: list[float], X) -> None:
        """Submarines: depth below the surface line at the top, deeper further down."""
        known = any(lg.depth is not None for lg in plan.legs)
        if not known:
            p.setPen(QPen(ALT_COL, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
            p.drawText(QPointF(r.left() + 6, r.center().y() - 4), "Depth: as the submarine starts (none set)")
            return
        deepest = max([lg.depth for lg in plan.legs if lg.depth is not None] + [plan.start_depth or 0.0, 50.0]) * 1.15
        Y = lambda m: r.top() + r.height() * (m / deepest)  # noqa: E731
        prev = plan.start_depth if plan.start_depth is not None else next(
            lg.depth for lg in plan.legs if lg.depth is not None)
        pts: list[QPointF] = []
        for i, lg in enumerate(plan.legs):
            b = lg.depth if lg.depth is not None else prev
            x0, x1 = X(xs[i]), X(xs[i + 1])
            pts += [QPointF(x0, Y(prev)), QPointF(x0 + (x1 - x0) * 0.2, Y(b)), QPointF(x1, Y(b))]
            prev = b
        fill = QColor(ALT_COL)
        fill.setAlpha(45)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawPolygon(QPolygonF([QPointF(pts[0].x(), r.top())] + pts + [QPointF(pts[-1].x(), r.top())]))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ALT_COL, 2))
        p.drawPolyline(QPolygonF(pts))
        p.setPen(ALT_COL)
        for m in (0.0, deepest / 2, deepest / 1.15):
            p.drawText(QRectF(0, Y(m) - 8, r.left() - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       "surface" if not m else f"{m:,.0f} m")
        p.drawText(QRectF(0, r.top() - 17, r.left() + 40, 14), Qt.AlignmentFlag.AlignLeft, "Depth")

    def mousePressEvent(self, e) -> None:
        i = self.leg_at(e.position().x())
        if i >= 0:
            self.legClicked.emit(i)

    def mouseMoveEvent(self, e) -> None:
        i = self.leg_at(e.position().x())
        if i < 0:
            QToolTip.hideText()
            return
        lg = self.plan.legs[i]
        alt = "" if lg.alt is None else f"{lg.alt:,.0f} m ({lg.alt * FT:,.0f} ft), "
        if self.plan.sub and lg.depth is not None:
            alt = f"depth {lg.depth:,.0f} m, "
        QToolTip.showText(e.globalPosition().toPoint(),
                          f"{lg.label}: {lg.nm:,.0f} nm, {alt}{lg.speed:,.0f} kn\n"
                          f"Radar {_onoff(lg.radar)}, weapons {WCS_TEXT.get(lg.weapons, lg.weapons)}"
                          + (f"\nWaits {lg.wait} min" if lg.wait else ""), self)


# ====================================================================== the window
class CourseDialog(QDialog):
    COLS = ["#", "Name", "Altitude", "Speed", "Radar", "Weapons", "Wait", "Leg", "Arrives"]

    def __init__(self, window, unit_id: str, parent=None, also: Optional[list] = None):
        super().__init__(parent or window)
        self.win = window
        self.doc = window.doc
        self.uid = unit_id
        self.work = copy.deepcopy(self.doc.project)
        u = self.unit
        if u.course is None:
            u.course = Course()
        self._orig = copy.deepcopy(u.course)
        self.copied_to: set[str] = set()
        self.also = [i for i in (also or []) if i != unit_id and self.work.unit(i) is not None]
        self.sel = 0 if u.course.waypoints else -1
        self.plan: Optional[CoursePlan] = None
        self._loading = False
        self.setWindowTitle(f"Course: {u.display_name()}" + (f" and {len(self.also)} more" if self.also else ""))
        self.resize(1320, 900)
        self._build()
        self._load_course_fields()
        self.refresh()
        QTimer.singleShot(0, self._initial_view)

    # ------------------------------------------------------------------ data
    @property
    def unit(self):
        return self.work.unit(self.uid)

    @property
    def course(self) -> Course:
        return self.unit.course

    def waypoint(self) -> Optional[Waypoint]:
        wps = self.course.waypoints
        return wps[self.sel] if 0 <= self.sel < len(wps) else None

    def dirty(self) -> bool:
        return self.course != self._orig or bool(self.copied_to)

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        u = self.unit
        air = u.type == "Aircraft"
        root = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-weight: bold")
        root.addWidget(self.summary)
        self.range_label = QLabel()
        self.range_label.setWordWrap(True)
        root.addWidget(self.range_label)
        vsplit = QSplitter(Qt.Orientation.Vertical)
        top = QSplitter(Qt.Orientation.Horizontal)

        # map and route tools
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for key, text, fn, tip in (
                ("add", "Add waypoints", self.add_mode, "Click the map for each new waypoint (added at the end); "
                                                        "double-click or Enter to finish"),
                ("insert", "Insert", self.insert, "Add a waypoint half-way along the leg to the selected one"),
                ("remove", "Remove", self.remove, "Remove the selected waypoint (Delete)"),
                ("up", "Up", lambda: self.move(-1), "Fly the selected waypoint earlier"),
                ("down", "Down", lambda: self.move(1), "Fly the selected waypoint later"),
                ("reverse", "Reverse", self.reverse, "Fly the course the other way round"),
                ("clear", "Clear", self.clear, "Remove every waypoint"),
                ("fit", "Fit", self.fit, "Zoom the map to the route")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setAutoDefault(False)
            b.clicked.connect(fn)
            bar.addWidget(b)
            self.buttons[key] = b
        bar.addStretch(1)
        lib = QPushButton("Library ▾")
        lib.setAutoDefault(False)
        lib.setToolTip("Save this course for other units or projects, use a saved one, or copy it to other units")
        menu = QMenu(lib)
        menu.addAction("Save this course to the library...", self.save_to_library)
        menu.addAction("Use a saved course...", self.load_from_library)
        menu.addSeparator()
        menu.addAction("Copy this course to other units...", self.copy_to_units)
        lib.setMenu(menu)
        bar.addWidget(lib)
        lv.addLayout(bar)
        main_map = self.win.map_page.map
        self.map = MapWidget(main_map.tiles)
        self.map.attribution = main_map.attribution
        for attr in ("show_labels", "show_zones", "show_rps", "show_grid", "hidden_sides"):
            setattr(self.map, attr, copy.copy(getattr(main_map, attr)))
        self.map.show_courses = True
        self.map.set_project(self.work)
        self.map.select(self.uid)
        self.map.setMinimumSize(480, 340)
        self.map.courseFinished.connect(self._plotted)
        self.map.waypointMoved.connect(self._dragged)
        self.map.waypointClicked.connect(lambda _uid, i: self.select(i))
        self.map.objectClicked.connect(lambda oid: oid != self.uid and self.map.select(self.uid))
        self.map.deleteRequested.connect(lambda _oid: self.remove())
        lv.addWidget(self.map, 1)
        self.status = hint_label("Drag a waypoint's white square to move it. Click one to select its leg.")
        self.map.message.connect(self.status.setText)
        lv.addWidget(self.status)
        top.addWidget(left)

        # legs and the selected leg's settings
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        sub = u.type == "Submarine"
        if sub:
            self.table.setHorizontalHeaderItem(2, QTableWidgetItem("Depth"))
        self.table.setColumnHidden(2, not (air or sub))
        self.table.currentCellChanged.connect(lambda row, *_: self._row_selected(row))
        rv.addWidget(self.table, 1)

        self.leg_box = QGroupBox("Leg")
        cols = QHBoxLayout(self.leg_box)
        form, tac = QFormLayout(), QFormLayout()      # route on the left, sensors and weapons on the right
        cols.addLayout(form, 1)
        cols.addSpacing(12)
        cols.addLayout(tac, 1)
        self.name = QLineEdit()
        self.name.setPlaceholderText("optional, e.g. IP, Tanker, Target")
        self.name.textEdited.connect(self._leg_changed)
        form.addRow("Name:", self.name)
        pos = QHBoxLayout()
        self.lat, self.lon = QDoubleSpinBox(), QDoubleSpinBox()
        for sb, lim in ((self.lat, 90), (self.lon, 180)):
            sb.setRange(-lim, lim)
            sb.setDecimals(5)
            sb.setSingleStep(0.01)
            sb.valueChanged.connect(self._leg_changed)
            pos.addWidget(sb)
        form.addRow("Lat, lon:", pos)
        altrow = QHBoxLayout()
        self.alt = QDoubleSpinBox()
        self.alt.setRange(0, 30000)
        self.alt.setDecimals(0)
        self.alt.setSingleStep(100)
        self.alt.setSuffix(" m")
        self.alt.setSpecialValueText("no change")
        self.alt.setToolTip("Altitude on the leg to this waypoint. 'no change' keeps the previous leg's (or lets CMO "
                            "choose).")
        self.alt.valueChanged.connect(self._leg_changed)
        self.alt_ft = QLabel()
        altrow.addWidget(self.alt, 1)
        altrow.addWidget(self.alt_ft)
        self.alt_row = QWidget()
        self.alt_row.setLayout(altrow)
        altrow.setContentsMargins(0, 0, 0, 0)
        form.addRow("Altitude:", self.alt_row)
        self.depth = QDoubleSpinBox()
        self.depth.setRange(-1, 3000)
        self.depth.setDecimals(0)
        self.depth.setSingleStep(10)
        self.depth.setSuffix(" m")
        self.depth.setSpecialValueText("no change")
        self.depth.setToolTip("Depth below the surface on the leg to this waypoint (0 = surfaced). 'no change' keeps "
                              "the previous leg's.")
        self.depth.valueChanged.connect(self._leg_changed)
        form.addRow("Depth:", self.depth)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0, 3000)
        self.speed.setDecimals(0)
        self.speed.setSingleStep(10)
        self.speed.setSuffix(" kn")
        self.speed.setSpecialValueText("no change")
        self.speed.valueChanged.connect(self._leg_changed)
        form.addRow("Speed:", self.speed)
        self.radar, self.sonar, self.ecm = self._combo(SENSOR_SETTING), self._combo(SENSOR_SETTING), \
            self._combo(SENSOR_SETTING)
        self.weapons, self.engage = self._combo(WEAPONS_SETTING), self._combo(ENGAGE_SETTING)
        tac.addRow("Radar:", self.radar)
        tac.addRow("Sonar:", self.sonar)
        tac.addRow("Jammers:", self.ecm)
        tac.addRow("Weapons:", self.weapons)
        tac.addRow("Targets:", self.engage)
        self.engage.setToolTip("Whether the unit may leave its course to attack a target it finds on this leg")
        self.wait = QSpinBox()
        self.wait.setRange(0, 24 * 60)
        self.wait.setSuffix(" min")
        self.wait.setSpecialValueText("no wait")
        self.wait.setToolTip("On arrival, circle here this long before flying on (a holding point, a tanker, a "
                             "time on target)")
        self.wait.valueChanged.connect(self._leg_changed)
        arow = QHBoxLayout()
        arow.setContentsMargins(0, 0, 0, 0)
        self.arrive = QSpinBox()
        self.arrive.setRange(-1, 60 * 24 * 60)
        self.arrive.setSuffix(" min after the start")
        self.arrive.setSpecialValueText("any time")
        self.arrive.setToolTip("Time on target: when the unit should reach this waypoint. 'Time it' sets the "
                               "departure and waits to meet it.")
        self.arrive.valueChanged.connect(self._leg_changed)
        self.arrive_info = QLabel()
        arow.addWidget(self.arrive, 1)
        arow.addWidget(self.arrive_info)
        self.arrive_row = QWidget()
        self.arrive_row.setLayout(arow)
        form.addRow("Arrive at:", self.arrive_row)
        form.addRow("Wait there:", self.wait)
        self.signal = QLineEdit()
        self.signal.setPlaceholderText("optional flag, e.g. STRIKE_AT_IP")
        self.signal.setToolTip("On arrival, set this flag (key value) to true. An event with the condition 'Flag "
                               "is set' can react: a message, a score, a mission switched on...")
        self.signal.textEdited.connect(self._leg_changed)
        form.addRow("Signal there:", self.signal)
        same = QPushButton("Same for every leg")
        same.setAutoDefault(False)
        same.setToolTip("Copy this leg's altitude (or depth), speed, sensors, weapons and targets setting to every "
                        "leg")
        same.clicked.connect(self.same_for_all)
        tac.addRow("", same)
        form.setRowVisible(self.alt_row, air)
        form.setRowVisible(self.depth, u.type == "Submarine")
        tac.setRowVisible(self.sonar, u.type != "GroundUnit")
        rv.addWidget(self.leg_box)
        rv.addWidget(hint_label("Settings apply on the leg flown <i>to</i> the waypoint and stay in force until a "
                                "later leg changes them. <i>No change</i> keeps what the unit already has."))
        top.addWidget(right)
        top.setSizes([780, 540])
        vsplit.addWidget(top)

        prof = QGroupBox("Profile" if air else "Depth profile" if u.type == "Submarine" else
                         "Speed and settings along the route")
        pv = QVBoxLayout(prof)
        self.chart = ProfileChart()
        self.chart.legClicked.connect(self._chart_clicked)
        pv.addWidget(self.chart)
        vsplit.addWidget(prof)
        vsplit.setSizes([600, 240])
        root.addWidget(vsplit, 1)

        # the course as a whole
        row = QHBoxLayout()
        row.addWidget(QLabel("Depart:"))
        self.depart = QSpinBox()
        self.depart.setRange(0, 60 * 24 * 60)
        self.depart.setSuffix(" min after the start")
        self.depart.setSpecialValueText("at the start")
        self.depart.setToolTip("When the unit sets off. Aircraft at a base take off at this time.")
        self.depart.valueChanged.connect(self._course_changed)
        row.addWidget(self.depart)
        row.addSpacing(12)
        row.addWidget(QLabel("At the end:"))
        self.finish = QComboBox()
        for k, label in COURSE_FINISH.items():
            self.finish.addItem(label, k)
        self.finish.currentIndexChanged.connect(self._course_changed)
        row.addWidget(self.finish)
        row.addSpacing(12)
        row.addWidget(QLabel("Land at:"))
        self.land_at = IdCombo()
        self.land_at.setMinimumWidth(220)
        self.land_at.currentIndexChanged.connect(self._course_changed)
        row.addWidget(self.land_at)
        self.time_btn = QPushButton("Time it")
        self.time_btn.setAutoDefault(False)
        self.time_btn.setToolTip("Set the departure (and waits) so the unit reaches its waypoints at their 'Arrive at' "
                                 "times")
        self.time_btn.clicked.connect(self.time_it)
        row.addWidget(self.time_btn)
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        for b in bb.buttons():
            b.setAutoDefault(False)
            b.setDefault(False)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        root.addLayout(row)

    @staticmethod
    def _combo(choices: dict[str, str]) -> QComboBox:
        cb = QComboBox()
        for k, label in choices.items():
            cb.addItem(label, k)
        return cb

    def _initial_view(self) -> None:
        self.fit()
        if not self.course.waypoints:
            self.add_mode()

    def _load_course_fields(self) -> None:
        c = self.course
        u = self.unit
        self._loading = True
        self.depart.setValue(int(c.depart_minutes or 0))
        self.finish.setCurrentIndex(max(0, self.finish.findData(c.finish)))
        bases = [(f"{h.name}  [{h.type}]", h.id) for h in self.work.units
                 if h.id != u.id and h.type in HOST_TYPES and h.side == u.side and not h.host]
        self.land_at.set_items(bases, blank="(choose a base)", keep=False)
        self.land_at.set_current_id(c.land_at)
        self._loading = False
        for cb in (self.radar, self.sonar, self.ecm, self.weapons, self.engage):
            cb.currentIndexChanged.connect(self._leg_changed)

    # ------------------------------------------------------------------ showing
    def refresh(self) -> None:
        """Recompute the plan and redraw the table, chart, map and summary (not the leg fields)."""
        u = self.unit
        c = self.course
        ctx = getattr(self.win, "ctx", None)
        self.plan = plan_course(self.work, u, getattr(ctx, "db", None))
        legs: list[Leg] = self.plan.legs if self.plan else []
        self._loading = True
        self.table.setRowCount(len(legs))
        grey = QColor("#8a8f99")
        for r, lg in enumerate(legs):
            level = lg.depth if self.plan.sub else lg.alt
            cells = [str(lg.n) if lg.n else "→", lg.label,
                     "" if level is None else f"{level:,.0f} m",
                     f"{lg.speed:,.0f} kn", _onoff(lg.radar), WCS_TEXT.get(lg.weapons, lg.weapons),
                     f"{lg.wait} min" if lg.wait else "", f"{lg.nm:,.0f} nm", f"H+{hms(lg.t1)}"]
            if lg.target_s is not None:
                d = lg.diff_s
                cells[8] += "  on time" if abs(d) <= LATE_S else f"  {hms(abs(d))} {'late' if d > 0 else 'early'}"
            inherited = {2: not (lg.depth_set if self.plan.sub else lg.alt_set), 3: not lg.speed_set}
            for col, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if inherited.get(col) or lg.n == 0:
                    it.setForeground(grey)
                if col == 8 and lg.target_s is not None:
                    d = lg.diff_s
                    it.setForeground(QColor("#30a46c") if abs(d) <= LATE_S else
                                     QColor("#e5484d") if d > 0 else QColor("#f5a524"))
                    it.setToolTip(f"Time on target H+{hms(lg.target_s)}" +
                                  (f"; needs about {lg.need_kn:,.0f} kn on this leg" if lg.need_kn not in
                                   (None, float('inf')) else "; cannot get there in time" if lg.need_kn else ""))
                self.table.setItem(r, col, it)
        if 0 <= self.sel < len(legs):
            self.table.selectRow(self.sel)
        else:
            self.table.clearSelection()
        self._loading = False
        self.chart.set_plan(self.plan, self.sel, sonar=u.type in ("Ship", "Submarine"))
        self.map.highlight_wp = self.sel
        self.map.update()
        has = bool(c.waypoints)
        for k in ("insert", "remove", "up", "down"):
            self.buttons[k].setEnabled(self.waypoint() is not None)
        for k in ("reverse", "clear"):
            self.buttons[k].setEnabled(has)
        self.land_at.setEnabled(self.finish.currentData() == "land")
        self.time_btn.setEnabled(bool(self.plan and self.plan.tot_depart_s is not None))
        self._range_text()
        self._arrive_hint()
        if not self.plan:
            self.summary.setText(f"{u.display_name()}: no course yet. Click the map to add waypoints; double-click "
                                 "or press Enter to finish.")
        else:
            pl = self.plan
            start = "takes off from " + pl.origin if pl.hosted else "sets off"
            when = "at the start" if not pl.depart_s else f"at H+{hms(pl.depart_s)}"
            loop = " and repeats" if pl.repeat else ""
            self.summary.setText(
                f"{u.display_name()} {start} {when}: {len(c.waypoints)} waypoint(s), {pl.total_nm:,.0f} nm, about "
                f"{hms(pl.end_s - pl.depart_s)} (h:mm){loop}. At the end: {pl.finish}, about H+{hms(pl.end_s)}.")

    def _range_text(self) -> None:
        pl = self.plan
        if pl is None or not pl.air:
            self.range_label.setText("")
            return
        if pl.range_nm is None:
            self.range_label.setText("<span style='color:#8a8f99'>Range: no estimate (choose a loadout to check the "
                                     "route against it).</span>")
            return
        waits = " including waits" if pl.fuel_nm > pl.total_nm + 0.5 else ""
        if pl.fuel_nm > pl.range_nm:
            self.range_label.setText(
                f"<span style='color:#e5484d'><b>Too far:</b> about {pl.fuel_nm:,.0f} nm{waits}, but the range is "
                f"about {pl.range_nm:,.0f} nm ({pl.range_note}); {pl.fuel_nm - pl.range_nm:,.0f} nm short. Shorten "
                "the route, choose another loadout, or plan a tanker.</span>")
        else:
            self.range_label.setText(
                f"<span style='color:#30a46c'>Within range:</span> about {pl.fuel_nm:,.0f} nm{waits} of about "
                f"{pl.range_nm:,.0f} nm ({pl.range_note}).")

    def _arrive_hint(self) -> None:
        lg = next((x for x in (self.plan.legs if self.plan else []) if x.n == self.sel + 1), None)
        if lg is None or lg.target_s is None:
            self.arrive_info.setText(f"H+{hms(lg.t1)} expected" if lg else "")
            self.arrive_info.setStyleSheet("")
            return
        d = lg.diff_s
        if abs(d) <= LATE_S:
            text, col = "on time", "#30a46c"
        elif d < 0:
            text, col = f"{hms(-d)} early", "#f5a524"
        else:
            text = f"{hms(d)} late" + (": cannot make it" if lg.need_kn == float("inf") else
                                       f": needs {lg.need_kn:,.0f} kn" if lg.need_kn else "")
            col = "#e5484d"
        self.arrive_info.setText(f"H+{hms(lg.target_s)}: {text}")
        self.arrive_info.setStyleSheet(f"color: {col}")

    def _load_leg_fields(self) -> None:
        w = self.waypoint()
        self._loading = True
        self.leg_box.setEnabled(w is not None)
        self.leg_box.setTitle(f"Leg to waypoint {self.sel + 1}" if w else "Leg (select a waypoint)")
        w = w or Waypoint()
        self.name.setText(w.name)
        self.lat.setValue(w.lat)
        self.lon.setValue(w.lon)
        self.alt.setValue(w.altitude or 0)
        self.depth.setValue(-1 if w.depth is None else w.depth)
        self.speed.setValue(w.speed or 0)
        for cb, val in ((self.radar, w.radar), (self.sonar, w.sonar), (self.ecm, w.ecm), (self.weapons, w.weapons),
                        (self.engage, w.engage)):
            cb.setCurrentIndex(max(0, cb.findData(val)))
        self.wait.setValue(int(w.wait_minutes or 0))
        self.arrive.setValue(-1 if w.arrive_minutes is None else int(w.arrive_minutes))
        self.signal.setText(w.signal)
        self._loading = False
        self._alt_hint()

    def _alt_hint(self) -> None:
        v = self.alt.value()
        self.alt_ft.setText(f"{v * FT:,.0f} ft" if v else "")

    def select(self, i: int) -> None:
        if not 0 <= i < len(self.course.waypoints):
            i = -1
        self.sel = i
        self._load_leg_fields()
        self.refresh()

    def _row_selected(self, row: int) -> None:
        if not self._loading and row != self.sel:
            self.select(row)

    def _chart_clicked(self, i: int) -> None:
        if self.plan and 0 <= i < len(self.plan.legs) and self.plan.legs[i].n:
            self.select(self.plan.legs[i].n - 1)

    # ------------------------------------------------------------------ editing
    def _leg_changed(self, *_):
        if self._loading:
            return
        w = self.waypoint()
        if w is None:
            return
        w.name = self.name.text().strip()
        w.lat, w.lon = round(self.lat.value(), 6), round(self.lon.value(), 6)
        if self.unit.type == "Aircraft":
            w.altitude = self.alt.value() or None
        if self.unit.type == "Submarine":
            w.depth = None if self.depth.value() < 0 else self.depth.value()
        w.speed = self.speed.value() or None
        w.radar, w.sonar, w.ecm = self.radar.currentData(), self.sonar.currentData(), self.ecm.currentData()
        w.weapons, w.engage = self.weapons.currentData(), self.engage.currentData()
        w.wait_minutes = int(self.wait.value())
        w.arrive_minutes = None if self.arrive.value() < 0 else int(self.arrive.value())
        w.signal = self.signal.text().strip()
        self._alt_hint()
        self.refresh()

    def _course_changed(self, *_):
        if self._loading:
            return
        c = self.course
        c.depart_minutes = int(self.depart.value())
        c.finish = self.finish.currentData() or "stop"
        c.land_at = self.land_at.current_id()
        self.refresh()

    def add_mode(self) -> None:
        self.map.start_course(self.uid, self.unit.display_name())
        self.map.setFocus()

    def _plotted(self, _uid: str, pts: list) -> None:
        first = len(self.course.waypoints)
        self.course.waypoints.extend(Waypoint(round(a, 6), round(b, 6)) for a, b in pts)
        self.select(first)

    def _dragged(self, _uid: str, i: int, lat: float, lon: float) -> None:
        if 0 <= i < len(self.course.waypoints):
            w = self.course.waypoints[i]
            w.lat, w.lon = round(lat, 6), round(lon, 6)
            self.select(i)

    def insert(self) -> None:
        w = self.waypoint()
        if w is None:
            return
        prev = self.course.waypoints[self.sel - 1] if self.sel > 0 else None
        a = (prev.lat, prev.lon) if prev else self.map.course_start(self.unit)
        self.course.waypoints.insert(self.sel, Waypoint(round((a[0] + w.lat) / 2, 6), round((a[1] + w.lon) / 2, 6)))
        self.select(self.sel)

    def remove(self) -> None:
        if self.waypoint() is None:
            return
        self.course.waypoints.pop(self.sel)
        self.select(min(self.sel, len(self.course.waypoints) - 1))

    def move(self, d: int) -> None:
        wps = self.course.waypoints
        i = self.sel
        if 0 <= i < len(wps) and 0 <= i + d < len(wps):
            wps[i], wps[i + d] = wps[i + d], wps[i]
            self.select(i + d)

    def reverse(self) -> None:
        self.course.waypoints.reverse()
        if self.sel >= 0:
            self.sel = len(self.course.waypoints) - 1 - self.sel
        self.select(self.sel)

    def clear(self) -> None:
        if self.course.waypoints and QMessageBox.question(
                self, "Clear course", "Remove every waypoint of this course?") != QMessageBox.StandardButton.Yes:
            return
        self.course.waypoints.clear()
        self.select(-1)

    def same_for_all(self) -> None:
        w = self.waypoint()
        if w is None:
            return
        for o in self.course.waypoints:
            o.altitude, o.speed, o.depth = w.altitude, w.speed, w.depth
            o.radar, o.sonar, o.ecm, o.weapons, o.engage = w.radar, w.sonar, w.ecm, w.weapons, w.engage
        self.refresh()

    def fit(self) -> None:
        u = self.unit
        pts = [self.map.course_start(u)] + [(w.lat, w.lon) for w in self.course.waypoints]
        base = self.work.unit(self.course.land_at) if self.course.finish == "land" else None
        if base is not None:
            pts.append((base.lat, base.lon))
        if len(pts) == 1:
            self.map.center_on(pts[0][0], pts[0][1], 7)
        else:
            self.map.fit(pts)

    def time_it(self) -> None:
        done = plan_times(self.work, self.unit)
        if not done:
            return
        self._load_course_fields()
        self._load_leg_fields()
        self.refresh()
        self.status.setText(" ".join(done))

    # ------------------------------------------------------------------ library and copying
    def _library_path(self):
        return self.win.ctx.settings.data_dir() / "routes.json"

    def save_to_library(self) -> None:
        from ..model.route_library import RouteLibrary
        if not self.course.waypoints:
            QMessageBox.information(self, "Save course", "Add waypoints first.")
            return
        name, ok = QInputDialog.getText(self, "Save course to the library", "Name (a saved course with the same name "
                                        "is replaced):", text=self.course.waypoints[0].name or
                                        f"{self.unit.display_name()} route")
        if not ok or not name.strip():
            return
        lib = RouteLibrary.load(self._library_path())
        lib.add(name, self.course, description=f"{len(self.course.waypoints)} waypoint(s), "
                                               f"{self.plan.total_nm:,.0f} nm" if self.plan else "")
        lib.save(self._library_path())
        self.status.setText(f"Saved '{name.strip()}' to the course library ({self._library_path()}).")

    def load_from_library(self) -> None:
        from ..model.route_library import RouteLibrary
        lib = RouteLibrary.load(self._library_path())
        if not lib.routes:
            QMessageBox.information(self, "Course library", "The library is empty. Use 'Save this course to the "
                                    "library...' to add one.")
            return
        dlg = RoutePickDialog(lib, self)
        if not dlg.exec() or dlg.chosen is None:
            if dlg.changed:
                lib.save(self._library_path())
            return
        if dlg.changed:
            lib.save(self._library_path())
        r = dlg.chosen
        c = copy.deepcopy(r.course)
        if dlg.append and self.course.waypoints:
            self.course.waypoints.extend(c.waypoints)
        else:
            self.course.waypoints = c.waypoints
            self.course.depart_minutes, self.course.finish, self.course.land_at = c.depart_minutes, c.finish, ""
            self._load_course_fields()
        self.select(0 if self.sel < 0 else self.sel)
        self.fit()
        self.status.setText(f"Used '{r.name}'.")

    def copy_to_units(self) -> None:
        u = self.unit
        if not self.course.waypoints:
            QMessageBox.information(self, "Copy course", "Add waypoints first.")
            return
        items = [(f"{x.display_name()}  [{x.type}]" + ("  (has a course)" if x.course and x.course.waypoints
                                                      else ""), x.id)
                 for x in self.work.units if x.id != u.id and x.side == u.side and x.type != "Facility"]
        dlg = PickerDialog("Copy this course to...", items, parent=self)
        if not dlg.exec():
            return
        ids = [i for i in dlg.selected_ids() if self.work.unit(i) is not None]
        for i in ids:
            other = self.work.unit(i)
            c = copy.deepcopy(self.course)
            if c.finish == "land" and other.type != "Aircraft":
                c.finish, c.land_at = "stop", ""
            other.course = c
        self.copied_to.update(ids)
        self.map.update()
        self.status.setText(f"Copied to {len(ids)} unit(s); saved with OK." if ids else "Nothing copied.")

    # ------------------------------------------------------------------ closing
    def save(self) -> None:
        real = self.doc.project.unit(self.uid)
        if real is None:
            self.reject()
            return
        new = copy.deepcopy(self.course) if self.course.waypoints else None
        for i in self.also:                   # 'Same course for all': the others get this course as saved
            other = self.work.unit(i)
            c = copy.deepcopy(self.course) if self.course.waypoints else None
            if c is not None and c.finish == "land" and other.type != "Aircraft":
                c.finish, c.land_at = "stop", ""
            other.course = c
            self.copied_to.add(i)
        copies = {i: copy.deepcopy(self.work.unit(i).course) for i in self.copied_to
                  if self.work.unit(i) is not None and self.doc.project.unit(i) is not None}
        if new != real.course or copies:
            label = f"Edit course for {real.name}" + (f" (and copy it to {len(copies)})" if copies else "")
            with self.doc.modify(label, "units"):
                real.course = new
                for i, c in copies.items():
                    self.doc.project.unit(i).course = c
        self.accept()

    def reject(self) -> None:
        if self.dirty() and QMessageBox.question(
                self, "Discard changes", "Close without saving the changes to this course?") \
                != QMessageBox.StandardButton.Yes:
            return
        super().reject()


class RoutePickDialog(QDialog):
    """Choose a saved course: use it instead of this one, add it to the end, or delete saved ones."""

    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.chosen = None
        self.append = False
        self.changed = False
        self.setWindowTitle("Course library")
        self.resize(520, 420)
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        self._fill()
        self.list.itemDoubleClicked.connect(lambda *_: self._use(False))
        row = QHBoxLayout()
        for text, fn in (("Use instead", lambda: self._use(False)), ("Add to the end", lambda: self._use(True)),
                         ("Delete", self._delete)):
            b = QPushButton(text)
            b.setAutoDefault(False)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        lay.addLayout(row)
        lay.addWidget(hint_label("Saved courses keep their waypoints and every leg setting. A landing base is not "
                                 "kept: 'Land at another base' comes back as 'Return to its base'."))

    def _fill(self):
        self.list.clear()
        for r in self.lib.routes:
            it = QListWidgetItem(f"{r.name}  ({r.waypoint_count} waypoint(s))" +
                                 (f"  {r.description}" if r.description else ""))
            it.setData(Qt.ItemDataRole.UserRole, r.id)
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _current(self):
        it = self.list.currentItem()
        return self.lib.route(it.data(Qt.ItemDataRole.UserRole)) if it else None

    def _use(self, append: bool):
        self.chosen, self.append = self._current(), append
        if self.chosen is not None:
            self.accept()

    def _delete(self):
        r = self._current()
        if r is not None:
            self.lib.remove(r.id)
            self.changed = True
            self._fill()


def edit_course(window, unit_id: str, also: Optional[list] = None) -> bool:
    """Open the course window for a unit; True if the course was saved."""
    u = window.doc.project.unit(unit_id)
    if u is None:
        return False
    if u.type == "Facility":
        QMessageBox.information(window, "Course", f"{u.name} is a facility; facilities cannot move.")
        return False
    window.map_page.map.set_tool(Tool.SELECT)
    return CourseDialog(window, unit_id, also=also).exec() == QDialog.DialogCode.Accepted
