"""Loadout queries and the Loadout Viewer (need a CMO install; skipped otherwise)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SU35S, SU35S_AA = 6645, 30249   # Su-35S Flanker M and its R-77-1 / R-73M loadout (DB3K_519)


def test_loadout_details(database):
    from cmo_studio.db.loadouts import aircraft_with_loadout, loadout_details
    d = loadout_details(database, SU35S_AA)
    assert d and d.role and d.radius_nm > 0
    assert {w.qty for w in d.weapons} and all(w.weapon_id for w in d.weapons)
    assert d.payload_kg > 0
    assert SU35S in {e.id for e in aircraft_with_loadout(database, SU35S_AA)}


def test_weapon_details_and_uses(database):
    from cmo_studio.db.loadouts import loadout_details, loadouts_with_weapon, weapon_details
    wid = loadout_details(database, SU35S_AA).weapons[0].weapon_id
    w = weapon_details(database, wid)
    assert w.stats and w.targets and w.warheads
    uses = loadouts_with_weapon(database, wid, limit=100000)
    assert any(u.loadout_id == SU35S_AA for u in uses)


def test_viewer_navigation(database, cmo_dir, tmp_path, sample):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    s.cmo_dir = str(cmo_dir)
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.doc.load(sample)
    w.open_loadout_viewer(SU35S, SU35S_AA)
    v = w._loadout_viewer
    app.processEvents()
    assert v.lo_table.rowCount() > 5 and v.wp_table.rowCount() >= 2
    v.wp_table.selectRow(0)
    assert v.place.weapon and v.wp_targets.count()
    # jump to another aircraft that carries the weapon, then go back
    v._use_row_activated(v.wp_uses.item(0, 0))
    assert v.place.aircraft
    v.go_back()
    assert v.place.loadout == SU35S_AA
    # the sample's F-35 squadron: apply a loadout through the viewer
    jets = next(u for u in sample.units if u.type == "Aircraft" and u.host)
    w.doc.select(jets.id)
    los = database.loadouts(jets.dbid, combat_only=True)
    v.loadoutChosen.emit(int(jets.dbid), los[-1].id)
    assert w.doc.project.unit(jets.id).loadout == los[-1].id
    v.close()
    w.doc.set_dirty(False)
    w.close()
