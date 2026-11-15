"""Predefined patrol areas: library, adding to a scenario (zone + mission), saving areas back, dialogs."""
import json
import os

import pytest

from cmo_studio.model import new_project
from cmo_studio.model.area_library import (DEFAULT_REGIONS, AreaLibrary, add_area, area_from_zone, default_library,
                                           default_library_text, load_library, suggested_mission, zone_name)
from cmo_studio.model.validation import ERROR, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def lib():
    return default_library()


def test_library_shape(lib):
    data = json.loads(default_library_text())
    assert data["format"] == "cmo-studio-areas"
    assert len(lib.areas) >= 120
    ids = [a.id for a in lib.areas]
    assert len(ids) == len(set(ids))
    assert lib.all_regions() == DEFAULT_REGIONS
    for region in DEFAULT_REGIONS:              # every region has both sea and air areas
        assert lib.filtered(region=region, kind="sea"), region
        assert lib.filtered(region=region, kind="air"), region
    for a in lib.areas:
        assert len(a.points) >= 3, a.id
        assert all(-90 <= p[0] <= 90 and -180 <= p[1] <= 180 for p in a.points), a.id
        assert a.kind in ("sea", "air") and a.description, a.id
    for must in ("biscay", "giuk_iceland_faroes", "hormuz", "taiwan_strait", "falklands_tez", "malacca",
                 "cap_baltic_air_policing"):
        assert lib.area(must), must


def test_biscay_is_where_it_should_be(lib):
    a = lib.area("biscay")
    lat, lon = a.centre()
    assert 43 < lat < 48 and -9 < lon < -1
    assert a.region == "Europe" and a.kind == "sea"
    assert lib.filtered("biscay")[0].id == "biscay"


def test_roundtrip_and_bad_user_file(lib, tmp_path):
    path = tmp_path / "areas.json"
    lib.save(path)
    again, source = load_library(path)
    assert source == str(path) and again.to_dict()["areas"] == lib.to_dict()["areas"]
    path.write_text('{"format": "something-else"}', encoding="utf-8")
    fallback, source = load_library(path)
    assert source == "built-in default" and len(fallback.areas) == len(lib.areas)


def test_suggested_missions(lib):
    assert suggested_mission(lib.area("biscay")) == ("patrol", "asw")
    assert suggested_mission(lib.area("channel_east")) == ("patrol", "naval")
    assert suggested_mission(lib.area("cap_baltic_air_policing")) == ("patrol", "aaw")
    assert suggested_mission(lib.area("aew_poland_orbit")) == ("support", "")
    assert suggested_mission(lib.area("tanker_north_sea")) == ("support", "")


def test_add_area_creates_zone_and_mission(lib):
    p = new_project("Areas")
    sid = p.sides[0].id
    res = add_area(p, lib.area("biscay"), sid, mission=suggested_mission(lib.area("biscay")))
    assert res.zone.name == "BISCAY" and len(res.zone.points) == len(lib.area("biscay").points)
    assert res.zone.rp_names()[0] == "BISCAY-1"
    m = res.mission
    assert m.zone == res.zone.id and m.mclass == "patrol" and m.subtype == "asw"
    assert m.name == "Bay of Biscay ASW Patrol"
    again = add_area(p, lib.area("biscay"), sid, mission=("patrol", "naval"))
    assert again.zone.name == "BISCAY_2" and again.mission.name == "Bay of Biscay ASuW Patrol"
    third = add_area(p, lib.area("biscay"), sid, mission=("patrol", "asw"))
    assert third.mission.name == "Bay of Biscay ASW Patrol 2"
    sup = add_area(p, lib.area("aew_poland_orbit"), sid, name="Orbit East", mission=("support", ""))
    assert sup.zone.name == "ORBIT_EAST" and sup.mission.mclass == "support" and sup.mission.subtype == ""
    plain = add_area(p, lib.area("hormuz"), sid, all_sides=True)
    assert plain.mission is None and plain.zone.all_sides
    errors = [i for i in validate(p) if i.level == ERROR]
    assert errors == []


def test_zone_name():
    assert zone_name("Bay of Biscay") == "BAY_OF_BISCAY"
    assert zone_name("GIUK Gap - Denmark Strait") == "GIUK_GAP_DENMARK_STRAIT"
    assert zone_name("  ") == "AREA"


def test_area_from_zone(lib):
    p = new_project("Areas")
    z = add_area(p, lib.area("hormuz"), p.sides[0].id).zone
    e = area_from_zone(z, lib, name="My Hormuz", region="Middle East", kind="sea", tags=["ASuW"])
    assert e.id == "my_hormuz" and e.points == z.points and e.region == "Middle East"
    z.points = z.points[:2]
    with pytest.raises(ValueError):
        area_from_zone(z, lib)


def test_dry_run_builds_library_areas(lib, lua_dll):
    from sample import make_sample

    from cmo_studio.tools.lua_engine import dry_run_build
    p = make_sample()
    sid = p.sides[0].id
    for aid in ("baltic_central", "cap_baltic_air_policing", "aew_poland_orbit"):
        add_area(p, lib.area(aid), sid, mission=suggested_mission(lib.area(aid)))
    res = dry_run_build(p, lua_dll)
    assert res.ok, res.output


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


def test_browser_filters_adds_and_undoes(window):
    w, app, _ = window
    from cmo_studio.ui.areas_library_ui import AreaBrowserDialog
    dlg = AreaBrowserDialog(w.ctx, w)
    assert dlg.tree.topLevelItemCount() == len(DEFAULT_REGIONS)
    dlg.filter.setText("biscay")
    assert [a.id for a in dlg.selected_areas()] == ["biscay"]
    assert dlg.name.text() == "BISCAY"
    assert len(dlg.preview.project.zones) >= 1 and dlg.preview.selected == "biscay"
    dlg.filter.clear()
    dlg.region.setCurrentIndex(dlg.region.findData("Asia"))
    dlg.kind.setCurrentIndex(dlg.kind.findData("air"))
    shown = dlg._visible_areas()
    assert shown and all(a.region == "Asia" and a.kind == "air" for a in shown)
    # pick two areas and add both with their suggested missions
    dlg.region.setCurrentIndex(0)
    dlg.kind.setCurrentIndex(0)
    dlg.select_area("hormuz")
    from cmo_studio.ui.areas_library_ui import _find_item
    _find_item(dlg.tree, "gulf_oman").setSelected(True)
    assert {a.id for a in dlg.selected_areas()} == {"hormuz", "gulf_oman"}
    nz, nm = len(w.doc.project.zones), len(w.doc.project.missions)
    dlg._add()
    assert len(w.doc.project.zones) == nz + 2 and len(w.doc.project.missions) == nm + 2
    assert {z.name for z in w.doc.project.zones} >= {"HORMUZ", "GULF_OMAN"}
    w.doc.undo()
    assert len(w.doc.project.zones) == nz and len(w.doc.project.missions) == nm


def test_browser_without_mission_and_preselect(window):
    w, app, _ = window
    from cmo_studio.ui.areas_library_ui import AreaBrowserDialog
    dlg = AreaBrowserDialog(w.ctx, w, select="falklands_tez")
    assert [a.id for a in dlg.selected_areas()] == ["falklands_tez"]
    dlg.make_mission.setChecked(False)
    dlg.name.setText("TEZ")
    dlg.name.setModified(True)
    nm = len(w.doc.project.missions)
    dlg._add()
    assert w.doc.project.zones[-1].name == "TEZ" and len(w.doc.project.missions) == nm
    assert len(w.doc.project.zones[-1].points) == 16


def test_library_editor_and_save_zone(window, monkeypatch):
    w, app, tmp = window
    from PyQt6.QtWidgets import QInputDialog

    from cmo_studio.ui.areas_library_ui import AreaLibraryDialog, guess_region, save_zone_to_library
    dlg = AreaLibraryDialog(w.ctx, w)
    dlg._go("biscay")
    dlg.points.item(0, 0).setText("48.1")
    assert dlg._a().points[0][0] == 48.1
    dlg._vertex_moved("biscay", 1, 47.9, -2.5)
    assert dlg._a().points[1] == [47.9, -2.5]
    dlg.name.setText("Biscay (edited)")
    dlg._fields()
    dlg.save()
    saved = AreaLibrary.load(tmp / "areas.json")
    assert saved.area("biscay").name == "Biscay (edited)" and saved.area("biscay").points[0][0] == 48.1
    dlg.dirty = False
    dlg.close()

    zone = w.doc.project.zones[0]
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Sample Box", True)))
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: (a[3][0], True)))
    entry = save_zone_to_library(w.ctx, zone.id, w)
    assert entry and AreaLibrary.load(tmp / "areas.json").area(entry.id).points == zone.points
    assert guess_region(45.5, -4.5) == "Europe"
    assert guess_region(26.5, 56.3) == "Middle East"
    assert guess_region(24.0, 121.0) == "Asia"
    assert guess_region(-51.7, -59.2) == "South America"
    assert guess_region(72.0, 35.0) == "Arctic"
    assert guess_region(-12.0, 131.0) == "Oceania"


def test_search_finds_library_areas(window):
    w, app, _ = window
    names = [c[0] for c in w.search_commands()]
    assert "Patrol area: Bay of Biscay" in names
    assert "Add patrol area from library" in names
