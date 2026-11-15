"""Predefined patrol areas: well-known sea and air operating areas grouped by region of the globe.

The library is a standalone JSON file. The studio ships ``cmo_studio/data/areas.json``; a user copy (written by
the Area Library editor, by "Save to area library" or by hand) replaces it when present.

Each area is a polygon of [lat, lon] corners with a kind ('sea' or 'air'), a region (Europe, Asia...) and a
sub-region. Adding one to a scenario creates an ordinary area (reference-point zone) and, optionally, a patrol
or support mission that uses it.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

from ..geo import distance_km
from .project import Mission, Project, Zone

FORMAT_ID = "cmo-studio-areas"
KINDS = ("sea", "air")
KIND_LABELS = {"sea": "Sea", "air": "Air"}
DEFAULT_REGIONS = ["Europe", "United Kingdom", "Arctic", "Middle East", "Africa", "Asia", "Oceania", "North America",
                   "South America"]
#: map colours used for library areas (sea / air)
KIND_COLORS = {"sea": "#3fa7ff", "air": "#ffb347"}


@dataclass
class AreaEntry:
    id: str
    name: str
    region: str = "Europe"
    kind: str = "sea"                   # 'sea' | 'air'
    subregion: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    points: list[list[float]] = field(default_factory=list)   # [[lat, lon], ...]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "region": self.region, "kind": self.kind,
                "subregion": self.subregion, "description": self.description, "tags": list(self.tags),
                "points": [[round(float(a), 5), round(float(b), 5)] for a, b in self.points]}

    @classmethod
    def from_dict(cls, d: dict) -> "AreaEntry":
        kind = str(d.get("kind", "sea")).lower()
        return cls(id=str(d.get("id") or d.get("name", "area")), name=str(d.get("name", "Area")),
                   region=str(d.get("region", "Europe")), kind=kind if kind in KINDS else "sea",
                   subregion=str(d.get("subregion", "")), description=str(d.get("description", "")),
                   tags=[str(t) for t in d.get("tags", [])],
                   points=[[float(p[0]), float(p[1])] for p in d.get("points", [])])

    # ------------------------------------------------------------------ geometry
    def centre(self) -> tuple[float, float]:
        if not self.points:
            return 0.0, 0.0
        return (sum(p[0] for p in self.points) / len(self.points),
                sum(p[1] for p in self.points) / len(self.points))

    def extent_nm(self) -> tuple[float, float]:
        """Approximate (east-west, north-south) size in nautical miles."""
        if len(self.points) < 2:
            return 0.0, 0.0
        lats = [p[0] for p in self.points]
        lons = [p[1] for p in self.points]
        mid = (max(lats) + min(lats)) / 2
        ew = distance_km(mid, min(lons), mid, max(lons)) / 1.852
        ns = distance_km(min(lats), 0.0, max(lats), 0.0) / 1.852
        return ew, ns

    def search_text(self) -> str:
        return f"{self.name} {self.id} {self.region} {self.kind} {self.subregion} {self.description} " \
               f"{' '.join(self.tags)}".lower()


@dataclass
class AreaLibrary:
    areas: list[AreaEntry]
    regions: list[str] = field(default_factory=lambda: list(DEFAULT_REGIONS))
    about: str = ""
    known_builtins: list[str] = field(default_factory=list)   # built-in ids this file has already seen

    @classmethod
    def from_dict(cls, d: dict) -> "AreaLibrary":
        if d.get("format") not in (None, FORMAT_ID):
            raise ValueError(f"Not an area library (format={d.get('format')!r})")
        return cls(areas=[AreaEntry.from_dict(a) for a in d.get("areas", [])],
                   regions=[str(r) for r in d.get("regions", DEFAULT_REGIONS)], about=str(d.get("about", "")),
                   known_builtins=[str(i) for i in d.get("known_builtins", [])])

    def to_dict(self) -> dict:
        d = {"format": FORMAT_ID, "version": 1, "about": self.about, "regions": self.all_regions(),
             "areas": [a.to_dict() for a in self.areas]}
        if self.known_builtins:
            d["known_builtins"] = list(self.known_builtins)
        return d

    def all_regions(self) -> list[str]:
        regs = list(self.regions)
        for a in self.areas:
            if a.region not in regs:
                regs.append(a.region)
        return regs

    def area(self, aid: str) -> Optional[AreaEntry]:
        return next((a for a in self.areas if a.id == aid), None)

    def filtered(self, text: str = "", region: str = "", kind: str = "") -> list[AreaEntry]:
        words = text.lower().split()
        return [a for a in self.areas if (not region or a.region == region) and (not kind or a.kind == kind)
                and all(w in a.search_text() for w in words)]

    def unique_id(self, base: str) -> str:
        base = "".join(ch if ch.isalnum() else "_" for ch in base.lower()).strip("_") or "area"
        base = re.sub(r"_+", "_", base)
        ids = {a.id for a in self.areas}
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
    def load(cls, path: str | Path) -> "AreaLibrary":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def clone(self) -> "AreaLibrary":
        return copy.deepcopy(self)


def default_library_text() -> str:
    return resources.files("cmo_studio").joinpath("data", "areas.json").read_text(encoding="utf-8")


def default_library() -> AreaLibrary:
    return AreaLibrary.from_dict(json.loads(default_library_text()))


def merge_new_builtins(lib: AreaLibrary, builtin: AreaLibrary) -> int:
    """Add built-in areas the user's library has never seen (new in an update); returns how many."""
    seen = set(lib.known_builtins)
    have = {a.id for a in lib.areas}
    new = [a for a in builtin.areas if a.id not in seen and a.id not in have]
    lib.areas += copy.deepcopy(new)
    for r in builtin.all_regions():
        if r not in lib.regions and any(a.region == r for a in new):
            lib.regions.insert(min(builtin.all_regions().index(r), len(lib.regions)), r)
    lib.known_builtins = [a.id for a in builtin.areas]
    return len(new)


def load_library(user_path: Optional[str | Path] = None) -> tuple[AreaLibrary, str]:
    builtin = default_library()
    if user_path and Path(user_path).is_file():
        try:
            lib = AreaLibrary.load(user_path)
        except (ValueError, OSError, KeyError, TypeError, IndexError):
            pass
        else:
            merge_new_builtins(lib, builtin)
            return lib, str(user_path)
    builtin.known_builtins = [a.id for a in builtin.areas]
    return builtin, "built-in default"


# =============================================================================== into the scenario
def zone_name(text: str) -> str:
    """'Bay of Biscay' -> 'BAY_OF_BISCAY' (reference points become BAY_OF_BISCAY-1...)."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()
    return s or "AREA"


def unique_zone_name(project: Project, base: str) -> str:
    names = {z.name for z in project.zones}
    if base not in names:
        return base
    i = 2
    while f"{base}_{i}" in names:
        i += 1
    return f"{base}_{i}"


def suggested_mission(entry: AreaEntry) -> tuple[str, str]:
    """(mission class, patrol subtype) that suits the area: AEW orbits and tanker tracks are support missions,
    air areas AAW patrols (land patrols for strike/ISR boxes), sea areas ASW or naval (ASuW) patrols."""
    tags = [t.lower() for t in entry.tags]
    if entry.kind == "air":
        if any(t in tags for t in ("aew", "tanker", "aar", "orbit")):
            return "support", ""
        if ("strike" in tags or "isr" in tags) and "cap" not in tags:
            return "patrol", "land"
        return "patrol", "aaw"
    if "asw" in tags and ("asuw" not in tags or tags.index("asw") < tags.index("asuw")):
        return "patrol", "asw"
    return "patrol", "naval"


def mission_label(mclass: str, subtype: str) -> str:
    if mclass == "support":
        return "Support"
    return {"aaw": "CAP", "asw": "ASW Patrol", "naval": "ASuW Patrol", "land": "Land Patrol", "mixed": "Patrol",
            "sead": "SEAD Patrol"}.get(subtype, "Patrol")


@dataclass
class AddResult:
    zone: Zone
    mission: Optional[Mission]


def add_area(project: Project, entry: AreaEntry, side: str, name: str = "", all_sides: bool = False,
             mission: Optional[tuple[str, str]] = None, color: str = "") -> AddResult:
    """Add the library area to ``project`` as a zone and optionally a mission ``(class, subtype)`` on it.
    Does not touch undo."""
    zname = unique_zone_name(project, zone_name(name or entry.id))
    notes = f"From the area library: {entry.name} ({entry.region}, {KIND_LABELS.get(entry.kind, entry.kind)})."
    if entry.description:
        notes += f"\n{entry.description}"
    z = Zone(side=side, name=zname, points=[[float(a), float(b)] for a, b in entry.points], color=color,
             all_sides=all_sides, notes=notes)
    project.zones.append(z)
    m = None
    if mission:
        mclass, subtype = mission
        base = f"{entry.name} {mission_label(mclass, subtype)}"
        names = {x.name for x in project.missions if x.side == side}
        mname, i = base, 2
        while mname in names:
            mname, i = f"{base} {i}", i + 1
        m = Mission(side=side, name=mname, mclass=mclass, subtype=subtype if mclass == "patrol" else "",
                    zone=z.id, notes=f"Created with area {zname} from the area library.")
        project.missions.append(m)
    return AddResult(z, m)


def area_from_zone(zone: Zone, lib: Optional[AreaLibrary] = None, name: str = "", region: str = "Europe",
                   kind: str = "sea", subregion: str = "", description: str = "",
                   tags: Optional[list[str]] = None) -> AreaEntry:
    """A library entry from an area in the scenario."""
    if len(zone.points) < 3:
        raise ValueError("An area needs at least three corners to be saved to the library.")
    label = name or zone.name.replace("_", " ").title()
    aid = lib.unique_id(label) if lib else zone_name(label).lower()
    return AreaEntry(id=aid, name=label, region=region, kind=kind if kind in KINDS else "sea", subregion=subregion,
                     description=description or (zone.notes.splitlines()[0] if zone.notes else ""),
                     tags=list(tags or []), points=[[float(a), float(b)] for a, b in zone.points])
