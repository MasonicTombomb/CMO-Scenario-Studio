"""The scenario at a moment: where units with a course should be, the weather, and which timed events have fired.

All of it is estimated from the project (course timings, the forecast, event triggers); nothing runs CMO.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .course_plan import CoursePlan, plan_course, position_at
from .project import Project
from .timeline import POINT, build_timeline


@dataclass
class Ghost:
    unit_id: str
    name: str
    side: str
    lat: float
    lon: float
    status: str


@dataclass
class Moment:
    t: int                                  # seconds after the start
    ghosts: list[Ghost] = field(default_factory=list)
    weather: tuple = ()                     # (temperature, rainfall, cloud, sea state)
    weather_changed_at: int = 0             # minutes after the start (0: the start weather)
    fired: list[str] = field(default_factory=list)     # timed events fired by now, oldest first


class ScenarioClock:
    """Plans the courses once (call :meth:`reset` when the project changes), then answers 'what about time t?'."""

    def __init__(self, project: Project):
        self.reset(project)

    def reset(self, project: Project) -> None:
        self.p = project
        self.plans: list[tuple] = []
        for u in project.units:
            plan = plan_course(project, u)
            if plan is not None:
                self.plans.append((u, plan))
        tl = build_timeline(project, include_missions=False, include_courses=False, include_weather=False)
        self.start = tl.start
        self.duration_s = tl.end - tl.start
        self.events = sorted((m.start - tl.start, r.name) for r in tl.rows if r.kind == "event" and r.active
                             for m in r.marks if m.style == POINT and m.start is not None)

    def at(self, t: int) -> Moment:
        m = Moment(t)
        for u, plan in self.plans:
            lat, lon, status = position_at(plan, t)
            if status.startswith("on the ground"):       # still in its base: nothing to show yet
                continue
            m.ghosts.append(Ghost(u.id, u.display_name(), u.side, lat, lon, status))
        w = self.p.weather
        m.weather = (w.temperature, w.rainfall, w.cloud, w.sea_state)
        for e in sorted(self.p.forecast, key=lambda e: e.offset_minutes):
            if 0 < e.offset_minutes * 60 <= t:
                m.weather = (e.temperature, e.rainfall, e.cloud, e.sea_state)
                m.weather_changed_at = e.offset_minutes
        m.fired = [name for s, name in self.events if s <= t]
        return m


def plan_of(clock: ScenarioClock, unit_id: str) -> CoursePlan | None:
    return next((pl for u, pl in clock.plans if u.id == unit_id), None)
