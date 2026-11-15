"""Persistent application settings (QSettings) and CMO install detection."""

from __future__ import annotations

import os
import re
import string
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QStandardPaths

from . import APP_NAME, ORG_NAME

CMO_FOLDER = "Command - Modern Operations"


def looks_like_cmo(path: str | os.PathLike | None) -> bool:
    if not path:
        return False
    p = Path(path)
    return p.is_dir() and (p / "DB").is_dir() and ((p / "Command.exe").is_file() or (p / "Lua").is_dir())


def _steam_libraries() -> list[Path]:
    """Steam library folders from libraryfolders.vdf plus the usual default locations."""
    roots: list[Path] = []
    candidates = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam",
                  Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Steam"]
    for steam in candidates:
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                text = vdf.read_text(encoding="utf-8", errors="ignore")
                for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                    roots.append(Path(m.group(1).replace("\\\\", "\\")))
            except OSError:
                pass
        roots.append(steam)
    for drive in string.ascii_uppercase:
        for sub in ("SteamLibrary", r"Steam", r"Games\Steam", r"Program Files (x86)\Steam"):
            p = Path(f"{drive}:\\") / sub
            if p.is_dir():
                roots.append(p)
    seen, out = set(), []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def detect_cmo_dir() -> Optional[Path]:
    env = os.environ.get("CMO_DIR")
    if looks_like_cmo(env):
        return Path(env)
    if os.name != "nt":
        return None
    for lib in _steam_libraries():
        p = lib / "steamapps" / "common" / CMO_FOLDER
        if looks_like_cmo(p):
            return p
    return None


ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{service}/MapServer/tile/{{z}}/{{y}}/{{x}}"

#: name: (url template, attribution, max zoom). All of these serve desktop clients without an API key.
TILE_SOURCES: dict[str, tuple[str, str, int]] = {
    "Esri Dark Gray": (ESRI.format(service="Canvas/World_Dark_Gray_Base"), "Tiles © Esri — Esri, HERE, Garmin, "
                                                                            "© OpenStreetMap contributors", 16),
    "Esri Ocean": (ESRI.format(service="Ocean/World_Ocean_Base"), "Tiles © Esri — GEBCO, NOAA, Garmin, HERE", 13),
    "Esri World Imagery": (ESRI.format(service="World_Imagery"), "Imagery © Esri, Maxar, Earthstar Geographics", 18),
    "OpenStreetMap": ("https://tile.openstreetmap.org/{z}/{x}/{y}.png", "© OpenStreetMap contributors", 19),
    "OpenTopoMap": ("https://tile.opentopomap.org/{z}/{x}/{y}.png", "© OpenStreetMap contributors, SRTM | "
                                                                    "© OpenTopoMap (CC-BY-SA)", 17),
    "None (offline grid)": ("", "", 12),
}
DEFAULT_TILES = "Esri Dark Gray"


class AppSettings:
    def __init__(self):
        self.q = QSettings(ORG_NAME, APP_NAME)

    def _get(self, key, default=None, typ=None):
        v = self.q.value(key, default)
        if typ is bool:
            return v in (True, "true", "1", 1)
        if typ is int:
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        return v

    # CMO install folder
    @property
    def cmo_dir(self) -> str:
        v = self._get("cmo_dir", "")
        if not v or not looks_like_cmo(v):
            found = detect_cmo_dir()
            if found:
                v = str(found)
                self.q.setValue("cmo_dir", v)
        return v or ""

    @cmo_dir.setter
    def cmo_dir(self, v: str) -> None:
        self.q.setValue("cmo_dir", v)

    @property
    def db_file(self) -> str:
        return self._get("db_file", "")

    @db_file.setter
    def db_file(self, v: str) -> None:
        self.q.setValue("db_file", v)

    @property
    def tile_source(self) -> str:
        v = self._get("tile_source", DEFAULT_TILES)
        return v if v in TILE_SOURCES or v == "Custom" else DEFAULT_TILES

    @tile_source.setter
    def tile_source(self, v: str) -> None:
        self.q.setValue("tile_source", v)

    @property
    def custom_tile_url(self) -> str:
        return self._get("custom_tile_url", "")

    @custom_tile_url.setter
    def custom_tile_url(self, v: str) -> None:
        self.q.setValue("custom_tile_url", v)

    @property
    def autosave_minutes(self) -> int:
        return self._get("autosave_minutes", 5, int)

    @autosave_minutes.setter
    def autosave_minutes(self, v: int) -> None:
        self.q.setValue("autosave_minutes", int(v))

    @property
    def check_updates(self) -> bool:
        return self._get("check_updates", True, bool)

    @check_updates.setter
    def check_updates(self, v: bool) -> None:
        self.q.setValue("check_updates", bool(v))

    @property
    def skipped_version(self) -> str:
        return self._get("skipped_version", "") or ""

    @skipped_version.setter
    def skipped_version(self, v: str) -> None:
        self.q.setValue("skipped_version", v)

    @property
    def export_dir(self) -> str:
        return self._get("export_dir", "")

    @export_dir.setter
    def export_dir(self, v: str) -> None:
        self.q.setValue("export_dir", v)

    @property
    def recent_files(self) -> list[str]:
        v = self._get("recent_files", []) or []
        if isinstance(v, str):
            v = [v]
        return [x for x in v if x and Path(x).is_file()][:10]

    def add_recent(self, path: str) -> None:
        files = [path] + [x for x in self.recent_files if Path(x) != Path(path)]
        self.q.setValue("recent_files", files[:10])

    def value(self, key, default=None):
        return self.q.value(key, default)

    def set_value(self, key, v) -> None:
        self.q.setValue(key, v)

    @staticmethod
    def data_dir() -> Path:
        p = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def cache_dir() -> Path:
        p = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation))
        p.mkdir(parents=True, exist_ok=True)
        return p

    def backup_dir(self) -> Path:
        p = self.data_dir() / "export_backups"
        p.mkdir(parents=True, exist_ok=True)
        return p
