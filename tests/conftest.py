import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _cmo_dir():
    env = os.environ.get("CMO_DIR")
    if env and Path(env, "DB").is_dir():
        return Path(env)
    try:
        from cmo_studio.settings import detect_cmo_dir
        return detect_cmo_dir()
    except Exception:  # noqa: BLE001 - PyQt may be missing in a minimal CI
        return None


@pytest.fixture(scope="session")
def cmo_dir():
    d = _cmo_dir()
    if not d:
        pytest.skip("CMO install not found (set CMO_DIR to run database/Lua tests)")
    return d


@pytest.fixture(scope="session")
def lua_dll(cmo_dir):
    p = cmo_dir / "lua54.dll"
    if not p.is_file():
        pytest.skip("lua54.dll not found in the CMO folder")
    return p


@pytest.fixture(scope="session")
def database(cmo_dir):
    from cmo_studio.db import Database, latest_database
    p = latest_database(cmo_dir)
    if not p:
        pytest.skip("No DB3K database found")
    return Database(p)


@pytest.fixture
def sample():
    from sample import make_sample
    return make_sample()
