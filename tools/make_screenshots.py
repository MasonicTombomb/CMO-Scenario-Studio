"""Render docs/images/*.png from the example project (maintainer tool).

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR=C:\\Windows\\Fonts python tools/make_screenshots.py
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from cmo_studio.model import Project  # noqa: E402
from cmo_studio.settings import AppSettings, detect_cmo_dir  # noqa: E402
from cmo_studio.ui.main_window import MainWindow  # noqa: E402
from cmo_studio.ui.theme import apply_dark_theme  # noqa: E402

OUT = ROOT / "docs" / "images"


def pump(app, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    apply_dark_theme(app)
    s = AppSettings()
    s.q = QSettings(str(OUT / "_shots.ini"), QSettings.Format.IniFormat)
    s.q.setValue("cmo_dir", str(detect_cmo_dir() or ""))
    s.tile_source = "Esri Dark Gray"
    w = MainWindow(s)
    w.resize(1680, 980)
    w.show()
    w.open_project(str(ROOT / "examples" / "Baltic Sentinel.cmoproj"))
    w.tabs.setCurrentWidget(w.map_page)
    pump(app, 0.5)
    w.map_page.map.center_on(60.0, 26.3, 7)
    amari = next(u for u in w.doc.project.units if u.name == "Amari AB")
    w.doc.select(amari.id)
    w.db_browser.set_type("Ship")
    w.db_browser.search.setText("Steregushchiy")
    w.db_browser._search_now()
    w.db_browser.table.selectRow(0)
    pump(app, 8)   # let tiles arrive
    w.grab().save(str(OUT / "map.png"))
    for page, name in ((w.units_page, "units"), (w.events_page, "events"), (w.missions_page, "missions"),
                       (w.briefings_page, "briefings"), (w.sides_page, "sides")):
        w.tabs.setCurrentWidget(page)
        if page is w.events_page:
            page.list.setCurrentRow(4)
            pump(app, 0.2)
            page.lists["actions"].list.setCurrentRow(0)
        if page is w.missions_page:
            page.list.setCurrentRow(1)
        pump(app, 0.4)
        w.grab().save(str(OUT / f"{name}.png"))
    w.tabs.setCurrentWidget(w.export_page)
    pump(app, 0.3)
    w.export_page._dry()
    pump(app, 0.3)
    w.grab().save(str(OUT / "export.png"))
    w.doc.set_dirty(False)
    w.close()
    (OUT / "_shots.ini").unlink(missing_ok=True)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
