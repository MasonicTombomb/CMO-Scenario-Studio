"""Render the annotated screenshots for the PDF manuals into docs/manual/img/ (maintainer tool).

    python tools/make_manual_shots.py

Each shot grabs one window, panel or dialog of the studio running the Baltic Sentinel example (off screen, at 1.5x
scale so the text stays sharp in print) and draws numbered call-outs on the controls the manual explains. Call-outs
find widgets by their visible text, so they follow the UI as it changes; a call-out that cannot be found is
reported and skipped.
"""

from __future__ import annotations

import copy
import os
import sys
import time
from pathlib import Path
from typing import Callable, Optional, Union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["QT_SCALE_FACTOR"] = "1.5"
os.environ["CMO_STUDIO_NO_UPDATE_CHECK"] = "1"

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSettings, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap  # noqa: E402
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QGroupBox, QLabel, QLineEdit,  # noqa: E402
                             QTabBar, QTableWidget, QTabWidget, QToolBar, QWidget)

from cmo_studio.settings import AppSettings, detect_cmo_dir  # noqa: E402
from cmo_studio.ui.main_window import MainWindow  # noqa: E402
from cmo_studio.ui.theme import apply_dark_theme  # noqa: E402

OUT = ROOT / "docs" / "manual" / "img"
ACCENT = QColor("#ff6a1a")
missing: list[str] = []
Target = Union[QWidget, QRect, str, tuple]


def pump(app, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def _text(w: QWidget) -> str:
    for attr in ("text", "title", "placeholderText", "windowTitle"):
        f = getattr(w, attr, None)
        if callable(f):
            try:
                t = f()
            except TypeError:
                continue
            if isinstance(t, str) and t:
                return t.replace("&", "")
    return ""


def find(root: QWidget, text: str,
         kinds=(QAbstractButton, QLabel, QGroupBox, QLineEdit, QComboBox)) -> Optional[QWidget]:
    """First visible widget whose text/title/placeholder equals (or starts with) ``text``."""
    best = None
    for w in root.findChildren(QWidget):
        if not isinstance(w, kinds) or not w.isVisible():
            continue
        t = _text(w)
        if isinstance(w, QLineEdit) and not t:
            t = w.placeholderText()
        if t == text:
            return w
        if best is None and t.startswith(text):
            best = w
    return best


def tab_rect(root: QWidget, text: str) -> Optional[QRect]:
    for bar in root.findChildren(QTabBar):
        if not bar.isVisible():
            continue
        for i in range(bar.count()):
            if bar.tabText(i).replace("&", "") == text:
                r = bar.tabRect(i)
                return QRect(bar.mapTo(root, r.topLeft()), r.size())
    return None


def action_rect(root: QWidget, text: str) -> Optional[QRect]:
    for tb in root.findChildren(QToolBar):
        for a in tb.actions():
            if a.text().replace("&", "") == text:
                w = tb.widgetForAction(a)
                if w is not None and w.isVisible():
                    return QRect(w.mapTo(root, QPoint(0, 0)), w.size())
    return None


def rect_of(root: QWidget, t: Target) -> Optional[QRect]:
    if isinstance(t, QRect):
        return t
    if isinstance(t, QWidget):
        return QRect(t.mapTo(root, QPoint(0, 0)), t.size()) if t.isVisible() else None
    if isinstance(t, tuple):           # ('tab', text) / ('action', text) / ('row', label text): label + field
        kind, text = t
        if kind == "tab":
            return tab_rect(root, text)
        if kind == "action":
            return action_rect(root, text)
        if kind == "row":
            lab = find(root, text, (QLabel,))
            if lab is None:
                return None
            r = QRect(lab.mapTo(root, QPoint(0, 0)), lab.size())
            buddy = lab.buddy()
            if buddy is None and lab.parentWidget() is not None and lab.parentWidget().layout() is not None:
                from PyQt6.QtWidgets import QFormLayout
                lay = lab.parentWidget().layout()
                if isinstance(lay, QFormLayout):
                    for i in range(lay.rowCount()):
                        li = lay.itemAt(i, QFormLayout.ItemRole.LabelRole)
                        if li is not None and li.widget() is lab:
                            fi = lay.itemAt(i, QFormLayout.ItemRole.FieldRole)
                            if fi is not None:
                                fw = fi.widget() or (fi.layout() and fi.layout().geometry())
                                if isinstance(fw, QWidget):
                                    r = r.united(QRect(fw.mapTo(root, QPoint(0, 0)), fw.size()))
                                elif isinstance(fw, QRect):
                                    r = r.united(QRect(lab.parentWidget().mapTo(root, fw.topLeft()), fw.size()))
            return r
    if isinstance(t, str):
        w = find(root, t)
        if w is not None:
            return QRect(w.mapTo(root, QPoint(0, 0)), w.size())
        r = tab_rect(root, t) or action_rect(root, t)
        return r
    return None


def shot(name: str, root: QWidget, callouts: list[tuple[int, Target]] = (), crop: Optional[QRect] = None,
         box: bool = True) -> None:
    """Grab ``root`` and draw numbered markers; saves docs/manual/img/<name>.png."""
    QApplication.processEvents()
    pm: QPixmap = root.grab(crop) if crop is not None else root.grab()
    origin = crop.topLeft() if crop is not None else QPoint(0, 0)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    f = QFont("Segoe UI", 8)
    f.setBold(True)
    p.setFont(f)
    placed: list[QRectF] = []
    for n, target in callouts:
        r = rect_of(root, target)
        if r is None or r.isEmpty():
            missing.append(f"{name}: #{n} {target!r}")
            continue
        r = r.translated(-origin)
        if box:
            p.setPen(QPen(ACCENT, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(r).adjusted(-1.5, -1.5, 1.5, 1.5), 3, 3)
        d = 17.0
        c = QPointF(r.left() - 2, r.top() - 2)
        c.setX(max(d / 2 + 1, min(pm.width() / pm.devicePixelRatio() - d / 2 - 1, c.x())))
        c.setY(max(d / 2 + 1, min(pm.height() / pm.devicePixelRatio() - d / 2 - 1, c.y())))
        disc = QRectF(c.x() - d / 2, c.y() - d / 2, d, d)
        for _ in range(6):           # nudge right if two markers would overlap
            if any(disc.intersects(o) for o in placed):
                disc.translate(d + 2, 0)
        placed.append(disc)
        p.setPen(QPen(QColor("#ffffff"), 1.4))
        p.setBrush(ACCENT)
        p.drawEllipse(disc)
        p.setPen(QColor("#ffffff"))
        p.drawText(disc, Qt.AlignmentFlag.AlignCenter, str(n))
    p.end()
    OUT.mkdir(parents=True, exist_ok=True)
    pm.save(str(OUT / f"{name}.png"))
    print("shot", name)


def dialog_shot(app, name: str, dlg: QWidget, callouts=(), prepare: Optional[Callable] = None, wait=0.3):
    dlg.show()
    if prepare:
        prepare()
    pump(app, wait)
    shot(name, dlg, list(callouts))
    try:
        dlg.dirty = False
    except Exception:  # noqa: BLE001
        pass
    dlg.close()


def main():
    app = QApplication([])
    apply_dark_theme(app)
    s = AppSettings()
    tmp_ini = OUT.parent / "_shots.ini"
    s.q = QSettings(str(tmp_ini), QSettings.Format.IniFormat)
    s.q.setValue("cmo_dir", str(detect_cmo_dir() or ""))
    s.tile_source = "Esri Dark Gray"
    w = MainWindow(s)
    w.resize(1400, 860)
    w.show()
    w.open_project(str(ROOT / "examples" / "Baltic Sentinel.cmoproj"))
    p = w.doc.project
    w.tabs.setCurrentWidget(w.map_page)
    pump(app, 0.5)
    w.map_page.map.center_on(59.4, 25.0, 7)
    ship = next(u for u in p.units if u.type == "Ship" and p.side_name(u.side) == "Russia")
    w.doc.select(ship.id)
    w.db_browser.set_type("Ship")
    w.db_browser.search.setText("Steregushchiy")
    w.db_browser._search_now()
    w.db_browser.table.selectRow(0)
    pump(app, 8)

    # 1. The whole window
    shot("window_overview", w, [
        (1, w.menuBar()), (2, w.tabs.tabBar()), (3, w.map_page.findChild(QToolBar)), (4, w.map_page.map),
        (5, w.map_page.unit_form), (6, w.db_dock), (7, w.issues_dock), (8, w.statusBar())])

    # 2. Map toolbar
    tb = w.map_page.findChild(QToolBar)
    shot("map_toolbar", w.map_page, [
        (1, ("action", "Select / move")), (2, ("action", "Place unit")), (3, ("action", "Reference point")),
        (4, ("action", "Draw area")), (5, ("action", "Measure")), (6, ("action", "Course...")),
        (7, w.map_page.side_combo), (8, ("action", "Templates...")), (9, ("action", "Patrol areas...")),
        (10, ("action", "Fit all")), (11, "Show ▾")], crop=QRect(QPoint(0, 0), QPoint(w.map_page.width(),
                                                                                   tb.height() + 4)))
    # 3. Map + inspector for a ship
    shot("map_unit_inspector", w.map_page, [
        (1, ("row", "Name:")), (2, ("row", "Side:")), (3, ("row", "Database:")), (4, ("row", "Count:")),
        (5, ("row", "Lat, lon:")), (6, ("row", "Heading:")), (7, ("row", "Speed:")), (8, "Radar active"),
        (9, "Hold position"), (10, ("row", "Proficiency:"))],
        crop=QRect(w.map_page.unit_form.mapTo(w.map_page, QPoint(0, 0)), w.map_page.unit_form.size()))
    # 4. An airbase with its squadrons
    amari = next(u for u in p.units if u.name == "Amari AB")
    w.doc.select(amari.id)
    w.db_browser.set_type("Aircraft")
    w.db_browser.search.setText("Eurofighter Typhoon")
    w.db_browser._search_now()
    w.db_browser.table.selectRow(0)
    pump(app, 0.5)
    shot("map_airbase_inspector", w.map_page, [(1, ("row", "Name:")), (2, "Hosted units")],
         crop=QRect(w.map_page.unit_form.mapTo(w.map_page, QPoint(0, 0)), w.map_page.unit_form.size()))
    # 4b. The course window: a Typhoon pair from Amari flying a strike route (in memory only, removed again)
    from cmo_studio.model.project import Course, Waypoint
    from cmo_studio.ui.course_dialog import CourseDialog
    jet = next(u for u in p.units if u.type == "Aircraft" and u.host == amari.id)
    jet.course = Course([
        Waypoint(59.05, 25.95, 9000, 450, name="Climb", radar="active", weapons="tight"),
        Waypoint(59.75, 26.9, 9000, 480, name="Tanker", wait_minutes=15, signal="TANKER_DONE"),
        Waypoint(59.65, 28.1, 150, 540, name="IP", radar="passive", ecm="active", weapons="free", engage="leave",
                 signal="STRIKE_AT_IP", arrive_minutes=75),
        Waypoint(59.35, 27.3, 6000, 480, name="Egress", radar="active", weapons="tight")], 20, "rtb")
    dlg = CourseDialog(w, jet.id)
    dlg.resize(1360, 900)
    dlg.show()
    pump(app, 0.5)
    dlg.fit()
    dlg.time_it()              # departure worked out from the time on target at the IP
    dlg.select(2)
    pump(app, 6)
    shot("dialog_course", dlg, [(1, dlg.map), (2, "Add waypoints"), (3, dlg.table), (4, dlg.leg_box),
                                (5, ("row", "Weapons:")), (6, ("row", "Wait there:")), (7, dlg.chart),
                                (8, dlg.depart), (9, dlg.finish), (10, dlg.summary), (11, dlg.range_label),
                                (12, ("row", "Arrive at:")), (13, dlg.time_btn), (14, "Library ▾")])
    timed = copy.deepcopy(dlg.course)
    dlg._orig = dlg.course     # not dirty: close without asking
    dlg.reject()
    form = w.map_page.unit_form
    w.doc.select(jet.id)
    pump(app, 0.3)
    cb = form.course_box
    shot("unit_course", cb, [(1, form.course_info), (2, "Edit course..."), (3, "Clear")])
    # 4c. The map clock part way through that sortie
    jet.course = timed
    mp = w.map_page
    mp._clock_reset()
    mp.map.fit([(amari.lat, amari.lon)] + [(x.lat, x.lon) for x in timed.waypoints])
    mp.clock.setValue(timed.depart_minutes + 40)
    pump(app, 4)
    shot("map_clock", mp, [(1, mp.clock), (2, mp.clock_label), (3, "Start"), (4, mp.clock_info),
                           (5, mp.map)])
    mp.clock.setValue(0)
    jet.course = None
    mp._clock_reset()
    form.refresh()
    w.doc.select(ship.id)
    pump(app, 0.2)
    # 4d. Several units selected together: the Russian ships
    ru_ships = [u for u in p.units if u.type == "Ship" and p.side_name(u.side) == "Russia"]
    mp.map.fit([(u.lat, u.lon) for u in ru_ships])
    mp.map.set_multi([u.id for u in ru_ships])
    pump(app, 4)
    shot("map_multi", mp.map, [])
    mp.map.set_multi([])

    # 5. Database dock
    shot("database_dock", w.db_browser, [
        (1, w.db_browser.findChild(QComboBox)), (2, ("row", "Type:")), (3, w.db_browser.search),
        (4, "In service in scenario year"), (5, "Show deprecated"), (6, w.db_browser.table), (7, "Place on map"),
        (8, "Add to selected base"), (9, "Use for selected unit"), (10, "Loadout viewer"), (11, ("tab", "Sensors"))])
    w.doc.select(ship.id)
    pump(app, 0.2)

    # 6. Pages
    def page(pg, name, callouts, prepare=None, wait=0.4):
        w.tabs.setCurrentWidget(pg)
        if prepare:
            prepare()
        pump(app, wait)
        shot(name, pg, callouts)

    page(w.scenario_page, "tab_scenario", [
        (1, ("row", "Title:")), (2, ("row", "Setting:")), (3, ("row", "Author:")), (4, "Files and database"),
        (5, "Time (Zulu)"), (6, "Weather"), (7, "Build options"),
        (8, "Initial key values (ScenEdit_SetKeyValue)"), (9, "Designer notes (never exported)")])
    page(w.sides_page, "tab_sides", [
        (1, w.sides_page.findChild(type(w.sides_page.list)) if hasattr(w.sides_page, "list") else "Side"),
        (2, ("row", "Name:")), (3, ("row", "Awareness:")), (4, ("row", "Proficiency:")),
        (5, "Computer-controlled only (never playable)"), (6, "Side doctrine (blank = CMO default)"),
        (7, "Postures (row side's view of the column side)"), (8, "Build variants (single-player versions)")])
    page(w.units_page, "tab_units", [
        (1, "Filter by name, class, group..."), (2, w.units_page.table if hasattr(w.units_page, "table") else
                                                  "Edit selected..."),
        (3, "Edit selected..."), (4, "Callsigns..."), (5, "Assign to mission..."), (6, "Make formation"),
        (7, "Toggle reinforcement"), (8, "Delete selected")],
        prepare=lambda: w.units_page.table.selectRow(2) if hasattr(w.units_page, "table") else None)

    def sel_area():
        if p.zones:
            w.doc.select(p.zones[0].id)
    page(w.areas_page, "tab_areas", [
        (1, ("tab", "Areas")), (2, ("tab", "Reference points")), (3, "New area (box)"), (4, "New reference point"),
        (5, "From library..."), (6, ("row", "Name:")), (7, "Create on every side"),
        (8, "Corners (drag the white squares on the map to move them):"), (9, "Save to area library..."),
        (10, "Delete area")], prepare=sel_area)
    page(w.missions_page, "tab_missions", [
        (1, ("row", "Name:")), (2, ("row", "Class:")), (3, ("row", "Type:")), (4, ("row", "Area:")),
        (5, "Options"), (6, "Assigned units")],
        prepare=lambda: w.missions_page.list.setCurrentRow(1))

    def sel_event():
        w.events_page.list.setCurrentRow(4)
        pump(app, 0.2)
        try:
            w.events_page.lists["actions"].list.setCurrentRow(0)
        except Exception:  # noqa: BLE001
            pass
    page(w.events_page, "tab_events", [
        (1, w.events_page.list), (2, "New ▾"), (3, ("row", "Name:")), (4, "Repeatable"), (5, "Active"),
        (6, ("row", "Probability:")), (7, w.events_page.lists["triggers"]), (8, w.events_page.lists["conditions"]),
        (9, w.events_page.lists["actions"]), (10, ("tab", "Generated Lua"))], prepare=sel_event)
    page(w.specials_page, "tab_special_actions", [(1, ("row", "Name:")), (2, ("row", "Side:")),
                                                  (3, ("row", "Description:")), (4, "Repeatable"), (5, "Check syntax")],
         prepare=lambda: w.specials_page.list.setCurrentRow(0) if hasattr(w.specials_page, "list") else None)
    page(w.scripts_page, "tab_scripts", [(1, w.scripts_page.list), (2, "Load on init (run from LuaInit.lua)"),
                                         (3, "Insert snippet ▾"), (4, "Check syntax")],
         prepare=lambda: w.scripts_page.list.setCurrentRow(0) if hasattr(w.scripts_page, "list") else None)
    page(w.briefings_page, "tab_briefings", [
        (1, "Prepend automatic header (author, date, location, sides, duration, ratings)"), (2, "Insert ▾"),
        (3, "Briefing pack (PDF)...")], prepare=lambda: None)
    page(w.export_page, "tab_export", [
        (1, "1. Check"), (2, "Validate"), (3, "Dry-run build"), (4, "2. Export"), (5, "Install into the CMO folder"),
        (6, "Export to a folder (e.g. a git repository)"), (7, "Export as a .zip"),
        (8, "Back up files that will be replaced (zip in the studio's data folder)"), (9, "Export"),
        (10, "3. In CMO"), (11, "Copy the console command")])
    w.export_page._dry()
    pump(app, 4)
    shot("tab_export_dryrun", w.export_page, [])

    def sel_form():
        if p.formations:
            w.formations_page.select_formation(p.formations[0].id)
    page(w.formations_page, "tab_formations", [
        (1, "Create units in formation..."), (2, ("row", "Layout:")), (3, ("row", "Spacing:")),
        (4, ("row", "Orientation (heading):")), (5, "Layout settings"), (6, "Members (station order)"),
        (7, "Keep members on station (move with the lead, follow setting changes)"),
        (8, "Build as a CMO group")], prepare=sel_form)
    w.tabs.setCurrentWidget(w.timeline_page)
    pump(app, 0.3)
    w.timeline_page._fit()
    pump(app, 0.3)
    shot("tab_timeline", w.timeline_page, [(1, "Filter events, missions and courses..."), (2, "Missions"), (4, "Weather"),
                                           (3, "Courses"), (5, "Condition-only events"), (6, "Sort by time")])

    # 7. Dialogs
    from cmo_studio.ui.briefing_pack_dialog import BriefingPackDialog
    from cmo_studio.ui.recipe_dialog import RecipeDialog
    from cmo_studio.ui.scenario_wizard import ScenarioWizard
    nato = next(s for s in p.sides if s.name == "NATO")
    zone = next((z for z in p.zones if z.side == nato.id), None)
    rd = RecipeDialog(w.ctx, "area_entered", w)

    def prep_recipe():
        if zone is not None:
            rd.set_value("zone", zone.id)
    dialog_shot(app, "dialog_recipe", rd, [(1, rd.list), (2, rd.desc), (3, rd.box), (4, "Create event")],
                prepare=prep_recipe)
    bp = BriefingPackDialog(w.ctx, nato.id, w)
    dialog_shot(app, "dialog_briefing_pack", bp, [(1, bp.side), (2, ("row", "Operation:")), (3, bp.fields["mission"]),
                                                  (4, bp.preview), (5, "Save PDF..."), (6, "Use as CMO briefing")],
                wait=1.0)
    wiz = ScenarioWizard([d.name for d in w.dbm.available()], w.dbm.db.path.name if w.dbm.db else "", w.dbm.db, w)

    def prep_wiz():
        wiz.next()
        wiz.next()
    dialog_shot(app, "dialog_wizard", wiz, [(1, wiz.region), (2, wiz.squadron), (3, wiz.bases), (4, wiz.areas),
                                            (5, wiz.probe), (6, wiz.events)], prepare=prep_wiz)
    from cmo_studio.ui.dialogs import NewProjectDialog, SettingsDialog
    dialog_shot(app, "dialog_settings", SettingsDialog(w.settings, w), [
        (1, ("row", "CMO folder:")), (2, "Browse..."), (3, "Detect"), (4, ("row", "Autosave (to a .autosave copy):")),
        (5, ("row", "Custom map tiles:")), (6, "Check GitHub for a new version when the studio starts")])
    dialog_shot(app, "dialog_new_project", NewProjectDialog([d.name for d in w.dbm.available()],
                                                            w.dbm.db.path.name if w.dbm.db else "", w),
                [(1, ("row", "Title:")), (2, ("row", "Database:"))])

    from cmo_studio.ui.pages.formations_page import FormationCreator
    fc = FormationCreator(w.ctx, w)
    dialog_shot(app, "dialog_formation_creator", fc, [
        (1, "Composition (the first unit of the first row is the lead)"), (2, ("row", "Layout:")),
        (3, ("row", "Spacing:")), (4, ("row", "Orientation:"))])

    from cmo_studio.ui.search import SearchDialog
    sd = SearchDialog(p, w.search_commands(), lambda h: None, w)
    dialog_shot(app, "dialog_search", sd, [(1, sd.edit)], prepare=lambda: sd.edit.setText("hogland"))

    from cmo_studio.ui.bulk_edit import BulkEditDialog
    ids = [u.id for u in p.units if u.type == "Ship" and p.side_name(u.side) == "Russia"]
    bd = BulkEditDialog(w.ctx, ids, w)

    def prep_bulk():
        marks = {cb.text(): cb for cb, _ in bd.fields}
        marks["Rename"].setChecked(True)
        bd.rename.setText("BF {nn} {name}")
        marks["Proficiency"].setChecked(True)
        bd.prof.setCurrentIndex(bd.prof.findData("Veteran"))
    dialog_shot(app, "dialog_bulk_edit", bd, [(1, "Rename"), (2, "Proficiency")], prepare=prep_bulk)

    from cmo_studio.ui.templates_ui import TemplateLibraryDialog, TemplatePlacerDialog
    tp = TemplatePlacerDialog(w.ctx, 59.411, 24.832, w)

    def prep_tp():   # three UK bases ticked, Lossiemouth highlighted
        from PyQt6.QtCore import Qt as _Qt
        tp.filter.setText("raf")
        lossie = None
        for i in range(tp.tree.topLevelItemCount()):
            head = tp.tree.topLevelItem(i)
            for k in range(head.childCount()):
                it = head.child(k)
                tid = it.data(0, _Qt.ItemDataRole.UserRole)
                if tid in ("uk_ab_fairford", "uk_ab_benson", "uk_ab_lossiemouth"):
                    it.setCheckState(0, _Qt.CheckState.Checked)
                if tid == "uk_ab_lossiemouth":
                    lossie = it
        tp.tree.setCurrentItem(lossie)
        tp.tree.scrollToItem(lossie)
    dialog_shot(app, "dialog_template_placer", tp, [
        (1, tp.filter), (2, tp.tree), (3, tp.parts), (4, ("row", "Site name:")), (5, ("row", "Side:")),
        (6, tp.real), (7, ("row", "Orientation / runway heading:")),
        (8, "Group the site in CMO and keep it together on the map"), (9, tp.preview), (10, tp.place_btn),
        (11, tp.ticked_label)],
        prepare=prep_tp)
    tl = TemplateLibraryDialog(w.ctx, w)
    dialog_shot(app, "dialog_template_library", tl, [(1, "Import..."), (2, "Export..."), (3, "Reset to defaults"),
                                                     (4, "Add component"), (5, "Save")])

    from cmo_studio.ui.areas_library_ui import AreaBrowserDialog
    ab = AreaBrowserDialog(w.ctx, w)

    def prep_ab():
        ab.region.setCurrentIndex(ab.region.findData("United Kingdom"))
        ab.select_area("uk_qra_north")
    dialog_shot(app, "dialog_area_library", ab, [
        (1, ab.filter), (2, ab.region), (3, ab.kind), (4, ab.tree), (5, ab.preview), (6, ("row", "Side:")),
        (7, ("row", "Area name:")), (8, ab.make_mission), (9, "Add to scenario")], prepare=prep_ab, wait=8)

    from cmo_studio.ui.callsigns_ui import CallsignAssignDialog, CallsignLibraryDialog
    ad = CallsignAssignDialog(w.ctx, [u.id for u in p.units if u.type == "Aircraft"], w)
    dialog_shot(app, "dialog_callsigns", ad, [(1, "Split counted units into single aircraft"),
                                              (2, "Edit callsign library..."), (3, "Apply")])
    cl = CallsignLibraryDialog(w.ctx, w)
    dialog_shot(app, "dialog_callsign_library", cl, [(1, "Import..."), (2, "Save")])

    typhoon = next((u for u in p.units if u.type == "Aircraft"), None)
    w.open_loadout_viewer(typhoon.dbid if typhoon else 0, typhoon.loadout if typhoon else 0)
    lv = w._loadout_viewer
    pump(app, 0.6)
    shot("dialog_loadout_viewer", lv, [(1, lv.ac_list), (2, lv.carried_by)])
    lv.close()

    from cmo_studio.updater import release_from_json
    from cmo_studio.ui.update_ui import UpdateDialog
    rel = release_from_json({"tag_name": "v1.7.0", "name": "CMO Scenario Studio 1.7.0",
                             "body": "## New\n- Example release notes shown before you update.\n- Your settings "
                                     "and libraries are kept.",
                             "html_url": "https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases",
                             "assets": [{"name": "CMO-Scenario-Studio-1.7.0-setup.exe",
                                         "browser_download_url": "https://github.com/x/y/releases/download/v1.7.0/"
                                                                 "CMO-Scenario-Studio-1.7.0-setup.exe"},
                                        {"name": "CMO-Scenario-Studio-1.7.0-setup.exe.sha256",
                                         "browser_download_url": "https://github.com/x/y/releases/download/v1.7.0/"
                                                                 "CMO-Scenario-Studio-1.7.0-setup.exe.sha256"}]})
    dialog_shot(app, "dialog_update", UpdateDialog(rel, "installed", w), [
        (1, "Download and install"), (2, "Skip this version"), (3, "Later")])

    # 8. Map drawing: an area and markers in close-up
    w.tabs.setCurrentWidget(w.map_page)
    if p.zones:
        w.doc.select(p.zones[0].id)
        z = p.zones[0]
        w.map_page.map.fit([(a, b) for a, b in z.points])
    pump(app, 6)
    shot("map_area_selected", w.map_page.map, [])
    w.doc.set_dirty(False)
    w.close()
    tmp_ini.unlink(missing_ok=True)
    if missing:
        print("\nCALL-OUTS NOT FOUND:\n  " + "\n  ".join(missing))


if __name__ == "__main__":
    main()
