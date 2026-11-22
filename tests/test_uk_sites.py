"""UK real-world site templates (pack), template packs and merging, part headings, and the UK area set."""
import json
import os
import random

import pytest

from cmo_studio.geo import distance_km
from cmo_studio.model import new_project
from cmo_studio.model.area_library import AreaLibrary
from cmo_studio.model.area_library import default_library as default_areas
from cmo_studio.model.area_library import load_library as load_areas
from cmo_studio.model.templates import (TemplateLibrary, default_library, load_library, pack_texts, place_template,
                                        template_from_units)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def lib():
    return default_library()


def uk(lib):
    return [t for t in lib.templates if t.category.startswith("UK - ")]


# ------------------------------------------------------------------ pack
def test_uk_pack_is_bundled_and_attributed():
    names = [n for n, _ in pack_texts()]
    assert "templates_uk.json" in names
    data = json.loads(dict(pack_texts())["templates_uk.json"])
    assert "OpenStreetMap" in data["about"] and "ODbL" in data["about"]


def test_uk_templates_have_real_locations(lib):
    sites = uk(lib)
    assert len([t for t in sites if t.category == "UK - Air bases"]) >= 35
    assert len(sites) >= 80
    for t in sites:
        assert t.location, t.id
        lat, lon = t.location
        assert 49.8 < lat < 61 and -8.5 < lon < 2, t.id
        assert t.site, t.id
    ids = [t.id for t in lib.templates]
    assert len(ids) == len(set(ids))
    cats = lib.all_categories()
    for c in ("UK - Air bases", "UK - Naval bases", "UK - Radar and air defence", "UK - Army garrisons"):
        assert c in cats


def test_lossiemouth_matches_the_real_base(lib):
    t = lib.template("uk_ab_lossiemouth")
    runways = {c.label: c for c in t.components if c.label.startswith("Runway") and "Access" not in c.label}
    assert set(runways) == {"Runway 05/23", "Runway 10/28"}
    assert abs(runways["Runway 05/23"].length - 2764) < 30 and abs(runways["Runway 10/28"].length - 1850) < 30
    assert 40 < runways["Runway 05/23"].hdg < 50 and 92 < runways["Runway 10/28"].hdg < 100
    has = sum(len(c.positions) for c in t.components if "Hardened" in c.db_name)
    assert has >= 15
    assert any(c.db_name == "Building (Control Tower)" for c in t.components)
    lat, lon = t.location
    assert distance_km(lat, lon, 57.705, -3.339) < 2.0


def test_every_air_base_has_runway_tower_and_host(lib):
    for t in uk(lib):
        if t.category != "UK - Air bases":
            continue
        assert any(c.db_name.startswith("Runway (") for c in t.components), t.id
        assert any(c.db_name == "Building (Control Tower)" for c in t.components), t.id
        assert any(c.host for c in t.components), t.id


def test_uk_components_resolve_in_db3000(lib, database):
    from cmo_studio.model.templates import resolve
    missing = [(t.id, c.label) for t in uk(lib) for c in t.components if resolve(database, c) is None]
    assert missing == []


def test_place_at_real_site_with_part_headings(lib):
    p = new_project("UK")
    t = lib.template("uk_ab_lossiemouth")
    res = place_template(p, t, None, p.sides[0].id, *t.location, heading=t.heading)
    rw = {u.name: u for u in res.units if "Runway" in u.name}
    assert rw["Lossiemouth Runway 05/23"].heading == pytest.approx(
        next(c.hdg for c in t.components if c.label == "Runway 05/23"))
    assert res.formation and res.formation.group_in_cmo
    # rotating the whole site rotates every part
    p2 = new_project("UK")
    res2 = place_template(p2, t, None, p2.sides[0].id, *t.location, heading=90)
    rw2 = {u.name: u for u in res2.units if "Runway" in u.name}
    assert rw2["Lossiemouth Runway 05/23"].heading == pytest.approx(
        (rw["Lossiemouth Runway 05/23"].heading + 90) % 360)


def test_save_as_template_keeps_relative_headings():
    p = new_project("UK")
    lib = default_library()
    t = lib.template("uk_ab_lossiemouth")
    res = place_template(p, t, None, p.sides[0].id, *t.location)
    rws = [u.id for u in res.units if "Runway" in u.name and "Access" not in u.name]
    units = [p.unit(i) for i in rws]
    tpl = template_from_units(p, rws, "Two runways")
    expect = round((units[1].heading - units[0].heading) % 360.0, 1)
    assert sorted(c.hdg for c in tpl.components) == sorted([0.0, expect])


def test_roundtrip_keeps_location_heading_and_length(lib, tmp_path):
    t = lib.template("uk_ab_brize_norton")
    one = TemplateLibrary(templates=[t])
    one.save(tmp_path / "t.json")
    back = TemplateLibrary.load(tmp_path / "t.json").templates[0]
    assert back.location == t.location and back.site == t.site
    assert [(c.hdg, c.length) for c in back.components] == [(c.hdg, c.length) for c in t.components]


# ------------------------------------------------------------------ merging new built-ins into a user library
def test_new_builtins_are_merged_into_an_old_user_file(tmp_path):
    builtin = default_library()
    old = TemplateLibrary(templates=[x for x in builtin.templates if not x.category.startswith("UK")][:5])
    old.save(tmp_path / "templates.json")          # a 1.5.x file: no known_builtins
    lib, source = load_library(tmp_path / "templates.json")
    assert source == str(tmp_path / "templates.json")
    assert lib.template("uk_ab_lossiemouth") and "UK - Air bases" in lib.all_categories()
    assert len(lib.templates) == len(builtin.templates)
    # deleting a built-in and saving keeps it deleted
    lib.templates = [x for x in lib.templates if x.id != "uk_ab_lossiemouth"]
    lib.save(tmp_path / "templates.json")
    again, _ = load_library(tmp_path / "templates.json")
    assert again.template("uk_ab_lossiemouth") is None


def test_new_areas_are_merged_into_an_old_user_file(tmp_path):
    builtin = default_areas()
    old = AreaLibrary(areas=[a for a in builtin.areas if a.region != "United Kingdom"],
                      regions=[r for r in builtin.regions if r != "United Kingdom"])
    old.save(tmp_path / "areas.json")
    lib, _ = load_areas(tmp_path / "areas.json")
    assert lib.area("uk_qra_north") and lib.all_regions()[1] == "United Kingdom"


# ------------------------------------------------------------------ UK areas
def _inside(p, poly):
    y, x = p
    c = False
    for i in range(len(poly)):
        (y1, x1), (y2, x2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def test_uk_intercept_sectors_cover_the_whole_fir_once():
    areas = default_areas()
    fir = areas.area("uk_fir").points
    sectors = [a.points for a in areas.areas if a.id.startswith("uk_sector_")]
    halves = [areas.area("uk_qra_north").points, areas.area("uk_qra_south").points]
    assert len(sectors) == 8
    rnd = random.Random(7)
    n = 0
    for _ in range(6000):
        p = (rnd.uniform(48, 62), rnd.uniform(-11, 6))
        if _inside(p, fir):
            n += 1
            assert sum(_inside(p, s) for s in sectors) == 1, p
            assert sum(_inside(p, h) for h in halves) == 1, p
    assert n > 2000


def test_uk_area_set():
    areas = default_areas()
    ukas = areas.filtered(region="United Kingdom")
    assert len(ukas) >= 50
    tags = {t for a in ukas for t in a.tags}
    for must in ("QRA", "CAP", "AEW", "tanker", "range"):
        assert must in tags
    assert areas.filtered(region="United Kingdom", kind="sea")


# ------------------------------------------------------------------ placer dialog
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


def test_placer_defaults_to_the_real_site(window):
    w, app, _ = window
    from cmo_studio.ui.templates_ui import TemplatePlacerDialog
    dlg = TemplatePlacerDialog(w.ctx, 58.5, 23.5, w)
    dlg.filter.setText("lossiemouth")
    t = dlg._tpl()
    assert t.id == "uk_ab_lossiemouth"
    assert dlg.real.isChecked() and dlg.real.isEnabled()
    assert (dlg.lat, dlg.lon) == tuple(t.location) and dlg.site.text() == "Lossiemouth"
    dlg.real.setChecked(False)
    assert (dlg.lat, dlg.lon) == (58.5, 23.5)
    dlg.real.setChecked(True)
    n = len(w.doc.project.units)
    dlg._place()
    assert len(w.doc.project.units) == n + t.unit_count
    tower = next(u for u in w.doc.project.units if u.name == "Lossiemouth Control Tower")
    assert distance_km(tower.lat, tower.lon, *t.location) < 3
    # a generic template has no real site
    dlg2 = TemplatePlacerDialog(w.ctx, 58.5, 23.5, w)
    dlg2.filter.setText("tactical fighter base")
    assert not dlg2.real.isEnabled() and (dlg2.lat, dlg2.lon) == (58.5, 23.5)


def test_dry_run_builds_uk_sites(lib, lua_dll):
    from sample import make_sample

    from cmo_studio.model.area_library import add_area, suggested_mission
    from cmo_studio.tools.lua_engine import dry_run_build
    p = make_sample()
    sid = p.sides[0].id
    for tid in ("uk_ab_lakenheath", "uk_hmnb_clyde", "uk_fylingdales"):
        t = lib.template(tid)
        place_template(p, t, None, sid, *t.location, heading=t.heading)
    areas = default_areas()
    for aid in ("uk_qra_north", "uk_sector_east_anglia", "uk_aara_6"):
        add_area(p, areas.area(aid), sid, mission=suggested_mission(areas.area(aid)))
    res = dry_run_build(p, lua_dll)
    assert res.ok, res.output


def test_official_uk_boundaries():
    areas = default_areas()
    # Scottish / London FIR boundary: 55N east of 5 30W (UK AIP ENR 2.1)
    north = areas.area("uk_qra_north").points
    south = areas.area("uk_qra_south").points
    def has(poly, lat, lon):
        return any(abs(p[0] - lat) < 1e-3 and abs(p[1] - lon) < 1e-3 for p in poly)
    assert has(north, 55.0, 5.0) and has(south, 55.0, 5.0)
    assert has(north, 55.0, -5.5) and has(south, 55.0, -5.5)
    assert has(north, 61.0, -10.0) and has(south, 48 + 50 / 60, -8.0)
    for a in (areas.area("uk_fir"), areas.area("uk_range_tain"), areas.area("uk_aara_1")):
        assert "official" in a.tags and "UK AIP" in a.description
    aaras = [a for a in areas.areas if a.id.startswith("uk_aara_")]
    assert len(aaras) == 15
    assert "notional" in areas.area("uk_cap_moray").description.lower()


# ------------------------------------------------------------------ several templates at once
TRIO = ("uk_ab_fairford", "uk_ab_benson", "uk_ab_lossiemouth")


def test_place_several_templates_at_their_real_sites(lib):
    from cmo_studio.model.templates import place_templates
    p = new_project("Three bases", "DB3K_519.db3")
    sid = p.sides[0].id
    tpls = [lib.template(t) for t in TRIO]
    out = place_templates(p, tpls, None, sid, 50.0, 0.0)
    assert [t.id for t, _r in out] == list(TRIO)
    assert len(p.units) == sum(t.unit_count for t in tpls)
    for t, res in out:
        assert res.units and res.formation is not None and res.formation.name == t.site
        assert all(distance_km(u.lat, u.lon, *t.location) < 6 for u in res.units)   # each at its own site
        assert all(u.name.startswith(t.site) for u in res.units)                      # and its own names


def test_templates_without_a_site_go_in_a_row_without_overlapping(lib):
    from cmo_studio.model.templates import place_templates, template_radius_m
    p = new_project("Row", "DB3K_519.db3")
    sid = p.sides[0].id
    tpls = [lib.template(t) for t in ("af_2000", "af_3200", "uk_ab_benson", "af_4000")]
    out = place_templates(p, tpls, None, sid, 58.0, 24.0, heading=90.0)
    centres = [res.formation for _t, res in out]
    leads = [p.unit(f.lead) for f in centres]
    benson = lib.template("uk_ab_benson")
    assert distance_km(leads[2].lat, leads[2].lon, *benson.location) < 6           # the real one at its site
    row = [leads[0], leads[1], leads[3]]
    assert all(abs(u.lat - 58.0) < 0.02 for u in row)                               # due east of the point
    assert row[0].lon < row[1].lon < row[2].lon
    gap = (template_radius_m(tpls[0]) + template_radius_m(tpls[1])) / 1000
    assert distance_km(row[0].lat, row[0].lon, row[1].lat, row[1].lon) >= gap      # no overlap
    # not at their real sites when asked: all four in the row
    p2 = new_project("Row2", "DB3K_519.db3")
    out2 = place_templates(p2, tpls, None, p2.sides[0].id, 58.0, 24.0, real_sites=False)
    assert all(abs(p2.unit(r.formation.lead).lat - 58.0) < 0.05 for _t, r in out2)


def _tick(dlg, tid):
    from PyQt6.QtCore import Qt
    for i in range(dlg.tree.topLevelItemCount()):
        head = dlg.tree.topLevelItem(i)
        for k in range(head.childCount()):
            it = head.child(k)
            if it.data(0, Qt.ItemDataRole.UserRole) == tid:
                it.setCheckState(0, Qt.CheckState.Checked)
                return it
    raise AssertionError(tid)


def test_placer_ticks_several_templates(window):
    w, app, _ = window
    from PyQt6.QtCore import Qt

    from cmo_studio.ui.templates_ui import TemplatePlacerDialog
    lib_ = default_library()
    before = len(w.doc.project.units)
    dlg = TemplatePlacerDialog(w.ctx, 58.5, 23.5, w)
    assert dlg.place_btn.text() == "Place" and not dlg.untick_btn.isEnabled()
    dlg.filter.setText("raf")
    for tid in TRIO:
        _tick(dlg, tid)
    assert dlg.ticked == list(TRIO)
    assert dlg.place_btn.text() == "Place 3 templates" and not dlg.site.isEnabled()
    assert "3 ticked" in dlg.ticked_label.text() and "RAF Fairford" in dlg.ticked_label.text()
    assert "own positions" in dlg.ticked_label.text()
    dlg.filter.setText("lossie")                         # ticks survive a new search
    assert dlg.ticked == list(TRIO)
    head = dlg.tree.topLevelItem(0)
    lossie = next(head.child(k) for k in range(head.childCount())
                  if head.child(k).data(0, Qt.ItemDataRole.UserRole) == "uk_ab_lossiemouth")
    assert lossie.checkState(0) == Qt.CheckState.Checked
    assert head.checkState(0) == Qt.CheckState.PartiallyChecked           # Kinloss also matches, not ticked
    dlg._place()
    assert dlg.placed_sites == 3
    total = sum(lib_.template(t).unit_count for t in TRIO)
    assert len(w.doc.project.units) == before + total
    names = {u.name for u in w.doc.project.units}
    assert {"Fairford Control Tower", "Lossiemouth Control Tower"} <= names
    w.doc.undo()                                          # one undo step for all three
    assert len(w.doc.project.units) == before


def test_placer_category_tick_and_untick(window):
    w, app, _ = window
    from PyQt6.QtCore import Qt

    from cmo_studio.ui.templates_ui import TemplatePlacerDialog
    dlg = TemplatePlacerDialog(w.ctx, 58.5, 23.5, w)
    dlg.filter.setText("twin-runway")
    head = dlg.tree.topLevelItem(0)
    head.setCheckState(0, Qt.CheckState.Checked)          # the whole category as shown
    assert len(dlg.ticked) == head.childCount() >= 2
    assert dlg.place_btn.text() == f"Place {head.childCount()} templates"
    assert not dlg.real.isEnabled()                       # none has a real site: a row from the position
    assert "row east" in dlg.ticked_label.text() and dlg.coords.isEnabled()
    dlg._untick_all()
    assert dlg.ticked == [] and dlg.place_btn.text() == "Place" and dlg.site.isEnabled()
    # one ticked, another highlighted: the ticked one is placed, by itself
    _tick(dlg, dlg.tree.topLevelItem(0).child(1).data(0, Qt.ItemDataRole.UserRole))
    dlg.tree.setCurrentItem(dlg.tree.topLevelItem(0).child(0))
    assert dlg._multi() and dlg.place_btn.text() == "Place"
    n = len(w.doc.project.units)
    dlg._place()
    assert dlg.placed_sites == 1 and len(w.doc.project.units) > n
