"""Aircraft must be able to taxi: runway access points in the templates, the check, and the repair."""
import os

import pytest

from cmo_studio.model import new_project
from cmo_studio.model.airbase import (LABEL, access_positions, add_missing_access, broken_sites, cannot_fly, repair,
                                      sites)
from cmo_studio.model.project import Unit
from cmo_studio.model.templates import default_library, place_template
from cmo_studio.model.validation import ERROR, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TYPHOON, TU95 = 334, 447


def base(tid="uk_ab_lossiemouth", old=False, db=None):
    """A placed base; ``old`` as templates were before they had access points."""
    p = new_project("Bases", "DB3K_519.db3")
    t = default_library().template(tid)
    if old:
        t.components = [c for c in t.components if c.label != LABEL]
    res = place_template(p, t, db, p.sides[0].id, *(t.location or (58.0, 24.0)), heading=t.heading)
    return p, res


def put(p, res, dbid=TYPHOON, kind="Hangar (4x Large)"):
    host = next(u for u in res.units if kind in u.name)
    u = Unit(side=p.sides[0].id, type="Aircraft", dbid=dbid, name="JACKAL 11", host=host.id)
    p.units.append(u)
    return u


def test_every_template_airbase_lets_its_aircraft_taxi(database):
    """All 46 UK bases shipped without a runway access point: aircraft waited for a taxiway for ever."""
    checked = 0
    for t in default_library().templates:
        p = new_project("T", "DB3K_519.db3")
        place_template(p, t, database, p.sides[0].id, 55.0, 1.0)
        assert not broken_sites(p, database), t.id
        checked += any(s.runways and s.parking for s in sites(p, database))
    assert checked >= 60


def test_access_points_lie_beside_the_runway_on_the_parking_side():
    pts = access_positions([(0, 0, 0, 2600), (500, 0, 90, 1400)], [(300, 100)])
    assert len(pts) == 6                                    # four on the longest, two on the other
    assert all(abs(x - 80) < 0.1 and abs(y) < 1000 for x, y in pts[:4])
    assert access_positions([(0, 0, 0, 2600)], [(-300, 0)])[0][0] < 0


def test_aircraft_at_an_old_base_are_reported_and_repaired(database):
    p, res = base(old=True, db=database)
    u = put(p, res)
    stuck = cannot_fly(p, database)
    assert [x[0].id for x in stuck] == [u.id] and "access point" in stuck[0][2]
    errs = [i for i in validate(p, database) if i.area == "Air bases" and i.level == ERROR]
    assert errs and "can never take off" in errs[0].message and errs[0].obj_id == u.id
    n, f = len(p.units), p.formations[0]
    members = len(f.members)
    done = repair(p, database)
    assert "6 runway access points" in done[0] and len(p.units) == n + 6
    assert len(f.members) == members + 6 == len(f.params["stations"])     # in the CMO group, with stations
    assert not cannot_fly(p, database) and not broken_sites(p, database) and repair(p, database) == []


def test_ungrouped_base_and_runway_too_short(database):
    p, res = base(db=database)
    put(p, res)
    assert not cannot_fly(p, database)
    res.formation.group_in_cmo = False
    assert "not one CMO group" in cannot_fly(p, database)[0][2]
    repair(p, database)
    assert res.formation.group_in_cmo and not cannot_fly(p, database)
    p2, res2 = base("ab_expeditionary", db=database)
    host = next(u for u in res2.units if "Parking" in u.name)
    p2.units.append(Unit(side=p2.sides[0].id, type="Aircraft", dbid=TU95, name="BEAR", host=host.id))
    assert cannot_fly(p2, database)                         # far too big for the strip


def test_single_unit_airfields_are_left_alone(database):
    p, res = base("af_strip_900", db=database)
    host = next(u for u in res.units if "Airfield" in u.name)
    p.units.append(Unit(side=p.sides[0].id, type="Aircraft", dbid=TYPHOON, name="V", host=host.id))
    assert not broken_sites(p, database) and not cannot_fly(p, database)


def test_dry_run_reports_aircraft_that_cannot_take_off(database, lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    p, res = base(old=True, db=database)
    put(p, res)
    assert any("can never take off" in e for e in dry_run_build(p, lua_dll, db=database).errors)
    repair(p, database)
    r = dry_run_build(p, lua_dll, db=database)
    assert r.ok and not any("take off" in e for e in r.errors)


def test_saved_libraries_get_the_access_points():
    lib = default_library()
    old = default_library()
    t = old.template("uk_ab_coningsby")
    t.components = [c for c in t.components if c.label != LABEL]
    assert add_missing_access(old, lib) == 1 and any(c.label == LABEL for c in t.components)
    assert add_missing_access(old, lib) == 0


def test_trimingham_is_on_land_where_cmo_puts_it():
    t = next(t for t in default_library().templates if "Trimingham" in t.name)
    assert t.location == pytest.approx([52.893037, 1.400577], abs=1e-4)


def test_repair_from_the_menu_is_one_undo(database, tmp_path, monkeypatch):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    w = MainWindow(s)
    w.dbm.db = database
    p, res = base(old=True, db=database)
    put(p, res)
    w.doc.load(p)
    n = len(w.doc.project.units)
    Box = QtWidgets.QMessageBox
    monkeypatch.setattr(Box, "question", staticmethod(lambda *a, **k: Box.StandardButton.No))
    w.repair_airbases(ask=True)
    assert len(w.doc.project.units) == n                     # declined: nothing changes
    monkeypatch.setattr(Box, "question", staticmethod(lambda *a, **k: Box.StandardButton.Yes))
    w.repair_airbases(ask=True)
    assert len(w.doc.project.units) == n + 6
    w.doc.undo()
    assert len(w.doc.project.units) == n
    w.dbm.db = None
    w.doc.set_dirty(False)
    w.close()
