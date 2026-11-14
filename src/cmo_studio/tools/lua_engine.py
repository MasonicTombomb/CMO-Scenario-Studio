"""Run Lua with CMO's own interpreter (``[CMO]\\lua54.dll``) through ctypes.

Used for two things:

* :func:`check_syntax` - compile (not run) a chunk and return the error, if any.
* :func:`dry_run_build` - export a project to a temporary folder and execute
  ``Build_Scenario.lua`` against ``Studio_Mock.lua``, a strict stand-in for the
  ScenEdit API, then run every generated event script once.

Nothing here needs CMO to be running. If the DLL is missing (or the Python is
32-bit) the functions report that instead of failing.
"""

from __future__ import annotations

import ctypes
import os
import struct
import tempfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

_LUA_MULTRET = -1


class LuaUnavailable(RuntimeError):
    pass


def find_lua_dll(cmo_dir: str | os.PathLike | None) -> Optional[Path]:
    if not cmo_dir:
        return None
    p = Path(cmo_dir) / "lua54.dll"
    return p if p.is_file() else None


class LuaState:
    """A minimal Lua 5.4 state over the C API."""

    def __init__(self, dll_path: str | os.PathLike):
        if struct.calcsize("P") != 8:
            raise LuaUnavailable("CMO's lua54.dll is 64-bit; run the studio with 64-bit Python.")
        try:
            self.dll = ctypes.CDLL(str(dll_path))
        except OSError as exc:
            raise LuaUnavailable(f"Cannot load {dll_path}: {exc}") from exc
        d = self.dll
        d.luaL_newstate.restype = ctypes.c_void_p
        d.luaL_openlibs.argtypes = [ctypes.c_void_p]
        d.luaL_loadbufferx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
                                       ctypes.c_char_p]
        d.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                 ctypes.c_void_p]
        d.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        d.lua_tolstring.restype = ctypes.c_char_p
        d.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        d.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        d.lua_close.argtypes = [ctypes.c_void_p]
        self.L = d.luaL_newstate()
        d.luaL_openlibs(self.L)

    def close(self) -> None:
        if self.L:
            self.dll.lua_close(self.L)
            self.L = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _top_string(self) -> str:
        s = self.dll.lua_tolstring(self.L, -1, None)
        return s.decode("utf-8", errors="replace") if s else "(no message)"

    def compile(self, source: str, chunk_name: str = "chunk") -> Optional[str]:
        data = source.encode("utf-8")
        rc = self.dll.luaL_loadbufferx(self.L, data, len(data), ("=" + chunk_name).encode(), b"t")
        err = self._top_string() if rc != 0 else None
        self.dll.lua_settop(self.L, 0)
        return err

    def run(self, source: str, chunk_name: str = "chunk") -> Optional[str]:
        data = source.encode("utf-8")
        rc = self.dll.luaL_loadbufferx(self.L, data, len(data), ("=" + chunk_name).encode(), b"t")
        if rc == 0:
            rc = self.dll.lua_pcallk(self.L, 0, 0, 0, None, None)
        err = self._top_string() if rc != 0 else None
        self.dll.lua_settop(self.L, 0)
        return err

    def get_string(self, name: str) -> str:
        self.dll.lua_getglobal(self.L, name.encode())
        s = self.dll.lua_tolstring(self.L, -1, None)
        self.dll.lua_settop(self.L, 0)
        return s.decode("utf-8", errors="replace") if s else ""


def check_syntax(dll_path: str | os.PathLike, files: dict[str, str]) -> dict[str, str]:
    """Compile each ``name -> source``; return ``name -> error`` for the ones that fail."""
    errors = {}
    with LuaState(dll_path) as L:
        for name, src in files.items():
            err = L.compile(src, name)
            if err:
                errors[name] = err
    return errors


@dataclass
class DryRunResult:
    ok: bool
    output: str = ""
    errors: list[str] = field(default_factory=list)


def _lq(s: str) -> str:
    return '"' + s.replace("\\", "/").replace('"', '\\"') + '"'


def dry_run_build(project, dll_path: str | os.PathLike, variant: Optional[str] = None) -> DryRunResult:
    """Export to a temp folder and run the builder (and every event script) against the mock API."""
    from ..export.exporter import Exporter

    exp = Exporter(project)
    mock = resources.files("cmo_studio.export").joinpath("lua", "Studio_Mock.lua").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="cmo_studio_dry_") as tmp:
        exp.write(tmp, backup_dir=None, clean=False, include_readme=False)
        lua_root = Path(tmp) / "Lua"
        prelude = (
            f"LUA_ROOT = {_lq(str(lua_root))}\n"
            f"MOCK_START = {project.clock.start_epoch()}\n"
            "STUDIO_OUT = {}\n"
            "print = function(...) local t = {} for i = 1, select('#', ...) do t[#t + 1] = tostring(select(i, ...)) end "
            "STUDIO_OUT[#STUDIO_OUT + 1] = table.concat(t, '\\t') end\n"
        )
        script = (
            (f"STUDIO_BUILD_VARIANT = {_lq(variant)}\n" if variant else "")
            + f"ScenEdit_RunScript({_lq('/' + exp.folder + '/Build_Scenario.lua')})\n"
            + "local n, bad = MOCK_RUN_EVENT_SCRIPTS()\n"
            + "print(MOCK_SUMMARY())\n"
            + "print(string.format('MOCK: ran %d event and special-action script(s) once', n))\n"
            + "for _, b in ipairs(bad) do print('MOCK SCRIPT ERROR: ' .. b) end\n"
            + "for _, e in ipairs(MOCK.errors) do print('MOCK API ERROR: ' .. e) end\n"
            + "STUDIO_TEXT = table.concat(STUDIO_OUT, '\\n')\n"
        )
        with LuaState(dll_path) as L:
            err = L.run(prelude + mock, "Studio_Mock")
            if err:
                return DryRunResult(False, "", [f"Mock failed to load: {err}"])
            err = L.run(script, "dry_run")
            out = L.get_string("STUDIO_TEXT")
            if not out:
                L.run("STUDIO_TEXT = table.concat(STUDIO_OUT or {}, '\\n')", "collect")
                out = L.get_string("STUDIO_TEXT")
    errors = [ln for ln in out.splitlines() if ln.startswith(("MOCK SCRIPT ERROR", "MOCK API ERROR", "FAILED")) or
              "ABORTED" in ln or "WARN:" in ln]
    if err:
        errors.insert(0, err)
    ok = not err and not any(e.startswith(("MOCK SCRIPT ERROR", "MOCK API ERROR")) or "ABORTED" in e
                             for e in errors)
    return DryRunResult(ok, out, errors)
