"""Can aircraft actually leave this base? What CMO needs for a working airbase group, and how to repair one.

CMO moves an aircraft from its parking (hangar, shelter, apron) through a *transit* facility (a Runway Access Point or
a Runway-Grade Taxiway) to a runway. A base built from separate facilities therefore needs, in one CMO group: parking,
a runway long enough, and an access point or taxiway at least as large as the aircraft (CMO manual 9.3.1). Without the
access point the aircraft is based and assigned but waits for a taxiway for ever. Single-unit airfields and ships have
all of it built in.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from ..geo import bearing_deg, destination, distance_km
from .hosting import PAD, PAD_HAULDOWN, PARKING, size_rank
from .project import Formation, Project, Unit

RUNWAYS = (2001, 2002)
TAXIWAY, ACCESS_POINT = 2003, 2004
TRANSIT = (TAXIWAY, ACCESS_POINT)
PADS = (PAD, PAD_HAULDOWN)

#: size rank -> (DBID, name) of the access point for aircraft up to that size
ACCESS_POINTS = {1: (827, "Runway Access Point (Small Aircraft)"), 2: (307, "Runway Access Point (Medium Aircraft)"),
                 3: (306, "Runway Access Point (Large Aircraft)"),
                 4: (353, "Runway Access Point (Very Large Aircraft)")}
LABEL = "Runway Access Point"
OFFSET_M = 80.0                         # from the runway's centre line, on the parking side


def runway_length(name: str, default: float = 1800.0) -> float:
    m = re.search(r"(\d{3,4}) ?m\b", name or "")
    return float(m.group(1)) if m else default


def access_positions(runways: list[tuple[float, float, float, float]],
                     parking: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Where to put access points, in metres. ``runways``: (x, y, heading, length). The longest runway gets four,
    the others two, on the side the parking is."""
    if not runways:
        return []
    cx = sum(x for x, _y in parking) / len(parking) if parking else 0.0
    cy = sum(y for _x, y in parking) / len(parking) if parking else 0.0
    out = []
    main = max(range(len(runways)), key=lambda i: runways[i][3])
    for i, (x, y, hdg, length) in enumerate(runways):
        h = math.radians(hdg)
        along, across = (math.sin(h), math.cos(h)), (math.cos(h), -math.sin(h))
        side = (cx - x) * across[0] + (cy - y) * across[1]
        side = -1.0 if side < 0 else 1.0
        for k in ((-0.36, -0.12, 0.12, 0.36) if i == main else (-0.36, 0.36)):
            out.append((round(x + along[0] * k * length + across[0] * side * OFFSET_M, 1),
                        round(y + along[1] * k * length + across[1] * side * OFFSET_M, 1)))
    return out


# ---------------------------------------------------------------- a site in a project
@dataclass
class Site:
    name: str
    side: str
    units: list[Unit]
    formation: Optional[Formation]
    runways: list[Unit] = field(default_factory=list)
    parking: list[Unit] = field(default_factory=list)
    park_rank: int = 0                  # largest aircraft it can park (1 small .. 4 very large)
    transit_rank: int = 0               # largest aircraft that can taxi to a runway
    runway_code: int = 0                # longest runway (EnumRunwayLength)
    pads: bool = False
    complete: bool = False              # has a single-unit airfield: runway, access and parking in one facility

    @property
    def grouped(self) -> bool:
        return len(self.units) == 1 or (self.formation is not None and self.formation.group_in_cmo)

    def can_taxi(self, rank: int) -> bool:
        return self.transit_rank >= rank


def _self_contained(types: set) -> bool:
    """CMO's single-unit airfields have all of it built in and need nothing added."""
    return bool(types & set(RUNWAYS)) and bool(types & set(PARKING)) and bool(types & set(TRANSIT))


def _site(p: Project, db, units: list[Unit], f: Optional[Formation], name: str) -> Site:
    s = Site(name, units[0].side, units, f)
    for u in units:
        if u.type != "Facility" or not u.dbid:
            continue
        spaces = db.aircraft_spaces("Facility", int(u.dbid))
        types = {x.ftype for x in spaces}
        if types & set(RUNWAYS):
            s.runways.append(u)
            s.runway_code = max(s.runway_code, db.runway_code(int(u.dbid)))
        if types & set(PARKING):
            s.parking.append(u)
        s.pads = s.pads or bool(types & set(PADS))
        s.complete = s.complete or _self_contained(types)
        for x in spaces:
            if x.ftype in PARKING:
                s.park_rank = max(s.park_rank, size_rank(x.size))
            elif x.ftype in TRANSIT:
                s.transit_rank = max(s.transit_rank, size_rank(x.size))
    return s


def _is_airbase_part(db, u: Unit) -> bool:
    return u.type == "Facility" and bool(u.dbid) and any(
        x.ftype in RUNWAYS + TRANSIT + PARKING for x in db.aircraft_spaces("Facility", int(u.dbid)))


def sites(p: Project, db) -> list[Site]:
    """Every airbase in the project: the units of each grouped site, or lone airbase facilities sharing a label."""
    out, used = [], set()
    for f in p.formations:
        units = [u for u in (p.unit(i) for i in [f.lead, *f.members]) if u is not None and not u.host]
        if any(_is_airbase_part(db, u) for u in units):
            used.update(u.id for u in units)
            out.append(_site(p, db, units, f, f.name))
    loose: dict[tuple[str, str], list[Unit]] = {}
    for u in p.units:
        if u.id not in used and not u.host and _is_airbase_part(db, u):
            loose.setdefault((u.side, u.group or u.id), []).append(u)
    for (_side, label), units in loose.items():
        out.append(_site(p, db, units, None, units[0].group or units[0].name))
    return out


def site_of(all_sites: list[Site], unit_id: str) -> Optional[Site]:
    return next((s for s in all_sites if any(u.id == unit_id for u in s.units)), None)


def broken_sites(p: Project, db) -> list[Site]:
    """Bases with a runway and parking whose parked aircraft could not reach the runway."""
    return [s for s in sites(p, db) if s.runways and s.parking and not s.complete and (not s.can_taxi(s.park_rank) or not s.grouped)]


def cannot_fly(p: Project, db) -> list[tuple[Unit, Site, str]]:
    """Aircraft based somewhere they can never take off from, and why."""
    out = []
    every = sites(p, db)
    for u in p.units:
        host = p.unit(u.host) if u.type == "Aircraft" and u.host else None
        if host is None or host.type != "Facility" or not u.dbid or not host.dbid:
            continue
        prof = db.aircraft_profile(int(u.dbid))
        s = site_of(every, host.id)
        if prof is None or s is None:
            continue
        rank = size_rank(prof.size)
        if prof.rotary and any(x.ftype in PADS for x in db.aircraft_spaces("Facility", int(host.dbid))):
            continue                                        # sits on its own pad
        if _self_contained({x.ftype for x in db.aircraft_spaces("Facility", int(host.dbid))}):
            continue                                        # a single-unit airfield
        if not s.runways and not (prof.rotary and s.pads):
            out.append((u, s, f"{s.name} has no runway"))
        elif not s.grouped:
            out.append((u, s, f"the parts of {s.name} are not one CMO group, so it cannot use the runway"))
        elif not s.can_taxi(rank):
            out.append((u, s, f"{s.name} has no runway access point or taxiway" + (
                " large enough" if s.transit_rank else "") + ", so it cannot taxi to the runway"))
        elif not prof.rotary and s.runways and 2001 < db.aircraft_runway_code(int(u.dbid)) <= 2009 and \
                s.runway_code and s.runway_code < db.aircraft_runway_code(int(u.dbid)):
            out.append((u, s, f"the longest runway at {s.name} is too short for it"))
    return out


# ---------------------------------------------------------------- repair
def repair(p: Project, db, which: Optional[list[Site]] = None) -> list[str]:
    """Give each broken base runway access points (and group it). Returns what was done. Does not touch undo."""
    done = []
    for s in (which if which is not None else broken_sites(p, db)):
        lead = (p.unit(s.formation.lead) if s.formation else None) or s.parking[0]
        done_here = []
        if not s.can_taxi(s.park_rank):
            dbid, dbname = ACCESS_POINTS[max(1, s.park_rank)]
            entry = db.get("Facility", dbid)
            if entry is None or entry.name != dbname:
                found = [e for e in db.search("Facility", dbname) if e.name == dbname]
                if not found:
                    done.append(f"{s.name}: '{dbname}' is not in this database.")
                    continue
                dbid = found[0].id

            def xy(u: Unit) -> tuple[float, float]:
                d = distance_km(lead.lat, lead.lon, u.lat, u.lon) * 1000.0
                b = math.radians(bearing_deg(lead.lat, lead.lon, u.lat, u.lon)) if d > 0.5 else 0.0
                return d * math.sin(b), d * math.cos(b)
            rws = [(*xy(r), float(r.heading or 0.0), runway_length(r.db_name)) for r in s.runways]
            pts = access_positions(rws, [xy(x) for x in s.parking])
            new = []
            for k, (x, y) in enumerate(pts, 1):
                lat, lon = destination(lead.lat, lead.lon, math.degrees(math.atan2(x, y)) % 360.0,
                                       math.hypot(x, y) / 1000.0)
                new.append(Unit(side=s.side, type="Facility", dbid=dbid, db_name=dbname, lat=round(lat, 6),
                                lon=round(lon, 6), group=lead.group or s.name,
                                name=p.unique_unit_name(f"{lead.group or s.name} {LABEL} {k}", s.side)))
                p.units.append(new[-1])
            s.units = s.units + new
            if s.formation is not None:
                f = s.formation
                stations = f.params.get("stations") if isinstance(f.params, dict) else None
                for u in new:
                    f.members.append(u.id)
                    if isinstance(stations, list):
                        x, y = xy(u)
                        brg = (math.degrees(math.atan2(x, y)) - float(f.heading or 0.0)) % 360.0
                        stations.append([round(brg, 2), round(math.hypot(x, y) / 1852.0, 5)])
            done_here.append(f"{len(new)} runway access points")
        if s.formation is not None and not s.formation.group_in_cmo:
            s.formation.group_in_cmo = True
            done_here.append("grouped in CMO")
        elif s.formation is None and len(s.units) > 1:
            from .templates import unique_formation_name
            f = Formation(name=unique_formation_name(p, s.name), side=s.side, preset="custom", lead=lead.id,
                          members=[u.id for u in s.units if u.id != lead.id], spacing_nm=1.0, heading=0.0,
                          keep_on_station=True, group_in_cmo=True, set_stations=False, set_heading=False,
                          station_type="Fixed", notes="Grouped so aircraft can use the runway.")
            f.params = {"stations": [[round(bearing_deg(lead.lat, lead.lon, u.lat, u.lon), 2),
                                      round(distance_km(lead.lat, lead.lon, u.lat, u.lon) / 1.852, 5)]
                                     for u in s.units if u.id != lead.id]}
            p.formations.append(f)
            done_here.append("grouped in CMO")
        if done_here:
            done.append(f"{s.name}: " + ", ".join(done_here))
    return done


# ---------------------------------------------------------------- templates
def template_access_component(tpl, spaces_of, length_of=None):
    """The access-point component a template needs, or None. ``spaces_of(component)`` gives its aircraft spaces."""
    from .templates import TemplateComponent
    runways, parking, park_rank, transit_rank = [], [], 0, 0
    for c in tpl.components:
        spaces = spaces_of(c)
        types = {s.ftype for s in spaces}
        if _self_contained(types):
            return None
        park_rank = max([park_rank] + [size_rank(s.size) for s in spaces if s.ftype in PARKING])
        transit_rank = max([transit_rank] + [size_rank(s.size) for s in spaces if s.ftype in TRANSIT])
        if types & set(RUNWAYS):
            runways += [(x, y, c.hdg, c.length or runway_length(c.db_name, 900.0)) for x, y in c.positions]
        if types & set(PARKING):
            parking += [(x, y) for x, y in c.positions]
    if not runways or not parking or transit_rank >= park_rank:
        return None
    dbid, name = ACCESS_POINTS[max(1, park_rank)]
    return TemplateComponent(label=LABEL, db_type="Facility", db_name=name, dbid=dbid,
                             positions=[list(x) for x in access_positions(runways, parking)])


def add_missing_access(lib, builtin) -> int:
    """Bring a user's saved library up to date: built-in templates saved before access points were added get them."""
    n = 0
    for t in lib.templates:
        b = builtin.template(t.id)
        if b is None or any(LABEL in c.db_name or "Taxiway" in c.db_name for c in t.components):
            continue
        extra = [c for c in b.components if c.label == LABEL]
        if extra:
            import copy
            t.components += copy.deepcopy(extra)
            n += 1
    return n


__all__ = ["Site", "sites", "site_of", "broken_sites", "cannot_fly", "repair", "access_positions",
           "template_access_component", "add_missing_access", "ACCESS_POINTS", "LABEL"]
