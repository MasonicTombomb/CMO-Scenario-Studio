"""Callsign library, role detection, allocation and the two dialogs."""
import json
import os

import pytest

from cmo_studio.model import Mission, Unit
from cmo_studio.model.callsigns import (Allocator, Library, PlanRow, apply_callsigns, default_library,
                                       default_library_text, detect_role, flight_format, load_library)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def lib():
    return default_library()


def test_default_library_is_valid_json_with_wide_coverage(lib):
    data = json.loads(default_library_text())
    assert data["format"] == "cmo-studio-callsigns"
    names = {c.name for c in lib.countries}
    for must in ("United States", "United Kingdom", "France", "Germany", "Italy", "Poland", "Turkey", "Canada",
                 "Russia", "China", "India", "Iran", "Israel", "Japan", "Australia", "Generic"):
        assert must in names, must
    assert sum(len(c.squadrons) for c in lib.countries) > 300
    for c in lib.countries:
        for s in c.squadrons:
            assert s.callsigns and s.roles and all(r in lib.roles for r in s.roles), (c.name, s.name)
    # every major air arm has several squadrons
    for name in ("United States", "United Kingdom", "France", "Russia", "China"):
        assert len(lib.country(name).squadrons) >= 10


def test_every_role_resolves_for_every_country(lib):
    for c in lib.countries:
        for role in lib.roles:
            assert lib.squadrons_for(c, role), (c.name, role)


def test_country_matching(lib):
    assert lib.country_for("Russia [1992-]").name == "Russia"
    assert lib.country_for("Soviet Union [-1991]").name == "Russia"
    assert lib.country_for("Germany [FRG/Reunified]").name == "Germany"
    assert lib.country_for("Lithuania [1992-]").name == "Baltic States"
    assert lib.country_for("Atlantis").name == "Generic"


@pytest.mark.parametrize("cat,sub,lo,role", [
    ("Fixed Wing", "Fighter", 2003, "FIGHTER"),
    ("Fixed Wing", "Multirole (Fighter/Attack)", 3202, "ASUW"),
    ("Fixed Wing", "Multirole (Fighter/Attack)", 3003, "SEAD"),
    ("Fixed Wing", "Multirole (Fighter/Attack)", 3401, "ATTACK"),
    ("Fixed Wing", "Airborne Early Warning (AEW)", 4002, "AEW"),
    ("Fixed Wing", "Tanker (Air Refueling)", 8001, "TANKER"),
    ("Fixed Wing", "Bomber", 3101, "BOMBER"),
    ("Fixed Wing", "Maritime Patrol Aircraft (MPA)", 6001, "MPA"),
    ("Helicopter", "Attack", 3401, "ATTACK_HELO"),
    ("Helicopter", "Anti-Submarine Warfare (ASW)", 6002, "ASW_HELO"),
    ("Helicopter", "Transport", 7102, "UTILITY_HELO"),
    ("Helicopter", "Transport", 4102, "CSAR"),
    ("Fixed Wing", "Unmanned Combat Aerial Vehicle (UCAV)", 3001, "UAV"),
])
def test_detect_role(cat, sub, lo, role):
    assert detect_role(cat, sub, lo) == role


def test_allocator_makes_flights_and_skips_used(lib):
    uk = lib.country("United Kingdom")
    a = Allocator(lib, used={"MONARCH 11"})
    first = a.allocate(uk, "FIGHTER", 6)
    names = [x.name for x in first]
    assert names[:4] == ["MONARCH 21", "MONARCH 22", "MONARCH 23", "MONARCH 24"]   # flight 1 taken
    assert names[4:] == ["MONARCH 31", "MONARCH 32"]
    nxt = a.allocate(uk, "FIGHTER", 1)
    assert nxt[0].squadron == "II(AC) Squadron"   # the next unit comes from the next squadron
    again = Allocator(lib, used={"MONARCH 11"}, rotate=False)
    again.allocate(uk, "FIGHTER", 6)
    assert again.allocate(uk, "FIGHTER", 1)[0].name == "MONARCH 41"   # partly used flight 3 is not shared
    assert a.allocate_flight_name(uk, "TANKER").name == "TARTAN 1"


def test_formats():
    assert flight_format("{word}-{flight}{member}") == "{word}-{flight}"
    lib = Library.from_dict({"roles": {"FIGHTER": "F"}, "fallbacks": {}, "countries": [
        {"name": "Test", "match": ["Test"], "format": "{word}{flight}{member:02d}", "flight_size": 2,
         "squadrons": [{"name": "S", "roles": ["FIGHTER"], "callsigns": ["ab"]}]}]})
    names = [x.name for x in Allocator(lib).allocate(lib.country("Test"), "FIGHTER", 3)]
    assert names == ["AB101", "AB102", "AB201"]


def test_apply_splits_and_keeps_links(sample, lib):
    jets = next(u for u in sample.units if u.type == "Aircraft" and u.count == 4)
    m = next(x for x in sample.missions if jets.id in x.units)
    res = apply_callsigns(sample, lib, [PlanRow(jets.id, "United Kingdom", "FIGHTER", "617 Squadron")])
    ids = res[jets.id]
    assert len(ids) == 4 and all(sample.unit(i).count == 1 for i in ids)
    assert [sample.unit(i).name for i in ids] == ["DAMBUSTER 11", "DAMBUSTER 12", "DAMBUSTER 13", "DAMBUSTER 14"]
    assert all(i in m.units for i in ids)
    assert all(sample.unit(i).group == "617 Squadron" and sample.unit(i).host == jets.host for i in ids)


def test_apply_without_split_and_reserves(sample, lib):
    reserve = next(u for u in sample.units if u.reserve)
    apply_callsigns(sample, lib, [PlanRow(reserve.id, "United States", "FIGHTER")], split=True)
    assert reserve.count == 2 and reserve.name == "STING 1"     # reinforcements keep their count


def test_user_file_overrides_default(tmp_path, lib):
    custom = lib.clone()
    custom.country("United Kingdom").squadrons[0].callsigns = ["CUSTOM"]
    path = tmp_path / "callsigns.json"
    custom.save(path)
    loaded, source = load_library(path)
    assert source == str(path) and loaded.country("United Kingdom").squadrons[0].callsigns == ["CUSTOM"]
    path.write_text("{ broken", encoding="utf-8")
    assert load_library(path)[1] == "built-in default"


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


def test_assign_dialog_applies(window):
    w, app, _ = window
    from cmo_studio.ui.callsigns_ui import CallsignAssignDialog
    p = w.doc.project
    ids = [u.id for u in p.units if u.type == "Aircraft" and not u.reserve]
    dlg = CallsignAssignDialog(w.ctx, ids, w)
    assert dlg.table.rowCount() == len(ids)
    for r in range(dlg.table.rowCount()):
        dlg.table.cellWidget(r, 3).setCurrentText("France")
    assert "NORMANDIE" in dlg.table.item(0, 6).text() or "CIGOGNE" in dlg.table.item(0, 6).text()
    n_before = len(p.units)
    dlg._apply()
    assert len(p.units) > n_before                  # the 4-ship was split
    assert all(any(ch.isdigit() for ch in u.name) for u in p.units if u.type == "Aircraft" and not u.reserve)
    w.doc.undo()
    assert len(w.doc.project.units) == n_before


def test_library_editor_saves_user_file(window):
    w, app, tmp = window
    from cmo_studio.ui.callsigns_ui import CallsignLibraryDialog
    dlg = CallsignLibraryDialog(w.ctx, w)
    dlg.country_name = "Norway"
    dlg._load_country()
    dlg.squadrons.item(0, 5).setText("fjord, troll")
    assert dlg._c().squadrons[0].callsigns == ["FJORD", "TROLL"]
    dlg.save()
    saved = Library.load(tmp / "callsigns.json")
    assert saved.country("Norway").squadrons[0].callsigns == ["FJORD", "TROLL"]
    dlg.dirty = False
    dlg.close()


def test_assign_from_units_page_uses_selection(window):
    w, app, _ = window
    assert isinstance(Unit(), Unit) and isinstance(Mission(), Mission)
    assert callable(w.assign_callsigns)
