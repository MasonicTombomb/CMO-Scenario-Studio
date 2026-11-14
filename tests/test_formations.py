import math
import os

import pytest

from cmo_studio.geo import bearing_deg, distance_km
from cmo_studio.model import Formation, Unit, new_project
from cmo_studio.model.formations import PRESETS, apply_formation, move_with_formation, stations
from cmo_studio.model.validation import ERROR, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _group(n=6, preset="line_ahead", **kw):
    p = new_project()
    sid = p.sides[0].id
    units = [Unit(side=sid, type="Ship", dbid=2814, name=f"S{i}", lat=59.5, lon=24.0) for i in range(n + 1)]
    p.units += units
    f = Formation(side=sid, preset=preset, lead=units[0].id, members=[u.id for u in units[1:]], **kw)
    p.formations.append(f)
    return p, f, units


@pytest.mark.parametrize("key", sorted(PRESETS))
def test_every_preset_places_every_member(key):
    p, f, units = _group(7, key, spacing_nm=PRESETS[key].spacing_nm, heading=30)
    assert apply_formation(p, f) == 7
    pos = {(round(u.lat, 6), round(u.lon, 6)) for u in units}
    assert len(pos) == 8, "two units share a station"


def test_line_ahead_geometry_and_heading():
    p, f, units = _group(3, "line_ahead", spacing_nm=2.0, heading=90)
    apply_formation(p, f)
    lead, second = units[0], units[1]
    assert distance_km(lead.lat, lead.lon, second.lat, second.lon) / 1.852 == pytest.approx(2.0, rel=1e-3)
    assert bearing_deg(lead.lat, lead.lon, second.lat, second.lon) == pytest.approx(270, abs=0.5)   # astern
    assert all(u.heading == 90 for u in units)


def test_mirror_flips_echelon():
    p, f, _ = _group(2, "echelon_right", heading=0)
    right = stations(f, 59.5, 24.0)[0].rel_bearing
    f.mirror = True
    left = stations(f, 59.5, 24.0)[0].rel_bearing
    assert right == pytest.approx(135) and left == pytest.approx(225)


def test_air_altitude_steps():
    p, f, units = _group(3, "ladder", heading=0)
    for u in units:
        u.type, u.altitude = "Aircraft", 5000.0
    apply_formation(p, f)
    assert [u.altitude for u in units[1:]] == [5300.0, 5600.0, 5900.0]


def test_custom_stations():
    p, f, _ = _group(2, "custom", spacing_nm=1.0)
    f.params = {"stations": [[90, 2], [270, 3]]}
    st = stations(f, 0.0, 0.0)
    assert (st[0].rel_bearing, st[0].distance_nm) == (90.0, 2.0)
    assert (st[1].rel_bearing, st[1].distance_nm) == (270.0, 3.0)


def test_moving_a_member_moves_the_formation():
    p, f, units = _group(3, "line_abreast", spacing_nm=1.0)
    apply_formation(p, f)
    before = [(u.lat, u.lon) for u in units]
    m = units[2]
    assert move_with_formation(p, m.id, m.lat + 0.1, m.lon + 0.2)
    for (lat, lon), u in zip(before, units):
        assert u.lat == pytest.approx(lat + 0.1, abs=1e-3) and u.lon == pytest.approx(lon + 0.2, abs=1e-3)


def test_validation_catches_shared_and_hosted_units():
    p, f, units = _group(2)
    f2 = Formation(name="Other", side=f.side, lead=units[1].id)
    p.formations.append(f2)
    units[2].host = units[0].id
    msgs = " ".join(i.message for i in validate(p) if i.level == ERROR)
    assert "also in formation" in msgs and "starts at a base" in msgs


def test_export_stations_relative_and_fixed():
    from cmo_studio.export.compiler import compile_formations
    p, f, units = _group(1, "line_ahead", spacing_nm=2.0, heading=90)
    apply_formation(p, f)
    rot = compile_formations(p)[0]["members"][0]
    assert rot["bearing"] == pytest.approx(180, abs=0.5) and rot["dist"] == pytest.approx(2.0, rel=1e-3)
    f.station_type = "Fixed"
    fixed = compile_formations(p)[0]["members"][0]
    assert fixed["bearing"] == pytest.approx(270, abs=0.5)


def test_dry_run_groups_formation(lua_dll):
    from sample import make_sample_with_formation

    from cmo_studio.tools.lua_engine import dry_run_build
    res = dry_run_build(make_sample_with_formation(), lua_dll)
    assert res.ok, res.output
    assert "1 group(s) with stations" in res.output


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
    w.doc.load(sample)
    yield w, app
    w.doc.set_dirty(False)
    w.close()


def test_page_make_formation_and_edit(window):
    w, app = window
    p = w.doc.project
    red_ids = [u.id for u in p.units if p.side_name(u.side) == "Red" and not u.host]
    w.make_formation(red_ids)
    page = w.formations_page
    f = p.formations[0]
    assert f.lead == red_ids[0] and f.members == red_ids[1:]
    page.preset.set_key("wedge")
    page._preset_changed()
    assert p.formations[0].preset == "wedge"
    page.heading.setValue(45)
    assert p.formations[0].heading == 45
    page.spacing.value.setValue(3.0)
    assert p.formations[0].spacing_nm == pytest.approx(3.0)
    st = stations(p.formations[0], p.unit(f.lead).lat, p.unit(f.lead).lon)
    m = p.unit(f.members[0])
    assert (m.lat, m.lon) == pytest.approx((st[0].lat, st[0].lon), abs=1e-5)
    w.doc.undo()
    assert p is not w.doc.project and w.doc.project.formations[0].spacing_nm != pytest.approx(3.0)


def test_creator_builds_units(window):
    w, app = window
    from cmo_studio.db.database import DBEntry
    from cmo_studio.ui.pages.formations_page import FormationCreator
    w.db_browser.current = DBEntry("Ship", 2814, "Corvette")
    dlg = FormationCreator(w.ctx, w)
    dlg.rows.cellWidget(0, 3).setValue(5)
    dlg.name.setText("Corvette Group")
    n_before = len(w.doc.project.units)
    dlg._create()
    p = w.doc.project
    assert len(p.units) == n_before + 5
    f = next(x for x in p.formations if x.name == "Corvette Group")
    assert len(f.members) == 4 and f.preset == "circular_screen"
    lead = p.unit(f.lead)
    assert all(math.isclose(distance_km(lead.lat, lead.lon, p.unit(m).lat, p.unit(m).lon) / 1.852,
                            f.spacing_nm, rel_tol=1e-3) for m in f.members)
