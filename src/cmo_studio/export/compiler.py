"""Project -> the data table ``D`` that Build_Scenario.lua builds from, and event scripts.

Kept separate from file writing so it can be unit-tested and previewed in the UI.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from ..model.enums import WCS_LUA
from ..model.project import Action, Condition, Event, Project, Trigger, Unit
from .lua_writer import LuaRaw, lua_long_str, lua_str

PSEUDO_TIME_TRIGGERS = ("StudioAtTime", "StudioAfterDelay")
ONE_MINUTE = 4   # RegularTime interval index for 1 minute


class CompileError(Exception):
    pass


# =============================================================================== helpers
def event_key(event: Event) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", event.id.split("_", 1)[-1])


def unit_first_name(u: Unit) -> str:
    return f"{u.name} #1" if u.count > 1 else u.name


def ordered_units(project: Project, include_reserve: bool = False) -> list[Unit]:
    """Units with every host before the units it hosts (cycles are broken, not looped)."""
    pool = [u for u in project.units if include_reserve or not u.reserve]
    ids = {u.id for u in pool}
    done: set[str] = set()
    out: list[Unit] = []
    visiting: set[str] = set()

    def visit(u: Unit) -> None:
        if u.id in done or u.id in visiting:
            return
        visiting.add(u.id)
        if u.host and u.host in ids:
            host = project.unit(u.host)
            if host:
                visit(host)
                if u.type == "Aircraft":            # the fallback bases must exist before the aircraft too
                    for aid in alternative_hosts(project, host):
                        alt = project.unit(aid)
                        if alt is not None and aid in ids:
                            visit(alt)
        visiting.discard(u.id)
        done.add(u.id)
        out.append(u)

    for u in pool:
        visit(u)
    return out


def iso_to_epoch(text: str) -> int:
    dt = datetime.fromisoformat(str(text).replace("Z", ""))
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v)


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


# =============================================================================== events
def compile_trigger(project: Project, event: Event, trig: Trigger, idx: int) -> dict:
    """One native trigger: {name, spec, unit?, area?} (unit/area resolved to GUIDs/RPs in-game)."""
    p = trig.params
    name = f"{event.name} - T{idx + 1}"
    t = trig.type
    out: dict[str, Any] = {"name": name}
    spec: dict[str, Any] = {}
    if t in PSEUDO_TIME_TRIGGERS:
        spec = {"type": "RegularTime", "Interval": ONE_MINUTE}
    elif t in ("ScenLoaded", "ScenEnded"):
        spec = {"type": t}
    elif t == "RegularTime":
        spec = {"type": t, "Interval": _int(p.get("Interval"), ONE_MINUTE)}
    elif t == "RandomTime":
        spec = {"type": t, "EarliestTime": str(p.get("EarliestTime", "")), "LatestTime": str(p.get("LatestTime", ""))}
    elif t in ("UnitDestroyed", "UnitDamaged", "UnitEntersArea", "UnitRemainsInArea", "UnitDetected"):
        flt: dict[str, Any] = {}
        if p.get("TargetSide"):
            flt["TargetSide"] = project.side_name(p["TargetSide"]) or p["TargetSide"]
        if p.get("TargetType"):
            flt["TargetType"] = p["TargetType"]
        spec = {"type": t, "TargetFilter": flt}
        if p.get("SpecificUnit"):
            out["unit"] = p["SpecificUnit"]
        if t == "UnitDamaged":
            spec["DamagePercent"] = _int(p.get("DamagePercent"), 50)
        if t in ("UnitEntersArea", "UnitRemainsInArea"):
            if p.get("Area"):
                out["area"] = p["Area"]
            if t == "UnitEntersArea" and _bool(p.get("ExitArea")):
                spec["ExitArea"] = True
            if t == "UnitRemainsInArea":
                spec["Duration"] = str(p.get("Duration") or "0:0:30:0")
        if t == "UnitDetected":
            if p.get("DetectorSide"):
                spec["DetectorSideID"] = project.side_name(p["DetectorSide"]) or p["DetectorSide"]
            if p.get("MCL") not in (None, ""):
                spec["MCL"] = _int(p.get("MCL"))
    elif t == "Points":
        spec = {"type": "Points", "SideID": project.side_name(p.get("Side", "")),
                "PointValue": _int(p.get("PointValue")),
                "ReachDirection": p.get("ReachDirection") or "GreaterThan"}
    elif t == "Raw":
        out["spec"] = LuaRaw(str(p.get("Spec") or "{}"))
        return out
    else:
        raise CompileError(f"Event '{event.name}': unknown trigger type {t}")
    out["spec"] = spec
    return out


def condition_lua(project: Project, cond: Condition) -> Optional[str]:
    """Lua boolean expression for a guard, or None for a native (raw) condition."""
    p, t = cond.params, cond.type
    if t == "LuaExpression":
        return f"({p.get('Expression') or 'true'})"
    if t == "FlagSet":
        return f"StudioFlag({lua_str(p.get('Key', ''))})"
    if t == "FlagNotSet":
        return f"not StudioFlag({lua_str(p.get('Key', ''))})"
    if t in ("ScoreAtLeast", "ScoreBelow"):
        op = ">=" if t == "ScoreAtLeast" else "<"
        return f"StudioScore({lua_str(project.side_name(p.get('Side', '')))}) {op} {_int(p.get('Value'))}"
    if t == "Chance":
        return f"math.random(100) <= {_int(p.get('Percent'), 50)}"
    if t in ("UnitAlive", "UnitDead"):
        u = project.unit(p.get("Unit", ""))
        sel = (f"{{ side = {lua_str(project.side_name(u.side))}, name = {lua_str(unit_first_name(u))} }}"
               if u else "{ name = '?' }")
        return f"{'' if t == 'UnitAlive' else 'not '}StudioUnitAlive({sel})"
    if t == "Raw":
        return None
    raise CompileError(f"Unknown condition type {t}")


def action_lua(project: Project, action: Action) -> Optional[str]:
    """Lua statements for one action, or None for a native (raw) action."""
    p, t = action.params, action.type
    if t == "Message":
        text = lua_long_str(p.get("Text", ""))
        if p.get("Side"):
            return f"StudioMsg({lua_str(project.side_name(p['Side']))}, {text})"
        return f"StudioMsgAll({text})"
    if t == "Score":
        return (f"StudioAddScore({lua_str(project.side_name(p.get('Side', '')))}, {_int(p.get('Change'))}, "
                f"{lua_str(p.get('Reason') or 'Scenario event')})")
    if t == "EndScenario":
        return "pcall(ScenEdit_EndScenario)"
    if t == "MissionStatus":
        m = project.mission(p.get("Mission", ""))
        if not m:
            return "-- (mission no longer exists)"
        return (f"StudioMissionStatus({lua_str(project.side_name(m.side))}, {lua_str(m.name)}, "
                f"{'true' if _bool(p.get('Active', True)) else 'false'})")
    if t == "SetFlag":
        return f"StudioSetKV({lua_str(p.get('Key', ''))}, {lua_str(str(p.get('Value', 'true')))})"
    if t == "RunScript":
        s = project.script(p.get("Script", ""))
        return f"StudioRunScript({lua_str(s.name if s else p.get('Script', ''))})"
    if t == "LuaScript":
        code = str(p.get("Code", "")).rstrip()
        return "do\n" + "\n".join("  " + ln if ln.strip() else "" for ln in code.split("\n")) + "\nend"
    if t == "SpawnUnit":
        return f"StudioSpawn({lua_str(p.get('Unit', ''))})"
    if t == "Raw":
        return None
    raise CompileError(f"Unknown action type {t}")


def event_needs_guard(project: Project, event: Event) -> bool:
    if event.probability < 100:
        return True
    if any(t.type in PSEUDO_TIME_TRIGGERS for t in event.triggers):
        return True
    return any(c.type != "Raw" for c in event.conditions)


def compile_event(project: Project, event: Event) -> dict:
    key = event_key(event)
    guard = event_needs_guard(project, event)
    # A one-shot event whose Lua guard can say "not yet" must stay repeatable in CMO,
    # otherwise the first trigger would consume it; the once-only rule moves into Lua.
    once_in_lua = guard and not event.repeatable
    times = [t for t in event.triggers if t.type in PSEUDO_TIME_TRIGGERS]
    if times:
        once_in_lua = True   # time triggers fire once
    lines = [f"-- Event: {event.name}"]
    flag = f"STUDIO_EVT_{key}"
    if once_in_lua:
        lines.append(f"if StudioFlag({lua_str(flag)}) then return end")
    for t in times:
        if t.type == "StudioAtTime":
            at = iso_to_epoch(t.params.get("Time") or project.clock.start)
        else:
            at = project.clock.start_epoch() + 60 * _int(t.params.get("Minutes"))
        when = datetime.fromtimestamp(at, timezone.utc).strftime("%Y-%m-%d %H:%M")
        lines.append(f"if (tonumber(ScenEdit_CurrentTime()) or 0) < {at} then return end   -- {when} Z")
    for c in event.conditions:
        expr = condition_lua(project, c)
        if expr is not None:
            lines.append(f"if not ({expr}) then return end")
    if event.probability < 100:
        lines.append(f"if math.random(100) > {max(0, event.probability)} then return end")
    if once_in_lua:
        lines.append(f"StudioSetFlag({lua_str(flag)}, true)")
    native_actions = []
    for i, a in enumerate(event.actions):
        code = action_lua(project, a)
        if code is None:
            native_actions.append({"name": f"{event.name} - A{i + 1}",
                                   "spec": LuaRaw(str(a.params.get("Spec") or "{}"))})
        else:
            lines.append(code)
    has_lua_actions = any(a.type != "Raw" for a in event.actions)
    script = "\n".join(lines) if (has_lua_actions or guard) else ""
    native_conditions = [{"name": f"{event.name} - C{i + 1}", "spec": LuaRaw(str(c.params.get("Spec") or "{}"))}
                         for i, c in enumerate(event.conditions) if c.type == "Raw"]
    return {
        "key": key,
        "name": event.name,
        "repeatable": bool(event.repeatable or once_in_lua),
        "active": bool(event.active),
        "shown": bool(event.shown),
        "triggers": [compile_trigger(project, event, t, i) for i, t in enumerate(event.triggers)],
        "conditions": native_conditions,
        "script": script,
        "actions": native_actions,
    }


# =============================================================================== whole build
def _doctrine(side) -> dict:
    out = {}
    for k, v in side.doctrine.items():
        if v in ("", None):
            continue
        if k.startswith("weapon_control_status") and v in WCS_LUA:
            out[k] = WCS_LUA[v]
        else:
            out[k] = v
    return out


_AIRCRAFT_FACILITY = re.compile(r"^A/C |Airfield|Airport|Air ?Base|Airstrip|Heliport|Helipad|FARP", re.I)


def alternative_hosts(project: Project, host: Unit, limit: int = 40) -> list[str]:
    """Other parts of the host's site that can hold aircraft, for the builder to try if CMO refuses the host
    (e.g. a runway or tower picked as the base, or a full shelter). Hangars and shelters first."""
    if not host.group:
        return []
    cands = [v for v in project.units
             if v.id != host.id and v.group == host.group and v.side == host.side and not v.host and not v.reserve
             and v.type in ("Facility", "Ship", "GroundUnit") and _AIRCRAFT_FACILITY.search(v.db_name or "")]
    order = {"hangar": 0, "hardened": 1, "shelter": 1, "tarmac": 2, "parking": 2}

    def rank(v: Unit) -> int:
        n = (v.db_name or "").lower()
        return min((r for k, r in order.items() if k in n), default=3)
    return [v.id for v in sorted(cands, key=rank)][:limit]


def unit_record(project: Project, u: Unit) -> dict:
    r: dict[str, Any] = {
        "id": u.id, "side": project.side_name(u.side), "type": u.type, "dbid": int(u.dbid),
        "name": u.name,
    }
    if u.count > 1:
        r["count"] = int(u.count)
    host = project.unit(u.host) if u.host else None
    if host:
        r["host"] = host.id
        if u.type == "Aircraft":
            alts = alternative_hosts(project, host)
            if alts:
                r["alts"] = alts
    else:
        r["lat"], r["lon"] = round(float(u.lat), 6), round(float(u.lon), 6)
    if u.type == "Aircraft":
        if u.altitude is not None:
            r["alt"] = float(u.altitude)
        if u.loadout:
            r["loadout"] = int(u.loadout)
    if u.type == "Submarine" and u.depth is not None:
        r["depth"] = float(u.depth)
    if u.heading is not None:
        r["heading"] = float(u.heading)
    if u.speed is not None:
        r["speed"] = float(u.speed)
    for flag, key in (("radar_active", "radar"), ("sonar_active", "sonar"), ("hold_position", "hold"),
                      ("autodetectable", "auto")):
        if getattr(u, flag):
            r[key] = True
    if u.proficiency:
        r["prof"] = u.proficiency
    if u.extra:
        r["set"] = dict(u.extra)
    return r


def page_names(project: Project) -> dict:
    prefix = project.meta.prefix()
    return {
        "desc": f"{prefix}_Desc.html",
        "briefings": {s.name: f"{prefix}_Briefing_{s.file_tag()}.html" for s in project.sides
                      if s.export_briefing and s.briefing_html.strip()},
        "variants": {v.key: (f"{prefix}_Desc_{v.key}.html" if v.description_html.strip() else f"{prefix}_Desc.html")
                     for v in project.variants},
    }


def compile_build_data(project: Project) -> dict:
    """Everything Build_Scenario.lua needs, as plain Python data (serialised to Lua as ``D``)."""
    m, c, w, b = project.meta, project.clock, project.weather, project.build
    dt = c.start_dt()
    pages = page_names(project)
    reserve_ids = {u.id for u in project.units if u.reserve}
    D: dict[str, Any] = {}
    D["CFG"] = {
        "TITLE": m.title, "FOLDER": m.folder(), "PATH": f"/{m.folder()}/", "SETTING": m.setting,
        "DB": m.db_file,
        "START": {"year": dt.year, "month": dt.month, "day": dt.day, "hour": dt.hour, "min": dt.minute,
                  "sec": dt.second},
        "DURATION": {"d": int(c.duration_days), "h": int(c.duration_hours), "m": int(c.duration_minutes)},
        "WEATHER": {"temp": float(w.temperature), "rain": int(w.rainfall), "cloud": float(w.cloud),
                    "sea": int(w.sea_state)},
        "ARMED_START": bool(b.armed_start), "DEFAULT_LOADOUT": int(b.default_loadout),
        "VERBOSE": int(b.verbose), "FORCE_REBUILD": bool(b.force_rebuild),
    }
    D["PAGES"] = {"desc": pages["desc"], "briefings": pages["briefings"]}
    D["SIDES"] = [{"name": s.name, "awareness": s.awareness, "proficiency": s.proficiency,
                   "computer": bool(s.computer_only), "score": int(s.start_score), "doctrine": _doctrine(s)}
                  for s in project.sides]
    postures = []
    for s in project.sides:
        for other in project.sides:
            if other.id != s.id:
                postures.append([s.name, other.name, s.postures.get(other.id, "N")])
    D["POSTURES"] = postures
    D["VARIANTS"] = {v.key: {"name": v.name, "computer": [project.side_name(x) for x in v.computer_sides],
                             "scen": m.title + v.scen_suffix, "desc": pages["variants"][v.key]}
                     for v in project.variants}
    rps = []
    for r in project.reference_points:
        sides = [s.name for s in project.sides] if r.all_sides else [project.side_name(r.side)]
        for sname in sides:
            rps.append({"side": sname, "name": r.name, "lat": round(r.lat, 6), "lon": round(r.lon, 6),
                        "hl": bool(r.highlighted)})
    D["RPS"] = rps
    D["ZONES"] = [{"id": z.id, "name": z.name,
                   "sides": [s.name for s in project.sides] if z.all_sides else [project.side_name(z.side)],
                   "pts": [[round(p[0], 6), round(p[1], 6)] for p in z.points]}
                  for z in project.zones if z.points]
    D["UNITS"] = [unit_record(project, u) for u in ordered_units(project)]
    D["FORMATIONS"] = compile_formations(project)
    missions = []
    for ms in project.missions:
        rec: dict[str, Any] = {"side": project.side_name(ms.side), "name": ms.name, "class": ms.mclass}
        if ms.subtype and ms.mclass in ("patrol", "strike"):
            rec["sub"] = ms.subtype
        if ms.zone and project.zone(ms.zone):
            rec["zone"] = ms.zone
        if ms.prosecution_zone and project.zone(ms.prosecution_zone):
            rec["pzone"] = ms.prosecution_zone
        if ms.destination and project.unit(ms.destination):
            rec["dest"] = ms.destination
        rec["units"] = [x for x in ms.units if project.unit(x) and x not in reserve_ids]
        rec["targets"] = [x for x in ms.targets if project.unit(x) and x not in reserve_ids]
        if ms.options:
            rec["opts"] = {k: v for k, v in ms.options.items() if v not in ("", None)}
        missions.append(rec)
    D["MISSIONS"] = missions
    D["KV"] = [[k, str(v)] for k, v in project.key_values.items()]
    start_epoch = c.start_epoch()
    D["FORECAST"] = [
        {"t": start_epoch + e.offset_minutes * 60,
         "temp": float(e.temperature), "rain": int(e.rainfall),
         "cloud": float(e.cloud), "sea": int(e.sea_state)}
        for e in sorted(project.forecast, key=lambda x: x.offset_minutes)
        if e.offset_minutes > 0
    ]
    D["EVENTS"] = [compile_event(project, e) for e in project.events]
    rev = route_event(project)
    if rev is not None:
        D["EVENTS"].append(compile_event(project, rev))
    D["SPECIALS"] = [{"side": project.side_name(a.side), "name": a.name, "desc": a.description,
                      "repeatable": bool(a.repeatable), "active": bool(a.active), "script": a.script}
                     for a in project.special_actions]
    return D


def compile_formations(project: Project) -> list[dict]:
    """Groups with stations measured from the units' actual positions (what the map shows)."""
    from ..geo import bearing_deg, distance_km
    out = []
    for f in project.formations:
        lead = project.unit(f.lead)
        if not f.group_in_cmo or lead is None or lead.reserve or lead.host:
            continue
        members = []
        for uid in f.members:
            u = project.unit(uid)
            if u is None or u.reserve or u.host or u.id == lead.id:
                continue
            dist_nm = distance_km(lead.lat, lead.lon, u.lat, u.lon) / 1.852
            true = bearing_deg(lead.lat, lead.lon, u.lat, u.lon) if dist_nm > 1e-6 else 0.0
            brg = true if f.station_type == "Fixed" else (true - f.heading) % 360.0
            members.append({"id": u.id, "bearing": round(brg, 1), "dist": round(dist_nm, 3)})
        rec = {"name": f.name, "lead": lead.id, "stype": f.station_type, "sprint": bool(f.sprint_drift),
               "members": members}
        if not f.set_stations:
            rec["nostations"] = True
        out.append(rec)
    return out


def unit_names(u: Unit) -> list[str]:
    """The names CMO gives the unit's copies: '<name> #1..n' when counted."""
    n = max(1, int(u.count or 1))
    return [f"{u.name} #{i}" for i in range(1, n + 1)] if n > 1 else [u.name]


#: the generated event that runs the route manager once a minute
ROUTE_EVENT_ID = "e_studio_courses"


def route_waypoint(w) -> dict:
    """One waypoint for STUDIO.ROUTES: position plus only the leg settings that are set."""
    from ..model.project import ENGAGE_SETTING, SENSOR_SETTING, WEAPONS_SETTING
    d: dict[str, Any] = {"lat": round(float(w.lat), 6), "lon": round(float(w.lon), 6)}
    if w.altitude is not None:
        d["alt"] = float(w.altitude)
    if w.speed:
        d["spd"] = float(w.speed)
    if w.name:
        d["name"] = w.name
    for key, val, allowed in (("radar", w.radar, SENSOR_SETTING), ("sonar", w.sonar, SENSOR_SETTING),
                              ("ecm", w.ecm, SENSOR_SETTING), ("wcs", w.weapons, WEAPONS_SETTING),
                              ("engage", w.engage, ENGAGE_SETTING)):
        if val and val in allowed:
            d[key] = val
    if w.wait_minutes and int(w.wait_minutes) > 0:
        d["wait"] = int(w.wait_minutes)
    if w.signal.strip():
        d["flag"] = w.signal.strip()
    return d


def compile_routes(project: Project) -> list[dict]:
    """Plotted courses for the runtime route manager (STUDIO.ROUTES in LuaInit.lua)."""
    from ..model.project import COURSE_FINISH
    out = []
    start = project.clock.start_epoch()
    for u in project.units:
        c = u.course
        if c is None or not c.waypoints or not project.side(u.side):
            continue
        r: dict[str, Any] = {
            "id": u.id, "side": project.side_name(u.side), "names": unit_names(u),
            "kind": u.type,
            "wps": [route_waypoint(w) for w in c.waypoints],
            "depart": start + 60 * max(0, int(c.depart_minutes or 0)),
            "finish": c.finish if c.finish in COURSE_FINISH else "stop",
        }
        if r["finish"] == "land":
            base = project.unit(c.land_at) if c.land_at else None
            if base is not None and project.side(base.side):
                r["land"] = {"side": project.side_name(base.side), "name": unit_first_name(base)}
            else:
                r["finish"] = "rtb"
        out.append(r)
    return out


def route_event(project: Project) -> Optional[Event]:
    """A once-a-minute event that runs StudioRoutesTick(), when any unit has a course."""
    if not any(u.course and u.course.waypoints for u in project.units):
        return None
    return Event(id=ROUTE_EVENT_ID, name="Studio: unit courses", repeatable=True,
                 triggers=[Trigger("RegularTime", {"Interval": ONE_MINUTE})],
                 actions=[Action("LuaScript", {"Code": "if StudioRoutesTick then StudioRoutesTick() end"})])


def compile_reserves(project: Project) -> dict:
    """Reinforcements spawned at run time by StudioSpawn(id) (written into LuaInit.lua)."""
    out = {}
    for u in project.units:
        if not u.reserve:
            continue
        r = unit_record(project, u)
        r.pop("id", None)
        r.pop("set", None)
        r["count"] = int(u.count)
        host = project.unit(u.host) if u.host else None
        r.pop("host", None)
        if "lat" not in r:   # hosted: fall back to the host's position if the host is gone at spawn time
            src = host or u
            r["lat"], r["lon"] = round(float(src.lat), 6), round(float(src.lon), 6)
        if host:
            r["host"] = unit_first_name(host)
            r["host_side"] = project.side_name(host.side)
        if u.type == "Aircraft":
            r["loadout"] = int(u.loadout) if (u.loadout and project.build.armed_start) else \
                int(project.build.default_loadout)
        r["missions"] = [ms.name for ms in project.missions if u.id in ms.units]
        out[u.id] = r
    return out
