"""Import the order of battle from a hand-written Build_Scenario.lua (the *If Russia Wins* pattern).

Recognised tables (any prefix, e.g. ``RW.``):

* ``X.CFG``        SIDE_<TAG> = 'Side name', START, DURATION_DAYS, WEATHER, PROFICIENCY_<TAG>
* ``X.DB``         KEY = { t='Aircraft', id=1234, n={'Class name'} }
* ``X.LOADOUTS``   KEY = loadout id
* ``X.BASES``      { s='TAG', k='DBKEY', n='Name', lat=, lon=, ac={ {'DBKEY', count, 'Squadron' [, loadout]} } }
* ``X.UNITS``      { 'TAG', 'DBKEY', 'Name', lat, lon, 'flags', 'group' }   flags: A radar on, H hold
* ``X.US_REINFORCE`` (or ``X.REINFORCE``)  { k='DBKEY', n=count, p='Name', base='Base name' | lat=, lon= }
* ``X.ZONES``      TAG = { ZONE = { {lat, lon}, ... } }
* ``X.MISSIONS``   { 'TAG', 'Name', 'class', 'subtype', 'ZONE', 'group' }

Events and scripts are not imported (the studio generates its own); copy the
logic into project scripts if you want it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..model.project import Mission, Project, Unit, Zone, new_project
from .lua_table import LuaTableReader

PALETTE = {"RU": "#e5484d", "NATO": "#3d8bfd", "CIV": "#aaaaaa", "SURV": "#f5a524"}


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _list(v: Any) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [v[k] for k in sorted(k for k in v if isinstance(k, int))]
    return []


def import_legacy_build(path: str | Path, db=None) -> tuple[Project, list[str]]:
    path = Path(path)
    src = path.read_text(encoding="utf-8", errors="replace")
    r = LuaTableReader(src)
    report: list[str] = [f"Imported from {path.name}"]
    prefix = next(iter(r.table_prefixes("UNITS") or r.table_prefixes("BASES") or r.table_prefixes("DB")), None)
    if not prefix:
        raise ValueError("No X.UNITS / X.BASES / X.DB tables found - is this an If Russia Wins-style builder?")

    def tbl(name):
        v = r.read(f"{prefix}.{name}")
        return v if v is not None else {}

    cfg = tbl("CFG") if isinstance(tbl("CFG"), dict) else {}
    dbmap = tbl("DB") if isinstance(tbl("DB"), dict) else {}
    loadouts = tbl("LOADOUTS") if isinstance(tbl("LOADOUTS"), dict) else {}

    title = path.parent.name if path.parent.name.lower() != "lua" else path.stem
    p = new_project(title, db.path.name if db else "")
    p.sides.clear()
    p.meta.description_html = ""

    # ------------------------------------------------------------------ sides
    side_names = {k[5:]: v for k, v in cfg.items() if isinstance(k, str) and k.startswith("SIDE_") and
                  isinstance(v, str)}
    tags_used = set()
    for row in _list(tbl("UNITS")):
        rl = _list(row)
        if rl and isinstance(rl[0], str):
            tags_used.add(rl[0])
    for b in _list(tbl("BASES")):
        if isinstance(b, dict) and isinstance(b.get("s"), str):
            tags_used.add(b["s"])
    zones_cfg = tbl("ZONES")
    if isinstance(zones_cfg, dict):
        tags_used |= {k for k in zones_cfg if isinstance(k, str)}
    for tag in tags_used:
        side_names.setdefault(tag, tag)
    sid: dict[str, str] = {}
    for tag, name in side_names.items():
        s = p.add_side(name, tag, PALETTE.get(tag, "#30a46c"))
        prof = cfg.get(f"PROFICIENCY_{tag}")
        if isinstance(prof, str):
            s.proficiency = prof
        if tag in ("CIV", "SURV"):
            s.computer_only = True
            s.awareness = "Blind"
            s.export_briefing = False
        sid[tag] = s.id
    combatants = [t for t in side_names if t not in ("CIV", "SURV")]
    for a in combatants:
        for b in combatants:
            if a != b:
                p.side(sid[a]).postures[sid[b]] = "H"
    report.append(f"Sides: {', '.join(side_names.values())}")

    # ------------------------------------------------------------------ clock / weather
    st = cfg.get("START")
    if isinstance(st, dict) and all(k in st for k in ("year", "month", "day")):
        p.clock.start = (f"{int(st['year']):04d}-{int(st['month']):02d}-{int(st['day']):02d}T"
                         f"{int(st.get('hour', 0)):02d}:{int(st.get('min', 0)):02d}:{int(st.get('sec', 0)):02d}")
    if _num(cfg.get("DURATION_DAYS")):
        p.clock.duration_days = int(cfg["DURATION_DAYS"])
    w = cfg.get("WEATHER")
    if isinstance(w, dict):
        p.weather.temperature = float(w.get("temp", p.weather.temperature))
        p.weather.rainfall = int(w.get("rain", p.weather.rainfall))
        p.weather.cloud = float(w.get("cloud", p.weather.cloud))
        p.weather.sea_state = int(w.get("sea", p.weather.sea_state))
    if isinstance(cfg.get("ARMED_START"), bool):
        p.build.armed_start = cfg["ARMED_START"]
    if _num(cfg.get("DEFAULT_LOADOUT")):
        p.build.default_loadout = int(cfg["DEFAULT_LOADOUT"])

    # ------------------------------------------------------------------ helpers
    missing: set[str] = set()

    def resolve(key: str) -> Optional[tuple[str, int, str]]:
        d = dbmap.get(key)
        if not isinstance(d, dict) or not isinstance(d.get("t"), str) or not _num(d.get("id")):
            missing.add(key)
            return None
        utype = {"Sub": "Submarine"}.get(d["t"], d["t"])
        dbid = int(d["id"])
        names = _list(d.get("n"))
        name = names[0] if names and isinstance(names[0], str) else ""
        if db is not None:
            name = db.name_of(utype, dbid) or name
        return utype, dbid, name

    def make(tag, key, name, lat=None, lon=None, host="", count=1, loadout=None) -> Optional[Unit]:
        if tag not in sid:
            return None
        res = resolve(key)
        if not res:
            return None
        utype, dbid, cls = res
        u = Unit(side=sid[tag], type=utype, dbid=dbid, db_name=cls, name=name, count=max(1, int(count)), host=host)
        if lat is not None and lon is not None:
            u.lat, u.lon = float(lat), float(lon)
        if utype == "Aircraft":
            lo = loadout if _num(loadout) else loadouts.get(key)
            u.loadout = int(lo) if _num(lo) else None
        p.units.append(u)
        return u

    # ------------------------------------------------------------------ bases and aircraft
    base_by_name: dict[str, Unit] = {}
    n_air = 0
    for b in _list(tbl("BASES")):
        if not isinstance(b, dict):
            continue
        base = make(b.get("s"), b.get("k"), b.get("n", "Base"), b.get("lat"), b.get("lon"))
        if not base:
            continue
        base_by_name[base.name] = base
        for ac in _list(b.get("ac")):
            acl = _list(ac)
            if len(acl) >= 3:
                u = make(b.get("s"), acl[0], acl[2], base.lat, base.lon, host=base.id, count=int(acl[1] or 1),
                         loadout=acl[3] if len(acl) > 3 else None)
                if u:
                    u.group = acl[2]
                    n_air += u.count
    report.append(f"Bases: {len(base_by_name)} with {n_air} aircraft")

    # ------------------------------------------------------------------ units
    groups: dict[str, list[str]] = {}
    n_units = 0
    for row in _list(tbl("UNITS")):
        rl = _list(row) + [None] * 7
        tag, key, name, lat, lon, flags, group = rl[:7]
        if not (isinstance(key, str) and _num(lat) is not None and _num(lon) is not None):
            continue
        u = make(tag, key, name or key, lat, lon)
        if not u:
            continue
        flags = flags if isinstance(flags, str) else ""
        u.radar_active = "A" in flags
        u.hold_position = "H" in flags
        if isinstance(group, str) and group:
            u.group = group
            groups.setdefault(group, []).append(u.id)
        n_units += 1
    report.append(f"Units: {n_units}")

    # ------------------------------------------------------------------ reinforcements
    reinf = r.read(f"{prefix}.US_REINFORCE") or r.read(f"{prefix}.REINFORCE") or []
    n_res = 0
    default_tag = "NATO" if "NATO" in sid else (combatants[0] if combatants else None)
    for rr in _list(reinf):
        if not isinstance(rr, dict):
            continue
        base = base_by_name.get(rr.get("base", "")) if rr.get("base") else None
        tag = next((t for t, s in sid.items() if base and s == base.side), default_tag)
        u = make(tag, rr.get("k"), rr.get("p", rr.get("k", "Reinforcement")),
                 base.lat if base else rr.get("lat"), base.lon if base else rr.get("lon"),
                 host=base.id if base else "", count=int(rr.get("n", 1) or 1))
        if u:
            u.reserve = True
            n_res += 1
    if n_res:
        report.append(f"Reinforcements (reserve units): {n_res}")

    # ------------------------------------------------------------------ zones and missions
    zone_ids: dict[tuple[str, str], str] = {}
    if isinstance(zones_cfg, dict):
        for tag, zones in zones_cfg.items():
            if tag not in sid or not isinstance(zones, dict):
                continue
            for zname, pts in zones.items():
                pl = [[float(_list(q)[0]), float(_list(q)[1])] for q in _list(pts) if len(_list(q)) >= 2]
                z = Zone(side=sid[tag], name=str(zname), points=pl)
                p.zones.append(z)
                zone_ids[(tag, str(zname))] = z.id
    n_m = 0
    for row in _list(tbl("MISSIONS")):
        rl = _list(row) + [None] * 6
        tag, name, mclass, sub, zkey, grp = rl[:6]
        if tag not in sid or not isinstance(name, str):
            continue
        m = Mission(side=sid[tag], name=name, mclass=str(mclass or "patrol"), subtype=str(sub or ""),
                    zone=zone_ids.get((tag, str(zkey)), ""), units=list(groups.get(grp, [])) if grp else [])
        if m.mclass == "patrol" and not m.subtype:
            m.subtype = "naval"
        p.missions.append(m)
        n_m += 1
    report.append(f"Areas: {len(p.zones)}, missions: {n_m}")
    if missing:
        report.append(f"Skipped {len(missing)} DB key(s) without a verified id: {', '.join(sorted(missing))}")
    report.append("Events, special actions and runtime scripts were not imported.")
    return p, report
