"""Builds examples/Baltic Sentinel.cmoproj - a small, complete scenario that shows every feature.

    python examples/make_example.py            (writes the .cmoproj)
    python examples/make_example.py --export   (also writes examples/output/ - the exported folder)

All DBIDs and loadouts are DB3K_519 entries.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from cmo_studio.export import Exporter  # noqa: E402
from cmo_studio.model import (Action, Condition, Event, Mission, ReferencePoint, Script, SpecialAction,  # noqa: E402
                              Trigger, Unit, Variant, Zone, new_project)

TICK = """-- Tick.lua - runs every minute (event 'Clock Tick').
-- Blue scores a point for every 30 minutes Hogland island stays out of Red hands.
local last = StudioGetNumKV('BS_LAST_HOLD', STUDIO.START)
local now = tonumber(ScenEdit_CurrentTime()) or 0
if now - last >= 1800 then
  StudioSetKV('BS_LAST_HOLD', now)
  if not StudioFlag('BS_HOGLAND_LOST') then
    StudioAddScore('NATO', 1, 'Hogland held')
  end
end
"""

HELPERS = """-- Helpers.lua - loaded when the scenario loads (shared functions for events).
function BS_Sitrep(side)
  local text = string.format('<P><B>SITREP</B></P><P>NATO score: %d<BR>Russia score: %d</P>',
    StudioScore('NATO'), StudioScore('Russia'))
  StudioMsg(side, text)
end
"""


def build():
    p = new_project("Baltic Sentinel", "DB3K_519.db3")
    m = p.meta
    m.author = "CMO Scenario Studio example"
    m.setting = "Gulf of Finland"
    m.location = "Gulf of Finland and the Estonian coast"
    m.complexity, m.difficulty = 2, 3
    m.hypothetical_note = "This is a hypothetical scenario made to demonstrate CMO Scenario Studio."
    m.description_html = (
        "<P>Tension in the Gulf of Finland has been rising for weeks. A Russian surface action group has sailed "
        "from Kronstadt, and Russian aircraft are probing Finnish and Estonian airspace.</P>\n\n"
        "<P>NATO commands a Finnish and Estonian force under Allied air cover. Russia must show the flag, test the "
        "Alliance's air defences and, if ordered, seize the island of Hogland (Suursaari).</P>")
    p.clock.start = "2030-05-12T04:00:00"
    p.clock.duration_hours, p.clock.duration_days = 12, 0
    p.weather.temperature, p.weather.cloud, p.weather.sea_state = 9, 0.3, 2

    nato, rus = p.sides
    nato.name, nato.tag, nato.color = "NATO", "NATO", "#3d8bfd"
    rus.name, rus.tag, rus.color = "Russia", "RU", "#e5484d"
    nato.doctrine = {"use_nuclear_weapons": "no", "weapon_control_status_air": "Tight"}
    rus.doctrine = {"use_nuclear_weapons": "no"}
    civ = p.add_side("Civilian", "CIV", "#aaaaaa")
    civ.computer_only, civ.awareness, civ.export_briefing = True, "Blind", False

    def unit(side, utype, dbid, cls, name, lat=0.0, lon=0.0, **kw):
        u = Unit(side=side.id, type=utype, dbid=dbid, db_name=cls, name=name, lat=lat, lon=lon, **kw)
        p.units.append(u)
        return u

    # NATO
    amari = unit(nato, "Facility", 1877, "Single-Unit Airfield (1x 2401-3200m Runway)", "Amari AB", 59.260, 24.208)
    rissala = unit(nato, "Facility", 1877, "Single-Unit Airfield (1x 2401-3200m Runway)", "Rissala AB", 62.645,
                   27.785)
    unit(nato, "Aircraft", 8261, "EF-2000 Typhoon", "JG 71 Typhoon", host=amari.id, count=4, loadout=17284)
    hornets = unit(nato, "Aircraft", 2836, "F/A-18C Hornet", "HavLLv 31 Hornet", host=rissala.id, count=6,
                   loadout=16771)
    unit(nato, "Aircraft", 1626, "E-3A Sentry", "NAEW E-3A", 59.4, 21.0, altitude=9000, loadout=8076)
    hamina = unit(nato, "Ship", 4643, "Hamina", "FNS Hamina", 59.95, 25.6, radar_active=True)
    unit(nato, "Facility", 2011, "NASAMS", "NASAMS Battery Helsinki", 60.20, 24.95, radar_active=True)
    reinf = unit(nato, "Aircraft", 6180, "F-35A Lightning II", "HavLLv 11 F-35A", host=rissala.id, count=4,
                 loadout=1836, reserve=True)

    # Russia
    besovets = unit(rus, "Facility", 1712, "Single-Unit Airfield (1x 1601-2400m Runway)", "Levashovo AB", 60.088,
                    30.193)
    flankers = unit(rus, "Aircraft", 6645, "Su-35S Flanker M", "159 IAP Su-35S", host=besovets.id, count=6,
                    loadout=30249)
    unit(rus, "Aircraft", 3461, "A-50U Mainstay", "A-50U", 60.0, 31.5, altitude=9000, loadout=8060)
    sag = [unit(rus, "Ship", 2814, "Steregushchiy", n, lat, lon, radar_active=True)
           for n, lat, lon in (("Soobrazitelny", 60.02, 27.30), ("Stoikiy", 59.98, 27.45))]
    karakurt = unit(rus, "Ship", 3294, "Karakurt", "Mytishchi", 60.05, 28.20)
    s400 = unit(rus, "Facility", 1937, "S-400", "S-400 Bn Kingisepp", 59.38, 28.60, radar_active=True,
                hold_position=True)
    unit(rus, "Submarine", 771, "Kilo", "B-271 Kolpino", 59.85, 25.0, depth=60)

    # Civilians
    for i, (lat, lon) in enumerate(((59.70, 23.5), (59.85, 26.0), (59.60, 22.4))):
        unit(civ, "Ship", 2357, "Fishing vessel", f"Fishing vessel {i + 1}", lat, lon)

    # Areas
    def zone(side, name, pts, all_sides=False):
        z = Zone(side=side.id, name=name, points=pts, all_sides=all_sides)
        p.zones.append(z)
        return z

    cap_n = zone(nato, "CAP_EST", [[59.75, 23.2], [59.75, 25.4], [59.25, 25.4], [59.25, 23.2]])
    cap_f = zone(nato, "CAP_FIN", [[60.55, 25.5], [60.55, 27.5], [60.15, 27.5], [60.15, 25.5]])
    gof = zone(nato, "GOF_PATROL", [[60.15, 24.6], [60.15, 26.6], [59.75, 26.6], [59.75, 24.6]])
    ru_cap = zone(rus, "CAP_GOF", [[60.35, 27.0], [60.35, 28.8], [59.85, 28.8], [59.85, 27.0]])
    sag_area = zone(rus, "SAG_AREA", [[60.25, 26.4], [60.25, 28.0], [59.80, 28.0], [59.80, 26.4]])
    hogland = zone(rus, "HOGLAND", [[60.13, 26.92], [60.13, 27.05], [60.02, 27.05], [60.02, 26.92]], all_sides=True)
    p.reference_points.append(ReferencePoint(side=nato.id, name="OBJ Hogland", lat=60.07, lon=26.98,
                                             highlighted=True, all_sides=True))

    # Missions
    p.missions += [
        Mission(side=nato.id, name="CAP Estonia", mclass="patrol", subtype="aaw", zone=cap_n.id,
                units=[p.units[2].id], options={"OneThirdRule": True}),
        Mission(side=nato.id, name="CAP Finland", mclass="patrol", subtype="aaw", zone=cap_f.id,
                units=[hornets.id, reinf.id], options={"OneThirdRule": True}),
        Mission(side=nato.id, name="Gulf Patrol", mclass="patrol", subtype="naval", zone=gof.id, units=[hamina.id]),
        Mission(side=rus.id, name="CAP Gulf", mclass="patrol", subtype="aaw", zone=ru_cap.id, units=[flankers.id]),
        Mission(side=rus.id, name="SAG Presence", mclass="patrol", subtype="naval", zone=sag_area.id,
                units=[s.id for s in sag] + [karakurt.id]),
        Mission(side=rus.id, name="Strike Hamina", mclass="strike", subtype="sea", targets=[hamina.id],
                options={"isactive": False}),
    ]

    # Scripts, events, special actions
    p.scripts += [Script(name="Helpers", content=HELPERS, load_on_init=True,
                         notes="Shared functions, loaded with LuaInit"),
                  Script(name="Tick", content=TICK, notes="Runs every minute")]
    p.events += [
        Event(name="Welcome", triggers=[Trigger("StudioAfterDelay", {"Minutes": 1})],
              actions=[Action("Message", {"Side": "", "Text": "<P><B>Baltic Sentinel</B></P><P>Forces are at "
                                                               "readiness. Good luck.</P>"})]),
        Event(name="Clock Tick", repeatable=True, triggers=[Trigger("RegularTime", {"Interval": 4})],
              actions=[Action("RunScript", {"Script": "Tick"})]),
        Event(name="Russian losses", repeatable=True,
              triggers=[Trigger("UnitDestroyed", {"TargetSide": rus.id, "TargetType": t})
                        for t in ("Aircraft", "Ship", "Submarine", "Facility")],
              actions=[Action("Score", {"Side": nato.id, "Change": 10, "Reason": "Russian unit destroyed"})]),
        Event(name="NATO losses", repeatable=True,
              triggers=[Trigger("UnitDestroyed", {"TargetSide": nato.id, "TargetType": t})
                        for t in ("Aircraft", "Ship", "Facility")],
              actions=[Action("Score", {"Side": rus.id, "Change": 10, "Reason": "NATO unit destroyed"})]),
        Event(name="Hogland landing", triggers=[Trigger("UnitEntersArea", {"TargetSide": rus.id,
                                                                           "TargetType": "Ship",
                                                                           "Area": hogland.id})],
              conditions=[Condition("FlagNotSet", {"Key": "BS_HOGLAND_LOST"})],
              actions=[Action("SetFlag", {"Key": "BS_HOGLAND_LOST", "Value": "true"}),
                       Action("Score", {"Side": rus.id, "Change": 50, "Reason": "Russian ships at Hogland"}),
                       Action("Message", {"Side": "", "Text": "<P>Russian warships are off Hogland.</P>"})]),
        Event(name="Finnish F-35s scramble", probability=75,
              triggers=[Trigger("StudioAfterDelay", {"Minutes": 180})],
              actions=[Action("SpawnUnit", {"Unit": reinf.id}),
                       Action("Message", {"Side": nato.id, "Text": "<P>HavLLv 11 F-35As are ready at "
                                                                   "Rissala.</P>"})]),
        Event(name="Release the strike", triggers=[Trigger("StudioAfterDelay", {"Minutes": 240})],
              actions=[Action("MissionStatus", {"Mission": p.missions[-1].id, "Active": True})]),
        Event(name="Time is nearly up", triggers=[Trigger("StudioAtTime", {"Time": "2030-05-12T15:45:00"})],
              actions=[Action("Message", {"Side": "", "Text": "<P>Fifteen minutes remain.</P>"})]),
    ]
    p.special_actions += [
        SpecialAction(side=nato.id, name="SITREP", description="Show the score.", repeatable=True,
                      script="BS_Sitrep('NATO')"),
        SpecialAction(side=rus.id, name="SITREP", description="Show the score.", repeatable=True,
                      script="BS_Sitrep('Russia')"),
    ]
    p.variants += [
        Variant(name="Play as NATO", key="PLAY_NATO", computer_sides=[rus.id], scen_suffix=" - Play as NATO",
                description_html="<P><B>In this version Russia is commanded by the computer.</B></P>"),
        Variant(name="Play as Russia", key="PLAY_RUSSIA", computer_sides=[nato.id],
                scen_suffix=" - Play as Russia",
                description_html="<P><B>In this version NATO is commanded by the computer.</B></P>"),
    ]
    p.key_values["BS_VERSION"] = "1"
    nato.briefing_html = """<h1>Situation</h1>
<p>A Russian surface action group of two Steregushchiy corvettes and a Karakurt missile ship is in the eastern
Gulf of Finland, covered by Su-35S fighters and an S-400 battalion near Kingisepp.</p>

<h1>Mission</h1>
<p>Keep Allied airspace and the sea lanes open, and keep Russian warships away from Hogland.</p>

<h1>Execution</h1>
<ul>
\t<li>Weapons tight in the air until the enemy shows hostile intent.</li>
\t<li>Finnish F-35As can be readied after three hours (75% chance).</li>
</ul>

<h1>Command and Signal</h1>
<p>+10 points per Russian unit destroyed, +1 every 30 minutes Hogland stays free.</p>"""
    rus.briefing_html = """<h1>Situation</h1>
<p>NATO has deployed Typhoons to Amari and Finnish Hornets are on alert at Rissala.</p>

<h1>Mission</h1>
<p>Show the flag in the Gulf of Finland and put warships off Hogland.</p>

<h1>Execution</h1>
<p>The strike on the Finnish patrol boat is released after four hours.</p>

<h1>Command and Signal</h1>
<p>+50 for reaching Hogland, +10 per NATO unit destroyed.</p>"""
    return p


def refresh_class_names(p) -> None:
    """Use the exact DB class names if a CMO install is available (optional)."""
    try:
        from cmo_studio.db import Database
        from cmo_studio.settings import detect_cmo_dir
        cmo = detect_cmo_dir()
        path = cmo / "DB" / p.meta.db_file if cmo else None
        if not path or not path.is_file():
            return
        db = Database(path)
        for u in p.units:
            u.db_name = db.name_of(u.type, u.dbid) or u.db_name
    except Exception:  # noqa: BLE001 - names are cosmetic
        pass


if __name__ == "__main__":
    proj = build()
    refresh_class_names(proj)
    out = HERE / "Baltic Sentinel.cmoproj"
    proj.save(out)
    print("wrote", out)
    if "--export" in sys.argv:
        res = Exporter(proj).write(HERE / "output", clean=True)
        print(f"exported {len(res.written)} files to {res.root}")
