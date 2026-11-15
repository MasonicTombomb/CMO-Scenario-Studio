import json
import zipfile

from cmo_studio.export import Exporter
from cmo_studio.export.exporter import MANIFEST


def test_file_layout(sample):
    files = Exporter(sample).build_files()
    f = sample.meta.folder()
    for rel in (f"Lua/{f}/Build_Scenario.lua", f"Lua/{f}/LuaInit.lua", f"Lua/{f}/Studio_Runtime.lua",
                f"Lua/{f}/Build_PLAY_BLUE.lua", f"Lua/{f}/Helpers.lua", f"Lua/{f}/project.cmoproj",
                f"Scenarios/{f}/TestScenario_Desc.html", f"Scenarios/{f}/TestScenario_Desc_PLAY_BLUE.html",
                f"Scenarios/{f}/TestScenario_Briefing_BLUE.html", f"Scenarios/{f}/briefing_style_dark.css",
                "README.md"):
        assert rel in files, rel
    assert "\r\n" in files[f"Lua/{f}/Build_Scenario.lua"]


def test_write_manifest_and_clean(sample, tmp_path):
    exp = Exporter(sample)
    res = exp.write(tmp_path, backup_dir=tmp_path / "bak")
    manifest = json.loads((tmp_path / exp.lua_dir / MANIFEST).read_text())
    assert len(manifest["files"]) == len(res.written)
    # a user's .scen next to the pages must survive re-exports
    scen = tmp_path / exp.scen_dir / "Test Scenario.scen"
    scen.write_text("keep me")
    sample.scripts.clear()
    for e in sample.events:
        e.actions = [a for a in e.actions if a.type != "RunScript"]
    res2 = exp.write(tmp_path, backup_dir=tmp_path / "bak")
    assert any(p.name == "Helpers.lua" for p in res2.removed)
    assert scen.read_text() == "keep me"
    assert res2.backup and res2.backup.is_file()


def test_preflight_detects_foreign_folder(sample, tmp_path):
    exp = Exporter(sample)
    lua = tmp_path / exp.lua_dir
    lua.mkdir(parents=True)
    (lua / "LuaInit.lua").write_text("-- someone else's")
    existing, managed = exp.preflight(tmp_path)
    assert existing and not managed


def test_zip(sample, tmp_path):
    z = Exporter(sample).write_zip(tmp_path / "x.zip")
    names = zipfile.ZipFile(z).namelist()
    assert any(n.endswith("Build_Scenario.lua") for n in names)
