"""tools/release_check.py: the parts that must hold on every commit, not only at release time."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_check  # noqa: E402


def test_version_is_the_same_everywhere():
    """1.9.0 left the User Manual saying 1.8.1."""
    found = release_check.versions()
    assert len(set(found.values())) == 1, found


def test_every_build_table_reaches_the_build_script():
    release_check.results.clear()
    release_check.check_build_tables()
    assert all(ok for ok, *_ in release_check.results), release_check.results


def test_failures_are_reported(monkeypatch, capsys):
    monkeypatch.setattr(release_check, "versions", lambda: {"pyproject.toml": "1.2.3", "b": "1.2.4",
                                                             "src/cmo_studio/__init__.py": "1.2.3"})
    release_check.results.clear()
    release_check.check_version("v1.2.3")
    ok, what, detail = release_check.results[0]
    assert not ok and "b: 1.2.4" in detail


def test_manual_fingerprint_ignores_line_endings(tmp_path, monkeypatch):
    pytest.importorskip("markdown")
    import make_manuals
    before = make_manuals.sources_digest()
    md = next(f for f in make_manuals.source_files() if f.suffix == ".md")
    text = md.read_bytes()
    try:
        md.write_bytes(text.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))   # as a CRLF checkout would
        assert make_manuals.sources_digest() == before
        md.write_bytes(text + b"\nchanged\n")
        assert make_manuals.sources_digest() != before
    finally:
        md.write_bytes(text)
