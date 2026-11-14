"""Tests that need a local CMO install (skipped otherwise; set CMO_DIR to point at it)."""
from cmo_studio.export import Exporter
from cmo_studio.model.validation import ERROR, validate
from cmo_studio.tools.lua_engine import check_syntax, dry_run_build


def test_database_search_and_details(database):
    rows = database.search("Ship", "Steregushchiy", include_deprecated=True)
    assert rows
    d = database.details("Ship", rows[0].id)
    assert d.sensors and d.weapons


def test_exact_id_lookup(database):
    e = database.search("Ship", "", limit=1)[0]
    assert database.get("Ship", e.id).id == e.id


def test_sample_validates_against_db(sample, database):
    assert [i for i in validate(sample, database) if i.level == ERROR] == []


def test_generated_lua_compiles(sample, lua_dll):
    lua = {k: v for k, v in Exporter(sample).build_files().items() if k.endswith(".lua")}
    assert check_syntax(lua_dll, lua) == {}


def test_dry_run(sample, lua_dll):
    res = dry_run_build(sample, lua_dll)
    assert res.ok, res.output
    assert "BUILD REPORT" in res.output
    res = dry_run_build(sample, lua_dll, "PLAY_BLUE")
    assert res.ok and "Play as Blue" in res.output
