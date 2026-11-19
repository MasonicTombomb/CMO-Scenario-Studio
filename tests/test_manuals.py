"""The PDF manuals: sources render, images exist, the app opens them."""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

markdown = pytest.importorskip("markdown")
sys.path.insert(0, str(ROOT / "tools"))
import make_manuals  # noqa: E402


@pytest.mark.parametrize("key", list(make_manuals.MANUALS))
def test_manual_sources_render(key):
    html = make_manuals.render_html(key)
    assert html.count('class="chapter"') >= 8
    assert 'class="toc"' in html and 'class="cover"' in html
    # every picture the manual uses exists
    for src in re.findall(r'<img src="([^"]+)"', html):
        if src.startswith("file:"):
            from urllib.parse import unquote, urlparse
            path = Path(unquote(urlparse(src).path.lstrip("/")))
            assert path.is_file(), src
        else:
            pytest.fail(f"image not found when building the manual: {src}")
    # no Markdown that failed to convert (outside code samples)
    prose = re.sub(r"<pre>.*?</pre>|<code>.*?</code>", "", html, flags=re.S)
    assert "```" not in prose and "!!! " not in prose and "[[" not in prose


def test_chapter_numbers_match_the_cross_references():
    """The About page promises fixed chapter numbers; keep them true when chapters are added."""
    html = make_manuals.render_html("user")
    chapters = re.findall(r'<span class="chapter">Chapter (\d+)</span>(.*?)</h1>', html)
    titles = {int(n): t for n, t in chapters}
    assert titles[2] == "Installing the studio"
    assert titles[4] == "Your first scenario, step by step"
    assert titles[15] == "Events"
    assert titles[21] == "Checking your scenario"
    assert titles[22] == "Exporting and building in CMO"
    assert titles[24] == "Troubleshooting"


def test_pdfs_are_committed():
    for _src, _title, pdf, _blurb in make_manuals.MANUALS.values():
        p = ROOT / "docs" / "manuals" / pdf
        assert p.is_file() and p.read_bytes()[:5] == b"%PDF-", pdf


def test_help_menu_opens_the_manual(tmp_path, monkeypatch, sample):
    QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtCore import QSettings
    from PyQt6.QtGui import QDesktopServices

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841 - must stay alive
    monkeypatch.setattr(AppSettings, "data_dir", staticmethod(lambda: tmp_path))
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    w = MainWindow(s)
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toString())))
    w.open_manual("User")
    w.open_manual("Reference")
    assert opened[0].endswith("CMO-Scenario-Studio-User-Manual.pdf")
    assert opened[1].endswith("CMO-Scenario-Studio-Reference-Manual.pdf")
    names = [a.text() for a in w.menuBar().actions()[-1].menu().actions()]
    assert "User manual (PDF)" in names and "Reference manual (PDF)" in names
    w.doc.set_dirty(False)
    w.close()
