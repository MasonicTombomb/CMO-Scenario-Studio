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
    depth: Optional[float]              # metres in force (submarines; None = unchanged from the start)
    depth_set: bool
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
    target_s: Optional[int] = None      # time on target set for this waypoint (seconds after the start)
    need_kn: Optional[float] = None     # when late: the speed this leg needs to arrive on time (inf: cannot)

    @property
    def diff_s(self) -> Optional[int]:
        """Seconds late (positive) or early (negative) against the time on target."""
        return None if self.target_s is None else self.t1 - self.target_s


@dataclass
class CoursePlan:
    legs: list[Leg] = field(default_factory=list)
    origin: str = ""
    air: bool = False
    sub: bool = False
    hosted: bool = False
    start_alt: Optional[float] = None
    start_depth: Optional[float] = None
    depart_s: int = 0
    end_s: int = 0
    total_nm: float = 0.0
    finish: str = ""
    repeat: bool = False
    tot_depart_s: Optional[int] = None  # departure that meets the first time on target
    range_nm: Optional[float] = None    # aircraft: estimated range with its loadout
    range_note: str = ""
    fuel_nm: float = 0.0                # distance flown, counting waits at the leg speed
    origin_pos: tuple[float, float] = (0.0, 0.0)

    @property
    def route_legs(self) -> list[Leg]:
        return [lg for lg in self.legs if lg.n]


def _nm(a, b) -> float:
    return distance_km(a[0], a[1], b[0], b[1]) / 1.852


def _flag(v: str, prev: Optional[bool]) -> Optional[bool]:
    return True if v == "active" else False if v == "passive" else prev


def plan_course(p: Project, u: Unit, db=None) -> Optional[CoursePlan]:
    c = u.course
    if c is None or not c.waypoints:
        return None
    host = p.unit(u.host) if u.host else None
    origin = (host.lat, host.lon) if host is not None else (u.lat, u.lon)
    plan = CoursePlan(origin=host.name if host is not None else u.name, air=u.type == "Aircraft",
                      sub=u.type == "Submarine",
                      hosted=host is not None, depart_s=60 * max(0, int(c.depart_minutes or 0)),
                      repeat=c.finish == "repeat", origin_pos=origin)
    alt = 0.0 if (plan.air and host is not None) else (u.altitude if plan.air else None)
    plan.start_alt = alt
    depth = u.depth if plan.sub else None
    plan.start_depth = depth
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
        if plan.sub and w.depth is not None:
            depth = float(w.depth)
        radar, sonar, ecm = _flag(w.radar, radar), _flag(w.sonar, sonar), _flag(w.ecm, ecm)
        weapons = w.weapons or weapons
        engage = w.engage or engage
        nm = _nm(here, (w.lat, w.lon))
        t1 = t + int(round(nm / max(speed, 1.0) * 3600))
        plan.legs.append(Leg(i, w.name or f"Waypoint {i}", here, (w.lat, w.lon), nm, alt, w.altitude is not None,
                             depth, plan.sub and w.depth is not None, speed, bool(w.speed), radar, sonar, ecm, weapons, engage,
                             max(0, int(w.wait_minutes or 0)), w.signal, t, t1,
                             None if w.arrive_minutes is None else 60 * int(w.arrive_minutes)))
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
        plan.legs.append(Leg(0, label, here, end, nm, alt, False, depth, False, speed, False, radar, sonar, ecm, weapons, engage,
                             0, "", t, t1))
        t = t1
    plan.end_s = t
    plan.total_nm = sum(lg.nm for lg in plan.legs)
    plan.fuel_nm = plan.total_nm + sum(lg.wait / 60 * lg.speed for lg in plan.legs)
    _times_on_target(plan)
    if plan.air and db is not None and u.loadout:
        _range(plan, db, int(u.loadout))
    return plan


LATE_S = 120          # within two minutes counts as on time


def _times_on_target(plan: CoursePlan) -> None:
    first = next((lg for lg in plan.legs if lg.target_s is not None), None)
    if first is not None:
        plan.tot_depart_s = plan.depart_s - first.diff_s
    for lg in plan.legs:
        if lg.target_s is not None and lg.diff_s > LATE_S:
            left = lg.target_s - lg.t0
            lg.need_kn = lg.nm / (left / 3600) if left > 0 else float("inf")


def _range(plan: CoursePlan, db, loadout: int) -> None:
    """Rough range from the database: out and back over the loadout's combat radius, plus its time on station at
    a typical cruise speed (the radius already allows for that loiter)."""
    try:
        from ..db.loadouts import loadout_details
        d = loadout_details(db, loadout)
    except Exception:  # noqa: BLE001 - a database without loadout data: no estimate
        return
    if d is None or not d.radius_nm:
        return
    loiter = d.time_on_station_min / 60 * TYPICAL_SPEED["Aircraft"]
    plan.range_nm = 2 * d.radius_nm + loiter
    plan.range_note = (f"{d.name}: {d.radius_nm:,} nm combat radius" +
                       (f" with {d.time_on_station_min} min on station" if d.time_on_station_min else ""))


def plan_times(p: Project, u: Unit) -> list[str]:
    """Time the course to its times on target: set the departure for the first one, then add waits before any later
    one it would reach early. Changes ``u.course``; returns what it did (empty when nothing is set)."""
    plan = plan_course(p, u)
    if plan is None or plan.tot_depart_s is None:
        return []
    c = u.course
    done = []
    want = plan.tot_depart_s
    if want < 0:
        done.append(f"It cannot leave early enough: it would have to leave {hms(-want)} before the start. "
                    "Departure set to the start; raise the speed.")
        want = 0
    c.depart_minutes = int(want // 60)
    done.append(f"Departure set to H+{hms(c.depart_minutes * 60)}.")
    for _ in range(len(c.waypoints)):
        plan = plan_course(p, u)
        early = next((lg for lg in plan.legs[1:] if lg.target_s is not None and lg.diff_s < -LATE_S), None)
        if early is None:
            break
        prev = c.waypoints[early.n - 2]
        add = int(-early.diff_s // 60)
        prev.wait_minutes = int(prev.wait_minutes or 0) + add
        done.append(f"Waits {add} min more at waypoint {early.n - 1} to reach waypoint {early.n} on time.")
    plan = plan_course(p, u)
    for lg in plan.legs:
        if lg.need_kn is not None:
            done.append(f"Still {hms(lg.diff_s)} late at waypoint {lg.n}: " +
                        ("it cannot get there in time." if lg.need_kn == float("inf") else
                         f"it needs about {lg.need_kn:,.0f} kn on that leg."))
    return done


def position_at(plan: CoursePlan, t: int) -> tuple[float, float, str]:
    """Where the unit should be ``t`` seconds after the start, by the estimates: (lat, lon, what it is doing)."""
    if t < plan.depart_s:
        return (*plan.origin_pos, f"on the ground at {plan.origin}" if plan.hosted else "waiting to set off")
    for lg in plan.legs:
        if t < lg.t1:
            f = 0.0 if lg.t1 <= lg.t0 else max(0.0, min(1.0, (t - lg.t0) / (lg.t1 - lg.t0)))
            return (lg.a[0] + (lg.b[0] - lg.a[0]) * f, lg.a[1] + (lg.b[1] - lg.a[1]) * f,
                    f"heading for {lg.label}" if lg.n else lg.label.replace("To ", "heading for ", 1)
                    .replace("Back to ", "returning to ", 1))
        if lg.wait and t < lg.t1 + 60 * lg.wait:
            return (*lg.b, f"waiting at {lg.label}")
    last = plan.legs[-1]
    if plan.repeat and len(plan.route_legs) > 1:
        first = plan.route_legs[0]
        close_nm = _nm(last.b, first.b)
        close_s = int(round(close_nm / max(last.speed, 1.0) * 3600))
        lap = (plan.end_s - first.t1) + close_s
        k = (t - plan.end_s) % max(lap, 1)
        if k < close_s:
            f = k / close_s
            return (last.b[0] + (first.b[0] - last.b[0]) * f, last.b[1] + (first.b[1] - last.b[1]) * f,
                    "flying the course again")
        return position_at(plan, first.t1 + (k - close_s))[:2] + ("flying the course again",)
    if last.n == 0:
        return (*last.b, "landed" if plan.air else "arrived")
    return (*last.b, "course finished")


def hms(seconds: int) -> str:
    """Duration as 'h:mm' (or 'd h:mm')."""
    seconds = max(0, int(seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    return (f"{d}d " if d else "") + f"{h}:{rem // 60:02d}"
