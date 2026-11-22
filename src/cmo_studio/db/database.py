"""Read-only access to CMO's DB3000 / CWDB SQLite databases (``[CMO]\\DB\\*.db3``).

The database is opened with ``mode=ro`` so the studio can never change it, even
while CMO itself is running. Only the columns needed by the studio are queried;
the schema is the one CMO has shipped since DB3K_456 (tables ``DataAircraft``,
``DataShip``... plus their ``Enum*`` lookup tables).
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from ..model.enums import UNIT_TABLES

# Category / type lookup tables per unit type: (category column, enum table), (type column, enum table)
_ENUMS = {
    "Aircraft": (("Category", "EnumAircraftCategory"), ("Type", "EnumAircraftType")),
    "Ship": (("Category", "EnumShipCategory"), ("Type", "EnumShipType")),
    "Submarine": (("Category", "EnumSubmarineCategory"), ("Type", "EnumSubmarineType")),
    "Facility": (("Category", "EnumFacilityCategory"), ("Type", "EnumFacilityType")),
    "GroundUnit": (("Category", "EnumGroundUnitCategory"), None),
    "Satellite": (("Category", "EnumSatelliteCategory"), ("Type", "EnumSatelliteType")),
    "Weapon": (None, ("Type", "EnumWeaponType")),
    "Sensor": (("Role", "EnumSensorRole"), ("Type", "EnumSensorType")),
}

BROWSABLE = tuple(UNIT_TABLES) + ("Weapon", "Sensor")
TABLES = dict(UNIT_TABLES, Weapon="DataWeapon", Sensor="DataSensor")

#: File-name prefix of images and descriptions per browsable type.
MEDIA_PREFIX = {
    "Aircraft": "Aircraft", "Ship": "Ship", "Submarine": "Submarine", "Facility": "Facility",
    "GroundUnit": "GroundUnit", "Satellite": "Satellite", "Weapon": "Weapon", "Sensor": "Sensor",
}

RESERVE_LOADOUT = 3
_NON_COMBAT_ROLES = (9001, 9002, 9003, 9005)   # ferry, unavailable, reserve, packed for cargo


@dataclass
class DBEntry:
    type: str
    id: int
    name: str
    country: str = ""
    category: str = ""
    subtype: str = ""
    year: int = 0
    year_end: int = 0
    deprecated: bool = False
    hypothetical: bool = False

    def in_service(self, year: int) -> bool:
        if self.year and self.year > year:
            return False
        if self.year_end and self.year_end < year:
            return False
        return True


@dataclass
class Loadout:
    id: int
    name: str
    role: str
    role_id: int
    deprecated: bool = False
    radius: int = 0
    time_on_station: int = 0


@dataclass
class DBDetails:
    entry: DBEntry
    service: str = ""
    comments: str = ""
    stats: list[tuple[str, str]] = field(default_factory=list)
    sensors: list[str] = field(default_factory=list)
    weapons: list[str] = field(default_factory=list)
    loadouts: list[Loadout] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)      # aircraft facilities / docking
    codes: list[str] = field(default_factory=list)


def find_databases(cmo_dir: str | os.PathLike) -> list[Path]:
    """All ``*.db3`` files in ``[CMO]\\DB``, newest DB3000 first, then CWDB."""
    db_dir = Path(cmo_dir) / "DB"
    if not db_dir.is_dir():
        return []

    def key(p: Path):
        m = re.match(r"(DB3K|CWDB|WW2DB?)_(\d+)([a-z]?)", p.stem, re.I)
        family = {"DB3K": 0, "CWDB": 1}.get(m.group(1).upper(), 2) if m else 3
        num = int(m.group(2)) if m else 0
        return family, -num, p.stem.lower()

    return sorted((p for p in db_dir.glob("*.db3") if p.is_file()), key=key)


def latest_database(cmo_dir: str | os.PathLike) -> Optional[Path]:
    dbs = [p for p in find_databases(cmo_dir) if p.stem.upper().startswith("DB3K")]
    return dbs[0] if dbs else None


class Database:
    """A single opened DB3000/CWDB file. Thread-safe for reads (one connection per thread)."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        self._local = threading.local()
        self._enum_cache: dict[str, dict[int, str]] = {}
        # Probe it now so a broken file fails here, not later in the UI.
        tables = {r[0] for r in self._q("select name from sqlite_master where type='table'")}
        if "DataAircraft" not in tables:
            raise ValueError(f"{self.path.name} is not a CMO database")
        self.tables = tables

    # ------------------------------------------------------------------ plumbing
    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            uri = "file:" + self.path.as_posix() + "?mode=ro"
            c = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._local.conn = c
        return c

    def _q(self, sql: str, args: Iterable = ()) -> list[tuple]:
        return self.conn.execute(sql, tuple(args)).fetchall()

    def close(self) -> None:
        c = getattr(self._local, "conn", None)
        if c is not None:
            c.close()
            self._local.conn = None

    @property
    def family(self) -> str:
        """'DB3000' or 'CWDB' - the sub-folder name used for images and descriptions."""
        return "CWDB" if self.path.stem.upper().startswith("CWDB") else "DB3000"

    def enum(self, table: str) -> dict[int, str]:
        if table not in self._enum_cache:
            if table in self.tables:
                self._enum_cache[table] = {r[0]: r[1] for r in self._q(f"select ID, Description from {table}")}
            else:
                self._enum_cache[table] = {}
        return self._enum_cache[table]

    def countries(self) -> list[str]:
        return sorted(set(self.enum("EnumOperatorCountry").values()))

    # ------------------------------------------------------------------ search
    def search(self, utype: str, text: str = "", country: str = "", year: Optional[int] = None,
               include_deprecated: bool = False, limit: int = 2000,
               exact_id: Optional[int] = None) -> list[DBEntry]:
        """Search one table by name (all words must match) and/or id."""
        table = TABLES[utype]
        cat, typ = _ENUMS.get(utype, (None, None))
        cols = ["ID", "Name"]
        has_country = utype not in ("Weapon", "Sensor")
        cols += ["OperatorCountry", "YearCommissioned", "YearDecommissioned"] if has_country else []
        cols += [cat[0] if cat else "NULL", typ[0] if typ else "NULL", "Deprecated", "Hypothetical"]
        where, args = [], []
        text = (text or "").strip()
        if exact_id is not None:
            where.append("ID = ?")
            args.append(int(exact_id))
        elif text.isdigit():
            where.append("(ID = ? OR Name LIKE ?)")
            args += [int(text), f"%{text}%"]
        else:
            for word in text.split():
                where.append("Name LIKE ?")
                args.append(f"%{word}%")
        if not include_deprecated:
            where.append("(Deprecated = 0 OR Deprecated IS NULL)")
        if country and has_country:
            ids = [k for k, v in self.enum("EnumOperatorCountry").items() if v == country]
            if ids:
                where.append(f"OperatorCountry IN ({','.join('?' * len(ids))})")
                args += ids
        if year and has_country:
            where.append("(YearCommissioned <= ? OR YearCommissioned = 0 OR YearCommissioned IS NULL)")
            where.append("(YearDecommissioned >= ? OR YearDecommissioned = 0 OR YearDecommissioned IS NULL)")
            args += [year, year]
        sql = f"select {', '.join(cols)} from {table}"
        if where:
            sql += " where " + " and ".join(where)
        sql += f" order by Name limit {int(limit)}"
        countries = self.enum("EnumOperatorCountry")
        cats = self.enum(cat[1]) if cat else {}
        typs = self.enum(typ[1]) if typ else {}
        out = []
        for r in self._q(sql, args):
            if has_country:
                rid, name, ctry, y0, y1, c, t, dep, hyp = r
            else:
                rid, name, c, t, dep, hyp = r
                ctry, y0, y1 = None, 0, 0
            out.append(DBEntry(utype, rid, name or "", countries.get(ctry, "") if ctry is not None else "",
                               cats.get(c, ""), typs.get(t, ""), y0 or 0, y1 or 0, bool(dep), bool(hyp)))
        return out

    def get(self, utype: str, dbid: int) -> Optional[DBEntry]:
        """Look up one record by id (deprecated ones included)."""
        table = TABLES.get(utype)
        if not table:
            return None
        res = self.search(utype, include_deprecated=True, limit=1, exact_id=int(dbid))
        return res[0] if res else None

    def name_of(self, utype: str, dbid: int) -> str:
        table = TABLES.get(utype)
        if not table:
            return ""
        r = self._q(f"select Name from {table} where ID=?", (dbid,))
        return r[0][0] if r else ""

    # ------------------------------------------------------------------ aircraft
    def loadouts(self, aircraft_id: int, include_deprecated: bool = False,
                 combat_only: bool = False) -> list[Loadout]:
        roles = self.enum("EnumLoadoutRole")
        rows = self._q(
            "select l.ID, l.Name, l.LoadoutRole, l.Deprecated, l.DefaultCombatRadius, l.DefaultTimeOnStation "
            "from DataAircraftLoadouts a join DataLoadout l on l.ID = a.ComponentID "
            "where a.ID = ? order by l.LoadoutRole, l.Name", (aircraft_id,))
        out = []
        for lid, name, role, dep, radius, tos in rows:
            if dep and not include_deprecated:
                continue
            if combat_only and role in _NON_COMBAT_ROLES:
                continue
            out.append(Loadout(lid, name or "", roles.get(role, str(role)), role or 0, bool(dep),
                               radius or 0, tos or 0))
        return out

    def loadout_valid(self, aircraft_id: int, loadout_id: int) -> bool:
        return bool(self._q("select 1 from DataAircraftLoadouts where ID=? and ComponentID=?",
                            (aircraft_id, loadout_id)))

    def loadout_name(self, loadout_id: int) -> str:
        r = self._q("select Name from DataLoadout where ID=?", (loadout_id,))
        return r[0][0] if r else ""

    def loadout_weapons(self, loadout_id: int) -> list[str]:
        rows = self._q("select w.Name, sum(r.DefaultLoad) from DataLoadoutWeapons lw "
                       "join DataWeaponRecord r on r.ID = lw.ComponentID join DataWeapon w on w.ID = r.ComponentID "
                       "where lw.ID = ? group by w.Name order by w.Name", (loadout_id,))
        return [f"{n}x {name}" if n and n > 1 else name for name, n in rows]

    def aircraft_spaces(self, utype: str, dbid: int) -> list:
        """The aircraft spaces of a facility, ship, submarine or ground unit (model.hosting.Space)."""
        from ..model.hosting import Space
        table = UNIT_TABLES.get(utype)
        if not table or utype == "Aircraft":
            return []
        try:
            rows = self._q(f"select af.Type, af.PhysicalSize, af.Capacity from {table}AircraftFacilities l "
                           "join DataAircraftFacility af on af.ID = l.ComponentID where l.ID = ?", (dbid,))
        except sqlite3.Error:
            return []
        return [Space(int(t or 0), int(s or 0), int(c or 0)) for t, s, c in rows]

    def runway_code(self, facility_id: int) -> int:
        """Longest runway of a facility as an EnumRunwayLength code (0: none)."""
        try:
            r = self._q("select max(af.RunwayLength) from DataFacilityAircraftFacilities l join DataAircraftFacility af "
                        "on af.ID = l.ComponentID where l.ID = ? and af.Type in (2001, 2002)", (facility_id,))
        except sqlite3.Error:
            return 0
        return int(r[0][0] or 0) if r else 0

    def aircraft_runway_code(self, aircraft_id: int) -> int:
        """The runway an aircraft needs, as an EnumRunwayLength code (0: unknown)."""
        r = self._q("select RunwayLengthCode from DataAircraft where ID=?", (aircraft_id,))
        return int(r[0][0] or 0) if r else 0

    def aircraft_profile(self, aircraft_id: int):
        """Size and rotary-wing flag of an aircraft (model.hosting.Aircraft), or None."""
        from ..model.hosting import ROTARY_CATEGORIES, Aircraft
        r = self._q("select PhysicalSizeCode, Category from DataAircraft where ID=?", (aircraft_id,))
        if not r:
            return None
        return Aircraft(int(r[0][0] or 0), int(r[0][1] or 0) in ROTARY_CATEGORIES)

    def runway_needed(self, aircraft_id: int) -> str:
        r = self._q("select RunwayLengthCode from DataAircraft where ID=?", (aircraft_id,))
        return self.enum("EnumRunwayLength").get(r[0][0], "") if r else ""

    # ------------------------------------------------------------------ details
    def details(self, utype: str, dbid: int) -> Optional[DBDetails]:
        entry = self.get(utype, dbid)
        if entry is None:
            return None
        table = TABLES[utype]
        row = self.conn.execute(f"select * from {table} where ID=?", (dbid,))
        names = [d[0] for d in row.description]
        values = dict(zip(names, row.fetchone()))
        d = DBDetails(entry=entry)
        d.comments = values.get("Comments") or ""
        if "OperatorService" in values:
            d.service = self.enum("EnumOperatorService").get(values.get("OperatorService"), "")
        d.stats = self._stats(utype, values)
        d.sensors = self._components_for(table + "Sensors", "DataSensor", dbid)
        d.weapons = self._weapons(table, dbid)
        if utype == "Aircraft":
            d.loadouts = self.loadouts(dbid)
            codes = self.enum("EnumAircraftCode")
            d.codes = [codes.get(c[0], str(c[0])) for c in self._q("select CodeID from DataAircraftCodes where ID=?",
                                                                    (dbid,))]
        for host_table in (table + "AircraftFacilities", table + "DockingFacilities"):
            if host_table in self.tables:
                comp = "DataAircraftFacility" if "Aircraft" in host_table else "DataDockingFacility"
                d.hosts += self._components_for(host_table, comp, dbid)
        return d

    def _components_for(self, link_table: str, comp_table: str, dbid: int) -> list[str]:
        if link_table not in self.tables or comp_table not in self.tables:
            return []
        cols = {r[1] for r in self._q(f"pragma table_info({comp_table})")}
        name_col = "Name" if "Name" in cols else None
        if name_col is None:
            # DataAircraftFacility / DataDockingFacility have no name: describe by type and size
            if comp_table == "DataAircraftFacility":
                types = self.enum("EnumAircraftFacilityType")
                rows = self._q(f"select c.Type, c.Capacity, count(*) from {link_table} l join {comp_table} c "
                               f"on c.ID = l.ComponentID where l.ID = ? group by c.Type, c.Capacity", (dbid,))
                return [f"{n}x {types.get(t, t)} (capacity {cap})" for t, cap, n in rows]
            if comp_table == "DataDockingFacility":
                types = self.enum("EnumDockingFacilityType")
                rows = self._q(f"select c.Type, c.Capacity, count(*) from {link_table} l join {comp_table} c "
                               f"on c.ID = l.ComponentID where l.ID = ? group by c.Type, c.Capacity", (dbid,))
                return [f"{n}x {types.get(t, t)} (capacity {cap})" for t, cap, n in rows]
            return []
        rows = self._q(f"select c.Name, count(*) from {link_table} l join {comp_table} c on c.ID = l.ComponentID "
                       f"where l.ID = ? group by c.Name order by c.Name", (dbid,))
        return [f"{n}x {name}" if n > 1 else str(name) for name, n in rows]

    def _weapons(self, table: str, dbid: int) -> list[str]:
        """Weapons on the unit's mounts and in its magazines, with default loads."""
        out: dict[str, int] = {}
        for link, inner in ((table + "Mounts", "DataMountWeapons"), (table + "Magazines", "DataMagazineWeapons")):
            if link not in self.tables:
                continue
            for name, n in self._q(f"select w.Name, sum(r.DefaultLoad) from {link} m "
                                   f"join {inner} mw on mw.ID = m.ComponentID "
                                   f"join DataWeaponRecord r on r.ID = mw.ComponentID "
                                   f"join DataWeapon w on w.ID = r.ComponentID where m.ID = ? group by w.Name",
                                   (dbid,)):
                out[name] = out.get(name, 0) + (n or 0)
        return [f"{n}x {name}" if n > 1 else name for name, n in sorted(out.items())]

    def _stats(self, utype: str, v: dict) -> list[tuple[str, str]]:
        def num(key, unit="", fmt="{:,.0f}"):
            x = v.get(key)
            if x in (None, 0, 0.0, ""):
                return None
            try:
                return fmt.format(x) + unit
            except (TypeError, ValueError):
                return str(x)

        rows: list[tuple[str, Optional[str]]] = []
        if utype == "Aircraft":
            rows += [("Length", num("Length", " m", "{:.1f}")), ("Span", num("Span", " m", "{:.1f}")),
                     ("Max weight", num("WeightMax", " kg")), ("Crew", num("Crew")),
                     ("Agility", num("Agility", "", "{:.1f}")),
                     ("Endurance", num("TotalEndurance", " min")),
                     ("Runway", self.enum("EnumRunwayLength").get(v.get("RunwayLengthCode"), "")),
                     ("Cockpit", self.enum("EnumAircraftCockpitGen").get(v.get("CockpitGen"), ""))]
        elif utype in ("Ship", "Submarine"):
            rows += [("Length", num("Length", " m", "{:.1f}")), ("Beam", num("Beam", " m", "{:.1f}")),
                     ("Displacement", num("DisplacementFull", " t")), ("Crew", num("Crew")),
                     ("Damage points", num("DamagePoints"))]
            if utype == "Submarine":
                rows.append(("Max depth", num("MaxDepth", " m")))
            else:
                rows.append(("Troops", num("TroopCapacity")))
        elif utype in ("Facility", "GroundUnit"):
            rows += [("Area", num("Area", " m²")), ("Crew", num("Crew")), ("Armor", num("ArmorGeneral")),
                     ("Damage points", num("DamagePoints"))]
        elif utype == "Weapon":
            rows += [("Air range", num("AirRangeMax", " nm", "{:g}")),
                     ("Surface range", num("SurfaceRangeMax", " nm", "{:g}")),
                     ("Land range", num("LandRangeMax", " nm", "{:g}")),
                     ("Sub range", num("SubsurfaceRangeMax", " nm", "{:g}")),
                     ("Weight", num("Weight", " kg")), ("Generation",
                                                       self.enum("EnumWeaponGeneration").get(v.get("Generation"), ""))]
        elif utype == "Sensor":
            rows += [("Range", f"{v.get('RangeMin') or 0:g}-{v.get('RangeMax') or 0:g} nm"),
                     ("Generation", self.enum("EnumSensorGeneration").get(v.get("Generation"), ""))]
        if v.get("Cost"):
            rows.append(("Cost", num("Cost", " M$", "{:,.1f}")))
        return [(k, x) for k, x in rows if x]

    # ------------------------------------------------------------------ media
    def media_root(self) -> Path:
        return self.path.parent

    def image_path(self, utype: str, dbid: int) -> Optional[Path]:
        folder = self.media_root() / "Images" / self.family
        return _find_media(folder, MEDIA_PREFIX.get(utype, utype), dbid, (".jpg", ".png", ".jpeg"))

    def description(self, utype: str, dbid: int) -> str:
        folder = self.media_root() / "Descriptions" / self.family
        p = _find_media(folder, MEDIA_PREFIX.get(utype, utype), dbid, (".txt",))
        if not p:
            return ""
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return p.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return ""


_MEDIA_INDEX: dict[Path, dict[str, Path]] = {}


def _find_media(folder: Path, prefix: str, dbid: int, exts: tuple[str, ...]) -> Optional[Path]:
    """Media files use inconsistent case (``AIrcraft_1390.jpg``), so index each folder once."""
    if not folder.is_dir():
        return None
    index = _MEDIA_INDEX.get(folder)
    if index is None:
        index = {}
        for p in folder.iterdir():
            index.setdefault(p.name.lower(), p)
        _MEDIA_INDEX[folder] = index
    for ext in exts:
        p = index.get(f"{prefix}_{dbid}{ext}".lower())
        if p:
            return p
    return None
