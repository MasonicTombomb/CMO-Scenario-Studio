"""Aircraft bases: which units can hold aircraft, validation, the builder's fallback and honest reporting.

Reproduces the reported bug: four single Typhoon FGR.4 (DBID 7090, loadout 13972) based on a runway of a placed
air base; CMO refused them with a .NET exception and the build blamed the loadout.
"""
import os

import pytest

from cmo_studio.model import new_project
from cmo_studio.model.hosting import (DECK_HELO, HANGAR, OPEN_PARKING, PAD, Aircraft, Space, room_for, size_rank,
                                      why_not)
from cmo_studio.model.project import Unit
from cmo_studio.model.templates import default_library, place_template
from cmo_studio.model.validation import ERROR, WARNING, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TYPHOON, METEOR_CAP = 7090, 13972
RUNWAY = Space(2001, 2004, 1)
MEDIUM = Aircraft(2002, False)
HELO = Aircraft(2002, True)


# ------------------------------------------------------------------ rules
def test_rules():
    assert room_for([RUNWAY], MEDIUM) == 0
    assert "no hangar" in why_not([RUNWAY], MEDIUM)
    assert room_for([Space(HANGAR, 2002, 4)], MEDIUM) == 4
    assert room_for([Space(HANGAR, 2001, 4)], MEDIUM) == 0          # too small
    assert "up to small" in why_not([Space(HANGAR, 2001, 4)], MEDIUM)
    assert room_for([Space(OPEN_PARKING, 2003, 4), Space(HANGAR, 2002, 2)], MEDIUM) == 6
    assert room_for([Space(PAD, 2002, 1), Space(DECK_HELO, 2003, 2)], HELO) == 3
    assert room_for([Space(PAD, 2002, 1)], MEDIUM) == 0             # fixed wing cannot use a pad
    assert size_rank(3002) == 1                                     # drones count as small


def test_database_spaces(database):
    assert database.aircraft_profile(TYPHOON) == Aircraft(2002, False)
    assert database.aircraft_profile(45).rotary                     # Merlin HM.1
    assert room_for(database.aircraft_spaces("Facility", 55), MEDIUM) == 0        # Runway (2600m)
    assert room_for(database.aircraft_spaces("Facility", 3), MEDIUM) == 0         # Control tower
    assert room_for(database.aircraft_spaces("Facility", 4), MEDIUM) == 1         # HAS (1x Medium)
    assert room_for(database.aircraft_spaces("Facility", 227), MEDIUM) == 4       # Hangar (4x Medium)
    assert database.loadout_valid(TYPHOON, METEOR_CAP)              # the loadout was never the problem


# ------------------------------------------------------------------ the reported project
def _lossiemouth_with_typhoons_on(host_label: str, n: int = 4):
    p = new_project("Intercept Test", "DB3K_519.db3")
    uk = p.sides[0]
    t = default_library().template("uk_ab_lossiemouth")
    res = place_template(p, t, None, uk.id, *t.location)
    host = next(u for u in res.units if u.name == f"Lossiemouth {host_label}")
    for i in range(n):
        p.units.append(Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name=f"MONARCH 1{i + 1}", host=host.id,
                            loadout=METEOR_CAP))
    return p, host


def test_validation_flags_a_runway_as_base(database):
    p, host = _lossiemouth_with_typhoons_on("Runway 05/23")
    errs = [i for i in validate(p, database) if i.level == ERROR and "cannot hold this aircraft" in i.message]
    assert len(errs) == 4
    assert "no hangar, shelter or parking" in errs[0].message


def test_validation_warns_when_a_shelter_is_full(database):
    p, host = _lossiemouth_with_typhoons_on("HAS 1")
    issues = validate(p, database)
    assert not [i for i in issues if i.level == ERROR and "cannot hold" in i.message]
    full = [i for i in issues if i.level == WARNING and "has room for 1 aircraft but 4" in i.message]
    assert full and full[0].obj_id == host.id


def test_builder_moves_aircraft_to_the_sites_hangars(database, lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    p, _ = _lossiemouth_with_typhoons_on("Runway 05/23")
    res = dry_run_build(p, lua_dll, db=database)
    assert res.ok, res.output
    out = res.output
    assert "FAILED" not in out
    assert "Runway 05/23 cannot take it, based at Lossiemouth" in out
    assert "loadout 13972 refused" not in out                     # the old, wrong diagnosis


def test_builder_reports_the_real_reason_when_nothing_fits(database, lua_dll):
    """A lone runway (no site to fall back on): the aircraft fail, with the base named as the cause."""
    from cmo_studio.tools.lua_engine import dry_run_build
    p = new_project("Intercept Test", "DB3K_519.db3")
    uk = p.sides[0]
    rw = Unit(side=uk.id, type="Facility", dbid=55, name="Lone Runway", lat=57.7, lon=-3.3)
    p.units.append(rw)
    p.units.append(Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name="MONARCH 11", host=rw.id,
                        loadout=METEOR_CAP))
    res = dry_run_build(p, lua_dll, db=database)
    out = res.output
    assert "FAILED" in out and "Lone Runway cannot base it" in out and "hangar, shelter or parking" in out
    assert "loadout 13972 refused" not in out


def test_squadron_spreads_over_shelters(database, lua_dll):
    """Twelve aircraft entered as one squadron on a one-aircraft shelter fill the site's other shelters."""
    from cmo_studio.tools.lua_engine import dry_run_build
    p, host = _lossiemouth_with_typhoons_on("HAS 1", n=0)
    p.units.append(Unit(side=host.side, type="Aircraft", dbid=TYPHOON, name="II(AC) Sqn", count=12, host=host.id,
                        loadout=METEOR_CAP))
    res = dry_run_build(p, lua_dll, db=database)
    assert res.ok and "FAILED" not in res.output, res.output
    import re
    assert re.search(r"Blue Aircraft\s+12", res.output)          # all twelve built
    assert "II(AC) Sqn #1: " not in res.output                     # the first one fits the shelter itself


# ------------------------------------------------------------------ Add to selected base
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
    yield w, app
    w.doc.set_dirty(False)
    w.close()


def test_add_to_base_offers_the_sites_hangars(window, database, monkeypatch):
    w, app = window
    if w.dbm.db is None:
        pytest.skip("no database open")
    from PyQt6.QtWidgets import QInputDialog
    p, runway = _lossiemouth_with_typhoons_on("Runway 05/23", n=0)
    w.doc.load(p)
    entry = w.dbm.db.get("Aircraft", TYPHOON)
    offered = {}

    def pick(parent, title, label, items, current, editable):
        offered["items"] = items
        return next(i for i in items if "Hangar (4x Medium)" in i), True
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(pick))
    base = w._usable_base(w.doc.project.unit(runway.id), entry)
    assert base is not None and base.name == "Lossiemouth Hangar (4x Medium)"
    assert all("room for" in i for i in offered["items"])
    assert w._free_room(base, entry) == 4
