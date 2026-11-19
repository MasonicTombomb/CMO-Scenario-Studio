"""The course window: plot a unit's route on a map, set what it does on each leg, and see the flight profile.

It edits a copy of the project; **OK** writes the course back as one undoable change and **Cancel** drops it.
"""

from __future__ import annotations

import copy
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
                             QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolTip, QVBoxLayout, QWidget)

from ..model.course_plan import CoursePlan, Leg, hms, plan_course
from ..model.enums import HOST_TYPES
from ..model.project import COURSE_FINISH, ENGAGE_SETTING, SENSOR_SETTING, WEAPONS_SETTING, Course, Waypoint
from .map.map_widget import MapWidget, Tool
from .widgets import IdCombo, hint_label

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
            if notes:
                p.setPen(QColor("#ffd166"))
                p.drawText(QPointF(x + 3, r.top() + 12), ", ".join(notes))
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
        QToolTip.showText(e.globalPosition().toPoint(),
                          f"{lg.label}: {lg.nm:,.0f} nm, {alt}{lg.speed:,.0f} kn\n"
                          f"Radar {_onoff(lg.radar)}, weapons {WCS_TEXT.get(lg.weapons, lg.weapons)}"
                          + (f"\nWaits {lg.wait} min" if lg.wait else ""), self)


# ====================================================================== the window
class CourseDialog(QDialog):
    COLS = ["#", "Name", "Altitude", "Speed", "Radar", "Weapons", "Wait", "Leg", "Arrives"]

    def __init__(self, window, unit_id: str, parent=None):
        super().__init__(parent or window)
        self.win = window
        self.doc = window.doc
        self.uid = unit_id
        self.work = copy.deepcopy(self.doc.project)
        u = self.unit
        if u.course is None:
            u.course = Course()
        self._orig = copy.deepcopy(u.course)
        self.sel = 0 if u.course.waypoints else -1
        self.plan: Optional[CoursePlan] = None
        self._loading = False
        self.setWindowTitle(f"Course: {u.display_name()}")
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
        return self.course != self._orig

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        u = self.unit
        air = u.type == "Aircraft"
        root = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-weight: bold")
        root.addWidget(self.summary)
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
        self.table.setColumnHidden(2, not air)
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
        form.addRow("Wait there:", self.wait)
        self.signal = QLineEdit()
        self.signal.setPlaceholderText("optional flag, e.g. STRIKE_AT_IP")
        self.signal.setToolTip("On arrival, set this flag (key value) to true. An event with the condition 'Flag "
                               "is set' can react: a message, a score, a mission switched on...")
        self.signal.textEdited.connect(self._leg_changed)
        form.addRow("Signal there:", self.signal)
        same = QPushButton("Same for every leg")
        same.setAutoDefault(False)
        same.setToolTip("Copy this leg's altitude, speed, sensors, weapons and targets setting to every leg")
        same.clicked.connect(self.same_for_all)
        tac.addRow("", same)
        form.setRowVisible(self.alt_row, air)
        tac.setRowVisible(self.sonar, u.type != "GroundUnit")
        rv.addWidget(self.leg_box)
        rv.addWidget(hint_label("Settings apply on the leg flown <i>to</i> the waypoint and stay in force until a "
                                "later leg changes them. <i>No change</i> keeps what the unit already has."))
        top.addWidget(right)
        top.setSizes([780, 540])
        vsplit.addWidget(top)

        prof = QGroupBox("Profile" if air else "Speed and settings along the route")
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
        self.plan = plan_course(self.work, u)
        legs: list[Leg] = self.plan.legs if self.plan else []
        self._loading = True
        self.table.setRowCount(len(legs))
        grey = QColor("#8a8f99")
        for r, lg in enumerate(legs):
            cells = [str(lg.n) if lg.n else "→", lg.label,
                     "" if lg.alt is None else f"{lg.alt:,.0f} m",
                     f"{lg.speed:,.0f} kn", _onoff(lg.radar), WCS_TEXT.get(lg.weapons, lg.weapons),
                     f"{lg.wait} min" if lg.wait else "", f"{lg.nm:,.0f} nm", f"H+{hms(lg.t1)}"]
            inherited = {2: not lg.alt_set, 3: not lg.speed_set}
            for col, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if inherited.get(col) or lg.n == 0:
                    it.setForeground(grey)
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
        self.speed.setValue(w.speed or 0)
        for cb, val in ((self.radar, w.radar), (self.sonar, w.sonar), (self.ecm, w.ecm), (self.weapons, w.weapons),
                        (self.engage, w.engage)):
            cb.setCurrentIndex(max(0, cb.findData(val)))
        self.wait.setValue(int(w.wait_minutes or 0))
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
        w.speed = self.speed.value() or None
        w.radar, w.sonar, w.ecm = self.radar.currentData(), self.sonar.currentData(), self.ecm.currentData()
        w.weapons, w.engage = self.weapons.currentData(), self.engage.currentData()
        w.wait_minutes = int(self.wait.value())
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
            o.altitude, o.speed = w.altitude, w.speed
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

    # ------------------------------------------------------------------ closing
    def save(self) -> None:
        real = self.doc.project.unit(self.uid)
        if real is None:
            self.reject()
            return
        new = copy.deepcopy(self.course) if self.course.waypoints else None
        if new != real.course:
            with self.doc.modify(f"Edit course for {real.name}", "units"):
                real.course = new
        self.accept()

    def reject(self) -> None:
        if self.dirty() and QMessageBox.question(
                self, "Discard changes", "Close without saving the changes to this course?") \
                != QMessageBox.StandardButton.Yes:
            return
        super().reject()


def edit_course(window, unit_id: str) -> bool:
    """Open the course window for a unit; True if the course was saved."""
    u = window.doc.project.unit(unit_id)
    if u is None:
        return False
    if u.type == "Facility":
        QMessageBox.information(window, "Course", f"{u.name} is a facility; facilities cannot move.")
        return False
    window.map_page.map.set_tool(Tool.SELECT)
    return CourseDialog(window, unit_id).exec() == QDialog.DialogCode.Accepted
