"""Course planning: time on target, range with the loadout, the course library, copying, weather on the timeline,
and the map clock."""
import os

import pytest

from cmo_studio.model import new_project
from cmo_studio.model.course_plan import LATE_S, plan_course, plan_times, position_at
from cmo_studio.model.project import Course, Unit, Waypoint, WeatherEntry
from cmo_studio.model.validation import WARNING, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TYPHOON, METEOR = 7090, 13972


def jet(p, wps, depart=0, finish="stop", **kw):
    u = Unit(side=p.sides[0].id, type="Aircraft", dbid=TYPHOON, name="VIPER 1", lat=57.0, lon=-2.0, altitude=8000,
             speed=450, loadout=METEOR, course=Course(wps, depart, finish), **kw)
    p.units.append(u)
    return u


# ------------------------------------------------------------------ time on target
def test_time_on_target_sets_departure_and_waits():
    p = new_project("TOT", "DB3K_519.db3")
    u = jet(p, [Waypoint(57.5, -1.0), Waypoint(58.0, 0.5, arrive_minutes=120), Waypoint(58.2, 1.5),
                Waypoint(58.5, 3.0, arrive_minutes=200)])
    plan = plan_course(p, u)
    assert plan.legs[1].target_s == 7200 and plan.legs[1].diff_s < -LATE_S          # far too early when leaving now
    assert plan.tot_depart_s == -plan.legs[1].diff_s
    done = plan_times(p, u)
    assert done[0].startswith("Departure set to H+")
    plan = plan_course(p, u)
    assert abs(plan.legs[1].diff_s) <= 60                                            # on target at waypoint 2
    assert abs(plan.legs[3].diff_s) <= LATE_S and u.course.waypoints[2].wait_minutes > 0   # waits before 4
    assert not [i for i in validate(p) if "time on target" in i.message]


def test_late_time_on_target_needs_more_speed():
    p = new_project("Late", "DB3K_519.db3")
    u = jet(p, [Waypoint(57.5, -1.0), Waypoint(60.0, 5.0, arrive_minutes=20)])
    plan = plan_course(p, u)
    late = plan.legs[1]
    assert late.diff_s > LATE_S and late.need_kn and late.need_kn > 450
    assert plan.tot_depart_s < 0
    msgs = [i.message for i in validate(p) if i.level == WARNING]
    assert any("after its time on target" in m for m in msgs)
    assert any("before the scenario starts" in m for m in msgs)
    done = plan_times(p, u)
    assert "cannot leave early enough" in done[0] and u.course.depart_minutes == 0


def test_position_at_follows_legs_waits_and_loops():
    p = new_project("Pos", "DB3K_519.db3")
    u = jet(p, [Waypoint(57.0, 0.0, wait_minutes=10), Waypoint(58.0, 0.0)], depart=5, finish="repeat")
    plan = plan_course(p, u)
    assert position_at(plan, 0)[2] == "waiting to set off"
    lat, lon, what = position_at(plan, plan.legs[0].t0 + (plan.legs[0].t1 - plan.legs[0].t0) // 2)
    assert what.startswith("heading for") and -2.0 < lon < 0.0
    assert position_at(plan, plan.legs[0].t1 + 300)[2].startswith("waiting at")
    assert position_at(plan, plan.end_s + 600)[2] == "flying the course again"


# ------------------------------------------------------------------ range
def test_range_from_the_loadout(database):
    p = new_project("Range", "DB3K_519.db3")
    near = jet(p, [Waypoint(57.5, -1.0), Waypoint(57.0, -2.0)])
    plan = plan_course(p, near, database)
    assert plan.range_nm == pytest.approx(2 * 100 + 165 / 60 * 450)                 # Meteor heavy CAP
    assert "combat radius" in plan.range_note and plan.fuel_nm < plan.range_nm
    far = jet(p, [Waypoint(62.0, 10.0, wait_minutes=60), Waypoint(66.0, 25.0), Waypoint(57.0, -2.0)])
    far.name = "LONG 1"
    pf = plan_course(p, far, database)
    assert pf.fuel_nm > pf.range_nm and pf.fuel_nm - pf.total_nm == pytest.approx(450.0)   # the wait counts
    assert any("may run out of fuel" in i.message and i.obj_id == far.id for i in validate(p, database))
    assert not any("may run out of fuel" in i.message and i.obj_id == near.id for i in validate(p, database))
    assert plan_course(p, far).range_nm is None                                     # no database: no estimate


# ------------------------------------------------------------------ weather on the timeline
def test_weather_forecast_on_the_timeline_and_issues():
    from cmo_studio.model.timeline import build_timeline
    p = new_project("Wx", "DB3K_519.db3")
    p.forecast = [WeatherEntry(60, 10.0, 5, 0.5, 3), WeatherEntry(60, 9.0, 5, 0.5, 3),
                  WeatherEntry(10 ** 5, 0.0, 0, 0.0, 0), WeatherEntry(0, 1.0, 0, 0.0, 0)]
    tl = build_timeline(p)
    row = next(r for r in tl.rows if r.kind == "weather")
    assert len(row.marks) == 3 and row.marks[0].start == tl.start + 3600
    assert "10 °C, rain 5" in row.marks[0].label and row.issues
    msgs = [(i.level, i.message) for i in validate(p) if i.area == "Weather"]
    assert any("after the scenario ends" in m for _l, m in msgs)
    assert any("Two forecast changes at 60 min" in m for _l, m in msgs)
    assert any("is ignored" in m for _l, m in msgs)
    assert not [r for r in build_timeline(p, include_weather=False).rows if r.kind == "weather"]


# ------------------------------------------------------------------ the course library
def test_route_library_round_trip(tmp_path):
    from cmo_studio.model.route_library import RouteLibrary
    lib = RouteLibrary()
    c = Course([Waypoint(56.0, 1.0, 6000, 400, name="Track A", wait_minutes=30, arrive_minutes=90)], 15, "land", "x")
    r = lib.add("Tanker track North", c)
    assert r.course.finish == "rtb" and r.course.land_at == ""                      # bases are per project
    lib.add("tanker track north", Course([Waypoint(1, 1)]))                         # same name: replaced
    assert len(lib.routes) == 1 and lib.routes[0].waypoint_count == 1
    lib.add("Lane", c)
    path = tmp_path / "routes.json"
    lib.save(path)
    back = RouteLibrary.load(path)
    assert [x.name for x in back.routes] == ["Tanker track North", "Lane"]
    assert back.routes[1].course.waypoints[0].arrive_minutes == 90
    assert RouteLibrary.load(tmp_path / "missing.json").routes == []


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
    yield w, app, tmp_path
    w.doc.set_dirty(False)
    w.close()


def test_course_window_time_it_library_and_copy(window, monkeypatch):
    w, app, tmp = window
    from PyQt6.QtWidgets import QInputDialog

    import cmo_studio.ui.course_dialog as cd
    p = new_project("UI", "DB3K_519.db3")
    u = jet(p, [Waypoint(57.5, -1.0), Waypoint(58.0, 0.5, arrive_minutes=120)])
    wing = Unit(side=p.sides[0].id, type="Aircraft", dbid=TYPHOON, name="VIPER 2", lat=57.0, lon=-2.1,
                altitude=8000, loadout=METEOR)
    ship = Unit(side=p.sides[0].id, type="Ship", dbid=2814, name="FFG", lat=56.0, lon=1.0)
    p.units += [wing, ship]
    w.doc.load(p)
    dlg = cd.CourseDialog(w, u.id)
    dlg.show()
    app.processEvents()
    assert dlg.time_btn.isEnabled()
    dlg.select(1)
    assert "early" in dlg.arrive_info.text() and "early" in dlg.table.item(1, 8).text()
    dlg.time_it()
    assert "on time" in dlg.arrive_info.text() and dlg.depart.value() == dlg.course.depart_minutes > 0
    if w.ctx.db is not None:
        assert "range" in dlg.range_label.text().lower()
    dlg.arrive.setValue(-1)                                                   # 'any time'
    assert dlg.course.waypoints[1].arrive_minutes is None and not dlg.time_btn.isEnabled()
    # save to and use from the library
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Strike route", True)))
    dlg.save_to_library()
    assert (tmp / "routes.json").is_file()

    class Pick:
        def __init__(self, lib, parent=None):
            self.chosen, self.append, self.changed = lib.routes[0], True, False

        def exec(self):
            return 1
    monkeypatch.setattr(cd, "RoutePickDialog", Pick)
    dlg.load_from_library()
    assert len(dlg.course.waypoints) == 4                                     # added to the end

    class Picker:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return 1

        def selected_ids(self):
            return [wing.id, ship.id]
    monkeypatch.setattr(cd, "PickerDialog", Picker)
    dlg.finish.setCurrentIndex(dlg.finish.findData("land"))
    dlg.copy_to_units()
    assert dlg.copied_to == {wing.id, ship.id}
    dlg.save()
    pr = w.doc.project
    assert len(pr.unit(u.id).course.waypoints) == 4
    assert len(pr.unit(wing.id).course.waypoints) == 4 and pr.unit(ship.id).course.finish == "stop"
    w.doc.undo()                                                              # one step for all of it
    assert pr is not w.doc.project and w.doc.project.unit(wing.id).course is None


def test_map_clock_shows_units_weather_and_events(window):
    w, app, _ = window
    from cmo_studio.model.project import Action, Event, Trigger
    p = new_project("Clock", "DB3K_519.db3")
    u = jet(p, [Waypoint(57.0, 2.0), Waypoint(58.0, 4.0)], depart=10)
    p.forecast = [WeatherEntry(30, 4.0, 20, 0.9, 6)]
    p.events.append(Event(name="Raid warning", triggers=[Trigger("StudioAfterDelay", {"Minutes": 20})],
                          actions=[Action("Message", {"Text": "x"})]))
    w.doc.load(p)
    mp = w.map_page
    assert mp.clock.maximum() > 60 and mp.map.clock_ghosts == []
    mp.clock.setValue(5)
    assert [g.status for g in mp.map.clock_ghosts] == ["waiting to set off"]
    assert "no timed event yet" in mp.clock_info.text() and "as at the start" in mp.clock_info.text()
    mp.clock.setValue(25)
    g = mp.map.clock_ghosts[0]
    assert g.unit_id == u.id and g.status.startswith("heading for") and g.lon > -2.0
    mp.clock.setValue(40)                                         # about 29 min of flying after H+0:10: done
    assert mp.map.clock_ghosts[0].status == "course finished"
    assert "4 °C, rain 20" in mp.clock_info.text() and "'Raid warning'" in mp.clock_info.text()
    assert mp.map.clock_text.startswith("H+0:40")
    mp.map.grab()
    mp.clock.setValue(0)
    assert mp.map.clock_ghosts == [] and mp.map.clock_text == ""
