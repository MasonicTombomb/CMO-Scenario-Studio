"""Unit templates: library, DB resolution, placement, saving units as a template, dialogs."""
import json
import math
import os

import pytest

from cmo_studio.geo import distance_km
from cmo_studio.model import new_project
from cmo_studio.model.formations import apply_formation, move_with_formation
from cmo_studio.model.templates import (TemplateComponent, TemplateLibrary, UnitTemplate, default_library,
                                        default_library_text, load_library, place_template, resolve,
                                        template_from_units)
from cmo_studio.model.validation import ERROR, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def lib():
    return default_library()


def test_library_shape(lib):
    data = json.loads(default_library_text())
    assert data["format"] == "cmo-studio-templates"
    assert len(lib.templates) >= 70
    cats = set(lib.all_categories())
    for must in ("Airfields (single unit)", "Airfields (multi unit)", "Command and control", "Communications and EW",
                 "Garrisons and bases", "Logistics", "Naval", "Infrastructure"):
        assert must in cats
    ids = [t.id for t in lib.templates]
    assert len(ids) == len(set(ids))
    for t in lib.templates:
        assert t.components and all(c.db_name and c.positions for c in t.components), t.id


def test_roundtrip(lib, tmp_path):
    path = tmp_path / "t.json"
    lib.save(path)
    again, source = load_library(path)
    assert source == str(path) and again.to_dict()["templates"] == lib.to_dict()["templates"]


def test_every_component_resolves_in_db3000(lib, database):
    missing = [(t.id, c.label) for t in lib.templates for c in t.components if resolve(database, c) is None]
    assert missing == []
    by_hint = sum(1 for t in lib.templates for c in t.components if resolve(database, c).how == "dbid")
    assert by_hint == sum(len(t.components) for t in lib.templates)


def test_resolve_falls_back_to_name_and_search(database):
    wrong_id = TemplateComponent("Tower", db_name="Building (Control Tower)", dbid=999999)
    assert resolve(database, wrong_id).how == "name"
    only_words = TemplateComponent("Barracks", db_name="", search="Building Barracks")
    r = resolve(database, only_words)
    assert r.how == "search" and "Barracks" in r.name
    assert resolve(database, TemplateComponent("X", db_name="No Such Facility")) is None


def test_place_creates_group_and_geometry(lib):
    p = new_project()
    side = p.sides[0].id
    t = lib.template("ab_tactical_has")
    res = place_template(p, t, None, side, 59.0, 24.0, heading=90, site_name="Amari")
    assert len(res.units) == t.unit_count and not res.skipped
    f = res.formation
    assert f and f.name == "Amari" and not f.set_stations and f.group_in_cmo
    lead = p.unit(f.lead)
    assert lead.name == "Amari HAS 1"                         # host component leads the group
    tower = next(u for u in res.units if u.name == "Amari Control Tower")
    runway = next(u for u in res.units if u.name == "Amari Runway")
    # the tower is 350 m right of the runway; heading 090 puts it due south
    assert distance_km(runway.lat, runway.lon, tower.lat, tower.lon) * 1000 == pytest.approx(350, abs=2)
    assert tower.lat < runway.lat and tower.lon == pytest.approx(runway.lon, abs=1e-4)
    assert all(u.heading == 90 for u in res.units)
    # formation stations reproduce the template layout
    before = {u.id: (u.lat, u.lon) for u in res.units}
    apply_formation(p, f)
    for u in res.units:
        assert (u.lat, u.lon) == pytest.approx(before[u.id], abs=2e-5)
    # moving any part moves the site
    move_with_formation(p, tower.id, tower.lat + 0.1, tower.lon)
    assert runway.lat == pytest.approx(before[runway.id][0] + 0.1, abs=2e-4)
    assert [i.message for i in validate(p) if i.level == ERROR] == []


def test_place_twice_gets_unique_names(lib):
    p = new_project()
    side = p.sides[0].id
    t = lib.template("c2_field_cp")
    place_template(p, t, None, side, 50, 10, site_name="Alpha")
    r2 = place_template(p, t, None, side, 50.1, 10, site_name="Alpha")
    names = [u.name for u in p.units]
    assert len(names) == len(set(names)) and r2.formation.name == "Alpha 2"


def test_skips_unresolvable(database):
    p = new_project()
    t = UnitTemplate("x", "X", components=[TemplateComponent("Good", db_name="Building (Barracks)", dbid=428),
                                           TemplateComponent("Bad", db_name="No Such Facility")])
    res = place_template(p, t, database, p.sides[0].id, 0, 0)
    assert len(res.units) == 1 and res.skipped == ["Bad (No Such Facility)"]


def test_template_from_units_roundtrip(lib):
    p = new_project()
    side = p.sides[0].id
    src = lib.template("gar_fob")
    res = place_template(p, src, None, side, 34.5, 69.2, heading=30, site_name="FOB Lion")
    tpl = template_from_units(p, [u.id for u in res.units], "My FOB", lib=lib)
    assert tpl.unit_count == src.unit_count
    q = new_project()
    again = place_template(q, tpl, None, q.sides[0].id, 34.5, 69.2, heading=30, site_name="FOB Lion")
    pos = sorted((round(u.lat, 4), round(u.lon, 4)) for u in again.units)
    orig = sorted((round(u.lat, 4), round(u.lon, 4)) for u in res.units)
    assert pos == orig


def test_dry_run_builds_sites(lib, lua_dll):
    from sample import make_sample

    from cmo_studio.tools.lua_engine import dry_run_build
    p = make_sample()
    for i, tid in enumerate(("ab_tactical_has", "c2_bunker", "nav_small_base")):
        place_template(p, lib.template(tid), None, p.sides[0].id, 58 + i * 0.3, 22, site_name=f"Site {i}")
    res = dry_run_build(p, lua_dll)
    assert res.ok, res.output
    assert "formations                         3" in res.output


# ------------------------------------------------------------------ dialogs
@pytest.fixture
def window(tmp_path, sample, monkeypatch):
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
    w.doc.load(sample)
    yield w, app, tmp_path
    w.doc.set_dirty(False)
    w.close()


def test_placer_dialog_places_and_undoes(window):
    w, app, _ = window
    from cmo_studio.ui.templates_ui import TemplatePlacerDialog
    dlg = TemplatePlacerDialog(w.ctx, 58.5, 23.5, w)
    assert dlg.tree.topLevelItemCount() >= 8
    dlg.filter.setText("tactical fighter base")
    assert dlg._tpl().id == "ab_tactical_has"          # name matches beat description matches
    dlg.filter.setText("barracks company")
    t = dlg._tpl()
    assert t and t.id == "gar_barracks_coy"
    dlg.site.setText("Tapa")
    n = len(w.doc.project.units)
    dlg._place()
    assert len(w.doc.project.units) == n + t.unit_count
    assert any(f.name == "Tapa" for f in w.doc.project.formations)
    w.doc.undo()
    assert len(w.doc.project.units) == n


def test_library_editor_and_save_as_template(window, monkeypatch):
    w, app, tmp = window
    from PyQt6.QtWidgets import QInputDialog

    from cmo_studio.ui.templates_ui import TemplateLibraryDialog, save_units_as_template
    dlg = TemplateLibraryDialog(w.ctx, w)
    dlg.tid = "c2_field_cp"
    dlg._load()
    dlg.comps.item(0, 4).setText("10,20; 30,40")
    assert dlg._t().components[0].positions == [[10.0, 20.0], [30.0, 40.0]]
    dlg.save()
    saved = TemplateLibrary.load(tmp / "templates.json")
    assert saved.template("c2_field_cp").components[0].positions == [[10.0, 20.0], [30.0, 40.0]]
    dlg.dirty = False
    dlg.close()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Sample Site", True)))
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Custom", True)))
    ids = [u.id for u in w.doc.project.units if not u.host][:3]
    tpl = save_units_as_template(w.ctx, ids, w)
    assert tpl and tpl.unit_count == 3
    assert TemplateLibrary.load(tmp / "templates.json").template(tpl.id)
    assert math.isfinite(tpl.components[0].positions[0][0])
