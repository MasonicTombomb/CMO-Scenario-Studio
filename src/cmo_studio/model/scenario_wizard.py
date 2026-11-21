"""Build a working scenario skeleton from a few choices (the New Scenario wizard).

:func:`build_scenario` makes the sides, bases (real UK sites, or a generic air base elsewhere), fighter squadrons
with an air-to-air loadout, patrol areas with combat air patrol missions, an enemy bomber probe on a plotted course,
and the usual events - everything the studio can then edit. Without a database the aircraft are left out (noted in
the result).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..geo import destination
from .area_library import add_area, default_library as default_areas, suggested_mission
from .event_recipes import recipe
from .project import Course, Project, Unit, Waypoint, new_project
from .templates import default_library as default_templates, place_templates

#: (side A, side B, tag A, tag B, colour A, colour B, fighter A, fighter B, bomber B)
PRESETS = {
    "uk_russia": ("United Kingdom", "Russia", "UK", "RU", "#3d8bfd", "#e5484d", "Typhoon FGR.4", "Su-35S", "Tu-95MS"),
    "nato_russia": ("NATO", "Russia", "NATO", "RU", "#3d8bfd", "#e5484d", "F-35A", "Su-35S", "Tu-95MS"),
    "blue_red": ("Blue", "Red", "BLUE", "RED", "#3d8bfd", "#e5484d", "F-35A", "Su-35S", "Tu-160"),
}
PRESET_LABELS = {"uk_russia": "United Kingdom v Russia", "nato_russia": "NATO v Russia", "blue_red": "Blue v Red"}


@dataclass
class WizardSpec:
    title: str = "New Scenario"
    setting: str = ""
    db_file: str = ""
    start: Optional[datetime] = None            # UTC; None keeps the default
    duration_hours: int = 12
    preset: str = "uk_russia"
    side_a: str = ""                            # names: blank -> the preset's
    side_b: str = ""
    player: str = "a"                           # a | b | both  (the other side is computer-controlled)
    civilian: bool = False
    region: str = "United Kingdom"
    bases: list[str] = field(default_factory=list)      # template ids for side A
    squadron: int = 4                                   # fighters per base (0: none)
    areas: list[str] = field(default_factory=list)      # area library ids: patrol areas + CAP missions for side A
    probe: bool = True                                  # side B bomber probe on a plotted course
    events: bool = True                                 # welcome, points for kills, 15 minutes left


@dataclass
class WizardResult:
    project: Project
    notes: list[str] = field(default_factory=list)


def uk_air_bases() -> list[tuple[str, str]]:
    return [(t.id, t.name) for t in default_templates().templates if t.category == "UK - Air bases"]


def region_areas(region: str) -> list[tuple[str, str]]:
    return [(a.id, a.name) for a in default_areas().areas if a.region == region and a.kind == "air"]


def default_bases(region: str) -> list[str]:
    return ["uk_ab_lossiemouth", "uk_ab_coningsby"] if region == "United Kingdom" else ["ab_main_operating"]


def default_areas_for(region: str) -> list[str]:
    ids = [a for a, _n in region_areas(region)]
    if region == "United Kingdom":
        return [a for a in ("uk_qra_north", "uk_qra_south") if a in ids]
    return ids[:2]


def _pick(db, query: str, year: int):
    """The newest database entry matching ``query`` in service by ``year`` (not a navalised/test variant)."""
    if db is None:
        return None
    try:
        found = [e for e in db.search("Aircraft", query, year=year)
                 if not any(w in e.name for w in ("Navalized", "Navalised", "Prototype", "Test"))]
    except Exception:  # noqa: BLE001
        return None
    if not found:
        return None
    dated = [e for e in found if 0 < (getattr(e, "year", 0) or 0) <= year]
    return max(dated, key=lambda e: e.year) if dated else found[0]


def _loadout(db, aircraft_id: int, prefer: str) -> int:
    try:
        los = db.loadouts(aircraft_id, combat_only=True)
    except Exception:  # noqa: BLE001
        return 0
    ok = [lo for lo in los if "nuclear" not in lo.name.lower()]
    best = next((lo for lo in ok if prefer.lower() in lo.name.lower()), None) or (ok[0] if ok else None)
    return best.id if best else 0


def _hosts_by_room(p: Project, units: list[Unit], db, ac_id: int) -> list[tuple[Unit, int]]:
    from .enums import HOST_TYPES
    from .hosting import room_for
    prof = db.aircraft_profile(ac_id) if db is not None else None
    out = []
    for u in units:
        if u.type not in HOST_TYPES or not u.dbid:
            continue
        room = room_for(db.aircraft_spaces(u.type, int(u.dbid)), prof) if prof is not None else 0
        if room > 0:
            out.append((u, room))
    return sorted(out, key=lambda x: -x[1])


def build_scenario(spec: WizardSpec, db=None) -> WizardResult:
    preset = PRESETS.get(spec.preset, PRESETS["blue_red"])
    p = new_project(spec.title.strip() or "New Scenario", spec.db_file)
    res = WizardResult(p)
    a, b = p.sides
    a.name, b.name = spec.side_a.strip() or preset[0], spec.side_b.strip() or preset[1]
    a.tag, b.tag, a.color, b.color = preset[2], preset[3], preset[4], preset[5]
    a.computer_only = spec.player == "b"
    b.computer_only = spec.player == "a"
    p.meta.setting = spec.setting or p.meta.setting
    p.meta.location = spec.setting or spec.region
    if spec.start is not None:
        p.clock.start = spec.start.strftime("%Y-%m-%dT%H:%M:%S")
    p.clock.duration_days, rem = divmod(max(1, int(spec.duration_hours)), 24)
    p.clock.duration_hours, p.clock.duration_minutes = rem, 0
    if spec.civilian:
        civ = p.add_side("Civilian", "CIV", "#aaaaaa")
        civ.computer_only, civ.awareness, civ.export_briefing = True, "Blind", False
    year = p.clock.start_dt().year

    # bases and squadrons for side A
    tlib = default_templates()
    tpls = [tlib.template(t) for t in spec.bases if tlib.template(t)]
    areas_lib = default_areas()
    chosen_areas = [areas_lib.area(x) for x in spec.areas if areas_lib.area(x)]
    centre = None
    if chosen_areas:
        pts = [pt for ar in chosen_areas for pt in ar.points]
        centre = (sum(x[0] for x in pts) / len(pts), sum(x[1] for x in pts) / len(pts))
    anchor = centre or (55.0, -2.0)
    placed = place_templates(p, tpls, db, a.id, *destination(anchor[0], anchor[1], 225.0, 150.0)) if tpls else []
    fighters: list[Unit] = []
    fighter = _pick(db, preset[6], year) if spec.squadron > 0 else None
    if spec.squadron > 0 and fighter is None:
        res.notes.append("No fighters added: " + ("no database chosen." if db is None else
                                                  f"'{preset[6]}' is not in this database."))
    lo = _loadout(db, fighter.id, "A/A") if fighter else 0
    for t, placed_res in placed:
        if fighter is None:
            break
        hosts = _hosts_by_room(p, placed_res.units, db, fighter.id)
        left, k = spec.squadron, 1
        for host, room in hosts:
            if left <= 0:
                break
            n = min(left, room)
            u = Unit(side=a.id, type="Aircraft", dbid=fighter.id, db_name=fighter.name, count=n, host=host.id,
                     name=p.unique_unit_name(f"{(t.site or t.name)} QRA" + (f" {k}" if k > 1 else ""), a.id),
                     loadout=lo or None)
            p.units.append(u)
            fighters.append(u)
            left -= n
            k += 1
        if left > 0:
            res.notes.append(f"{t.name}: room for only {spec.squadron - left} of {spec.squadron} {fighter.name}.")

    # patrol areas and combat air patrols for side A, with the squadrons on them
    missions = []
    for ar in chosen_areas:
        r = add_area(p, ar, a.id, mission=suggested_mission(ar))
        if r.mission is not None:
            missions.append(r.mission)
    for i, m in enumerate(missions):
        m.units = [u.id for k, u in enumerate(fighters) if k % len(missions) == i]

    # side B: a bomber probe on a plotted course through the area and home again
    if spec.probe:
        bomber = _pick(db, preset[8], year)
        if bomber is None:
            res.notes.append("No bomber probe: " + ("no database chosen." if db is None else
                                                     f"'{preset[8]}' is not in this database."))
        else:
            c = centre or anchor
            start = destination(c[0], c[1], 30.0, 900.0)
            wps = [Waypoint(*map(lambda v: round(v, 4), destination(c[0], c[1], 20.0, 350.0)), 9000, 450, name="Entry",
                           radar="passive"),
                   Waypoint(*map(lambda v: round(v, 4), destination(c[0], c[1], 300.0, 150.0)), name="Probe",
                            signal="BEAR_PROBE"),
                   Waypoint(*map(lambda v: round(v, 4), destination(c[0], c[1], 250.0, 450.0)), name="Turn"),
                   Waypoint(round(start[0], 4), round(start[1], 4), name="Exit")]
            u = Unit(side=b.id, type="Aircraft", dbid=bomber.id, db_name=bomber.name, count=2,
                     name=p.unique_unit_name(f"{bomber.name.split()[0]} probe", b.id), lat=round(start[0], 4),
                     lon=round(start[1], 4), altitude=9000, loadout=_loadout(db, bomber.id, "Conventional") or None,
                     course=Course(wps, 30, "stop"))
            p.units.append(u)

    # events
    if spec.events:
        for rid, vals in (("timed_message", {"minutes": 1, "side": "", "title": "Welcome",
                                             "text": f"{p.meta.title}: the scenario has begun."}),
                          ("score_on_destroy", {"side": a.id, "target": b.id, "type": "", "unit": "", "points": 10,
                                                "reason": f"{b.name} unit destroyed"}),
                          ("score_on_destroy", {"side": b.id, "target": a.id, "type": "", "unit": "", "points": 10,
                                                "reason": f"{a.name} unit destroyed"}),
                          ("time_limit", {"warn": 15, "text": "Fifteen minutes remain."})):
            p.events.append(recipe(rid).build(p, vals))
    return res


__all__ = ["PRESETS", "PRESET_LABELS", "WizardSpec", "WizardResult", "build_scenario", "uk_air_bases",
           "region_areas", "default_bases", "default_areas_for"]
