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
    w.tabs.setCurrentWidget(w.timeline_page)
    pump(app, 0.3)
    w.timeline_page._fit()
    rel_row = next(r for r in w.timeline_page.canvas.rows if r.name == "Release the strike")
    w.timeline_page.canvas.selected_id = rel_row.obj_id
    w.timeline_page._show_row(rel_row)
    pump(app, 0.3)
    w.grab().save(str(OUT / "timeline.png"))
    from cmo_studio.ui.search import SearchDialog
    sd = SearchDialog(w.doc.project, w.search_commands(), lambda h: None, w)
    sd.edit.setText("hogland")
    sd.show()
    pump(app, 0.3)
    sd.grab().save(str(OUT / "search.png"))
    sd.reject()
    from cmo_studio.ui.bulk_edit import BulkEditDialog
    ids = [u.id for u in w.doc.project.units if u.type == "Ship" and w.doc.project.side_name(u.side) == "Russia"]
    bd = BulkEditDialog(w.ctx, ids, w)
    marks = {cb.text(): cb for cb, _ in bd.fields}
    marks["Rename"].setChecked(True)
    bd.rename.setText("BF {nn} {name}")
    marks["Proficiency"].setChecked(True)
    bd.prof.setCurrentIndex(bd.prof.findData("Veteran"))
    marks["Radar active"].setChecked(True)
    marks["Group tag"].setChecked(True)
    bd.group.setText("Baltic Fleet")
    bd.show()
    pump(app, 0.3)
    bd.grab().save(str(OUT / "bulk_edit.png"))
    bd.reject()
    from cmo_studio.ui.callsigns_ui import CallsignAssignDialog, CallsignLibraryDialog
    ad = CallsignAssignDialog(w.ctx, [u.id for u in w.doc.project.units if u.type == "Aircraft"], w)
    ad.show()
    pump(app, 0.3)
    ad.grab().save(str(OUT / "callsigns_assign.png"))
    ad.reject()
    ld = CallsignLibraryDialog(w.ctx, w)
    ld.country_name = "United Kingdom"
    ld._fill_countries()
    ld.show()
    pump(app, 0.3)
    ld.grab().save(str(OUT / "callsigns_library.png"))
    ld.dirty = False
    ld.close()
    from cmo_studio.ui.templates_ui import TemplateLibraryDialog, TemplatePlacerDialog
    pd = TemplatePlacerDialog(w.ctx, 59.411, 24.832, w)
    pd.filter.setText("tactical fighter base")
    pd.site.setText("Tallinn")
    pd.heading.setValue(84)
    pd.show()
    pump(app, 0.3)
    pd.grab().save(str(OUT / "templates_place.png"))
    pd._place()
    w.tabs.setCurrentWidget(w.map_page)
    w.map_page.map.center_on(59.411, 24.845, 13)
    pump(app, 6)
    w.grab().save(str(OUT / "templates_map.png"))
    w.doc.undo()
    ld2 = TemplateLibraryDialog(w.ctx, w)
    ld2.tid = "nav_major_base"
    ld2._fill()
    ld2.show()
    pump(app, 0.3)
    ld2.grab().save(str(OUT / "templates_library.png"))
    ld2.dirty = False
    ld2.close()
    w.tabs.setCurrentWidget(w.formations_page)
    w.formations_page.select_formation(w.doc.project.formations[0].id)
    pump(app, 0.4)
    w.grab().save(str(OUT / "formations.png"))
    from cmo_studio.db.database import DBEntry
    from cmo_studio.ui.pages.formations_page import FormationCreator
    w.db_browser.current = DBEntry("Ship", 2814, "MPK Steregushchiy [Pr.20380]")
    dlg = FormationCreator(w.ctx, w)
    dlg.rows.cellWidget(0, 3).setValue(7)
    dlg.preset.set_key("double_screen")
    dlg._preset_changed()
    dlg.show()
    pump(app, 0.4)
    dlg.grab().save(str(OUT / "formation_creator.png"))
    dlg.reject()
    w.open_loadout_viewer(6645, 30249)          # Su-35S, R-77-1 / R-73M loadout
    v = w._loadout_viewer
    v.resize(1680, 900)
    v.ac_search.setText("Su-35S")
    v._search_aircraft()
    v.navigate(v.place)
    v.wp_table.selectRow(1)
    pump(app, 0.4)
    v.grab().save(str(OUT / "loadout_viewer.png"))
    v.close()
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
