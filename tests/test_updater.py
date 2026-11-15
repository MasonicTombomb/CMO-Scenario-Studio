"""Updater: version comparison, GitHub release parsing, checksum/URL safety and the update dialog (no network)."""
import hashlib
import io
import json
import os

import pytest

from cmo_studio import __version__, updater
from cmo_studio.updater import (ReleaseInfo, UpdateError, expected_sha256, install_mode, is_newer, parse_version,
                                release_from_json, verify_installer)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SAMPLE = {
    "tag_name": "v9.1.0", "name": "CMO Scenario Studio 9.1.0", "body": "## New\n- things",
    "html_url": "https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases/tag/v9.1.0",
    "published_at": "2026-12-01T10:00:00Z",
    "assets": [
        {"name": "CMO-Scenario-Studio-9.1.0-win64.zip", "size": 10,
         "browser_download_url": "https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases/download/v9.1.0/"
                                 "CMO-Scenario-Studio-9.1.0-win64.zip"},
        {"name": "CMO-Scenario-Studio-9.1.0-setup.exe", "size": 12,
         "browser_download_url": "https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases/download/v9.1.0/"
                                 "CMO-Scenario-Studio-9.1.0-setup.exe"},
        {"name": "CMO-Scenario-Studio-9.1.0-setup.exe.sha256", "size": 90,
         "browser_download_url": "https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases/download/v9.1.0/"
                                 "CMO-Scenario-Studio-9.1.0-setup.exe.sha256"},
    ],
}


def test_versions():
    assert parse_version("v1.5.2") == (1, 5, 2)
    assert parse_version("1.6.0-beta") == (1, 6)
    assert parse_version("1.6") == parse_version("1.6.0")
    assert parse_version("garbage") == ()
    assert is_newer("1.10.0", "1.9.9") and is_newer("v2.0", "1.99")
    assert not is_newer("1.5.2", "1.5.2") and not is_newer("1.5.1", "1.5.2") and not is_newer("", "1.0")
    assert not is_newer(__version__)


def test_release_parsing():
    r = release_from_json(SAMPLE)
    assert r.version == "9.1.0" and r.is_newer
    assert r.installer.name.endswith("-setup.exe") and r.installer_sha256.name.endswith(".sha256")
    assert r.asset(".zip").size == 10


def test_fetch_latest_uses_github_api(monkeypatch):
    seen = {}

    class Resp(io.BytesIO):
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout):
        seen["url"] = req.full_url
        seen["ua"] = req.get_header("User-agent")
        return Resp(json.dumps(SAMPLE).encode())
    monkeypatch.setattr(updater._opener, "open", fake_open)
    r = updater.fetch_latest()
    assert seen["url"] == updater.API_LATEST and "CMO-Scenario-Studio/" in seen["ua"]
    assert r.version == "9.1.0"


def test_only_github_urls_are_followed():
    updater._check_url("https://github.com/x/y/releases/download/v1/a.exe")
    updater._check_url("https://objects.githubusercontent.com/abc")
    for bad in ("http://github.com/x", "https://evil.example.com/a.exe", "https://github.com.evil.io/a",
                "file:///C:/a.exe"):
        with pytest.raises(UpdateError):
            updater._check_url(bad)


def test_checksum_file_parsing():
    d = "a" * 64
    assert expected_sha256(f"{d}  CMO-Scenario-Studio-9.1.0-setup.exe\n", "CMO-Scenario-Studio-9.1.0-setup.exe") == d
    assert expected_sha256(f"{d.upper()} *x.exe", "x.exe") == d
    with pytest.raises(UpdateError):
        expected_sha256(f"{d}  other.exe", "x.exe")


def test_verify_installer(tmp_path, monkeypatch):
    f = tmp_path / "CMO-Scenario-Studio-9.1.0-setup.exe"
    f.write_bytes(b"not really an installer")
    good = hashlib.sha256(f.read_bytes()).hexdigest()
    monkeypatch.setattr(updater, "authenticode", lambda p: updater.Signature("NotSigned"))
    assert verify_installer(f, f"{good}  {f.name}").status == "NotSigned"
    with pytest.raises(UpdateError, match="checksum"):
        verify_installer(f, f"{'0' * 64}  {f.name}")
    # a signed copy only accepts an installer from the same publisher
    me = tmp_path / "me.exe"
    me.write_bytes(b"x")
    sigs = {f: updater.Signature("Valid", "CN=Someone Else"), me: updater.Signature("Valid", "CN=Studio")}
    monkeypatch.setattr(updater, "authenticode", lambda p: sigs[p])
    with pytest.raises(UpdateError, match="different publisher"):
        verify_installer(f, f"{good}  {f.name}", me)
    sigs[f] = updater.Signature("NotSigned")
    with pytest.raises(UpdateError, match="not validly signed"):
        verify_installer(f, f"{good}  {f.name}", me)
    sigs[f] = updater.Signature("Valid", "CN=Studio")
    assert verify_installer(f, f"{good}  {f.name}", me).valid


def test_prepare_update_downloads_and_verifies(tmp_path, monkeypatch):
    payload = b"setup-bytes" * 1000
    digest = hashlib.sha256(payload).hexdigest()
    rel = release_from_json(SAMPLE)

    class Resp(io.BytesIO):
        def __init__(self, data):
            super().__init__(data)
            self.headers = {"Content-Length": str(len(data))}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(url, timeout, accept="application/octet-stream"):
        updater._check_url(url)
        if url.endswith(".sha256"):
            return Resp(f"{digest}  {rel.installer.name}\n".encode())
        return Resp(payload)
    monkeypatch.setattr(updater, "_open", fake_open)
    monkeypatch.setattr(updater, "authenticode", lambda p: updater.Signature("NotSigned"))
    seen = []
    path, sig = updater.prepare_update(rel, lambda d, t: seen.append((d, t)) or True, folder=tmp_path)
    assert path.read_bytes() == payload and seen[-1] == (len(payload), len(payload))
    # cancelling stops the download and leaves nothing behind
    other = tmp_path / "x"
    other.mkdir()
    with pytest.raises(UpdateError, match="cancelled"):
        updater.prepare_update(rel, lambda d, t: False, folder=other)
    assert not list(other.iterdir())


def test_install_mode_from_source():
    assert install_mode() == "source"


# ------------------------------------------------------------------ UI
@pytest.fixture
def window(tmp_path, sample, monkeypatch):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.show()
    w.doc.load(sample)
    yield w, app
    w.doc.set_dirty(False)
    w.close()


def test_update_dialog_modes(window):
    from cmo_studio.ui.update_ui import UpdateDialog
    rel = release_from_json(SAMPLE)
    d = UpdateDialog(rel, "installed", window[0])
    names = [b.text() for b in d.findChildren(__import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton)]
    assert "Download and install" in names and "Skip this version" in names
    d2 = UpdateDialog(rel, "portable", window[0])
    names2 = [b.text() for b in d2.findChildren(__import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton)]
    assert "Open release page" in names2 and "Download and install" not in names2


def test_skip_version_and_up_to_date(window, monkeypatch):
    w, app = window
    from cmo_studio.ui import update_ui
    rel = release_from_json(SAMPLE)

    def fake_exec(self):
        self.choice = update_ui.UpdateDialog.SKIP
        return 1
    monkeypatch.setattr(update_ui.UpdateDialog, "exec", fake_exec)
    worker = update_ui._Worker()
    w.updater._workers.append(worker)
    w.updater._checked(rel, None, False, worker)
    assert w.settings.skipped_version == "9.1.0"
    # a skipped version is not offered again automatically
    shown = []
    monkeypatch.setattr(update_ui.UpdateDialog, "exec", lambda self: shown.append(1) or 1)
    worker2 = update_ui._Worker()
    w.updater._workers.append(worker2)
    w.updater._checked(rel, None, False, worker2)
    assert shown == []
    # the current version is not an update
    old = ReleaseInfo(version=__version__, tag="v" + __version__, name="", notes="", page="")
    worker3 = update_ui._Worker()
    w.updater._workers.append(worker3)
    w.updater._checked(old, None, False, worker3)
    assert shown == []


def test_save_falls_back_when_folder_is_read_only(window, tmp_path, monkeypatch):
    w, app = window
    from pathlib import Path

    from cmo_studio.ui import main_window as mw
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    w.doc.path = Path(tmp_path / "ro" / "x.cmoproj")
    (tmp_path / "ro").mkdir()
    monkeypatch.setattr(mw, "_writable_dir", lambda d: d != tmp_path / "ro")
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    target = tmp_path / "saved.cmoproj"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    assert w.save_project()
    assert target.is_file() and w.doc.path == target
