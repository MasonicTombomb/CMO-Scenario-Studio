"""When things happen: events (by trigger), missions (by start/end time) and unit courses (by departure) on
the scenario clock.

Pure Python so it can be tested; the Timeline tab draws what :func:`build_timeline` returns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .enums import ACTION_TYPES, TRIGGER_TYPES
from .project import Event, Project

#: RegularTime interval index -> seconds (see enums.REGULAR_INTERVALS)
INTERVAL_SECONDS = (1, 5, 15, 30, 60, 300, 900, 1800, 3600, 21600, 43200, 86400)

POINT, BAND, REPEAT, CONDITION = "point", "band", "repeat", "condition"


@dataclass
class Mark:
    """One trigger of an event (or a mission's active period) placed on the clock."""
    style: str                      # point | band | repeat | condition
    start: Optional[int] = None     # epoch seconds (None for 'condition')
    end: Optional[int] = None       # band / repeat end
    interval: int = 0               # repeat interval, seconds
    label: str = ""


@dataclass
class Row:
    kind: str                       # 'event' | 'mission' | 'course'
    obj_id: str
    name: str
    active: bool = True
    once: bool = True
    marks: list[Mark] = field(default_factory=list)
    detail: str = ""                # multi-line summary for tooltips / the detail pane
    issues: list[str] = field(default_factory=list)

    @property
    def timed(self) -> bool:
        return any(m.style != CONDITION for m in self.marks)

    def first_time(self) -> Optional[int]:
        times = [m.start for m in self.marks if m.start is not None]
        return min(times) if times else None


@dataclass
class Timeline:
    start: int
    end: int
    rows: list[Row]
    clashes: list[tuple[str, str, int]] = field(default_factory=list)   # (row id, row id, epoch)


_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M",
                 "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d/%m/%Y")


def parse_time(text) -> Optional[int]:
    """ISO or CMO-style dd/mm/yyyy [hh:mm[:ss]] (UTC) -> epoch seconds."""
    if text in (None, ""):
        return None
    t = re.sub(r"\s+", " ", str(text).strip().replace("Z", ""))
    for fmt in _DATE_FORMATS:
        try:
            return int(datetime.strptime(t, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return None


def fmt_time(epoch: int, start: Optional[int] = None) -> str:
    s = datetime.fromtimestamp(epoch, timezone.utc).strftime("%d %b %H:%M Z")
    if start is not None:
        s += f"  (H{rel(epoch - start)})"
    return s


def rel(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    seconds = abs(int(seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"{sign}{d}d {h:02d}:{m:02d}" if d else f"{sign}{h:02d}:{m:02d}"


def _int(v, default=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def event_marks(p: Project, e: Event, start: int, end: int) -> list[Mark]:
    marks = []
    for t in e.triggers:
        prm = t.params
        label = TRIGGER_TYPES.get(t.type, (t.type,))[0]
        if t.type == "StudioAtTime":
            marks.append(Mark(POINT, parse_time(prm.get("Time")) or start, label=label))
        elif t.type == "StudioAfterDelay":
            marks.append(Mark(POINT, start + 60 * _int(prm.get("Minutes")), label=label))
        elif t.type == "ScenLoaded":
            marks.append(Mark(POINT, start, label=label))
        elif t.type == "ScenEnded":
            marks.append(Mark(POINT, end, label=label))
        elif t.type == "RegularTime":
            iv = _int(prm.get("Interval"), 4)
            secs = INTERVAL_SECONDS[iv] if 0 <= iv < len(INTERVAL_SECONDS) else 60
            marks.append(Mark(REPEAT, start, end, secs, label=f"{label} every {_interval_text(secs)}"))
        elif t.type == "RandomTime":
            a, b = parse_time(prm.get("EarliestTime")), parse_time(prm.get("LatestTime"))
            if a and b:
                marks.append(Mark(BAND, min(a, b), max(a, b), label=label))
            else:
                marks.append(Mark(CONDITION, label=f"{label} (times not readable)"))
        else:
            marks.append(Mark(CONDITION, label=label + _target_text(p, prm)))
    return marks


def _interval_text(secs: int) -> str:
    if secs < 60:
        return f"{secs} s"
    if secs < 3600:
        return f"{secs // 60} min"
    return f"{secs // 3600} h"


def _target_text(p: Project, prm: dict) -> str:
    bits = []
    if prm.get("TargetSide"):
        bits.append(p.side_name(prm["TargetSide"]))
    if prm.get("TargetType"):
        bits.append(prm["TargetType"])
    if prm.get("SpecificUnit") and p.unit(prm["SpecificUnit"]):
        bits.append(p.unit(prm["SpecificUnit"]).name)
    if prm.get("Area") and p.zone(prm["Area"]):
        bits.append(p.zone(prm["Area"]).name)
    if prm.get("Side"):
        bits.append(p.side_name(prm["Side"]))
    return f" ({', '.join(bits)})" if bits else ""


def event_detail(p: Project, e: Event) -> str:
    lines = [e.name, "Repeatable" if e.repeatable else "Once", ("" if e.active else "INACTIVE")]
    if e.probability < 100:
        lines.append(f"Probability {e.probability}%")
    if e.conditions:
        lines.append("Conditions: " + ", ".join(c.type for c in e.conditions))
    for a in e.actions:
        label = ACTION_TYPES.get(a.type, (a.type,))[0]
        extra = ""
        if a.type == "SpawnUnit" and p.unit(a.params.get("Unit", "")):
            extra = f": {p.unit(a.params['Unit']).display_name()}"
        elif a.type == "Score":
            extra = f": {p.side_name(a.params.get('Side', ''))} {_int(a.params.get('Change')):+d}"
        elif a.type == "MissionStatus" and p.mission(a.params.get("Mission", "")):
            m = p.mission(a.params["Mission"])
            extra = f": {m.name} {'on' if a.params.get('Active', True) else 'off'}"
        elif a.type == "RunScript":
            extra = f": {a.params.get('Script', '')}.lua"
        elif a.type == "Message":
            txt = re.sub(r"<[^>]+>", " ", str(a.params.get("Text", "")))
            extra = ": " + re.sub(r"\s+", " ", txt).strip()[:60]
        lines.append(f"  - {label}{extra}")
    return "\n".join(x for x in lines if x)


def course_rows(p: Project, start: int, end: int) -> list[Row]:
    """A row per unit with a plotted course: a diamond where it takes off or sets off, then a bar while it is
    (by estimate) on its route."""
    from .course_plan import hms, plan_course
    rows = []
    for u in p.units:
        plan = plan_course(p, u)
        if plan is None:
            continue
        t = start + plan.depart_s
        verb = f"takes off from {plan.origin}" if plan.hosted else "sets off"
        waits = sum(lg.wait for lg in plan.legs)
        r = Row("course", u.id, u.display_name(), active=True, once=True,
                marks=[Mark(POINT, t, label=verb.split(" from ")[0]),
                       Mark(BAND, t, start + plan.end_s, label="en route (estimate)" + (", then repeats" if plan.repeat
                                                                                        else ""))],
                detail=f"{u.display_name()} ({p.side_name(u.side)})\n{verb.capitalize()} at {fmt_time(t, start)}, "
                       f"{len(u.course.waypoints)} waypoint(s), {plan.total_nm:,.0f} nm, about "
                       f"{hms(plan.end_s - plan.depart_s)} h" + (f" including {waits} min waiting" if waits else "")
                       + f"\nAt the end: {plan.finish}"
                       + ("\nA reinforcement: the course starts once it has arrived" if u.reserve else ""))
        if t > end:
            r.issues.append(f"Departs at {fmt_time(t, start)}, after the scenario ends.")
        rows.append(r)
    return rows


def build_timeline(p: Project, include_missions: bool = True, include_courses: bool = True) -> Timeline:
    start = p.clock.start_epoch()
    end = start + 60 * (p.clock.duration_days * 1440 + p.clock.duration_hours * 60 + p.clock.duration_minutes)
    if end <= start:
        end = start + 86400
    rows: list[Row] = []
    for e in p.events:
        r = Row("event", e.id, e.name, active=e.active, once=not e.repeatable or any(
            t.type in ("StudioAtTime", "StudioAfterDelay") for t in e.triggers),
            marks=event_marks(p, e, start, end), detail=event_detail(p, e))
        for m in r.marks:
            if m.start is not None and m.style == POINT and not (start <= m.start <= end):
                r.issues.append(f"Fires at {fmt_time(m.start, start)}, outside the scenario "
                                f"({'before the start' if m.start < start else 'after the end'}).")
            if m.style == BAND and m.end is not None and (m.end < start or m.start > end):
                r.issues.append("Its random window lies outside the scenario.")
        if not e.triggers:
            r.issues.append("No trigger: it never fires.")
        rows.append(r)
    if include_missions:
        for ms in p.missions:
            a = parse_time(ms.options.get("starttime"))
            b = parse_time(ms.options.get("endtime"))
            active = ms.options.get("isactive", True) is not False
            switches = [e for e in p.events for act in e.actions
                        if act.type == "MissionStatus" and act.params.get("Mission") == ms.id]
            r = Row("mission", ms.id, ms.name, active=active, once=True,
                    detail=f"{ms.name}\n{p.side_name(ms.side)} {ms.mclass}"
                           f"{('/' + ms.subtype) if ms.subtype else ''}, {len(ms.units)} unit(s)"
                           + ("" if active else "\nStarts inactive")
                           + "".join(f"\nSwitched by event '{e.name}'" for e in switches))
            if a or b or not active:
                s = a or start
                t = b or end
                r.marks.append(Mark(BAND, s, t, label="active" if active else "inactive at start"))
                if b and a and b < a:
                    r.issues.append("Mission end time is before its start time.")
            else:
                r.marks.append(Mark(BAND, start, end, label="active all scenario"))
            for e in switches:
                for m in event_marks(p, e, start, end):
                    if m.style == POINT:
                        r.marks.append(Mark(POINT, m.start, label=f"switched by '{e.name}'"))
            rows.append(r)
    if include_courses:
        rows += course_rows(p, start, end)
    # clashes: two one-shot timed events in the same minute
    clashes = []
    points = [(m.start // 60, r) for r in rows if r.kind == "event" and r.active
              for m in r.marks if m.style == POINT and m.start is not None]
    points.sort(key=lambda x: x[0])
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if points[j][0] != points[i][0]:
                break
            if points[i][1].obj_id != points[j][1].obj_id:
                clashes.append((points[i][1].obj_id, points[j][1].obj_id, points[i][0] * 60))
    return Timeline(start, end, rows, clashes)
