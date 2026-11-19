"""Estimates for a plotted course: each leg's length, timing and the settings in force.

Pure Python, used by the course window (leg table and flight profile), the unit form and the Timeline. Times are
estimates: the leg speed if set, else the unit's starting speed, else a typical speed for its type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..geo import distance_km
from .project import COURSE_FINISH, Project, Unit

#: knots, when neither the leg nor the unit gives a speed
TYPICAL_SPEED = {"Aircraft": 450.0, "Ship": 15.0, "Submarine": 8.0, "GroundUnit": 12.0}


@dataclass
class Leg:
    n: int                              # waypoint number flown to (1-based); 0 = the last leg home / to the base
    label: str
    a: tuple[float, float]
    b: tuple[float, float]
    nm: float
    alt: Optional[float]                # metres in force on this leg (None = CMO chooses)
    alt_set: bool
    speed: float                        # knots in force (estimate when not set)
    speed_set: bool
    radar: Optional[bool]               # True on, False off, None = unit's default
    sonar: Optional[bool]
    ecm: Optional[bool]
    weapons: str                        # '' = side doctrine, else free / tight / hold
    engage: str
    wait: int                           # minutes circling at the end of the leg
    signal: str
    t0: int                             # seconds after the scenario start: leaves
    t1: int                             # arrives (before any wait)


@dataclass
class CoursePlan:
    legs: list[Leg] = field(default_factory=list)
    origin: str = ""
    air: bool = False
    hosted: bool = False
    start_alt: Optional[float] = None
    depart_s: int = 0
    end_s: int = 0
    total_nm: float = 0.0
    finish: str = ""
    repeat: bool = False

    @property
    def route_legs(self) -> list[Leg]:
        return [lg for lg in self.legs if lg.n]


def _nm(a, b) -> float:
    return distance_km(a[0], a[1], b[0], b[1]) / 1.852


def _flag(v: str, prev: Optional[bool]) -> Optional[bool]:
    return True if v == "active" else False if v == "passive" else prev


def plan_course(p: Project, u: Unit) -> Optional[CoursePlan]:
    c = u.course
    if c is None or not c.waypoints:
        return None
    host = p.unit(u.host) if u.host else None
    origin = (host.lat, host.lon) if host is not None else (u.lat, u.lon)
    plan = CoursePlan(origin=host.name if host is not None else u.name, air=u.type == "Aircraft",
                      hosted=host is not None, depart_s=60 * max(0, int(c.depart_minutes or 0)),
                      repeat=c.finish == "repeat")
    alt = 0.0 if (plan.air and host is not None) else (u.altitude if plan.air else None)
    plan.start_alt = alt
    speed = float(u.speed) if u.speed else TYPICAL_SPEED.get(u.type, 15.0)
    radar: Optional[bool] = True if u.radar_active else None
    sonar: Optional[bool] = True if u.sonar_active else None
    ecm: Optional[bool] = None
    weapons = engage = ""
    t = plan.depart_s
    here = origin
    for i, w in enumerate(c.waypoints, 1):
        if w.altitude is not None:
            alt = float(w.altitude)
        if w.speed:
            speed = float(w.speed)
        radar, sonar, ecm = _flag(w.radar, radar), _flag(w.sonar, sonar), _flag(w.ecm, ecm)
        weapons = w.weapons or weapons
        engage = w.engage or engage
        nm = _nm(here, (w.lat, w.lon))
        t1 = t + int(round(nm / max(speed, 1.0) * 3600))
        plan.legs.append(Leg(i, w.name or f"Waypoint {i}", here, (w.lat, w.lon), nm, alt, w.altitude is not None,
                             speed, bool(w.speed), radar, sonar, ecm, weapons, engage,
                             max(0, int(w.wait_minutes or 0)), w.signal, t, t1))
        t = t1 + 60 * max(0, int(w.wait_minutes or 0))
        here = (w.lat, w.lon)
    plan.finish = COURSE_FINISH.get(c.finish, c.finish)
    end = None
    if c.finish == "rtb" and host is not None:
        end, label = origin, f"Back to {host.name}"
    elif c.finish == "land" and p.unit(c.land_at):
        b = p.unit(c.land_at)
        end, label = (b.lat, b.lon), f"To {b.name}"
        plan.finish = f"Lands at {b.name}"
    if end is not None:
        nm = _nm(here, end)
        t1 = t + int(round(nm / max(speed, 1.0) * 3600))
        plan.legs.append(Leg(0, label, here, end, nm, alt, False, speed, False, radar, sonar, ecm, weapons, engage,
                             0, "", t, t1))
        t = t1
    plan.end_s = t
    plan.total_nm = sum(lg.nm for lg in plan.legs)
    return plan


def hms(seconds: int) -> str:
    """Duration as 'h:mm' (or 'd h:mm')."""
    seconds = max(0, int(seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    return (f"{d}d " if d else "") + f"{h}:{rem // 60:02d}"
