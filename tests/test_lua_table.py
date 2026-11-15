from cmo_studio.importers.legacy_lua import import_legacy_build
from cmo_studio.importers.lua_table import LuaTableReader

SRC = r"""
--[[ header ]]
local A, S, U, F = 'Aircraft', 'Ship', 'Submarine', 'Facility'
local LO_X = 31552  -- comment
RW = {}
RW.CFG = { SIDE_RED = 'Red', SIDE_BLUE = 'Blue', START = { month = 3, day = 27, year = 2028, hour = 3, min = 0, sec = 0 },
  DURATION_DAYS = 2, SCRIPT_PATH = scenarioScriptFilePath or '/X/', WEATHER = { temp = 3, rain = 8, cloud = 0.6, sea = 3 } }
RW.LOADOUTS = { JET = 1836 }
RW.DB = {
  AF  = { t=F, id=1592, n={'Airfield'} },
  JET = { t=A, id=6180, n={'F-35A'} },
  SHIP = { t=S, id=2814, n={"Ship [x]"} },
  BAD = { t=S, id=nil, n={'?'} },
}
RW.BASES = { { s='BLUE', k='AF', n='Base', lat=59.0, lon=24.0, ac={ {'JET', 4, 'Sqn'}, {'JET', 2, 'Sqn2', LO_X} } } }
RW.UNITS = {
  {'RED','SHIP','Ship 1', 59.5, 26.0, 'AH', 'GRP'},
  {'RED','BAD','Nope', 59.5, 26.0},
}
RW.ZONES = { RED = { PAT = { {60,26},{60,27},{59,27} } } }
RW.MISSIONS = { {'RED','Patrol','patrol','naval','PAT','GRP'} }
"""


def test_reader_handles_locals_and_expressions():
    r = LuaTableReader(SRC)
    cfg = r.read("RW.CFG")
    assert cfg["SIDE_RED"] == "Red" and cfg["SCRIPT_PATH"] is None
    assert r.read("RW.DB")["JET"]["t"] == "Aircraft"
    assert r.read("RW.BASES")[0]["ac"][1][3] == 31552


def test_import(tmp_path):
    f = tmp_path / "Demo" / "Build_Scenario.lua"
    f.parent.mkdir()
    f.write_text(SRC)
    p, report = import_legacy_build(f)
    assert p.meta.title == "Demo"
    assert {s.name for s in p.sides} == {"Red", "Blue"}
    assert p.clock.start.startswith("2028-03-27T03:00")
    jets = [u for u in p.units if u.type == "Aircraft"]
    assert sum(u.count for u in jets) == 6 and {u.loadout for u in jets} == {1836, 31552}
    ship = next(u for u in p.units if u.type == "Ship")
    assert ship.radar_active and ship.hold_position
    assert p.missions[0].units == [ship.id] and p.missions[0].zone
    assert any("BAD" in line for line in report)
