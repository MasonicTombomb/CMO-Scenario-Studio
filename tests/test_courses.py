"""Plotted courses: model, export (routes table + route manager event), the runtime in play, validation, UI."""
import os
import re

import pytest

from cmo_studio.export.compiler import compile_build_data, compile_routes
from cmo_studio.export.exporter import Exporter
from cmo_studio.model import new_project
from cmo_studio.model.project import Course, Project, Unit, Waypoint
from cmo_studio.model.templates import default_library, place_template
from cmo_studio.model.validation import ERROR, WARNING, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TYPHOON, METEOR = 7090, 13972
ROUTE = [Waypoint(58.5, -1.0, 9000, 450), Waypoint(57.0, 1.0), Waypoint(55.0, 0.5)]


def scenario():
    """Lossiemouth and Coningsby; VIPER 1 airborne with a course; TARTAN x2 at Lossiemouth departing at +30 min,
    flying the route and landing at Coningsby."""
    p = new_project("Course Test", "DB3K_519.db3")
    uk = p.sides[0]
    lib = default_library()
    for tid in ("uk_ab_lossiemouth", "uk_ab_coningsby"):
        t = lib.template(tid)
        place_template(p, t, None, uk.id, *t.location)
    hangar = next(u for u in p.units if u.name == "Lossiemouth Hangar (4x Medium)")
    con = next(u for u in p.units if u.name.startswith("Coningsby Hangar"))
    viper = Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name="VIPER 1", lat=57.0, lon=-2.0, altitude=8000,
                 loadout=METEOR, course=Course([Waypoint(w.lat, w.lon, w.altitude, w.speed) for w in ROUTE], 0, "rtb"))
    tartan = Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name="TARTAN", count=2, host=hangar.id, loadout=METEOR,
                  course=Course([Waypoint(w.lat, w.lon) for w in ROUTE], 30, "land", con.id))
    p.units += [viper, tartan]
    return p, viper, tartan, con


# ------------------------------------------------------------------ model
def test_course_round_trip_and_cleanup():
    p, viper, tartan, con = scenario()
    q = Project.from_json(p.to_json())
    t = q.unit(tartan.id)
    assert t.course.depart_minutes == 30 and t.course.finish == "land" and t.course.land_at == con.id
    assert q.unit(viper.id).course.waypoints[0].altitude == 9000
    q.remove_unit(con.id)
    assert q.unit(tartan.id).course.land_at == "" and q.unit(tartan.id).course.finish == "rtb"


# ------------------------------------------------------------------ export
def test_routes_table_and_manager_event():
    p, viper, tartan, con = scenario()
    routes = {r["id"]: r for r in compile_routes(p)}
    t = routes[tartan.id]
    assert t["names"] == ["TARTAN #1", "TARTAN #2"]
    assert t["depart"] == p.clock.start_epoch() + 30 * 60
    assert t["finish"] == "land" and t["land"]["name"] == con.name
    assert routes[viper.id]["wps"][0] == {"lat": 58.5, "lon": -1.0, "alt": 9000.0, "spd": 450.0}
    assert routes[viper.id]["wps"][1] == {"lat": 57.0, "lon": 1.0}
    assert routes[viper.id]["kind"] == "Aircraft"
    lua = Exporter(p).luainit_lua()
    assert "STUDIO.ROUTES = {" in lua and "TARTAN #2" in lua
    events = compile_build_data(p)["EVENTS"]
    tick = [e for e in events if e["name"] == "Studio: unit courses"]
    assert len(tick) == 1 and "StudioRoutesTick()" in tick[0]["script"]


def test_no_route_event_without_courses():
    p = new_project("Plain", "DB3K_519.db3")
    assert not [e for e in compile_build_data(p)["EVENTS"] if e["name"] == "Studio: unit courses"]
    assert compile_routes(p) == []


def test_land_without_a_base_falls_back_to_rtb():
    p, viper, tartan, con = scenario()
    tartan.course.land_at = ""
    assert {r["id"]: r for r in compile_routes(p)}[tartan.id]["finish"] == "rtb"


# ------------------------------------------------------------------ the runtime in play (mock CMO)
PLAY = r"""
local start = MOCK.now
local function state(id, n) return ScenEdit_GetKeyValue('STUDIO_RT_' .. id .. '_' .. n) end
local function find(name) return ScenEdit_GetUnit({ name = name }) end
print('PLAY build ' .. state('%(viper)s', 1) .. ' ' .. state('%(tartan)s', 1))
MOCK.now = start + 10 * 60; StudioRoutesTick()
print('PLAY t+10 ' .. state('%(tartan)s', 1))
MOCK.now = start + 31 * 60; StudioRoutesTick()
print('PLAY t+31 ' .. state('%(tartan)s', 1) .. ' ' .. state('%(tartan)s', 2))
StudioRoutesTick()
print('PLAY t+32 ' .. state('%(tartan)s', 1) .. ' course ' .. #(find('TARTAN #1').course or {}))
find('TARTAN #1').course = {}; find('TARTAN #2').course = {}; find('VIPER 1').course = {}
StudioRoutesTick()
local con = find('%(con)s')
print('PLAY end ' .. state('%(tartan)s', 1) .. ' ' .. state('%(viper)s', 1) .. ' landbase '
      .. tostring(find('TARTAN #1').base == con.guid))
"""


def test_play_through_launch_course_and_land(database, lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    p, viper, tartan, con = scenario()
    res = dry_run_build(p, lua_dll, db=database,
                        after=PLAY % {"viper": viper.id, "tartan": tartan.id, "con": con.name})
    out = res.output
    assert res.ok and "FAILED" not in out and "MOCK API ERROR" not in out, out
    assert re.search(r"courses given at build\s+1", out)
    assert re.search(r"courses waiting to depart\s+2", out)
    plays = [ln for ln in out.splitlines() if ln.startswith("PLAY")]
    assert plays[0] == "PLAY build enroute wait"               # airborne: course at build; parked: waiting
    assert plays[1] == "PLAY t+10 wait"                        # not yet time to go
    assert plays[2] == "PLAY t+31 launched launched"           # both copies take off at +30
    assert plays[3] == "PLAY t+32 enroute course 3"            # airborne -> given the 3-waypoint course
    assert plays[4] == "PLAY end done done landbase true"      # end of route: re-based at Coningsby, RTB


# ------------------------------------------------------------------ validation
def test_validation(database):
    p, viper, tartan, con = scenario()
    assert not [i for i in validate(p, database) if i.area == "Courses" and i.level in (ERROR, WARNING)]
    runway = next(u for u in p.units if u.name == "Coningsby Runway 07/25")
    tartan.course.land_at = runway.id
    msgs = [i.message for i in validate(p, database) if i.area == "Courses" and i.level == ERROR]
    assert any("cannot take this aircraft" in m for m in msgs)
    tower = next(u for u in p.units if u.name == "Lossiemouth Control Tower")
    tower.course = Course([Waypoint(57.0, -3.0)])
    assert any("facility cannot move" in i.message for i in validate(p, database))
    p.missions.append(__import__("cmo_studio.model.project", fromlist=["Mission"]).Mission(
        side=viper.side, name="CAP", units=[viper.id]))
    assert any("assigned to a mission" in i.message for i in validate(p, database))


# ------------------------------------------------------------------ UI
@pytest.fixture
def window(tmp_path, monkeypatch):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.show()
    yield w, app
    w.doc.set_dirty(False)
    w.close()


def test_course_window(window, monkeypatch):
    w, app = window
    from PyQt6.QtWidgets import QMessageBox

    from cmo_studio.ui.course_dialog import CourseDialog
    from cmo_studio.ui.map.map_widget import Tool
    p, viper, tartan, con = scenario()
    tartan.course = None
    w.doc.load(p)
    dlg = CourseDialog(w, tartan.id)
    dlg.show()
    app.processEvents()
    assert dlg.map.tool == Tool.COURSE and dlg.map.course_unit == tartan.id       # no course yet: plotting
    assert "no course yet" in dlg.summary.text()
    dlg.map.courseFinished.emit(tartan.id, [[58.5, -1.0], [57.0, 1.0], [55.0, 0.5]])
    assert len(dlg.course.waypoints) == 3 and dlg.sel == 0
    assert w.doc.project.unit(tartan.id).course is None                          # only the copy so far
    # leg 1: altitude, speed, radar on, weapons tight
    dlg.alt.setValue(9000)
    dlg.speed.setValue(450)
    dlg.radar.setCurrentIndex(dlg.radar.findData("active"))
    dlg.weapons.setCurrentIndex(dlg.weapons.findData("tight"))
    assert "29,528 ft" in dlg.alt_ft.text()
    # leg 2 via the map: click its waypoint, then set a wait and a signal
    dlg.map.waypointClicked.emit(tartan.id, 1)
    assert dlg.sel == 1 and dlg.leg_box.title() == "Leg to waypoint 2"
    dlg.wait.setValue(15)
    dlg.signal.setText("AT_IP")
    dlg.signal.textEdited.emit("AT_IP")
    dlg.weapons.setCurrentIndex(dlg.weapons.findData("free"))
    legs = dlg.plan.legs
    assert [lg.alt for lg in legs] == [9000.0, 9000.0, 9000.0]
    assert [lg.weapons for lg in legs] == ["tight", "free", "free"] and legs[1].wait == 15
    assert dlg.table.rowCount() == 3 and dlg.table.item(1, 6).text() == "15 min"
    # land at Coningsby: a 4th row, the leg to the base
    dlg.finish.setCurrentIndex(dlg.finish.findData("land"))
    dlg.land_at.set_current_id(con.id)
    dlg.land_at.currentIndexChanged.emit(dlg.land_at.currentIndex())
    assert dlg.table.rowCount() == 4 and dlg.plan.legs[-1].n == 0 and "Lands at" in dlg.summary.text()
    # drag, insert, reorder, remove
    dlg.map.waypointMoved.emit(tartan.id, 2, 54.5, 0.0)
    assert (dlg.course.waypoints[2].lat, dlg.course.waypoints[2].lon) == (54.5, 0.0)
    dlg.select(1)
    dlg.insert()
    assert len(dlg.course.waypoints) == 4 and dlg.course.waypoints[2].signal == "AT_IP"
    dlg.remove()
    assert len(dlg.course.waypoints) == 3
    dlg.select(0)
    dlg.same_for_all()
    assert all(x.altitude == 9000 for x in dlg.course.waypoints)
    dlg.chart.grab()
    dlg.map.grab()
    # OK: written back as one undoable step
    dlg.save()
    c = w.doc.project.unit(tartan.id).course
    assert c is not None and c.finish == "land" and c.land_at == con.id and c.waypoints[1].wait_minutes == 15
    w.doc.undo()
    assert w.doc.project.unit(tartan.id).course is None
    # Cancel with changes asks first
    dlg2 = CourseDialog(w, viper.id)
    dlg2.course.waypoints.pop()
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: asked.append(1) or QMessageBox.StandardButton.No))
    dlg2.show()
    dlg2.reject()
    assert asked and dlg2.isVisible()                                         # 'No': stays open
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dlg2.reject()
    assert not dlg2.isVisible()
    assert len(w.doc.project.unit(viper.id).course.waypoints) == 3


def test_sidebar_course_summary_and_buttons(window, monkeypatch):
    w, app = window
    import cmo_studio.ui.course_dialog as cd
    p, viper, tartan, con = scenario()
    w.doc.load(p)
    form = w.map_page.unit_form
    form.set_unit(tartan.id)
    assert "Takes off from Lossiemouth Hangar" in form.course_info.text() and "H+0:30" in form.course_info.text()
    assert form.course_btn.text() == "Edit course..."
    opened = []
    monkeypatch.setattr(cd, "edit_course", lambda win, uid: opened.append(uid))
    form.course_btn.click()
    w.map_page.set_tool(__import__("cmo_studio.ui.map.map_widget", fromlist=["Tool"]).Tool.COURSE)
    assert opened[0] == tartan.id
    form._clear_course()
    assert w.doc.project.unit(tartan.id).course is None and form.course_btn.text() == "Plot a course..."
    tower = next(u for u in w.doc.project.units if u.name == "Lossiemouth Control Tower")
    form.set_unit(tower.id)
    assert not form.course_btn.isEnabled()


def test_show_menu_layers_and_sides(window):
    w, app = window
    mp = w.map_page
    mp.courses_cb.setChecked(False)
    assert mp.map.show_courses is False
    mp.courses_cb.setChecked(True)
    assert mp.map.show_courses is True
    mp._fill_side_actions()
    mp._fill_side_actions()                                      # refilled, not duplicated
    sides = [a for a in mp.show_menu.actions() if a in mp._side_actions]
    assert [a.text() for a in sides] == [s.name for s in w.doc.project.sides]
    sides[0].setChecked(False)
    assert w.doc.project.sides[0].id in mp.map.hidden_sides


# ------------------------------------------------------------------ leg settings
def leg_scenario():
    p = new_project("Legs", "DB3K_519.db3")
    uk = p.sides[0]
    wps = [Waypoint(58.5, -1.0, 9000, 450, name="IP", radar="active", weapons="tight", engage="stay"),
           Waypoint(57.0, 1.0, 300, 520, radar="passive", ecm="active", weapons="free", engage="leave",
                    wait_minutes=10, signal="AT_TARGET"),
           Waypoint(55.0, 0.5)]
    viper = Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name="VIPER 1", lat=57.0, lon=-2.0, altitude=8000,
                 loadout=METEOR, course=Course(wps, 0, "stop"))
    p.units.append(viper)
    return p, viper


def test_leg_settings_export():
    p, viper = leg_scenario()
    wps = compile_routes(p)[0]["wps"]
    assert wps[0] == {"lat": 58.5, "lon": -1.0, "alt": 9000.0, "spd": 450.0, "name": "IP", "radar": "active",
                      "wcs": "tight", "engage": "stay"}
    assert wps[1]["wait"] == 10 and wps[1]["flag"] == "AT_TARGET" and wps[1]["ecm"] == "active"
    assert wps[2] == {"lat": 55.0, "lon": 0.5}
    q = Project.from_json(p.to_json())
    assert q.unit(viper.id).course.waypoints[1].signal == "AT_TARGET"


LEGS = r"""
local start = MOCK.now
local u = ScenEdit_GetUnit({ name = 'VIPER 1' })
local key = 'STUDIO_RT_%(id)s_1'
local function show(tag)
  print('LEG ' .. tag .. ' ' .. ScenEdit_GetKeyValue(key) .. ' leg=' .. ScenEdit_GetKeyValue(key .. '_leg')
        .. ' alt=' .. tostring(u.manualAltitude) .. ' emcon=' .. tostring(u.emcon) .. ' course=' .. #(u.course or {})
        .. ' flag=' .. ScenEdit_GetKeyValue('AT_TARGET'))
end
show('build')
table.remove(u.course, 1); StudioRoutesTick(); show('passed1')
u.course = {}; MOCK.now = start + 20 * 60; StudioRoutesTick(); show('arrived2')
MOCK.now = start + 25 * 60; u.course = {}; StudioRoutesTick(); show('circling')
MOCK.now = start + 31 * 60; StudioRoutesTick(); show('wait over')
u.course = {}; StudioRoutesTick(); show('end')
print('LEG doctrine ' .. table.concat(MOCK.unitdoctrine or {}, ','))
"""


def test_play_through_leg_settings(database, lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    p, viper = leg_scenario()
    res = dry_run_build(p, lua_dll, db=database, after=LEGS % {"id": viper.id})
    assert res.ok and "MOCK API ERROR" not in res.output, res.output
    legs = [ln for ln in res.output.splitlines() if ln.startswith("LEG")]
    assert legs[0] == "LEG build enroute leg=1 alt=9000.0 emcon=Radar=Active course=3 flag="
    assert legs[1] == "LEG passed1 enroute leg=2 alt=300.0 emcon=Radar=Passive;OECM=Active course=2 flag="
    assert legs[2] == "LEG arrived2 loiter leg=2 alt=300.0 emcon=Radar=Passive;OECM=Active course=4 flag=true"
    assert legs[3].startswith("LEG circling loiter leg=2") and legs[3].endswith("course=4 flag=true")
    assert legs[4].startswith("LEG wait over enroute leg=3") and "course=1" in legs[4]
    assert legs[5].startswith("LEG end done")
    doctrine = legs[6]
    assert "VIPER 1 weapon_control_status_air=1" in doctrine and "VIPER 1 weapon_control_status_air=0" in doctrine
    assert "ignore_plotted_course=no" in doctrine and "ignore_plotted_course=yes" in doctrine


def test_course_plan_estimates():
    from cmo_studio.model.course_plan import plan_course
    p, viper, tartan, con = scenario()
    plan = plan_course(p, tartan)
    assert plan.hosted and plan.air and plan.start_alt == 0.0
    assert [lg.n for lg in plan.legs] == [1, 2, 3, 0] and plan.legs[-1].label == f"To {con.name}"
    assert plan.depart_s == 30 * 60 and plan.legs[0].t0 == 30 * 60
    first = plan.legs[0]
    assert abs(first.t1 - first.t0 - first.nm / 450 * 3600) < 2          # typical aircraft speed when none is set
    assert plan.end_s == plan.legs[-1].t1 and abs(plan.total_nm - sum(lg.nm for lg in plan.legs)) < 1e-6
    p2, v2 = leg_scenario()
    lp = plan_course(p2, v2)
    assert [lg.alt for lg in lp.legs] == [9000.0, 300.0, 300.0]          # carried forward
    assert [lg.radar for lg in lp.legs] == [True, False, False]
    assert [lg.weapons for lg in lp.legs] == ["tight", "free", "free"]
    assert lp.legs[2].t0 == lp.legs[1].t1 + 600                           # the 10-minute wait


# ------------------------------------------------------------------ not just aircraft
SURFACE = r"""
local start = MOCK.now
local u = ScenEdit_GetUnit({ name = '%(name)s' })
local key = 'STUDIO_RT_%(id)s_1'
local function show(tag)
  print('UNIT ' .. tag .. ' ' .. ScenEdit_GetKeyValue(key) .. ' leg=' .. ScenEdit_GetKeyValue(key .. '_leg')
        .. ' speed=' .. tostring(u.manualSpeed) .. ' emcon=' .. tostring(u.emcon) .. ' course=' .. #(u.course or {})
        .. ' flag=' .. ScenEdit_GetKeyValue('%(flag)s'))
end
show('build')
MOCK.now = start + 10 * 60; StudioRoutesTick(); show('depart')
table.remove(u.course, 1); StudioRoutesTick(); show('arrived1')
MOCK.now = start + 16 * 60; StudioRoutesTick(); show('wait over')
u.course = {}; StudioRoutesTick(); show('end')
print('UNIT doctrine ' .. table.concat(MOCK.unitdoctrine or {}, ','))
"""


@pytest.mark.parametrize("utype,dbid,sensor,emcon", [("Ship", 2814, "sonar", "Sonar=Active"),
                                                    ("Submarine", 771, "sonar", "Sonar=Active"),
                                                    ("GroundUnit", 491, "radar", "Radar=Active")])
def test_ships_submarines_and_ground_units_follow_courses(database, lua_dll, utype, dbid, sensor, emcon):
    """Same route manager for every moving unit: departure time, leg speed and sensors, weapons, wait, signal."""
    from cmo_studio.tools.lua_engine import dry_run_build
    p = new_project("Surface", "DB3K_519.db3")
    first = Waypoint(56.6, 3.2, speed=12, weapons="hold", wait_minutes=5, signal="LEG1_DONE")
    setattr(first, sensor, "active")
    unit = Unit(side=p.sides[0].id, type=utype, dbid=dbid, name="MOVER", lat=56.5, lon=3.0,
                course=Course([first, Waypoint(56.8, 3.6, speed=18, weapons="free")], 10, "stop"))
    p.units.append(unit)
    res = dry_run_build(p, lua_dll, db=database, after=SURFACE % {"name": "MOVER", "id": unit.id, "flag": "LEG1_DONE"})
    assert res.ok and "MOCK API ERROR" not in res.output, res.output
    out = [ln for ln in res.output.splitlines() if ln.startswith("UNIT")]
    assert out[0] == "UNIT build wait leg= speed=nil emcon=nil course=0 flag="             # waits for H+10
    assert out[1] == f"UNIT depart enroute leg=1 speed=12.0 emcon={emcon} course=2 flag="
    assert out[2] == f"UNIT arrived1 loiter leg=1 speed=12.0 emcon={emcon} course=4 flag=true"   # holds 5 min
    assert out[3] == f"UNIT wait over enroute leg=2 speed=18.0 emcon={emcon} course=1 flag=true"
    assert out[4].startswith("UNIT end done")
    assert "MOVER weapon_control_status_surface=2" in out[5] and "MOVER weapon_control_status_land=0" in out[5]
