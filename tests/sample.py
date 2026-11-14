"""A small but complete project used by the tests (and as a smoke-test fixture)."""
from cmo_studio.model import (Action, Condition, Event, Mission, ReferencePoint, Script, SpecialAction, Trigger,
                              Unit, Variant, Zone, new_project)


def make_sample():
    p = new_project("Test Scenario", "DB3K_519.db3")
    p.meta.author = "Studio Tests"
    p.meta.setting = "Baltic Sea"
    p.clock.start = "2028-03-27T03:00:00"
    blue, red = p.sides
    civ = p.add_side("Civilian", "CIV", "#aaaaaa")
    civ.computer_only = True
    base = Unit(side=blue.id, type="Facility", dbid=1592, db_name="Single-Unit Airfield", name="Amari AB",
                lat=59.26, lon=24.21)
    p.units.append(base)
    jets = Unit(side=blue.id, type="Aircraft", dbid=6180, name="F-35A Flight", count=4, host=base.id, loadout=1836)
    p.units.append(jets)
    awacs = Unit(side=blue.id, type="Aircraft", dbid=1626, name="E-3A", lat=58.0, lon=22.0, altitude=9000, loadout=8076)
    p.units.append(awacs)
    ship = Unit(side=red.id, type="Ship", dbid=2814, name="Steregushchiy", lat=59.8, lon=26.5, radar_active=True)
    p.units.append(ship)
    sub = Unit(side=red.id, type="Submarine", dbid=771, name="Kilo", lat=59.5, lon=21.0, depth=60)
    p.units.append(sub)
    tank = Unit(side=red.id, type="Facility", dbid=1919, name="Tank Plt", lat=59.37, lon=28.17, hold_position=True)
    p.units.append(tank)
    reinf = Unit(side=blue.id, type="Aircraft", dbid=6180, name="Reinforcement F-35", count=2, host=base.id,
                 loadout=1836, reserve=True)
    p.units.append(reinf)
    cap = Zone(side=blue.id, name="CAP_WEST", points=[[59.6, 23.6], [59.6, 25.4], [58.7, 25.4], [58.7, 23.6]])
    p.zones.append(cap)
    area = Zone(side=red.id, name="NARVA", points=[[59.45, 28.0], [59.45, 28.3], [59.3, 28.3], [59.3, 28.0]],
                all_sides=True)
    p.zones.append(area)
    p.reference_points.append(ReferencePoint(side=blue.id, name="OBJ Narva", lat=59.377, lon=28.19,
                                             highlighted=True, all_sides=True))
    p.missions.append(Mission(side=blue.id, name="CAP West", mclass="patrol", subtype="aaw", zone=cap.id,
                              units=[jets.id, reinf.id], options={"OneThirdRule": True}))
    p.missions.append(Mission(side=blue.id, name="AEW Orbit", mclass="support", zone=cap.id, units=[awacs.id]))
    p.missions.append(Mission(side=blue.id, name="Strike Tanks", mclass="strike", subtype="land", units=[],
                              targets=[tank.id]))
    p.scripts.append(Script(name="Helpers", content="function Hello() StudioLog('hello') end", load_on_init=True))
    p.events.append(Event(name="Welcome", triggers=[Trigger("StudioAfterDelay", {"Minutes": 0})],
                          actions=[Action("Message", {"Side": blue.id, "Text": "<p>Good luck]] commander</p>"}),
                                   Action("RunScript", {"Script": "Helpers"})]))
    p.events.append(Event(name="Tank lost", repeatable=True,
                          triggers=[Trigger("UnitDestroyed", {"TargetSide": red.id, "TargetType": "Facility"})],
                          conditions=[Condition("FlagNotSet", {"Key": "DONE"})],
                          actions=[Action("Score", {"Side": blue.id, "Change": 10, "Reason": "Tank destroyed"})]))
    p.events.append(Event(name="Enter Narva", probability=50,
                          triggers=[Trigger("UnitEntersArea", {"TargetSide": blue.id, "Area": area.id})],
                          actions=[Action("SpawnUnit", {"Unit": reinf.id}), Action("LuaScript", {"Code": "Hello()"}),
                                   Action("EndScenario")]))
    p.events.append(Event(name="Ship hit", triggers=[Trigger("UnitDamaged", {"SpecificUnit": ship.id,
                                                                              "DamagePercent": 25})],
                          actions=[Action("MissionStatus", {"Mission": p.missions[0].id, "Active": False})]))
    p.special_actions.append(SpecialAction(side=blue.id, name="SITREP", description="Report",
                                           script="StudioMsg('Blue', 'Score: ' .. StudioScore('Blue'))"))
    p.variants.append(Variant(name="Play as Blue", key="PLAY_BLUE", computer_sides=[red.id],
                              scen_suffix=" - Play as Blue", description_html="<P>Red is the computer.</P>"))
    p.key_values["MY_KEY"] = "42"
    return p


def make_sample_with_formation():
    from cmo_studio.model import Formation
    from cmo_studio.model.formations import apply_formation
    p = make_sample()
    red = p.sides[1]
    lead = next(u for u in p.units if u.type == "Ship")
    escorts = [Unit(side=red.id, type="Ship", dbid=2814, name=f"Escort {i}", lat=lead.lat, lon=lead.lon)
               for i in range(1, 5)]
    p.units += escorts
    f = Formation(name="Red SAG", side=red.id, preset="circular_screen", lead=lead.id,
                  members=[u.id for u in escorts], spacing_nm=3.0, heading=270)
    p.formations.append(f)
    apply_formation(p, f)
    return p
