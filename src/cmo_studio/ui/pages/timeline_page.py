"""Timeline: every event (by trigger) and mission (by active period) on the scenario clock."""

from __future__ import annotations

import html
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSplitter,
                             QTextBrowser, QToolTip, QVBoxLayout, QWidget)

from ...model.timeline import BAND, CONDITION, POINT, REPEAT, Row, Timeline, build_timeline, fmt_time, rel
from ..widgets import hint_label
from .base import AppContext, Page

LABEL_W = 250
AXIS_H = 40
ROW_H = 28
EVENT_COL = QColor("#3d8bfd")
MISSION_COL = QColor("#30a46c")
COURSE_COL = QColor("#f5a524")
KIND_COL = {"event": EVENT_COL, "mission": MISSION_COL, "course": COURSE_COL}
CLASH_COL = QColor("#e5484d")


class TimelineCanvas(QWidget):
    rowSelected = pyqtSignal(object)        # Row or None
    rowActivated = pyqtSignal(object)       # Row (double-click)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.tl: Optional[Timeline] = None
        self.rows: list[Row] = []
        self.px_per_hour = 30.0
        self.selected_id = ""
        self.clash_ids: set[str] = set()

    # ------------------------------------------------------------------ data
    def set_rows(self, tl: Timeline, rows: list[Row]) -> None:
        self.tl, self.rows = tl, rows
        self.clash_ids = {a for a, _, _ in tl.clashes} | {b for _, b, _ in tl.clashes}
        self._resize()
        self.update()

    def _resize(self) -> None:
        if not self.tl:
            return
        hours = (self.tl.end - self.tl.start) / 3600
        w = int(LABEL_W + hours * self.px_per_hour + 60)
        h = int(AXIS_H + max(1, len(self.rows)) * ROW_H + 20)
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def x_of(self, epoch: int) -> float:
        return LABEL_W + (epoch - self.tl.start) / 3600 * self.px_per_hour

    def epoch_at(self, x: float) -> int:
        return int(self.tl.start + (x - LABEL_W) / self.px_per_hour * 3600)

    def set_zoom(self, pph: float, anchor_x: Optional[float] = None) -> None:
        pph = max(0.5, min(2400.0, pph))
        self.px_per_hour = pph
        self._resize()
        self.update()

    def fit(self, width: int) -> None:
        if self.tl:
            hours = max(0.25, (self.tl.end - self.tl.start) / 3600)
            self.set_zoom((width - LABEL_W - 80) / hours)

    # ------------------------------------------------------------------ painting
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        vis = self.visibleRegion().boundingRect()
        p.fillRect(vis, QColor("#1b1d21"))
        if not self.tl:
            return
        tl = self.tl
        small = QFont(p.font())
        small.setPointSize(8)
        p.setFont(small)
        # rows background
        for i, r in enumerate(self.rows):
            y = AXIS_H + i * ROW_H
            if i % 2:
                p.fillRect(QRectF(vis.left(), y, vis.width(), ROW_H), QColor("#202227"))
            if r.obj_id == self.selected_id:
                p.fillRect(QRectF(vis.left(), y, vis.width(), ROW_H), QColor(61, 139, 253, 45))
        # grid + scenario window
        x0, x1 = self.x_of(tl.start), self.x_of(tl.end)
        p.fillRect(QRectF(x0, AXIS_H, x1 - x0, len(self.rows) * ROW_H), QColor(255, 255, 255, 6))
        step = self._tick_step()
        t = tl.start - (tl.start % step) + step if tl.start % step else tl.start
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        while t <= tl.end:
            x = self.x_of(t)
            p.drawLine(QPointF(x, AXIS_H), QPointF(x, AXIS_H + len(self.rows) * ROW_H))
            t += step
        p.setPen(QPen(QColor("#ffd166"), 1.5))
        p.drawLine(QPointF(x0, AXIS_H - 6), QPointF(x0, AXIS_H + len(self.rows) * ROW_H))
        p.setPen(QPen(CLASH_COL, 1.5, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(x1, AXIS_H - 6), QPointF(x1, AXIS_H + len(self.rows) * ROW_H))
        # marks
        for i, r in enumerate(self.rows):
            self._paint_row(p, r, AXIS_H + i * ROW_H)
        # sticky axis (top) and labels (left)
        p.fillRect(QRectF(vis.left(), vis.top(), vis.width(), AXIS_H), QColor("#26282c"))
        self._paint_axis(p, vis)
        p.fillRect(QRectF(vis.left(), vis.top() + AXIS_H, LABEL_W - 6, vis.height()), QColor("#23252a"))
        for i, r in enumerate(self.rows):
            y = AXIS_H + i * ROW_H
            if y + ROW_H < vis.top() + AXIS_H:
                continue
            col = KIND_COL.get(r.kind, MISSION_COL)
            if not r.active:
                col = QColor("#6b6f78")
            p.fillRect(QRectF(vis.left() + 4, y + 7, 4, ROW_H - 14), col)
            p.setPen(QColor("#e3e5e8") if r.active else QColor("#7c818a"))
            name = ("⚠ " if r.issues or r.obj_id in self.clash_ids else "") + r.name
            p.drawText(QRectF(vis.left() + 14, y, LABEL_W - 24, ROW_H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       p.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, LABEL_W - 26))
        p.fillRect(QRectF(vis.left(), vis.top(), LABEL_W - 6, AXIS_H), QColor("#26282c"))
        p.setPen(QColor("#9fb3c8"))
        p.drawText(QRectF(vis.left() + 10, vis.top(), LABEL_W, AXIS_H), Qt.AlignmentFlag.AlignVCenter,
                   f"{sum(r.kind == 'event' for r in self.rows)} events, "
                   f"{sum(r.kind == 'mission' for r in self.rows)} missions"
                   + (f", {n} courses" if (n := sum(r.kind == 'course' for r in self.rows)) else ""))
        p.end()

    def _tick_step(self) -> int:
        for step in (300, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400, 172800):
            if step / 3600 * self.px_per_hour >= 70:
                return step
        return 604800

    def _paint_axis(self, p: QPainter, vis) -> None:
        tl = self.tl
        step = self._tick_step()
        t = tl.start - (tl.start % step) + (step if tl.start % step else 0)
        p.setPen(QColor("#c8ccd4"))
        while t <= tl.end:
            x = self.x_of(t)
            if x >= vis.left() + LABEL_W:
                p.drawLine(QPointF(x, vis.top() + AXIS_H - 6), QPointF(x, vis.top() + AXIS_H))
                p.drawText(QPointF(x + 3, vis.top() + 16), fmt_time(t).replace(" Z", "Z"))
                p.setPen(QColor("#8a8f99"))
                p.drawText(QPointF(x + 3, vis.top() + 30), "H" + rel(t - tl.start))
                p.setPen(QColor("#c8ccd4"))
            t += step

    def _paint_row(self, p: QPainter, r: Row, y: float) -> None:
        tl = self.tl
        base = KIND_COL.get(r.kind, MISSION_COL)
        if not r.active:
            base = QColor("#6b6f78")
        mid = y + ROW_H / 2
        conds = [m.label for m in r.marks if m.style == CONDITION]
        if conds:   # one dotted line and one label, however many condition triggers
            p.setPen(QPen(QColor(base.red(), base.green(), base.blue(), 120), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(self.x_of(tl.start), mid), QPointF(self.x_of(tl.end), mid))
            p.setPen(QColor("#9aa0aa"))
            text = "on condition: " + conds[0] + (f"  (+{len(conds) - 1} more)" if len(conds) > 1 else "")
            width = self.x_of(tl.end) - self.x_of(tl.start) - 12
            p.drawText(QPointF(self.x_of(tl.start) + 6, mid - 3),
                       p.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, int(max(40, width))))
        for m in r.marks:
            if m.style == CONDITION:
                continue
            elif m.style in (BAND, REPEAT):
                a, b = self.x_of(m.start), self.x_of(m.end or tl.end)
                fill = QColor(base)
                fill.setAlpha(55 if m.style == BAND else 30)
                p.setPen(QPen(base, 1))
                p.setBrush(QBrush(fill))
                p.drawRoundedRect(QRectF(a, y + 7, max(2.0, b - a), ROW_H - 14), 3, 3)
                if m.style == REPEAT and m.interval / 3600 * self.px_per_hour >= 5:
                    p.setPen(QPen(base, 1))
                    t = m.start
                    while t <= (m.end or tl.end):
                        x = self.x_of(t)
                        p.drawLine(QPointF(x, y + 9), QPointF(x, y + ROW_H - 9))
                        t += m.interval
                p.setPen(QColor("#d0d4da"))
                if b - a > 120:
                    p.drawText(QRectF(a + 6, y, b - a - 12, ROW_H), Qt.AlignmentFlag.AlignVCenter, m.label)
            elif m.style == POINT and m.start is not None:
                x = self.x_of(m.start)
                out = not (tl.start <= m.start <= tl.end)
                clash = r.obj_id in self.clash_ids
                col = CLASH_COL if out else base
                p.setPen(QPen(QColor("#ffffff") if r.obj_id == self.selected_id else QColor("#0b0b0b"), 1.2))
                p.setBrush(QBrush(col))
                d = 7
                p.drawPolygon(QPolygonF([QPointF(x, mid - d), QPointF(x + d, mid), QPointF(x, mid + d),
                                         QPointF(x - d, mid)]))
                if clash:
                    p.setPen(QPen(CLASH_COL, 1.5))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(QPointF(x, mid), d + 4, d + 4)
                p.setPen(QColor("#d0d4da"))
                p.drawText(QPointF(x + 11, mid + 4), m.label if r.kind == "mission" else
                           f"{m.label} {fmt_time(m.start)[7:]}" if r.kind == "course" else fmt_time(m.start)[7:])

    # ------------------------------------------------------------------ interaction
    def row_at(self, y: float) -> Optional[Row]:
        i = int((y - AXIS_H) // ROW_H)
        return self.rows[i] if 0 <= i < len(self.rows) and y >= AXIS_H else None

    def mouseMoveEvent(self, e) -> None:
        r = self.row_at(e.position().y())
        if r is None or not self.tl:
            QToolTip.hideText()
            return
        t = self.epoch_at(e.position().x())
        tip = html.escape(r.detail).replace("\n", "<br>")
        if e.position().x() > LABEL_W:
            tip += f"<br><br><i>cursor {html.escape(fmt_time(t, self.tl.start))}</i>"
        if r.issues:
            tip += "<br><br><b style='color:#e5484d'>" + "<br>".join(html.escape(x) for x in r.issues) + "</b>"
        QToolTip.showText(e.globalPosition().toPoint(), tip, self)

    def mousePressEvent(self, e) -> None:
        r = self.row_at(e.position().y())
        self.selected_id = r.obj_id if r else ""
        self.rowSelected.emit(r)
        self.update()

    def mouseDoubleClickEvent(self, e) -> None:
        r = self.row_at(e.position().y())
        if r:
            self.rowActivated.emit(r)

    def wheelEvent(self, e) -> None:
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if e.angleDelta().y() > 0 else 0.8
            self.set_zoom(self.px_per_hour * factor)
            e.accept()
        else:
            super().wheelEvent(e)


class TimelinePage(Page):
    title = "Timeline"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter events, missions and courses...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(lambda *_: self._apply())
        bar.addWidget(self.filter, 1)
        self.missions = QCheckBox("Missions")
        self.missions.setChecked(True)
        self.courses = QCheckBox("Courses")
        self.courses.setChecked(True)
        self.courses.setToolTip("Units with a plotted course: when each takes off or sets off")
        self.conditional = QCheckBox("Condition-only events")
        self.conditional.setChecked(True)
        self.sort_time = QCheckBox("Sort by time")
        self.sort_time.setChecked(True)
        for cb in (self.missions, self.courses, self.conditional, self.sort_time):
            cb.toggled.connect(lambda *_: self._apply())
            bar.addWidget(cb)
        for text, fn in (("Fit", self._fit), ("Zoom in", lambda: self._zoom(1.5)),
                         ("Zoom out", lambda: self._zoom(1 / 1.5))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bar.addWidget(b)
        lay.addLayout(bar)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.canvas = TimelineCanvas()
        self.scroll.setWidget(self.canvas)
        self.scroll.horizontalScrollBar().valueChanged.connect(lambda *_: self.canvas.update())
        self.scroll.verticalScrollBar().valueChanged.connect(lambda *_: self.canvas.update())
        split.addWidget(self.scroll)
        side = QWidget()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        self.detail = QTextBrowser()
        sl.addWidget(self.detail, 1)
        sl.addWidget(hint_label("Diamonds fire once; bars are random windows or mission periods; ticked bars "
                                "repeat; dotted lines fire on a condition. Red: outside the scenario or two "
                                "one-shot events in the same minute. Amber rows are unit courses (when each "
                                "unit takes off or sets off). Ctrl+wheel zooms; double-click opens the event, "
                                "mission or unit."))
        split.addWidget(side)
        split.setSizes([1100, 320])
        lay.addWidget(split, 1)
        self.canvas.rowSelected.connect(self._show_row)
        self.canvas.rowActivated.connect(self._open)
        self._tl: Optional[Timeline] = None
        self._fitted = False

    def refresh(self) -> None:
        self._tl = build_timeline(self.project, include_missions=True)
        self._apply()
        if not self._fitted:
            self._fitted = True
            self._fit()
        self._summary()

    def _apply(self):
        if not self._tl:
            return
        words = self.filter.text().lower().split()
        rows = []
        for r in self._tl.rows:
            if r.kind == "mission" and not self.missions.isChecked():
                continue
            if r.kind == "course" and not self.courses.isChecked():
                continue
            if r.kind == "event" and not r.timed and not self.conditional.isChecked():
                continue
            if words and not all(w in (r.name + " " + r.detail).lower() for w in words):
                continue
            rows.append(r)
        if self.sort_time.isChecked():
            big = 1 << 62
            order = {"event": 0, "mission": 1, "course": 2}
            rows.sort(key=lambda r: (order.get(r.kind, 3), r.first_time() if r.first_time() is not None else big,
                                     r.name.lower()))
        self.canvas.set_rows(self._tl, rows)

    def _fit(self):
        self.canvas.fit(self.scroll.viewport().width())

    def _zoom(self, f: float):
        self.canvas.set_zoom(self.canvas.px_per_hour * f)

    def _summary(self):
        tl = self._tl
        p = self.project
        names = {e.id: e.name for e in p.events}
        lines = [f"<b>{html.escape(p.meta.title)}</b><br>{html.escape(fmt_time(tl.start))} to "
                 f"{html.escape(fmt_time(tl.end))}<br>"]
        issues = [(r.name, i) for r in tl.rows for i in r.issues]
        if tl.clashes:
            lines.append("<b style='color:#e5484d'>Same-minute events</b><ul>")
            for a, b, t in tl.clashes:
                lines.append(f"<li>{html.escape(names.get(a, a))} and {html.escape(names.get(b, b))} at "
                             f"{html.escape(fmt_time(t, tl.start))}</li>")
            lines.append("</ul>")
        if issues:
            lines.append("<b style='color:#e5484d'>Timing problems</b><ul>")
            lines += [f"<li>{html.escape(n)}: {html.escape(i)}</li>" for n, i in issues]
            lines.append("</ul>")
        if not tl.clashes and not issues:
            lines.append("<span style='color:#30a46c'>No timing problems found.</span>")
        lines.append("<p>Click a row for details.</p>")
        self.detail.setHtml("".join(lines))

    def _show_row(self, r: Optional[Row]):
        if r is None:
            self._summary()
            return
        when = [f"{html.escape(m.label)}: {html.escape(fmt_time(m.start, self._tl.start))}"
                + (f" to {html.escape(fmt_time(m.end, self._tl.start))}" if m.end else "")
                for m in r.marks if m.start is not None]
        cond = [html.escape(m.label) for m in r.marks if m.style == CONDITION]
        txt = ("<b>" + html.escape(r.name) + "</b> <i>(" + r.kind + ")</i><br>"
               + html.escape(r.detail).replace("\n", "<br>")
               + ("<br><br><b>When</b><br>" + "<br>".join(when) if when else "")
               + ("<br><br><b>On condition</b><br>" + "<br>".join(cond) if cond else "")
               + ("<br><br><b style='color:#e5484d'>" + "<br>".join(html.escape(i) for i in r.issues) + "</b>"
                  if r.issues else "")
               + "<br><br><i>Double-click the row to edit it.</i>")
        self.detail.setHtml(txt)

    def _open(self, r: Row):
        w = self.ctx.window
        if w is None:
            return
        w.goto_object(r.obj_id)
