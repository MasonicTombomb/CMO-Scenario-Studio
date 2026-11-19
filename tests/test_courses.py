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
    assert routes[viper.id]["wps"][0] == [58.5, -1.0, 9000.0, 450.0]
    assert routes[viper.id]["wps"][1][2:] == [False, False]
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


def test_plot_course_on_the_map_and_edit_it(window):
    w, app = window
    from cmo_studio.ui.map.map_widget import Tool
    p = new_project("UI", "DB3K_519.db3")
    ship = Unit(side=p.sides[0].id, type="Ship", dbid=752, name="HMS Montrose", lat=60.0, lon=-3.0)
    p.units.append(ship)
    w.doc.load(p)
    mp = w.map_page
    w.tabs.setCurrentWidget(mp)
    w.doc.select(ship.id)
    mp.set_tool(Tool.COURSE)
    assert mp.map.tool == Tool.COURSE and mp.map.course_unit == ship.id
    mp.map.courseFinished.emit(ship.id, [[60.5, -2.0], [61.0, -1.0]])
    u = w.doc.project.unit(ship.id)
    assert [(wp.lat, wp.lon) for wp in u.course.waypoints] == [(60.5, -2.0), (61.0, -1.0)]
    assert mp.map.tool == Tool.SELECT or mp.tool_actions[Tool.SELECT].isChecked()
    mp.map.waypointMoved.emit(ship.id, 1, 61.2, -0.5)
    assert (u.course.waypoints[1].lat, u.course.waypoints[1].lon) == (61.2, -0.5)
    form = mp.unit_form
    form.set_unit(ship.id)
    assert form.wps.rowCount() == 2 and "2 waypoint(s)" in form.course_info.text()
    form.wps.item(0, 3).setText("18")                            # speed at waypoint 1
    assert u.course.waypoints[0].speed == 18.0
    form.finish.setCurrentIndex(form.finish.findData("repeat"))
    assert u.course.finish == "repeat"
    form._wp_reverse()
    assert u.course.waypoints[0].lat == 61.2
    w.doc.undo()
    assert w.doc.project.unit(ship.id).course.waypoints[0].lat == 60.5
    form._wp_clear()
    assert w.doc.project.unit(ship.id).course is None
    mp.map.grab()                                                # draws without errors


# ------------------------------------------------------------------ timeline
def test_timeline_course_rows():
    from cmo_studio.model.timeline import POINT, build_timeline
    p, viper, tartan, con = scenario()
    tl = build_timeline(p)
    rows = {r.obj_id: r for r in tl.rows if r.kind == "course"}
    assert set(rows) == {viper.id, tartan.id}
    t = rows[tartan.id]
    assert t.marks[0].style == POINT and t.marks[0].start == tl.start + 30 * 60
    assert t.marks[0].label == "takes off" and f"Lands at {con.name}" in t.detail and not t.issues
    assert rows[viper.id].marks[0].label == "sets off"
    tartan.course.depart_minutes = 10 ** 6
    assert any("after the scenario ends" in i for i in {r.obj_id: r for r in build_timeline(p).rows}[tartan.id].issues)
    assert not [r for r in build_timeline(p, include_courses=False).rows if r.kind == "course"]


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
