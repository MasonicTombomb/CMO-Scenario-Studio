"""Unit templates: pre-grouped sites (airfields, command posts, barracks...) placed in one go.

The library is a standalone JSON file. The studio ships ``cmo_studio/data/templates.json`` plus optional packs
(``templates_*.json``, e.g. the UK real-world sites); a user copy (written by the Template Library editor or by
hand) replaces them when present, and built-in templates added by later updates are merged into it.

A template may carry a real-world ``location`` and ``heading``: its components are then laid out exactly as the
real site (x east, y north when the heading is 0) and the placer puts it there by default.

A template is a list of components, each naming a database entry and one or more positions in metres
(x to the right of the site's orientation, y ahead of it). Placing a template creates the units and a
formation that groups them (a CMO group in the build) and keeps them together when the site is moved
or rotated on the map.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

from ..geo import bearing_deg, destination, distance_km
from .project import Formation, Project, Unit

FORMAT_ID = "cmo-studio-templates"


@dataclass
class TemplateComponent:
    label: str
    db_type: str = "Facility"
    db_name: str = ""
    dbid: int = 0                       # hint: used when it still matches db_name
    search: str = ""                    # fallback search words
    positions: list[list[float]] = field(default_factory=lambda: [[0.0, 0.0]])
    host: bool = False
    radar: bool = False
    hold: bool = False
    hdg: float = 0.0                    # heading relative to the site orientation (e.g. a crossing runway)
    length: float = 0.0                 # real length in metres (runways; preview and docs only)

    def to_dict(self) -> dict:
        db = {"type": self.db_type, "name": self.db_name}
        if self.dbid:
            db["dbid"] = int(self.dbid)
        if self.search:
            db["search"] = self.search
        d: dict = {"label": self.label, "db": db}
        if len(self.positions) == 1:
            d["x"], d["y"] = self.positions[0]
        else:
            d["at"] = [list(p) for p in self.positions]
        if self.hdg:
            d["hdg"] = round(float(self.hdg) % 360.0, 1)
        if self.length:
            d["length"] = round(float(self.length))
        for flag in ("host", "radar", "hold"):
            if getattr(self, flag):
                d[flag] = True
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateComponent":
        db = d.get("db", {})
        at = d.get("at") or [[d.get("x", 0.0), d.get("y", 0.0)]]
        return cls(label=str(d.get("label", "Unit")), db_type=str(db.get("type", "Facility")),
                   db_name=str(db.get("name", "")), dbid=int(db.get("dbid") or 0), search=str(db.get("search", "")),
                   positions=[[float(p[0]), float(p[1])] for p in at],
                   host=bool(d.get("host")), radar=bool(d.get("radar")), hold=bool(d.get("hold")),
                   hdg=float(d.get("hdg") or 0.0), length=float(d.get("length") or 0.0))


@dataclass
class UnitTemplate:
    id: str
    name: str
    category: str = "Custom"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    components: list[TemplateComponent] = field(default_factory=list)
    location: Optional[list[float]] = None      # [lat, lon] of a real-world site
    heading: float = 0.0                        # orientation the layout is drawn in at that location
    site: str = ""                              # default site name used to name the units

    @property
    def unit_count(self) -> int:
        return sum(len(c.positions) for c in self.components)

    def to_dict(self) -> dict:
        d = {"id": self.id, "name": self.name, "category": self.category, "description": self.description,
             "tags": list(self.tags)}
        if self.location:
            d["location"] = [round(float(self.location[0]), 6), round(float(self.location[1]), 6)]
            d["heading"] = round(float(self.heading), 1)
        if self.site:
            d["site"] = self.site
        d["components"] = [c.to_dict() for c in self.components]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "UnitTemplate":
        loc = d.get("location")
        return cls(id=str(d.get("id") or d.get("name", "template")), name=str(d.get("name", "Template")),
                   category=str(d.get("category", "Custom")), description=str(d.get("description", "")),
                   tags=[str(t) for t in d.get("tags", [])],
                   components=[TemplateComponent.from_dict(c) for c in d.get("components", [])],
                   location=[float(loc[0]), float(loc[1])] if loc else None,
                   heading=float(d.get("heading") or 0.0), site=str(d.get("site", "")))


@dataclass
class TemplateLibrary:
    templates: list[UnitTemplate]
    categories: list[str] = field(default_factory=list)
    about: str = ""
    known_builtins: list[str] = field(default_factory=list)   # built-in ids this file has already seen

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateLibrary":
        if d.get("format") not in (None, FORMAT_ID):
            raise ValueError(f"Not a template library (format={d.get('format')!r})")
        return cls(templates=[UnitTemplate.from_dict(t) for t in d.get("templates", [])],
                   categories=[str(c) for c in d.get("categories", [])], about=str(d.get("about", "")),
                   known_builtins=[str(i) for i in d.get("known_builtins", [])])

    def to_dict(self) -> dict:
        d = {"format": FORMAT_ID, "version": 1, "about": self.about, "categories": self.all_categories(),
             "templates": [t.to_dict() for t in self.templates]}
        if self.known_builtins:
            d["known_builtins"] = list(self.known_builtins)
        return d

    def all_categories(self) -> list[str]:
        cats = list(self.categories)
        for t in self.templates:
            if t.category not in cats:
                cats.append(t.category)
        return cats

    def template(self, tid: str) -> Optional[UnitTemplate]:
        return next((t for t in self.templates if t.id == tid), None)

    def unique_id(self, base: str) -> str:
        base = "".join(ch if ch.isalnum() else "_" for ch in base.lower()).strip("_") or "template"
        ids = {t.id for t in self.templates}
        if base not in ids:
            return base
        i = 2
        while f"{base}_{i}" in ids:
            i += 1
        return f"{base}_{i}"

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: str | Path) -> "TemplateLibrary":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def clone(self) -> "TemplateLibrary":
        return copy.deepcopy(self)


def default_library_text() -> str:
    return resources.files("cmo_studio").joinpath("data", "templates.json").read_text(encoding="utf-8")


def pack_texts() -> list[tuple[str, str]]:
    """(file name, text) of the bundled template packs, ``data/templates_*.json``, in name order."""
    data = resources.files("cmo_studio").joinpath("data")
    files = sorted((f for f in data.iterdir() if f.name.startswith("templates_") and f.name.endswith(".json")),
                   key=lambda f: f.name)
    return [(f.name, f.read_text(encoding="utf-8")) for f in files]


def default_library() -> TemplateLibrary:
    lib = TemplateLibrary.from_dict(json.loads(default_library_text()))
    for _name, text in pack_texts():
        pack = TemplateLibrary.from_dict(json.loads(text))
        ids = {t.id for t in lib.templates}
        lib.templates += [t for t in pack.templates if t.id not in ids]
        lib.categories += [c for c in pack.all_categories() if c not in lib.categories]
    return lib


def merge_new_builtins(lib: TemplateLibrary, builtin: TemplateLibrary) -> int:
    """Add built-in templates the user's library has never seen (new in an update); returns how many."""
    seen = set(lib.known_builtins)
    have = {t.id for t in lib.templates}
    new = [t for t in builtin.templates if t.id not in seen and t.id not in have]
    lib.templates += copy.deepcopy(new)
    lib.categories += [c for c in builtin.all_categories() if c not in lib.categories and
                       any(t.category == c for t in new)]
    lib.known_builtins = [t.id for t in builtin.templates]
    return len(new)


def load_library(user_path: Optional[str | Path] = None) -> tuple[TemplateLibrary, str]:
    builtin = default_library()
    if user_path and Path(user_path).is_file():
        try:
            lib = TemplateLibrary.load(user_path)
        except (ValueError, OSError, KeyError, TypeError, IndexError):
            pass
        else:
            merge_new_builtins(lib, builtin)
            from .airbase import add_missing_access
            add_missing_access(lib, builtin)      # saved before 1.11: aircraft could not taxi at these bases
            return lib, str(user_path)
    builtin.known_builtins = [t.id for t in builtin.templates]
    return builtin, "built-in default"


# =============================================================================== database resolution
@dataclass
class Resolved:
    dbid: int
    name: str
    how: str          # 'dbid' | 'name' | 'search' | 'unchecked'


def resolve(db, comp: TemplateComponent) -> Optional[Resolved]:
    """Find the component's database entry: the DBID hint if its name still matches, else the exact name
    (preferring a generic, non-deprecated entry), else the search words. Without a database the hint is
    trusted as is."""
    if db is None:
        return Resolved(comp.dbid, comp.db_name, "unchecked") if comp.dbid else None
    if comp.dbid:
        e = db.get(comp.db_type, comp.dbid)
        if e is not None and e.name.lower() == comp.db_name.lower() and not e.deprecated:
            return Resolved(e.id, e.name, "dbid")
    if comp.db_name:
        hits = [e for e in db.search(comp.db_type, comp.db_name, include_deprecated=False, limit=200)
                if e.name.lower() == comp.db_name.lower()]
        if hits:
            hits.sort(key=lambda e: (e.country != "Generic", e.id))
            return Resolved(hits[0].id, hits[0].name, "name")
    if comp.search:
        hits = db.search(comp.db_type, comp.search, include_deprecated=False, limit=50)
        if hits:
            hits.sort(key=lambda e: (e.country != "Generic", len(e.name)))
            return Resolved(hits[0].id, hits[0].name, "search")
    return None


# =============================================================================== placement
def offset_latlon(lat: float, lon: float, heading: float, x: float, y: float) -> tuple[float, float]:
    dist_m = math.hypot(x, y)
    if dist_m < 1e-6:
        return lat, lon
    brg = (heading + math.degrees(math.atan2(x, y))) % 360.0
    return destination(lat, lon, brg, dist_m / 1000.0)


@dataclass
class PlaceResult:
    units: list[Unit]
    formation: Optional[Formation]
    skipped: list[str]


def unique_formation_name(project: Project, base: str) -> str:
    names = {f.name for f in project.formations}
    if base not in names:
        return base
    i = 2
    while f"{base} {i}" in names:
        i += 1
    return f"{base} {i}"


def place_template(project: Project, tpl: UnitTemplate, db, side: str, lat: float, lon: float,
                   heading: float = 0.0, site_name: str = "", group: bool = True) -> PlaceResult:
    """Create the template's units (and a grouping formation) in ``project``. Does not touch undo."""
    site = (site_name or tpl.site or tpl.name).strip()
    units: list[Unit] = []
    offsets: list[tuple[float, float]] = []
    hosts: list[bool] = []
    skipped: list[str] = []
    taken = {u.name for u in project.units if u.side == side}
    for comp in tpl.components:
        res = resolve(db, comp)
        if res is None:
            skipped.append(f"{comp.label} ({comp.db_name or comp.search})")
            continue
        many = len(comp.positions) > 1
        for i, (x, y) in enumerate(comp.positions, 1):
            plat, plon = offset_latlon(lat, lon, heading, x, y)
            name = base = f"{site} {comp.label}" + (f" {i}" if many else "")
            k = 2
            while name in taken:
                name, k = f"{base} ({k})", k + 1
            taken.add(name)
            u = Unit(side=side, type=comp.db_type, dbid=res.dbid, db_name=res.name, name=name,
                     lat=round(plat, 6), lon=round(plon, 6),
                     radar_active=comp.radar, hold_position=comp.hold, group=site)
            u.heading = float(heading + comp.hdg) % 360.0
            units.append(u)
            offsets.append((x, y))
            hosts.append(comp.host)
    project.units.extend(units)
    formation = None
    if group and len(units) > 1:
        lead_i = hosts.index(True) if True in hosts else 0     # the airfield / host unit leads the group
        lx, ly = offsets[lead_i]
        stations = []
        members = []
        for i, u in enumerate(units):
            if i == lead_i:
                continue
            dx, dy = offsets[i][0] - lx, offsets[i][1] - ly
            stations.append([round((math.degrees(math.atan2(dx, dy)) + 360) % 360, 2),
                             round(math.hypot(dx, dy) / 1852.0, 5)])
            members.append(u.id)
        formation = Formation(name=unique_formation_name(project, site), side=side, preset="custom",
                              lead=units[lead_i].id, members=members, spacing_nm=1.0, heading=float(heading) % 360,
                              params={"stations": stations}, keep_on_station=True, group_in_cmo=True,
                              set_stations=False, set_heading=True, station_type="Fixed",
                              notes=f"Placed from template '{tpl.name}'.")
        project.formations.append(formation)
    return PlaceResult(units, formation, skipped)


def template_radius_m(tpl: UnitTemplate) -> float:
    """How far the template's furthest unit lies from its centre, in metres."""
    return max((math.hypot(x, y) for c in tpl.components for x, y in c.positions), default=0.0)


def place_templates(project: Project, tpls: list[UnitTemplate], db, side: str, lat: float, lon: float,
                    heading: float = 0.0, real_sites: bool = True, group: bool = True,
                    gap_m: float = 1000.0) -> list[tuple[UnitTemplate, PlaceResult]]:
    """Place several templates in one go. With ``real_sites``, real-world templates go to their own position and
    orientation; every other template goes in a row running east from (lat, lon), spaced so they do not overlap.
    Each keeps its own site name. Does not touch undo."""
    out = []
    here: Optional[tuple[float, float]] = None
    prev_r = 0.0
    for t in tpls:
        if real_sites and t.location:
            res = place_template(project, t, db, side, t.location[0], t.location[1], heading=t.heading, group=group)
        else:
            r = template_radius_m(t)
            here = (lat, lon) if here is None else destination(here[0], here[1], 90.0, (prev_r + r + gap_m) / 1000.0)
            prev_r = r
            res = place_template(project, t, db, side, here[0], here[1], heading=heading, group=group)
        out.append((t, res))
    return out


def template_from_units(project: Project, unit_ids: list[str], name: str, category: str = "Custom",
                        description: str = "", lib: Optional[TemplateLibrary] = None) -> UnitTemplate:
    """A template from existing units: positions relative to the first unit, oriented to its heading."""
    units = [project.unit(i) for i in unit_ids if project.unit(i) and not project.unit(i).host]
    if not units:
        raise ValueError("No placeable units selected (units at a base cannot be part of a template).")
    origin = units[0]
    heading = float(origin.heading or 0.0)
    comps: dict[tuple, TemplateComponent] = {}
    for u in units:
        d_m = distance_km(origin.lat, origin.lon, u.lat, u.lon) * 1000.0
        brg = bearing_deg(origin.lat, origin.lon, u.lat, u.lon) if d_m > 0.01 else 0.0
        rel = math.radians(brg - heading)
        x, y = round(d_m * math.sin(rel), 1), round(d_m * math.cos(rel), 1)
        label = u.name
        if u.group and label.startswith(u.group + " "):
            label = label[len(u.group) + 1:]
        rel_hdg = round((float(u.heading or 0.0) - heading) % 360.0, 1)
        rel_hdg = 0.0 if rel_hdg in (0.0, 360.0) else rel_hdg
        key = (u.type, int(u.dbid), label, u.radar_active, u.hold_position, rel_hdg)
        if key in comps:
            comps[key].positions.append([x, y])
        else:
            comps[key] = TemplateComponent(label=label, db_type=u.type, db_name=u.db_name, dbid=int(u.dbid),
                                           positions=[[x, y]], radar=u.radar_active, hold=u.hold_position,
                                           host=bool(project.hosted_by(u.id)), hdg=rel_hdg)
    tid = lib.unique_id(name) if lib else name.lower().replace(" ", "_")
    return UnitTemplate(id=tid, name=name, category=category or "Custom",
                        description=description or f"Saved from {len(units)} unit(s).", components=list(comps.values()))
