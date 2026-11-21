"""Weather forecast: timed weather changes after the start (compiler table and the built events)."""
import re

from cmo_studio.export.compiler import compile_build_data
from cmo_studio.model import new_project
from cmo_studio.model.project import Project, WeatherEntry


def forecast_project():
    p = new_project("Weather", "DB3K_519.db3")
    p.forecast = [WeatherEntry(180, 8.0, 20, 0.9, 5), WeatherEntry(60, 12.0, 0, 0.4, 3),
                  WeatherEntry(0, 30.0, 0, 0.0, 0)]          # offset 0 is the start weather: not a change
    return p


def test_forecast_round_trip_and_table():
    p = forecast_project()
    q = Project.from_json(p.to_json())
    assert [e.offset_minutes for e in q.forecast] == [180, 60, 0]
    start = p.clock.start_epoch()
    fc = compile_build_data(p)["FORECAST"]
    assert [f["t"] for f in fc] == [start + 3600, start + 3 * 3600]          # sorted, offset 0 left out
    assert fc[0] == {"t": start + 3600, "temp": 12.0, "rain": 0, "cloud": 0.4, "sea": 3}


def test_forecast_builds_one_event_per_change(lua_dll):
    from cmo_studio.tools.lua_engine import dry_run_build
    res = dry_run_build(forecast_project(), lua_dll)
    assert res.ok and "MOCK API ERROR" not in res.output, res.output
    assert re.search(r"weather changes\s+2", res.output)
    assert "Weather forecast (2 change(s))" in res.output


def test_every_build_table_is_written_to_the_build_script():
    """1.9.0 compiled the forecast but never wrote it into Build_Scenario.lua."""
    from cmo_studio.export.exporter import Exporter
    p = forecast_project()
    lua = Exporter(p).build_scenario_lua()
    for key in compile_build_data(p):
        assert f"D.{key} = " in lua, key
