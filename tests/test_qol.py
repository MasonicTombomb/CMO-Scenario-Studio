"""Event timeline, search everything, and bulk editing of units."""
import os

import pytest

from cmo_studio.model import Action, Event, Mission, Trigger
from cmo_studio.model.timeline import BAND, CONDITION, POINT, REPEAT, build_timeline, parse_time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ------------------------------------------------------------------ timeline (model)
def test_parse_time_formats():
    t = parse_time("2028-03-27T03:00:00")
    assert t == parse_time("27/03/2028 03:00:00") == parse_time("27.03.2028 03:00")
    assert parse_time("nonsense") is None and parse_time("") is None


def test_event_marks(sample):
    tl = build_timeline(sample)
    rows = {r.name: r for r in tl.rows if r.kind == "event"}
    welcome = rows["Welcome"].marks[0]
    assert welcome.style == POINT and welcome.start == sample.clock.start_epoch()
    assert rows["Tank lost"].marks[0].style == CONDITION
    assert not rows["Tank lost"].timed


def test_regular_and_random_and_outside(sample):
    start = sample.clock.start_epoch()
    sample.events += [
        Event(name="Tick", repeatable=True, triggers=[Trigger("RegularTime", {"Interval": 5})],
              actions=[Action("EndScenario")]),
        Event(name="Window", triggers=[Trigger("RandomTime", {"EarliestTime": "27/03/2028 05:00:00",
                                                              "LatestTime": "27/03/2028 07:00:00"})],
              actions=[Action("EndScenario")]),
        Event(name="Too late", triggers=[Trigger("StudioAfterDelay", {"Minutes": 3 * 1440})],
              actions=[Action("EndScenario")]),
    ]
    tl = build_timeline(sample)
    rows = {r.name: r for r in tl.rows}
    tick = rows["Tick"].marks[0]
    assert tick.style == REPEAT and tick.interval == 300
    win = rows["Window"].marks[0]
    assert win.style == BAND and win.end - win.start == 7200 and win.start == start + 7200
    assert rows["Too late"].issues


def test_same_minute_clash(sample):
    for name in ("A", "B"):
        sample.events.append(Event(name=name, triggers=[Trigger("StudioAfterDelay", {"Minutes": 30})],
                                   actions=[Action("EndScenario")]))
    tl = build_timeline(sample)
    names = {e.id: e.name for e in sample.events}
    assert any({names[a], names[b]} == {"A", "B"} for a, b, _ in tl.clashes)


def test_missions_on_timeline(sample):
    m = sample.missions[0]
    m.options.update({"starttime": "27/03/2028 06:00:00", "endtime": "27/03/2028 04:00:00"})
    tl = build_timeline(sample)
    row = next(r for r in tl.rows if r.kind == "mission" and r.obj_id == m.id)
    assert row.marks[0].style == BAND and row.issues     # ends before it starts
    switched = next(r for r in tl.rows if r.kind == "mission" and r.name == "CAP West")
    assert "Switched by event 'Ship hit'" in switched.detail      # condition-triggered: listed, not plotted


# ------------------------------------------------------------------ search (model)
def test_search_finds_everything(sample):
    from cmo_studio.ui.search import collect, score
    sample.scripts[0].content += "\nfunction FindMe() end"
    hits = collect(sample)
    kinds = {h.kind for h in hits}
    assert {"Unit", "Side", "Mission", "Event", "Area", "Ref. point", "Script", "Script line",
            "Special action", "Variant"} <= kinds

    def top(q):
        ranked = sorted((h for h in hits if score(h, q.lower().split(), q.lower()) > 0),
                        key=lambda h: -score(h, q.lower().split(), q.lower()))
        return ranked[0] if ranked else None
    assert top("Amari").name == "Amari AB"
    assert top("cap west").kind == "Mission"
    assert top("findme").kind == "Script line" and top("findme").line > 0
    assert top("zzzz") is None


# ------------------------------------------------------------------ UI
@pytest.fixture
def window(tmp_path, sample):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.show()
    w.doc.load(sample)
    yield w, app
    w.doc.set_dirty(False)
    w.close()


def test_timeline_page(window):
    w, app = window
    w.tabs.setCurrentWidget(w.timeline_page)
    app.processEvents()
    page = w.timeline_page
    assert len(page.canvas.rows) >= len(w.doc.project.events)
    ev = w.doc.project.events[1]
    row = next(r for r in page.canvas.rows if r.obj_id == ev.id)
    page._open(row)
    assert w.tabs.currentWidget() is w.events_page and w.events_page.eid == ev.id


def test_goto_object_routes(window):
    w, app = window
    p = w.doc.project
    w.goto_object(p.missions[1].id)
    assert w.tabs.currentWidget() is w.missions_page and w.missions_page.mid == p.missions[1].id
    w.goto_object(p.scripts[0].id, line=1)
    assert w.tabs.currentWidget() is w.scripts_page
    w.goto_object(p.zones[0].id)
    assert w.tabs.currentWidget() is w.map_page and w.doc.selection == p.zones[0].id


def test_search_dialog_runs_command_and_opens_object(window):
    w, app = window
    from cmo_studio.ui.search import SearchDialog
    opened = []
    dlg = SearchDialog(w.doc.project, w.search_commands(), opened.append, w)
    dlg.edit.setText("tank lost")
    assert dlg.list.count() and dlg.list.item(0).text().startswith("Tank lost")
    dlg._activate(dlg.list.item(0))
    assert opened[0].kind == "Event"


def test_bulk_edit(window):
    w, app = window
    from cmo_studio.ui.bulk_edit import BulkEditDialog
    p = w.doc.project
    red = p.sides[1]
    ids = [u.id for u in p.units if u.side == red.id]
    dlg = BulkEditDialog(w.ctx, ids, w)
    checks = {cb.text(): cb for cb, _ in dlg.fields}
    checks["Rename"].setChecked(True)
    dlg.rename.setText("Red {nn} {class}")
    checks["Proficiency"].setChecked(True)
    dlg.prof.setCurrentIndex(dlg.prof.findData("Ace"))
    checks["Hold position"].setChecked(True)
    checks["Heading"].setChecked(True)
    dlg.heading.setValue(90)
    checks["Group tag"].setChecked(True)
    dlg.group.setText("OPFOR")
    dlg._apply()
    units = [p.unit(i) for i in ids]
    assert [u.name.split()[1] for u in units] == [f"{i:02d}" for i in range(1, len(ids) + 1)]
    assert all(u.proficiency == "Ace" and u.hold_position and u.heading == 90 and u.group == "OPFOR"
               for u in units)
    w.doc.undo()
    assert all(w.doc.project.unit(i).group != "OPFOR" for i in ids)


def test_bulk_change_side_cleans_links(window):
    w, app = window
    from cmo_studio.ui.bulk_edit import change_side
    p = w.doc.project
    jets = next(u for u in p.units if u.type == "Aircraft" and u.host and not u.reserve)
    m = next(x for x in p.missions if jets.id in x.units)
    change_side(p, jets, p.sides[1].id)
    assert jets.host == "" and jets.id not in m.units
    assert isinstance(Mission(), Mission)
