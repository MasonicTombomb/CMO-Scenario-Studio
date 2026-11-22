"""Checks a project for mistakes before export. Pure Python; the DB checks are optional."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from .enums import HOST_TYPES, MISSION_CLASSES, MISSION_NEEDS_ZONE, UNIT_TYPES
from .project import Project

ERROR, WARNING, INFO = "error", "warning", "info"
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FILE = re.compile(r"^[A-Za-z0-9_\- ]+$")
RESERVED_SCRIPTS = {"build_scenario", "luainit", "studio_runtime"}


@dataclass
class Issue:
    level: str
    area: str
    message: str
    obj_id: str = ""

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.area}: {self.message}"


def validate(p: Project, db=None) -> list[Issue]:
    out: list[Issue] = []

    def add(level, area, msg, oid=""):
        out.append(Issue(level, area, msg, oid))

    # ------------------------------------------------------------------ meta
    m = p.meta
    if not m.title.strip():
        add(ERROR, "Scenario", "The scenario has no title.")
    if not m.db_file:
        add(WARNING, "Scenario", "No database selected; the build report cannot name it.")
    elif db is not None and db.path.name.lower() != m.db_file.lower():
        add(INFO, "Scenario", f"Project targets {m.db_file} but {db.path.name} is open in the browser.")
    total = p.clock.duration_days * 1440 + p.clock.duration_hours * 60 + p.clock.duration_minutes
    if total <= 0:
        add(WARNING, "Scenario", "Scenario duration is zero.")

    # ------------------------------------------------------------------ sides
    if not p.sides:
        add(ERROR, "Sides", "The scenario has no sides.")
    for name, n in Counter(s.name for s in p.sides).items():
        if n > 1:
            add(ERROR, "Sides", f"Two sides are called '{name}'.")
    for s in p.sides:
        if not s.name.strip():
            add(ERROR, "Sides", "A side has no name.", s.id)
    if p.sides and all(s.computer_only for s in p.sides):
        add(WARNING, "Sides", "Every side is computer-only: nobody can play the standard version.")

    side_ids = {s.id for s in p.sides}
    units = {u.id: u for u in p.units}

    # ------------------------------------------------------------------ units
    names_by_side = Counter((u.side, u.name) for u in p.units)
    for (sid, name), n in names_by_side.items():
        if n > 1:
            add(WARNING, "Units", f"{n} units on {p.side_name(sid)} are called '{name}' "
                                  f"(scripts that find units by name will pick the first).")
    year = p.scenario_year()
    for u in p.units:
        label = f"{u.name} ({p.side_name(u.side) or '?'})"
        if u.side not in side_ids:
            add(ERROR, "Units", f"{label}: unknown side.", u.id)
        if u.type not in UNIT_TYPES:
            add(ERROR, "Units", f"{label}: unit type '{u.type}' cannot be placed.", u.id)
        if not u.dbid:
            add(ERROR, "Units", f"{label}: no database entry chosen.", u.id)
        if not u.name.strip():
            add(ERROR, "Units", "A unit has no name.", u.id)
        if u.count < 1:
            add(ERROR, "Units", f"{label}: count must be 1 or more.", u.id)
        host = units.get(u.host) if u.host else None
        if u.host and not host:
            add(ERROR, "Units", f"{label}: its host unit no longer exists.", u.id)
        if host:
            if host.type not in HOST_TYPES:
                add(ERROR, "Units", f"{label}: host '{host.name}' is a {host.type} and cannot host units.", u.id)
            if host.side != u.side:
                add(WARNING, "Units", f"{label}: host '{host.name}' belongs to another side.", u.id)
            if host.reserve and not u.reserve:
                add(ERROR, "Units", f"{label}: starts at '{host.name}', which is a reinforcement that does not "
                                    f"exist at the start.", u.id)
        elif not (-90 <= u.lat <= 90 and -180 <= u.lon <= 180):
            add(ERROR, "Units", f"{label}: position {u.lat:.4f}, {u.lon:.4f} is off the map.", u.id)
        elif u.lat == 0 and u.lon == 0:
            add(WARNING, "Units", f"{label}: has not been placed (position 0, 0).", u.id)
        if u.type == "Aircraft" and not host and u.altitude is None:
            add(INFO, "Units", f"{label}: airborne with no altitude set; the builder uses 9000 m.", u.id)
        if u.type == "Aircraft" and not u.loadout:
            add(INFO, "Units", f"{label}: no loadout chosen; starts in reserve "
                               f"(loadout {p.build.default_loadout}).", u.id)
        if db is not None and u.dbid and u.type in UNIT_TYPES:
            entry = db.get(u.type, int(u.dbid))
            if entry is None:
                add(ERROR, "Database", f"{label}: DBID {u.dbid} is not a {u.type} in {db.path.name}.", u.id)
            else:
                if entry.deprecated:
                    add(WARNING, "Database", f"{label}: '{entry.name}' (DBID {u.dbid}) is deprecated.", u.id)
                if not entry.in_service(year):
                    add(INFO, "Database", f"{label}: '{entry.name}' is not in service in {year} "
                                          f"({entry.year or '?'}-{entry.year_end or ''}).", u.id)
                if u.type == "Aircraft" and u.loadout and not db.loadout_valid(int(u.dbid), int(u.loadout)):
                    add(ERROR, "Database", f"{label}: loadout {u.loadout} does not belong to '{entry.name}'.", u.id)
    if db is not None:
        _check_aircraft_hosts(p, db, units, add)
    if db is not None:
        from .airbase import cannot_fly
        for u, site, why in cannot_fly(p, db):
            add(ERROR, "Air bases", f"{u.name or '(unnamed)'} can never take off: {why}. "
                                    "Tools > Repair air bases fixes this.", u.id)
    _check_courses(p, db, add)
    _check_forecast(p, add)

    # ------------------------------------------------------------------ reference points and zones
    rp_names: Counter = Counter()
    for r in p.reference_points:
        if r.side not in side_ids and not r.all_sides:
            add(ERROR, "Areas", f"Reference point '{r.name}': unknown side.", r.id)
        rp_names[r.name] += 1
    zone_names = Counter((z.side, z.name) for z in p.zones)
    for (sid, name), n in zone_names.items():
        if n > 1:
            add(ERROR, "Areas", f"Two areas on {p.side_name(sid)} are called '{name}' (their reference points "
                                f"would clash).")
    for z in p.zones:
        if z.side not in side_ids and not z.all_sides:
            add(ERROR, "Areas", f"Area '{z.name}': unknown side.", z.id)
        if not z.points:
            add(WARNING, "Areas", f"Area '{z.name}' has no points and is not exported.", z.id)
        for nm in z.rp_names():
            if nm in rp_names:
                add(WARNING, "Areas", f"Area '{z.name}' point '{nm}' has the same name as a reference point.", z.id)

    # ------------------------------------------------------------------ missions
    for (sid, name), n in Counter((ms.side, ms.name) for ms in p.missions).items():
        if n > 1:
            add(ERROR, "Missions", f"Two missions on {p.side_name(sid)} are called '{name}'.")
    for ms in p.missions:
        label = f"Mission '{ms.name}'"
        if ms.side not in side_ids:
            add(ERROR, "Missions", f"{label}: unknown side.", ms.id)
        if ms.mclass not in MISSION_CLASSES:
            add(ERROR, "Missions", f"{label}: unknown class '{ms.mclass}'.", ms.id)
            continue
        subs = MISSION_CLASSES[ms.mclass]
        if subs and ms.subtype not in subs:
            add(ERROR, "Missions", f"{label}: '{ms.subtype}' is not a {ms.mclass} type.", ms.id)
        zone = p.zone(ms.zone) if ms.zone else None
        if ms.mclass in MISSION_NEEDS_ZONE and not zone:
            add(ERROR, "Missions", f"{label}: a {ms.mclass} mission needs an area.", ms.id)
        if zone:
            if zone.side != ms.side and not zone.all_sides:
                add(ERROR, "Missions", f"{label}: area '{zone.name}' belongs to "
                                       f"{p.side_name(zone.side)} (tick 'all sides' or redraw it).", ms.id)
            if ms.mclass == "patrol" and len(zone.points) < 3:
                add(ERROR, "Missions", f"{label}: a patrol area needs at least 3 points.", ms.id)
        if ms.mclass == "ferry" and not ms.destination:
            add(WARNING, "Missions", f"{label}: no destination chosen.", ms.id)
        if ms.mclass == "strike" and not ms.targets:
            add(INFO, "Missions", f"{label}: no targets assigned yet." + (
                " CMO launches it at the first air contact of any kind; for aircraft that launch on conditions use an "
                "Intercept mission." if ms.subtype == "air" else ""), ms.id)
        if ms.mclass == "intercept":
            _check_intercept(p, ms, label, add)
        for uid in ms.units:
            u = units.get(uid)
            if not u:
                add(ERROR, "Missions", f"{label}: an assigned unit no longer exists.", ms.id)
            elif u.side != ms.side:
                add(ERROR, "Missions", f"{label}: '{u.name}' belongs to another side.", ms.id)
        if not ms.units:
            add(INFO, "Missions", f"{label}: no units assigned (players fill it).", ms.id)

    # ------------------------------------------------------------------ events
    for name, n in Counter(e.name for e in p.events).items():
        if n > 1:
            add(ERROR, "Events", f"Two events are called '{name}'.")
    for e in p.events:
        label = f"Event '{e.name}'"
        if not e.triggers:
            add(ERROR, "Events", f"{label}: no trigger.", e.id)
        times = [t for t in e.triggers if t.type.startswith("Studio")]
        if times and len(e.triggers) > 1:
            add(WARNING, "Events", f"{label}: a date/time trigger should be the event's only trigger.", e.id)
        if not e.actions:
            add(WARNING, "Events", f"{label}: no actions.", e.id)
        guards = e.probability < 100 or times or any(c.type != "Raw" for c in e.conditions)
        if guards and e.actions and all(a.type == "Raw" for a in e.actions):
            add(WARNING, "Events", f"{label}: conditions, probability and time triggers only gate Lua actions, "
                                   f"not native (raw) actions.", e.id)
        for t in e.triggers:
            prm = t.params
            if prm.get("TargetSide") and prm["TargetSide"] not in side_ids:
                add(ERROR, "Events", f"{label}: trigger refers to a deleted side.", e.id)
            if prm.get("SpecificUnit") and prm["SpecificUnit"] not in units:
                add(ERROR, "Events", f"{label}: trigger refers to a deleted unit.", e.id)
            if t.type in ("UnitEntersArea", "UnitRemainsInArea"):
                if not prm.get("Area") or not p.zone(prm["Area"]):
                    add(ERROR, "Events", f"{label}: area trigger has no area.", e.id)
            if t.type == "StudioAtTime" and not prm.get("Time"):
                add(ERROR, "Events", f"{label}: date/time trigger has no time.", e.id)
        for a in e.actions:
            prm = a.params
            if a.type == "SpawnUnit":
                u = units.get(prm.get("Unit", ""))
                if not u:
                    add(ERROR, "Events", f"{label}: spawn action has no unit.", e.id)
                elif not u.reserve:
                    add(ERROR, "Events", f"{label}: '{u.name}' is not marked as a reinforcement, so it already "
                                         f"exists at the start.", e.id)
            if a.type == "MissionStatus" and not p.mission(prm.get("Mission", "")):
                add(ERROR, "Events", f"{label}: mission action refers to a deleted mission.", e.id)
            if a.type == "RunScript" and not p.script(prm.get("Script", "")):
                add(ERROR, "Events", f"{label}: script '{prm.get('Script', '')}' does not exist.", e.id)
            if a.type in ("Message", "Score") and prm.get("Side") and prm["Side"] not in side_ids:
                add(ERROR, "Events", f"{label}: action refers to a deleted side.", e.id)

    # ------------------------------------------------------------------ special actions
    for a in p.special_actions:
        if a.side not in side_ids:
            add(ERROR, "Special actions", f"'{a.name}': unknown side.", a.id)
        if not a.script.strip():
            add(WARNING, "Special actions", f"'{a.name}': no script.", a.id)

    # ------------------------------------------------------------------ scripts
    for name, n in Counter(s.name.lower() for s in p.scripts).items():
        if n > 1:
            add(ERROR, "Scripts", f"Two scripts are called '{name}'.")
    for s in p.scripts:
        if not _FILE.match(s.name or ""):
            add(ERROR, "Scripts", f"Script name '{s.name}' must be letters, digits, '_', '-' or spaces.", s.id)
        if s.name.lower() in RESERVED_SCRIPTS:
            add(ERROR, "Scripts", f"'{s.name}' is generated by the studio; rename your script.", s.id)

    # ------------------------------------------------------------------ formations
    from .formations import PRESETS
    seen: dict[str, str] = {}
    for (fsid, fname), n in Counter((f.side, f.name) for f in p.formations).items():
        if n > 1:
            add(ERROR, "Formations", f"Two formations on {p.side_name(fsid)} are called '{fname}' "
                                     f"(CMO group names would clash).")
    for f in p.formations:
        label = f"Formation '{f.name}'"
        if f.preset not in PRESETS:
            add(ERROR, "Formations", f"{label}: unknown preset '{f.preset}'.", f.id)
        if not units.get(f.lead):
            add(ERROR, "Formations", f"{label}: no lead unit.", f.id)
        if f.spacing_nm <= 0:
            add(ERROR, "Formations", f"{label}: spacing must be more than zero.", f.id)
        for uid in [f.lead] + list(f.members):
            u = units.get(uid)
            if not u:
                if uid:
                    add(ERROR, "Formations", f"{label}: a member unit no longer exists.", f.id)
                continue
            if u.side != f.side:
                add(ERROR, "Formations", f"{label}: '{u.name}' belongs to another side.", f.id)
            if u.host:
                add(ERROR, "Formations", f"{label}: '{u.name}' starts at a base and cannot be on station.", f.id)
            if u.reserve:
                add(WARNING, "Formations", f"{label}: '{u.name}' is a reinforcement; it is not grouped at the "
                                           f"start.", f.id)
            if u.count > 1:
                add(WARNING, "Formations", f"{label}: '{u.name}' has count {u.count}; only the first copy gets "
                                           f"a station.", f.id)
            if uid in seen and seen[uid] != f.id:
                add(ERROR, "Formations", f"{label}: '{u.name}' is also in formation "
                                         f"'{p.formation(seen[uid]).name}'.", f.id)
            seen[uid] = f.id
        if f.lead in f.members:
            add(ERROR, "Formations", f"{label}: the lead is also listed as a member.", f.id)
        if not f.members:
            add(INFO, "Formations", f"{label}: no members yet.", f.id)

    # ------------------------------------------------------------------ variants
    for name, n in Counter(v.key for v in p.variants).items():
        if n > 1:
            add(ERROR, "Variants", f"Two variants use the key '{name}'.")
    for v in p.variants:
        if not _KEY.match(v.key or ""):
            add(ERROR, "Variants", f"Variant key '{v.key}' must be a Lua identifier (letters, digits, _).", v.id)
        if any(x not in side_ids for x in v.computer_sides):
            add(ERROR, "Variants", f"'{v.name}' refers to a deleted side.", v.id)
        ai = set(v.computer_sides) | {s.id for s in p.sides if s.computer_only}
        if p.sides and ai >= side_ids:
            add(WARNING, "Variants", f"'{v.name}' leaves no playable side.", v.id)

    order = {ERROR: 0, WARNING: 1, INFO: 2}
    out.sort(key=lambda i: (order[i.level], i.area))
    return out


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == ERROR for i in issues)


def find_issue_object(p: Project, issue: Issue) -> Optional[object]:
    return p.find(issue.obj_id) if issue.obj_id else None


def _check_aircraft_hosts(p: Project, db, units: dict, add) -> None:
    """Aircraft based in a unit that cannot hold them (a runway, a tower, too small) or more than fit."""
    from .hosting import room_for, why_not
    by_host: dict[str, list] = {}
    for u in p.units:
        if u.type == "Aircraft" and u.host and u.host in units and u.dbid:
            by_host.setdefault(u.host, []).append(u)
    for hid, planes in by_host.items():
        host = units[hid]
        if host.type == "Aircraft" or not host.dbid:
            continue
        spaces = db.aircraft_spaces(host.type, int(host.dbid))
        used = 0
        biggest_room = 0
        for u in planes:
            ac = db.aircraft_profile(int(u.dbid))
            if ac is None:
                continue
            room = room_for(spaces, ac)
            biggest_room = max(biggest_room, room)
            if room == 0:
                add(ERROR, "Units", f"{u.name or '(unnamed)'}: '{host.name}' cannot hold this aircraft: "
                                    f"{why_not(spaces, ac)}. Base it in a hangar, shelter, apron or airfield "
                                    f"instead (CMO refuses to create it).", u.id)
            elif not u.reserve:
                used += max(1, int(u.count or 1))
        if biggest_room and used > biggest_room:
            add(WARNING, "Units", f"'{host.name}' has room for {biggest_room} aircraft but {used} start there; "
                                  "CMO refuses the extra ones. Spread them over more hangars or shelters.", hid)


def _check_intercept(p: Project, ms, label: str, add) -> None:
    from .intercept import home, intercept_of, ticked
    ic = intercept_of(ms)
    aircraft = [u for u in (p.unit(i) for i in ms.units) if u is not None and u.type == "Aircraft"]
    n = sum(max(1, u.count) for u in aircraft)
    if not aircraft:
        add(ERROR, "Missions", f"{label}: no aircraft on call. Choose an air base or assign aircraft.", ms.id)
    for u in (p.unit(i) for i in ms.units):
        if u is not None and u.type != "Aircraft":
            add(ERROR, "Missions", f"{label}: {u.name} is not an aircraft.", ms.id)
    for u in aircraft:
        if not u.host:
            add(WARNING, "Missions", f"{label}: {u.name} starts in the air, not at a base.", ms.id)
        other = [m.name for m in p.missions if m.id != ms.id and u.id in m.units and m.mclass != "intercept"]
        if other:
            add(WARNING, "Missions", f"{label}: {u.name} is also on '{other[0]}', so it may be away when needed.", ms.id)
        if u.course and u.course.waypoints:
            add(WARNING, "Missions", f"{label}: {u.name} also has a course, so it may be away when needed.", ms.id)
    if aircraft and n - int(ic.reserve) < int(ic.per_contact):
        add(ERROR, "Missions", f"{label}: {n} aircraft on call with {ic.reserve} kept in reserve cannot launch "
                               f"{ic.per_contact}.", ms.id)
    if not ticked(ic):
        add(WARNING, "Missions", f"{label}: no conditions ticked, so it launches at every air contact.", ms.id)
    zone = p.zone(ms.zone) if ms.zone else None
    if ic.in_area and (zone is None or len(zone.points) < 3):
        add(ERROR, "Missions", f"{label}: 'inside the intercept area' is ticked but no area is chosen.", ms.id)
    if ic.posture and not ic.postures:
        add(ERROR, "Missions", f"{label}: 'is classed as' is ticked but no class is.", ms.id)
    if (ic.near or ic.inbound) and home(p, ms) is None:
        add(ERROR, "Missions", f"{label}: nothing to measure distance from; assign aircraft or choose a unit.", ms.id)
    if ic.altitude and ic.alt_min >= ic.alt_max:
        add(ERROR, "Missions", f"{label}: the lowest altitude is not below the highest.", ms.id)
    if ic.window and ic.window_to and ic.window_to <= ic.window_from:
        add(ERROR, "Missions", f"{label}: its time window ends before it starts.", ms.id)
    if ic.flag and not ic.flag_key.strip():
        add(ERROR, "Missions", f"{label}: 'only once this flag is set' is ticked but no flag is given.", ms.id)


def _check_courses(p: Project, db, add) -> None:
    """Plotted courses: who can follow one, where it ends, and conflicts with missions and formations."""
    from .formations import formation_of
    total_min = p.clock.duration_days * 1440 + p.clock.duration_hours * 60 + p.clock.duration_minutes
    on_mission = {uid for m in p.missions for uid in m.units}
    for u in p.units:
        c = u.course
        if c is None or not c.waypoints:
            continue
        label = f"{u.name or '(unnamed)'}"
        if u.type == "Facility":
            add(ERROR, "Courses", f"{label}: a facility cannot move, so it cannot follow a course.", u.id)
            continue
        for i, w in enumerate(c.waypoints, 1):
            if not (-90 <= w.lat <= 90 and -180 <= w.lon <= 180):
                add(ERROR, "Courses", f"{label}: waypoint {i} is off the map.", u.id)
            if w.signal.strip() and not re.fullmatch(r"[A-Za-z0-9_]+", w.signal.strip()):
                add(WARNING, "Courses", f"{label}: waypoint {i} signal '{w.signal}' should use only letters, digits "
                                        "and _ so events can test it.", u.id)
            if w.altitude is not None and u.type != "Aircraft":
                add(INFO, "Courses", f"{label}: waypoint {i} has an altitude, which only aircraft use.", u.id)
            if w.depth is not None and u.type != "Submarine":
                add(INFO, "Courses", f"{label}: waypoint {i} has a depth, which only submarines use.", u.id)
        if c.depart_minutes and total_min and c.depart_minutes >= total_min:
            add(WARNING, "Courses", f"{label}: departs {c.depart_minutes} min after the start, after the scenario "
                                    f"ends ({total_min} min).", u.id)
        if c.finish == "land":
            base = p.unit(c.land_at) if c.land_at else None
            if base is None:
                add(WARNING, "Courses", f"{label}: 'Land at another base' has no base chosen; it will return to "
                                        "its own base instead.", u.id)
            elif base.side != u.side:
                add(ERROR, "Courses", f"{label}: landing base '{base.name}' belongs to another side.", u.id)
            elif db is not None and u.type == "Aircraft" and base.dbid and u.dbid:
                from .hosting import room_for, why_not
                ac = db.aircraft_profile(int(u.dbid))
                spaces = db.aircraft_spaces(base.type, int(base.dbid))
                if ac is not None and room_for(spaces, ac) == 0:
                    add(ERROR, "Courses", f"{label}: '{base.name}' cannot take this aircraft: {why_not(spaces, ac)}."
                                          " Choose a hangar, shelter, apron or airfield to land at.", u.id)
        if c.finish == "rtb" and u.type == "Aircraft" and not u.host:
            add(INFO, "Courses", f"{label}: starts in the air with no base; at the end of its course CMO sends it "
                                 "to the nearest suitable base.", u.id)
        if u.id in on_mission:
            add(WARNING, "Courses", f"{label}: is assigned to a mission, which will override its course. Give it a "
                                    "course or a mission, not both.", u.id)
        fm = formation_of(p, u.id)
        if fm is not None and fm.lead != u.id and fm.keep_on_station:
            add(WARNING, "Courses", f"{label}: is a member of formation '{fm.name}' and follows its lead; plot the "
                                    "course on the lead instead.", u.id)
        from .course_plan import hms, plan_course
        plan = plan_course(p, u, db)
        if plan is None:
            continue
        for lg in plan.legs:
            if lg.need_kn is not None:
                add(WARNING, "Courses", f"{label}: reaches waypoint {lg.n} about {hms(lg.diff_s)} after its time on "
                                        f"target (H+{hms(lg.target_s)}); " +
                    ("it cannot get there in time." if lg.need_kn == float("inf") else
                     f"it would need about {lg.need_kn:,.0f} kn. Use 'Time it' in the course window.") , u.id)
        if plan.tot_depart_s is not None and plan.tot_depart_s < 0:
            add(WARNING, "Courses", f"{label}: to meet its first time on target it would have to leave "
                                    f"{hms(-plan.tot_depart_s)} before the scenario starts.", u.id)
        if plan.range_nm is not None and plan.fuel_nm > plan.range_nm:
            add(WARNING, "Courses", f"{label}: the route is about {plan.fuel_nm:,.0f} nm but the estimated range "
                                    f"with its loadout is about {plan.range_nm:,.0f} nm; it may run out of fuel.",
                u.id)


def _check_forecast(p: Project, add) -> None:
    """Timed weather changes (Scenario tab > Weather Forecast...)."""
    total_min = p.clock.duration_days * 1440 + p.clock.duration_hours * 60 + p.clock.duration_minutes
    seen = {}
    for e in p.forecast:
        if e.offset_minutes <= 0:
            add(INFO, "Weather", f"A forecast change at {e.offset_minutes} min is ignored; the weather at the start is "
                                 "set above the forecast.", "")
        elif total_min and e.offset_minutes >= total_min:
            add(WARNING, "Weather", f"A forecast change at {e.offset_minutes} min comes after the scenario ends "
                                    f"({total_min} min), so it never happens.", "")
        if e.offset_minutes in seen:
            add(WARNING, "Weather", f"Two forecast changes at {e.offset_minutes} min; only one of them will stick.", "")
        seen[e.offset_minutes] = e
