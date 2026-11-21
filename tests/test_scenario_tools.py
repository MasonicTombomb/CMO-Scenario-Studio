"""Selecting several units on the map, event recipes, flight schedules, briefing packs and the scenario wizard."""
import os
import re
from datetime import datetime

import pytest

from cmo_studio.model import new_project
from cmo_studio.model.project import Course, Mission, Unit, Waypoint, Zone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TYPHOON, METEOR = 7090, 13972


def two_sided():
    p = new_project("Tools", "DB3K_519.db3")
    a, b = p.sides
    ships = [Unit(side=a.id, type="Ship", dbid=2814, name=f"FFG {i}", lat=56.0 + i * 0.1, lon=2.0) for i in range(3)]
    enemy = Unit(side=b.id, type="Ship", dbid=2814, name="Enemy FFG", lat=57.5, lon=4.0)
    jet = Unit(side=a.id, type="Aircraft", dbid=TYPHOON, name="VIPER 1", count=2, lat=56.5, lon=0.0, altitude=8000,
               speed=450, loadout=METEOR,
               course=Course([Waypoint(57.0, 2.0, name="IP", arrive_minutes=40, signal="VIPER_AT_IP"),
                              Waypoint(57.5, 3.0, name="Target")], 0, "stop"))
    p.units += ships + [enemy, jet]
    p.zones.append(Zone(side=a.id, name="BOX", points=[[56, 1], [58, 1], [58, 5], [56, 5]]))
    p.missions.append(Mission(side=a.id, name="Sea patrol", mclass="patrol", subtype="naval", zone=p.zones[0].id))
    return p, ships, enemy, jet


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
    w.resize(1400, 900)
    w.show()
    yield w, app, tmp_path
    w.doc.set_dirty(False)
    w.close()


# ------------------------------------------------------------------ several units on the map
def test_select_move_and_delete_several_units(window, monkeypatch):
    w, app, _ = window
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtWidgets import QMenu, QMessageBox
    p, ships, enemy, jet = two_sided()
    w.doc.load(p)
    mp = w.map_page
    w.tabs.setCurrentWidget(mp)
    mp.map.fit([(56.0, 1.0), (58.0, 5.0)])
    app.processEvents()
    # Ctrl-click two, then a box round all three ships
    mp.map._click(mp.map.to_screen(ships[0].lat, ships[0].lon), Qt.KeyboardModifier.ControlModifier)
    mp.map._click(mp.map.to_screen(ships[1].lat, ships[1].lon), Qt.KeyboardModifier.ControlModifier)
    assert mp.map.multi == [ships[0].id, ships[1].id]
    box = mp.map.units_in(mp.map.to_screen(55.9, 1.9), mp.map.to_screen(56.3, 2.1))
    assert set(box) == {s.id for s in ships}
    mp.map.set_multi(box)
    assert mp.selected_units() == box
    # move them all by the same amount: one undo step
    before = [(s.lat, s.lon) for s in ships]
    mp.map.groupMoved.emit(box, 0.5, -0.25)
    moved = [w.doc.project.unit(s.id) for s in ships]
    assert all(abs(m.lat - (b[0] + 0.5)) < 1e-9 and abs(m.lon - (b[1] - 0.25)) < 1e-9 for m, b in zip(moved, before))
    w.doc.undo()
    assert [(w.doc.project.unit(s.id).lat, w.doc.project.unit(s.id).lon) for s in ships] == before
    # the right-click menu for several
    menu = QMenu()
    mp._multi_menu(menu, box)
    texts = [a.text() for a in menu.actions()]
    assert texts[0] == "3 units selected" and "Same course for all..." in texts and "Delete 3 units" in texts
    # same course for all opens the course window for the first with the rest along
    import cmo_studio.ui.course_dialog as cd
    called = {}
    monkeypatch.setattr(cd, "edit_course", lambda win, uid, also=None: called.update(uid=uid, also=also))
    mp._course_for_all(box)
    assert called["uid"] == box[0] and called["also"] == box[1:]
    # add to a mission (only units of the mission's side)
    import cmo_studio.ui.widgets as wd

    class Pick:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return 1

        def selected_ids(self):
            return [w.doc.project.missions[0].id]
    monkeypatch.setattr(wd, "PickerDialog", Pick)
    mp._add_to_mission(box + [enemy.id])
    assert set(w.doc.project.missions[0].units) == set(box)
    # delete them (after asking)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    mp._delete_many(box)
    assert not any(w.doc.project.unit(i) for i in box) and mp.map.multi == []
    mp.map.grab()


def test_same_course_for_several_units(window):
    w, app, _ = window
    from cmo_studio.ui.course_dialog import CourseDialog
    p, ships, enemy, jet = two_sided()
    w.doc.load(p)
    dlg = CourseDialog(w, ships[0].id, also=[ships[1].id, ships[2].id])
    assert "and 2 more" in dlg.windowTitle()
    dlg.map.courseFinished.emit(ships[0].id, [[56.5, 3.0], [57.0, 4.0]])
    dlg.save()
    pr = w.doc.project
    assert all(len(pr.unit(s.id).course.waypoints) == 2 for s in ships)
    w.doc.undo()
    assert all(w.doc.project.unit(s.id).course is None for s in ships)


# ------------------------------------------------------------------ event recipes
def answers(p, r):
    from cmo_studio.model.event_recipes import Ask  # noqa: F401
    v = r.defaults(p)
    a, b = p.sides
    for ask in r.asks:
        if ask.kind == "unit" and not ask.optional:
            v[ask.key] = p.units[0].id
        elif ask.kind == "zone":
            v[ask.key] = p.zones[0].id
        elif ask.kind == "mission":
            v[ask.key] = p.missions[0].id
    return v


def test_every_recipe_builds_an_event_that_compiles_and_runs(lua_dll):
    from cmo_studio.export.compiler import compile_event
    from cmo_studio.model.event_recipes import RECIPES, missing_answers
    from cmo_studio.tools.lua_engine import dry_run_build
    p, ships, enemy, jet = two_sided()
    for r in RECIPES:
        v = answers(p, r)
        assert not missing_answers(r, v), r.id
        e = r.build(p, v)
        assert e.triggers and e.actions, r.id
        compile_event(p, e)                          # raises on a broken event
        p.events.append(e)
    assert p.units[0].reserve                        # 'Reinforcements arrive' made it a reinforcement
    res = dry_run_build(p, lua_dll)
    assert res.ok and "MOCK SCRIPT ERROR" not in res.output, res.output


def test_recipe_details():
    from cmo_studio.model.event_recipes import recipe
    p, ships, enemy, jet = two_sided()
    a, b = p.sides
    e = recipe("end_when_destroyed").build(p, {"unit": enemy.id, "side": a.id, "points": 50, "text": "Done"})
    assert [x.type for x in e.actions] == ["Score", "Message", "EndScenario"]
    e = recipe("end_when_destroyed").build(p, {"unit": enemy.id, "side": a.id, "points": 0, "text": "Done"})
    assert [x.type for x in e.actions] == ["Message", "EndScenario"]
    e = recipe("score_on_destroy").build(p, {"side": a.id, "target": b.id, "type": "Ship", "unit": "", "points": 5})
    assert e.repeatable and len(e.triggers) == 1 and e.triggers[0].params["TargetType"] == "Ship"
    e = recipe("mission_on_flag").build(p, {"mission": p.missions[0].id, "flag": "VIPER_AT_IP", "text": "Go"})
    assert e.conditions[0].params["Key"] == "VIPER_AT_IP" and e.actions[0].params["Active"] is True


def test_recipe_dialog(window, monkeypatch):
    w, app, _ = window
    from PyQt6.QtWidgets import QMessageBox

    from cmo_studio.ui.recipe_dialog import RecipeDialog
    told = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: told.append(a[2])))
    p, ships, enemy, jet = two_sided()
    w.doc.load(p)
    dlg = RecipeDialog(w.ctx, "area_entered", w)
    assert dlg.current.id == "area_entered" and set(dlg.inputs) >= {"zone", "target", "side", "text"}
    dlg._create()                                    # area not chosen: asks, creates nothing
    assert dlg.event is None and "Area" in told[0]
    dlg.set_value("zone", p.zones[0].id)
    dlg._create()
    assert dlg.event is not None and dlg.event in w.doc.project.events
    assert dlg.event.triggers[0].params["Area"] == p.zones[0].id


# ------------------------------------------------------------------ flight schedule and briefing pack
def test_flight_schedule():
    from cmo_studio.model.briefing_pack import dtg, flight_schedule, flight_schedule_html
    p, ships, enemy, jet = two_sided()
    a = p.sides[0]
    fl = flight_schedule(p, a.id)
    assert [f.callsign for f in fl] == ["VIPER 1"] and fl[0].count == 2 and fl[0].signals == ["VIPER_AT_IP"]
    assert fl[0].tots[0][0] == "IP" and fl[0].tots[0][1] == p.clock.start_epoch() + 40 * 60
    h = flight_schedule_html(p, a.id)
    assert "VIPER 1" in h and "VIPER_AT_IP" in h and "Time on target" in h
    assert dtg(p.clock.start_epoch()) == "010600Z JAN 30"
    assert "No units of this side" in flight_schedule_html(p, p.sides[1].id)


def test_operation_order_content():
    from cmo_studio.model.briefing_pack import DEFAULT_BANNER, opord_html, orbat_rows
    p, ships, enemy, jet = two_sided()
    a, b = p.sides
    h = opord_html(p, a.id)
    for must in ("1. Situation", "2. Mission", "3. Execution", "4. Service support", "5. Command and signal",
                 "Annex A - Intelligence summary", "Annex B - Air tasking", "Annex C - Meteorology", DEFAULT_BANNER,
                 "VIPER_AT_IP", "maritime (anti-surface) patrol", "H-hour is 010600Z JAN 30", "ACKNOWLEDGE"):
        assert must in h, must
    assert h.count("Generated from the scenario") >= 3
    # the side's own text replaces the generated paragraphs
    a.orders.mission = "Defend the North Sea gas fields."
    a.orders.operation = "OPERATION NORTHERN SHIELD"
    a.orders.classification = "EXERCISE - NATO UNCLASSIFIED"
    h = opord_html(p, a.id)
    assert "Defend the North Sea gas fields." in h and "OPERATION NORTHERN SHIELD" in h
    assert "EXERCISE - NATO UNCLASSIFIED" in h and DEFAULT_BANNER not in h
    # enemy positions: approximate by default, exact on request
    rows = orbat_rows(p, b.id, exact=False)
    assert rows[0][3] == "in the BOX area"
    a.orders.exact_positions = True
    assert re.search(r"57\.50N 4\.00E", opord_html(p, a.id))


def test_briefing_pack_pdf(tmp_path):
    from cmo_studio.export.pdf import find_browser, html_to_pdf
    from cmo_studio.model.briefing_pack import opord_html
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841 - the Qt fallback needs one
    p, *_ = two_sided()
    out = tmp_path / "pack.pdf"
    how = html_to_pdf(opord_html(p, p.sides[0].id), out)
    assert out.read_bytes()[:5] == b"%PDF-"
    assert how == ("browser" if find_browser() else "qt")


def test_briefing_pack_window(window, monkeypatch):
    w, app, _ = window
    from cmo_studio.ui.briefing_pack_dialog import BriefingPackDialog
    p, ships, enemy, jet = two_sided()
    w.doc.load(p)
    dlg = BriefingPackDialog(w.ctx, p.sides[0].id, w)
    assert "conduct" in dlg.fields["mission"].placeholderText()
    dlg.fields["mlcoa"].setPlainText("Red probes our air defences with bombers.")
    dlg.operation.setText("OPERATION TEST")
    dlg.operation.textEdited.emit("OPERATION TEST")
    o = w.doc.project.sides[0].orders
    assert o.mlcoa.startswith("Red probes") and o.operation == "OPERATION TEST"
    assert "Red probes our air defences" in dlg.html()
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dlg.to_cmo()
    assert "<h1>2. Mission</h1>" in w.doc.project.sides[0].briefing_html
    dlg._render()
    # flight schedule from the briefing editor's Insert menu
    bpage = w.briefings_page
    bpage.target = ("side", p.sides[0].id)
    bpage.editor.setPlainText("")
    bpage._schedule()
    assert "VIPER 1" in bpage.editor.toPlainText()


# ------------------------------------------------------------------ the scenario wizard
def test_wizard_builds_a_uk_scenario(database, lua_dll):
    from cmo_studio.model.scenario_wizard import WizardSpec, build_scenario, default_areas_for, default_bases
    from cmo_studio.model.validation import ERROR, validate
    from cmo_studio.tools.lua_engine import dry_run_build
    spec = WizardSpec(title="Northern Watch", db_file="DB3K_519.db3", start=datetime(2030, 3, 1, 6, 0),
                      duration_hours=30, bases=default_bases("United Kingdom"),
                      areas=default_areas_for("United Kingdom"), civilian=True)
    r = build_scenario(spec, database)
    p = r.project
    assert r.notes == []
    assert [s.name for s in p.sides] == ["United Kingdom", "Russia", "Civilian"] and p.sides[1].computer_only
    assert (p.clock.duration_days, p.clock.duration_hours) == (1, 6)
    qra = [u for u in p.units if u.type == "Aircraft" and u.side == p.sides[0].id]
    assert len(qra) == 2 and all(u.count == 4 and u.loadout and u.host for u in qra)
    assert len(p.missions) == 2 and all(m.units for m in p.missions)
    probe = next(u for u in p.units if u.side == p.sides[1].id)
    assert probe.count == 2 and len(probe.course.waypoints) == 4 and probe.course.depart_minutes == 30
    assert len(p.events) == 4
    assert not [i for i in validate(p, database) if i.level == ERROR]
    res = dry_run_build(p, lua_dll, db=database)
    assert res.ok and "MOCK API ERROR" not in res.output, res.output


def test_wizard_without_a_database_and_elsewhere():
    from cmo_studio.model.scenario_wizard import WizardSpec, build_scenario, default_areas_for, default_bases
    r = build_scenario(WizardSpec(region="Europe", preset="nato_russia", bases=default_bases("Europe"),
                                  areas=default_areas_for("Europe"), player="both"), None)
    p = r.project
    assert any("no database" in n for n in r.notes)
    assert [s.name for s in p.sides] == ["NATO", "Russia"] and not any(s.computer_only for s in p.sides)
    assert p.units and not any(u.type == "Aircraft" for u in p.units) and len(p.missions) == 2


def test_wizard_window(window, monkeypatch):
    w, app, _ = window
    from PyQt6.QtWidgets import QMessageBox

    from cmo_studio.ui.scenario_wizard import ScenarioWizard
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    wiz = ScenarioWizard(["DB3K_519.db3"], "DB3K_519.db3", None, w)
    wiz.title.setText("Quick")
    wiz.preset.setCurrentIndex(wiz.preset.findData("nato_russia"))
    assert wiz.side_a.text() == "NATO"
    wiz.region.setCurrentText("Europe")
    assert wiz.bases.count() == 2 and wiz.areas.count() > 2
    s = wiz.spec()
    assert s.region == "Europe" and s.bases == ["ab_main_operating"] and len(s.areas) == 2
    wiz._summarise()
    assert "Quick" in wiz.summary.text()
    wiz.accept()
    assert wiz.result_ is not None and wiz.result_.project.meta.title == "Quick"
    monkeypatch.setattr(ScenarioWizard, "exec", lambda self: (self.accept(), 1)[1])
    w.doc.set_dirty(False)
    w.new_from_wizard()
    assert w.doc.project.missions and w.tabs.currentWidget() is w.map_page
