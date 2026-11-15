"""Where the studio's own files are, both from a source checkout and in the packaged .exe."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """The release folder (next to CMO-Scenario-Studio.exe) or the repository root."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PACKAGE_DIR.parents[1]


def resource(name: str) -> Path:
    return PACKAGE_DIR / "resources" / name


def docs_dir() -> Path:
    return app_dir() / "docs"


def examples_dir() -> Path:
    return app_dir() / "examples"
