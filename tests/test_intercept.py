"""Intercept missions: conditions, export, the manager in play (mock CMO), checks and the editor."""
import os

import pytest

from cmo_studio.export.compiler import compile_build_data, compile_intercepts
from cmo_studio.export.exporter import Exporter
from cmo_studio.model import new_project
from cmo_studio.model.intercept import PRESETS, apply_preset, bases_with_aircraft, describe, intercept_of
from cmo_studio.model.project import Action, Event, Mission, Project, Trigger, Unit, Zone
from cmo_studio.model.templates import default_library, place_template
from cmo_studio.model.validation import ERROR, WARNING, validate

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TYPHOON, TU95, METEOR = 334, 447, 13972


def scenario(**conditions):
    p = new_project("QRA", "DB3K_519.db3")
    uk, red = p.sides
    t = default_library().template("uk_ab_lossiemouth")
    res = place_template(p, t, None, uk.id, *t.location)
    hangar = next(u for u in res.units if "Hangar (4x Large)" in u.name)
    jets = [Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name=f"QRA {i}", host=hangar.id, loadout=METEOR)
            for i in (1, 2, 3, 4)]
    bears = [Unit(side=red.id, type="Aircraft", dbid=TU95, name=f"BEAR {i}", lat=62.0, lon=5.0 + i, altitude=9000)
             for i in (1, 2, 3)]
    bear = bears[0]
    p.units += jets + bears
    p.zones.append(Zone(side=uk.id, name="QRA_NORTH", points=[[57, -8], [61, -8], [61, 3], [57, 3]]))
    m = Mission(side=uk.id, name="QRA North", mclass="intercept", subtype="", zone=p.zones[0].id,
                units=[j.id for j in jets])
    for k, v in conditions.items():
        setattr(intercept_of(m), k, v)
    p.missions.append(m)
    return p, m, jets, bear


# ------------------------------------------------------------------ model and export
def test_round_trip_and_description():
    p, m, jets, bear = scenario(near=True, near_nm=150, roe="tight", reserve=1)
    q = Project.from_json(p.to_json())
    ic = q.mission(m.id).intercept
    assert ic.near_nm == 150 and ic.postures == ["H", "U", "X"] and ic.roe == "tight"
    text = describe(p, m)
    for must in ("2 aircraft per contact", "4 on call", "1 kept back", "inside QRA_NORTH", "within 150 nm of Lossiemouth",
                 "hostile or unfriendly or unknown", "weapons tight"):
        assert must in text, must
    assert bases_with_aircraft(p, p.sides[0].id) == [("Lossiemouth", "Lossiemouth", 4)]


def test_export_is_an_empty_switched_off_air_intercept():
    p, m, jets, bear = scenario(flag=True, flag_key="GO", window=True, window_from=10, window_to=60, altitude=True)
    D = compile_build_data(p)
    rec = next(x for x in D["MISSIONS"] if x["name"] == "QRA North")
    assert (rec["class"], rec["sub"], rec["units"], rec["targets"]) == ("strike", "air", [], [])
    assert rec["opts"]["isactive"] is False and rec["opts"]["flightSize"] == 2 and rec["wcs"] == 2
    ic = compile_intercepts(p)[0]
    start = p.clock.start_epoch()
    assert ic["names"] == ["QRA 1", "QRA 2", "QRA 3", "QRA 4"] and ic["armed"] and len(ic["area"]) == 4
    assert (ic["from"], ic["to"], ic["flag"]) == (start + 600, start + 3600, "GO")
    assert ic["c"] == {"area": True, "posture": {"H": True, "U": True, "X": True}, "altitude": [0.0, 20000.0]}
    assert "STUDIO.INTERCEPTS = {" in Exporter(p).luainit_lua()
    assert [e for e in D["EVENTS"] if e["name"] == "Studio: intercepts"]
    plain = new_project("Plain")
    assert not [e for e in compile_build_data(plain)["EVENTS"] if e["name"] == "Studio: intercepts"]


# ------------------------------------------------------------------ in play
HEAD = r"""
local start = MOCK.now
local id = '%(id)s'
local m; for _, x in pairs(MOCK.missions) do if x.name == 'QRA North' then m = x end end
local bear = ScenEdit_GetUnit({ name = 'BEAR 1' })
MOCK.contacts = { Blue = {} }
local function contact(g, lat, lon, over)      -- C1, C2, C3 are three different aircraft
  local who = ScenEdit_GetUnit({ name = 'BEAR ' .. (g:match('^C([123])$') or '1') }) or bear
  local c = { guid = g, actualunitid = who.guid, name = g, latitude = lat, longitude = lon, altitude = 9000, speed = 400,
              heading = 225, posture = 'X', type_description = 'Air', classificationlevel = 1, emissions = {} }
  for k, v in pairs(over or {}) do c[k] = v end
  return c
end
local function see(...) MOCK.contacts.Blue = { ... } end
local function tick(min) MOCK.now = start + min * 60; return StudioInterceptTick() end
local function show(tag, n)
  print('IC ' .. tag .. ' launched=' .. tostring(n) .. ' active=' .. tostring(m.active) .. ' targets=' .. #m.targets
        .. ' units=' .. #m.units)
end
"""


def play(p, m, script, database, lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    p.sides[0].name = "Blue"
    res = dry_run_build(p, lua_dll, db=database, after=HEAD % {"id": m.id} + script)
    assert res.ok and "MOCK API ERROR" not in res.output and 'Intercept "' not in res.output, res.output
    return [ln[3:] for ln in res.output.splitlines() if ln.startswith("IC ")]


def test_scramble_and_stand_down(database, lua_dll):
    p, m, jets, bear = scenario(signal="QRA_AIRBORNE")
    out = play(p, m, r"""
show('built', 0)
see(contact('C1', 63, 5)); show('outside', tick(1))
see(contact('C1', 60, 2)); show('enters', tick(2))
show('same contact', tick(3))
see(contact('C1', 60, 2), contact('C2', 59, 0)); show('second', tick(4))
see(contact('C1', 60, 2), contact('C2', 59, 0), contact('C3', 58, 0)); show('third waits', tick(5))
ScenEdit_GetUnit({ name = 'QRA 1' }).condition_v = 'Airborne'
see(contact('C1', 63, 5), contact('C2', 63, 5)); show('left', tick(6))
show('grace', tick(9)); show('over', tick(11))
print('IC rtb ' .. tostring(ScenEdit_GetUnit({ name = 'QRA 1' }).rtb) .. ' flag ' .. ScenEdit_GetKeyValue('QRA_AIRBORNE'))
see(contact('C9', 60, 0)); show('again', tick(20))
""", database, lua_dll)
    assert out[0] == "built launched=0 active=false targets=0 units=0"
    assert out[1] == "outside launched=0 active=false targets=0 units=0"
    assert out[2] == "enters launched=2 active=true targets=1 units=2"
    assert out[3] == "same contact launched=0 active=true targets=1 units=2"
    assert out[4] == "second launched=2 active=true targets=2 units=4"
    assert out[5] == "third waits launched=0 active=true targets=2 units=4"      # two contacts at once
    assert out[6].startswith("left launched=0 active=true targets=2")
    assert out[7].startswith("grace launched=0 active=true")
    assert out[8] == "over launched=0 active=false targets=0 units=0"            # 5 min after it stopped matching
    assert out[9] == "rtb true flag true"
    assert out[10] == "again launched=2 active=true targets=1 units=2"


def test_reserve_readiness_destroyed_target_and_switching_off(database, lua_dll):
    p, m, jets, bear = scenario(reserve=1, per_contact=2, max_contacts=2)
    out = play(p, m, r"""
ScenEdit_GetUnit({ name = 'QRA 1' }).readytime_v = 3600
see(contact('C1', 60, 2), contact('C2', 59, 0)); show('reserve', tick(1))
for _, n in ipairs({ 'BEAR 1', 'BEAR 2' }) do ScenEdit_DeleteUnit({ guid = ScenEdit_GetUnit({ name = n }).guid }) end
see(); show('destroyed', tick(2))
StudioMissionStatus('Blue', 'QRA North', false)
see(contact('C3', 60, 2)); show('switched off', tick(3))
StudioMissionStatus('Blue', 'QRA North', true); show('switched on', tick(4))
""", database, lua_dll)
    assert out[0] == "reserve launched=2 active=true targets=2 units=2"          # 3 ready, 1 kept back
    assert out[1] == "destroyed launched=0 active=false targets=0 units=0"       # at once, not after the grace time
    assert out[2] == "switched off launched=0 active=false targets=0 units=0"
    assert out[3].startswith("switched on launched=2 active=true")


@pytest.mark.parametrize("cond,yes,no", [
    ({"posture": True, "postures": ["H"]}, "{posture='H'}", "{posture='X'}"),
    ({"near": True, "near_nm": 100}, "{latitude=58.5,longitude=-3}", "{latitude=62,longitude=5}"),
    ({"inbound": True, "inbound_deg": 30}, "{latitude=60,longitude=-3.3,heading=180}",
     "{latitude=60,longitude=-3.3,heading=20}"),
    ({"altitude": True, "alt_min": 100, "alt_max": 1000}, "{altitude=500}", "{altitude=9000}"),
    ({"speed": True, "speed_min": 600}, "{speed=700}", "{speed=400}"),
    ({"unidentified": True}, "{classificationlevel=1}", "{classificationlevel=4}"),
    ({"unidentified": True}, "{classificationlevel='KnownDomain'}", "{classificationlevel='PreciseID'}"),
    ({"emitting": True}, "{emissions={{name='Big Bulge'}}}", "{emissions={}}"),
    ({"missiles": True}, "{type_description='Missile'}", "{type_description='Surface'}"),
])
def test_each_condition(database, lua_dll, cond, yes, no):
    off = {"in_area": False, "posture": False}
    p, m, jets, bear = scenario(**{**off, **cond})
    out = play(p, m, f"see(contact('C1', 60, 2, {no})); show('no', tick(1))\n"
                     f"see(contact('C2', 60, 2, {yes})); show('yes', tick(2))\n", database, lua_dll)
    assert out[0].startswith("no launched=0 active=false") and out[1].startswith("yes launched=2 active=true"), out


def test_tracked_raid_window_flag_and_any(database, lua_dll):
    p, m, jets, bear = scenario(in_area=False, posture=False, tracked=True, tracked_min=3)
    out = play(p, m, "see(contact('C1', 60, 2)); show('a', tick(1)); show('b', tick(3)); show('c', tick(4))",
               database, lua_dll)
    assert [x.split()[1] for x in out] == ["launched=0", "launched=0", "launched=2"]
    p, m, jets, bear = scenario(raid=True, raid_min=2)
    out = play(p, m, "see(contact('C1', 60, 2)); show('one', tick(1))\n"
                     "see(contact('C1', 60, 2), contact('C2', 59, 1)); show('two', tick(2))", database, lua_dll)
    assert out[0].startswith("one launched=0") and out[1].startswith("two launched=4")
    p, m, jets, bear = scenario(window=True, window_from=10, window_to=20, flag=True, flag_key="GO")
    out = play(p, m, "see(contact('C1', 60, 2)); show('early', tick(5)); show('no flag', tick(12))\n"
                     "StudioSetFlag('GO', true); show('go', tick(13)); show('late', tick(30))", database, lua_dll)
    assert [x.split("launched=")[1][0] for x in out] == ["0", "0", "2", "0"]
    p, m, jets, bear = scenario(logic="any", posture=False, speed=True, speed_min=900)   # in the area OR that fast
    out = play(p, m, "see(contact('C1', 64, 8, {speed=500})); show('slow', tick(1))\n"
                     "see(contact('C2', 64, 8, {speed=950})); show('fast', tick(2))", database, lua_dll)
    assert out[0].startswith("slow launched=0") and out[1].startswith("fast launched=2")


# ------------------------------------------------------------------ never the same thing twice (1.11.0: CMO's
# "An item with the same key has already been added")
def test_the_same_aircraft_is_never_a_target_twice(database, lua_dll):
    p, m, jets, bear = scenario()
    out = play(p, m, r"""
see(contact('C1', 60, 2)); show('first', tick(1))
see(contact('NEW', 60, 2)); show('tracked again', tick(2))          -- lost, then found under a new contact id
see(contact('C1', 60, 2), contact('NEW', 60, 2)); show('both', tick(3))
print('IC reactivated ' .. tostring(MOCK.reactivated))
""", database, lua_dll)
    assert out[0] == "first launched=2 active=true targets=1 units=2"
    assert out[1] == "tracked again launched=0 active=true targets=1 units=2"
    assert out[2] == "both launched=0 active=true targets=1 units=2"
    assert out[3] == "reactivated nil"                       # switched on once, not every half minute


@pytest.mark.parametrize("flags", ["MOCK.emptyReply = true", "MOCK.emptyReply, MOCK.noTargetList = true, true", ""])
def test_whatever_cmo_answers_a_target_is_added_once(database, lua_dll, flags):
    p, m, jets, bear = scenario()
    out = play(p, m, flags + r"""
see(contact('C1', 60, 2)); show('a', tick(1)); show('b', tick(2)); show('c', tick(3))
""", database, lua_dll)
    assert out[0] == "a launched=2 active=true targets=1 units=2" and out[2].endswith("targets=1 units=2")


def test_contact_without_a_unit_id_uses_its_own(database, lua_dll):
    p, m, jets, bear = scenario()
    out = play(p, m, r"""
local c = contact('C1', 60, 2)
MOCK.contactUnit = function(g) if g == 'C1' then return bear.guid end end
c.actualunitid = nil
see(c); show('a', tick(1)); show('b', tick(2))
""", database, lua_dll)
    assert out[0].endswith("targets=1 units=2") and out[1].endswith("targets=1 units=2")


def two_bases():
    """QRA North from Lossiemouth, QRA South from Coningsby."""
    p, north, jets, bear = scenario()
    uk = p.sides[0]
    t = default_library().template("uk_ab_coningsby")
    res = place_template(p, t, None, uk.id, *t.location)
    hangar = next(u for u in res.units if "Hangar (4x Large)" in u.name)
    bats = [Unit(side=uk.id, type="Aircraft", dbid=TYPHOON, name=f"BAT {i}", host=hangar.id, loadout=METEOR)
            for i in (1, 2, 3, 4)]
    p.units += bats
    p.zones.append(Zone(side=uk.id, name="QRA_SOUTH", points=[[50, -6], [55, -6], [55, 3], [50, 3]]))
    south = Mission(side=uk.id, name="QRA South", mclass="intercept", subtype="", zone=p.zones[-1].id,
                    units=[b.id for b in bats])
    intercept_of(south)
    p.missions.append(south)
    return p, north, south, jets, bats


def test_each_base_answers_only_its_own_intercept(database, lua_dll):
    p, north, south, jets, bats = two_bases()
    out = play(p, north, r"""
local function who(name)
  local t = {}
  for _, x in pairs(MOCK.missions) do if x.name == name then
    for _, g in ipairs(x.units) do t[#t + 1] = ScenEdit_GetUnit({ guid = g }).name end
  end end
  table.sort(t)
  return table.concat(t, ',')
end
see(contact('C1', 60, 2)); tick(1); print('IC north ' .. who('QRA North') .. ' south ' .. who('QRA South'))
see(contact('C1', 60, 2), contact('C2', 53, 0)); tick(2); print('IC north ' .. who('QRA North') .. ' south ' .. who('QRA South'))
for _, l in ipairs(STUDIO.INTERCEPTS) do print('IC msg ' .. tostring(l.message)) end
StudioInterceptReport()
""", database, lua_dll)
    assert out[0] == "north QRA 1,QRA 2 south "
    assert out[1] == "north QRA 1,QRA 2 south BAT 1,BAT 2"


def test_shared_aircraft_are_claimed_by_one_intercept_only(database, lua_dll):
    p, north, south, jets, bats = two_bases()
    south.units = [j.id for j in jets] + south.units              # the mix-up 1.11.0's editor made easy
    errs = [i.message for i in validate(p) if i.level == ERROR and i.obj_id == south.id]
    assert any("one intercept only" in e for e in errs)
    ics = {r["mission"]: r["names"] for r in compile_intercepts(p)}
    assert ics["QRA North"] == ["QRA 1", "QRA 2", "QRA 3", "QRA 4"]
    assert ics["QRA South"] == ["BAT 1", "BAT 2", "BAT 3", "BAT 4"]
    out = play(p, north, r"""
STUDIO.INTERCEPTS[2].names = STUDIO.INTERCEPTS[1].names            -- even if an old export shares them
see(contact('C1', 60, 2), contact('C2', 53, 0)); show('north', tick(1))
""", database, lua_dll)
    assert out[0].endswith("active=true targets=1 units=2")


def test_low_fuel_sends_an_aircraft_home_and_messages_are_plain(database, lua_dll):
    p, m, jets, bear = scenario()
    out = play(p, m, r"""
local said
local old = ScenEdit_SpecialMessage
ScenEdit_SpecialMessage = function(side, text) said = text; return old(side, text) end
see(contact('C1', 60, 2)); show('up', tick(1))
print('IC said ' .. tostring(said))
local u = ScenEdit_GetUnit({ name = 'QRA 1' })
u.condition_v, u.fuel = 'Airborne', { [2001] = { current = 900, max = 4000 } }
show('low', tick(2)); print('IC rtb ' .. tostring(u.rtb) .. ' ' .. tostring(ScenEdit_GetUnit({ name = 'QRA 2' }).rtb))
""", database, lua_dll)
    assert out[1].startswith("said QRA North: scramble! 2 aircraft") and "<" not in out[1]
    assert out[2] == "low launched=1 active=true targets=1 units=2"                 # another takes its place
    assert out[3] == "rtb true nil"


# ------------------------------------------------------------------ checks
def test_validation():
    p, m, jets, bear = scenario()
    assert not [i for i in validate(p) if i.obj_id == m.id and i.level in (ERROR, WARNING)]

    def msgs(level=ERROR):
        return " | ".join(i.message for i in validate(p) if i.obj_id == m.id and i.level == level)
    ic = intercept_of(m)
    m.zone = ""
    ic.reserve, ic.flag, ic.postures, ic.altitude, ic.alt_min, ic.alt_max = 3, True, [], True, 500, 100
    for must in ("no area is chosen", "cannot launch 2", "no flag is given", "'is classed as' is ticked",
                 "lowest altitude"):
        assert must in msgs(), must
    m.units = []
    assert "no aircraft on call" in msgs()
    m2 = Mission(side=p.sides[0].id, name="Old", mclass="strike", subtype="air")
    p.missions.append(m2)
    assert any("use an Intercept mission" in i.message for i in validate(p))


def test_timeline_and_briefing():
    from cmo_studio.model.briefing_pack import opord_html
    from cmo_studio.model.timeline import build_timeline
    p, m, jets, bear = scenario(window=True, window_from=30, window_to=90)
    tl = build_timeline(p)
    row = next(r for r in tl.rows if r.obj_id == m.id)
    assert row.marks[0].label == "on call" and row.marks[0].start == tl.start + 1800 and "Launches 2" in row.detail
    h = opord_html(p, p.sides[0].id)
    assert "quick reaction alert (QRA)" in h and "Launches 2 aircraft per contact" in h
    p.events.append(Event(name="Stand QRA down", triggers=[Trigger("StudioAfterDelay", {"Minutes": 60})],
                          actions=[Action("MissionStatus", {"Mission": m.id, "Active": False})]))
    assert "StudioMissionStatus" in str([e for e in compile_build_data(p)["EVENTS"] if e["name"] == "Stand QRA down"])


# ------------------------------------------------------------------ the editor
def test_editor(tmp_path, monkeypatch):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings, Qt

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    w = MainWindow(s)
    w.show()
    p, m, jets, bear = scenario()
    m.units = []
    m.mclass, m.subtype, m.intercept = "patrol", "aaw", None
    w.doc.load(p)
    pg = w.missions_page
    w.tabs.setCurrentWidget(pg)
    pg.mid = m.id
    pg.refresh()
    app.processEvents()
    assert not pg.intercept.isVisible()
    pg.mclass.setCurrentIndex(pg.mclass.findData("intercept"))
    app.processEvents()
    f = pg.intercept
    assert f.isVisible() and not pg.tgt_box.isVisible() and f.bases.item(0).text().startswith("Lossiemouth")
    f.bases.item(0).setCheckState(Qt.CheckState.Checked)

    def ms():
        return w.doc.project.mission(m.id)
    assert len(ms().units) == 4
    f.boxes["near"].setChecked(True)
    f.values["near_nm"].setValue(75)
    f.postures["X"].setChecked(False)
    assert ms().intercept.near and ms().intercept.near_nm == 75 and ms().intercept.postures == ["H", "U"]
    assert not f.values["speed_min"].isEnabled() and f.values["near_nm"].isEnabled()
    assert "within 75 nm" in f.summary.text()
    f.boxes["flag"].setChecked(True)
    f.values["flag_key"].setText("GO")
    f.values["flag_key"].textEdited.emit("GO")
    assert ms().intercept.flag_key == "GO"
    f.presetChosen.emit("raid")
    assert ms().intercept.raid and ms().intercept.roe == "free" and f.boxes["raid"].isChecked()
    w.doc.undo()
    assert ms().intercept.near_nm == 75 and not ms().intercept.raid
    assert all(u.type == "Aircraft" for u in (w.doc.project.unit(i) for _l, i in pg._unit_choices()))
    for k in PRESETS:
        apply_preset(ms(), k)
    w.doc.set_dirty(False)
    w.close()


def test_editor_keeps_each_base_on_its_own_mission(tmp_path, monkeypatch):
    """1.11.0: the base box kept the last mission's base and the button only added, so QRA South got all eight."""
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings, Qt

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    w = MainWindow(s)
    w.show()
    p, north, south, jets, bats = two_bases()
    north.units, south.units = [], []
    w.doc.load(p)
    pg = w.missions_page
    w.tabs.setCurrentWidget(pg)
    Box = QtWidgets.QMessageBox
    asked = []

    def answer(yes):
        monkeypatch.setattr(Box, "question", staticmethod(
            lambda *a, **k: (asked.append(a[2]), Box.StandardButton.Yes if yes else Box.StandardButton.No)[1]))

    def open_(m):
        pg.mid = m.id
        pg.refresh()
        app.processEvents()

    def tick(base, on=True):
        lst = pg.intercept.bases
        it = next(lst.item(i) for i in range(lst.count()) if lst.item(i).text().startswith(base))
        it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)

    def names(m):
        pr = w.doc.project
        return [pr.unit(i).name.split()[0] for i in pr.mission(m.id).units]

    def state(base):
        lst = pg.intercept.bases
        return next(lst.item(i) for i in range(lst.count()) if lst.item(i).text().startswith(base)).checkState()
    answer(False)
    open_(north)
    tick("Lossiemouth")
    assert names(north) == ["QRA"] * 4 and names(south) == [] and not asked
    open_(south)
    assert state("Lossiemouth") == Qt.CheckState.Unchecked             # nothing carried over from North
    assert "4 on QRA North" in pg.intercept.bases.item(1).text()
    tick("Coningsby")
    assert names(south) == ["BAT"] * 4 and names(north) == ["QRA"] * 4
    tick("Lossiemouth")                                                  # already on North: asks; No leaves it alone
    assert asked and names(south) == ["BAT"] * 4 and names(north) == ["QRA"] * 4
    assert state("Lossiemouth") == Qt.CheckState.Unchecked
    answer(True)
    tick("Lossiemouth")
    assert sorted(set(names(south))) == ["BAT", "QRA"] and names(north) == []
    w.doc.undo()                                                         # moving them is one undo
    assert names(south) == ["BAT"] * 4 and names(north) == ["QRA"] * 4
    open_(south)
    tick("Coningsby", False)
    assert names(south) == [] and names(north) == ["QRA"] * 4
    w.doc.set_dirty(False)
    w.close()
