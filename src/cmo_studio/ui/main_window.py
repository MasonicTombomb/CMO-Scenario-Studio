"""Main window: menus, tabs, docks, file handling, autosave."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QCloseEvent, QDesktopServices, QGuiApplication, QKeySequence
from PyQt6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QMainWindow, QMessageBox, QTabWidget)

from .. import APP_NAME, GITHUB_REPO, __version__
from ..updater import RELEASES_PAGE
from ..db.database import DBEntry, latest_database
from ..importers.legacy_lua import import_legacy_build
from ..model.project import PROJECT_SUFFIX, Project, Unit, new_project
from ..paths import docs_dir, examples_dir, is_frozen
from ..settings import AppSettings
from .db_browser import DBBrowser, DBManager
from .dialogs import AboutDialog, IssuesPanel, NewProjectDialog, SettingsDialog
from .document import ProjectDocument
from .pages.areas_page import AreasPage
from .pages.base import AppContext
from .pages.briefings_page import BriefingsPage
from .pages.events_page import EventsPage
from .pages.export_page import ExportPage
from .pages.formations_page import FormationsPage
from .pages.map_page import MapPage
from .pages.missions_page import MissionsPage
from .pages.scenario_page import ScenarioPage
from .pages.scripts_page import ScriptsPage, SpecialActionsPage
from .pages.sides_page import SidesPage
from .pages.timeline_page import TimelinePage
from .pages.units_page import UnitsPage

FILE_FILTER = f"CMO Scenario Studio project (*{PROJECT_SUFFIX});;All files (*)"
REPO_URL = f"https://github.com/{GITHUB_REPO}"


class MainWindow(QMainWindow):
    def __init__(self, settings: Optional[AppSettings] = None):
        super().__init__()
        self.settings = settings or AppSettings()
        self.doc = ProjectDocument(parent=self)
        self.dbm = DBManager(self)
        self.dbm.cmo_dir = self.settings.cmo_dir
        self.ctx = AppContext(self.doc, self.dbm, self.settings, self)
        self.resize(1500, 920)

        # ------------------------------------------------ pages
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.scenario_page = ScenarioPage(self.ctx)
        self.sides_page = SidesPage(self.ctx)
        self.map_page = MapPage(self.ctx)
        self.units_page = UnitsPage(self.ctx)
        self.formations_page = FormationsPage(self.ctx)
        self.areas_page = AreasPage(self.ctx)
        self.missions_page = MissionsPage(self.ctx)
        self.events_page = EventsPage(self.ctx)
        self.timeline_page = TimelinePage(self.ctx)
        self.specials_page = SpecialActionsPage(self.ctx)
        self.scripts_page = ScriptsPage(self.ctx)
        self.briefings_page = BriefingsPage(self.ctx)
        self.export_page = ExportPage(self.ctx)
        for page in (self.scenario_page, self.sides_page, self.map_page, self.units_page, self.formations_page,
                     self.areas_page,
                     self.missions_page, self.events_page, self.timeline_page, self.specials_page, self.scripts_page,
                     self.briefings_page, self.export_page):
            self.tabs.addTab(page, page.title)
        self.setCentralWidget(self.tabs)

        # ------------------------------------------------ docks
        self.db_browser = DBBrowser(self.dbm, lambda: self.doc.project.scenario_year())
        self.db_dock = QDockWidget("Database", self)
        self.db_dock.setObjectName("db_dock")
        self.db_dock.setWidget(self.db_browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.db_dock)
        self.issues = IssuesPanel(self.ctx)
        self.issues_dock = QDockWidget("Issues", self)
        self.issues_dock.setObjectName("issues_dock")
        self.issues_dock.setWidget(self.issues)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.issues_dock)
        self.resizeDocks([self.db_dock], [470], Qt.Orientation.Horizontal)
        self.resizeDocks([self.issues_dock], [150], Qt.Orientation.Vertical)

        self.db_browser.placeRequested.connect(self._place_from_db)
        self.db_browser.applyRequested.connect(self._apply_db)
        self.db_browser.loadoutRequested.connect(self._loadout_from_db)
        self.db_browser.addToBaseRequested.connect(self._add_to_base)
        self.db_browser.loadoutViewRequested.connect(self.open_loadout_viewer)
        self._loadout_viewer = None
        self.issues.jumpTo.connect(self._jump)
        for form in (self.map_page.unit_form, self.units_page.form):
            form.showInBrowser.connect(self._show_in_browser)
            form.centerRequested.connect(self.show_on_map)
            form.loadoutViewRequested.connect(self.open_loadout_viewer)

        # ------------------------------------------------ status bar
        self.cursor_label = QLabel("")
        self.statusBar().addPermanentWidget(self.cursor_label)
        self.db_label = QLabel("")
        self.statusBar().addPermanentWidget(self.db_label)

        self._build_menus()
        self.doc.dirtyChanged.connect(lambda *_: self._title())
        self.doc.pathChanged.connect(lambda *_: self._title())
        self.doc.changed.connect(lambda *_: self._update_undo())
        self.doc.reset.connect(self._update_undo)
        self.dbm.changed.connect(self._db_changed)

        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self._autosave)
        self._restart_autosave()

        # open a database
        db = self.settings.db_file
        cmo = self.settings.cmo_dir
        if cmo:
            path = Path(cmo) / "DB" / db if db else latest_database(cmo)
            if path and Path(path).is_file():
                self.dbm.open(path)
            elif latest_database(cmo):
                self.dbm.open(latest_database(cmo))
        self.doc.load(new_project("New Scenario", self.dbm.db.path.name if self.dbm.db else ""))
        self._title()
        state = self.settings.value("window_state")
        if state is not None:
            self.restoreState(state)
        else:
            QTimer.singleShot(0, lambda: self.resizeDocks([self.db_dock], [440], Qt.Orientation.Horizontal))
        geo = self.settings.value("window_geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        self.tabs.setCurrentWidget(self.map_page)
        # Ask for the CMO folder on first run - but never on a headless (off-screen) display, where a modal box
        # would wait forever (this hung the GitHub Actions test runs).
        if not cmo and QGuiApplication.platformName() != "offscreen":
            QTimer.singleShot(300, self._first_run)
        from .update_ui import Updater
        self.updater = Updater(self)
        self._quitting_for_update = False
        # Look for a new release a few seconds after start (packaged builds; never on a headless display).
        if (self.settings.check_updates and is_frozen() and QGuiApplication.platformName() != "offscreen"
                and not os.environ.get("CMO_STUDIO_NO_UPDATE_CHECK")):
            QTimer.singleShot(4000, lambda: self.updater.check(manual=False))

    # ------------------------------------------------------------------ menus
    def _action(self, menu, text, slot, shortcut=None, tip=""):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if tip:
            a.setStatusTip(tip)
        a.triggered.connect(slot)
        menu.addAction(a)
        return a

    def _build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu("&File")
        self._action(f, "&New scenario...", self.new_project, QKeySequence.StandardKey.New)
        self._action(f, "&Open...", self.open_project, QKeySequence.StandardKey.Open)
        self.recent_menu = f.addMenu("Open &recent")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        f.addSeparator()
        self._action(f, "&Save", self.save_project, QKeySequence.StandardKey.Save)
        self._action(f, "Save &as...", self.save_project_as, QKeySequence.StandardKey.SaveAs)
        f.addSeparator()
        self._action(f, "Import order of battle from a Build_Scenario.lua (If Russia Wins style)...",
                     self.import_legacy)
        self._action(f, "Open example project...", self.open_example)
        f.addSeparator()
        self._action(f, "&Export...", lambda: self.tabs.setCurrentWidget(self.export_page), "Ctrl+E")
        f.addSeparator()
        self._action(f, "Settings...", self.open_settings)
        f.addSeparator()
        self._action(f, "E&xit", self.close, QKeySequence.StandardKey.Quit)

        e = mb.addMenu("&Edit")
        self.undo_act = self._action(e, "&Undo", self.doc.undo, QKeySequence.StandardKey.Undo)
        self.redo_act = self._action(e, "&Redo", self.doc.redo, QKeySequence.StandardKey.Redo)
        e.addSeparator()
        self._action(e, "Search everything...", self.open_search, "Ctrl+K")
        self._action(e, "Edit selected units...", self.bulk_edit_selected, "Ctrl+Shift+E")
        self._update_undo()

        v = mb.addMenu("&View")
        v.addAction(self.db_dock.toggleViewAction())
        v.addAction(self.issues_dock.toggleViewAction())
        v.addSeparator()
        for i in range(self.tabs.count()):
            self._action(v, self.tabs.tabText(i), lambda _c, k=i: self.tabs.setCurrentIndex(k), f"Ctrl+{i + 1}"
                         if i < 9 else None)

        t = mb.addMenu("&Tools")
        self._action(t, "Validate project", lambda: self.run_validation(True), "F7")
        self._action(t, "Dry-run build (CMO Lua)", lambda: (self.tabs.setCurrentWidget(self.export_page),
                                                            self.export_page._dry()), "F5")
        self._action(t, "Loadout viewer...", lambda: self.open_loadout_viewer(), "Ctrl+L")
        self._action(t, "Place unit template...", lambda: self.place_template(), "Ctrl+T")
        self._action(t, "Template library...", self.open_template_library)
        self._action(t, "Add patrol area from library...", lambda: self.add_library_area(), "Ctrl+Shift+A")
        self._action(t, "Area library...", self.open_area_library)
        self._action(t, "Assign callsigns to aircraft...", self.assign_callsigns, "Ctrl+Shift+C")
        self._action(t, "Callsign library...", self.open_callsign_library)
        self._action(t, "Create units in formation...",
                     lambda: (self.tabs.setCurrentWidget(self.formations_page), self.formations_page.open_creator()),
                     "Ctrl+Shift+F")
        self._action(t, "Fit map to scenario", lambda: (self.tabs.setCurrentWidget(self.map_page),
                                                        self.map_page.map.fit_project()))
        self._action(t, "Open the CMO folder", self._open_cmo)

        h = mb.addMenu("&Help")
        self._action(h, "User manual (PDF)", lambda: self.open_manual("User"), "F1")
        self._action(h, "Reference manual (PDF)", lambda: self.open_manual("Reference"))
        self._action(h, "Check for updates...", lambda: self.updater.check(manual=True))
        self._action(h, "Release notes (GitHub)", lambda: QDesktopServices.openUrl(QUrl(RELEASES_PAGE)))
        h.addSeparator()
        self._action(h, "About", lambda: AboutDialog(self).exec())

    def _fill_recent(self):
        self.recent_menu.clear()
        for path in self.settings.recent_files:
            self.recent_menu.addAction(path, lambda p=path: self.open_project(p))
        if not self.settings.recent_files:
            self.recent_menu.addAction("(none)").setEnabled(False)

    def _update_undo(self, *_):
        self.undo_act.setEnabled(self.doc.can_undo())
        self.redo_act.setEnabled(self.doc.can_redo())
        self.undo_act.setText(f"&Undo {self.doc.undo_label()}".strip())
        self.redo_act.setText(f"&Redo {self.doc.redo_label()}".strip())

    def _title(self):
        name = self.doc.path.name if self.doc.path else "untitled"
        self.setWindowTitle(f"{'*' if self.doc.dirty else ''}{self.doc.project.meta.title} - {name} - "
                            f"{APP_NAME} {__version__}")

    def set_cursor_text(self, text: str):
        self.cursor_label.setText(text)

    def _db_changed(self):
        db = self.dbm.db
        self.db_label.setText(f"DB: {db.path.name}" if db else "No database")
        if db:
            self.settings.db_file = db.path.name

    # ------------------------------------------------------------------ files
    def _confirm_discard(self) -> bool:
        if not self.doc.dirty:
            return True
        r = QMessageBox.question(self, APP_NAME, "Save changes to the current scenario?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.save_project()
        return r == QMessageBox.StandardButton.Discard

    def new_project(self):
        if not self._confirm_discard():
            return
        dbs = [p.name for p in self.dbm.available()]
        dlg = NewProjectDialog(dbs, self.dbm.db.path.name if self.dbm.db else "", self)
        if not dlg.exec():
            return
        p = new_project(dlg.title.text().strip() or "New Scenario", dlg.db.currentText())
        if dlg.template.currentIndex() == 1:
            civ = p.add_side("Civilian", "CIV", "#aaaaaa")
            civ.computer_only = True
            civ.awareness = "Blind"
            civ.export_briefing = False
        elif dlg.template.currentIndex() == 2:
            p.sides.clear()
        self.doc.load(p)
        self.tabs.setCurrentWidget(self.scenario_page)

    def open_project(self, path: Optional[str] = None):
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open scenario project", self._project_dir(), FILE_FILTER)
            if not path:
                return
        try:
            p = Project.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open", f"Could not open {path}:\n{exc}")
            return
        self.doc.load(p, Path(path))
        self.settings.add_recent(str(path))
        self._maybe_switch_db(p)
        self.map_page.map.fit_project()
        self.statusBar().showMessage(f"Opened {path}", 5000)

    def _maybe_switch_db(self, p: Project):
        want = p.meta.db_file
        if want and self.settings.cmo_dir and (not self.dbm.db or self.dbm.db.path.name.lower() != want.lower()):
            path = Path(self.settings.cmo_dir) / "DB" / want
            if path.is_file():
                self.dbm.open(path)

    def _project_dir(self) -> str:
        if self.doc.path and _writable_dir(self.doc.path.parent):
            return str(self.doc.path.parent)
        d = self.settings.value("project_dir", "")
        if d and Path(d).is_dir() and _writable_dir(Path(d)):
            return d
        docs = Path.home() / "Documents"
        return str(docs if docs.is_dir() else Path.home())

    def save_project(self) -> bool:
        if not self.doc.path:
            return self.save_project_as()
        if not _writable_dir(self.doc.path.parent):
            QMessageBox.information(self, "Save", f"{self.doc.path.parent} cannot be written to (for example the "
                                                  "program folder in Program Files). Choose where to save it.")
            return self.save_project_as()
        try:
            self.doc.save()
        except PermissionError:
            QMessageBox.information(self, "Save", f"No permission to write {self.doc.path}. Choose another place.")
            return self.save_project_as()
        except OSError as exc:
            QMessageBox.critical(self, "Save", str(exc))
            return False
        self.settings.add_recent(str(self.doc.path))
        self.statusBar().showMessage(f"Saved {self.doc.path}", 4000)
        return True

    def save_project_as(self) -> bool:
        name = self.doc.project.meta.folder() + PROJECT_SUFFIX
        path, _ = QFileDialog.getSaveFileName(self, "Save scenario project", str(Path(self._project_dir()) / name),
                                              FILE_FILTER)
        if not path:
            return False
        if not path.endswith(PROJECT_SUFFIX):
            path += PROJECT_SUFFIX
        self.doc.path = Path(path)
        self.settings.set_value("project_dir", str(Path(path).parent))
        return self.save_project()

    def _autosave(self):
        if self.doc.dirty and self.doc.path:
            try:
                self.doc.project.save(self.doc.path.with_suffix(PROJECT_SUFFIX + ".autosave"))
            except OSError:
                pass

    def _restart_autosave(self):
        m = self.settings.autosave_minutes
        if m > 0:
            self.autosave.start(m * 60 * 1000)
        else:
            self.autosave.stop()

    def import_legacy(self):
        start = str(Path(self.settings.cmo_dir) / "Lua") if self.settings.cmo_dir else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Import Build_Scenario.lua", start, "Lua (*.lua)")
        if not path:
            return
        if not self._confirm_discard():
            return
        try:
            p, report = import_legacy_build(path, self.dbm.db)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import", f"Could not import {path}:\n{exc}")
            return
        self.doc.load(p)
        self.map_page.map.fit_project()
        QMessageBox.information(self, "Import", "\n".join(report[:40]) + ("\n..." if len(report) > 40 else ""))

    def open_example(self):
        ex = examples_dir()
        path, _ = QFileDialog.getOpenFileName(self, "Open example", str(ex if ex.is_dir() else Path.home()),
                                              FILE_FILTER)
        if path:
            self.open_project(path)

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.dbm.cmo_dir = self.settings.cmo_dir
            latest = latest_database(self.settings.cmo_dir) if self.settings.cmo_dir else None
            if latest and (not self.dbm.db or self.dbm.db.path.parent != latest.parent):
                self.dbm.open(latest)
            self.db_browser.refresh_db_list()
            self._restart_autosave()
            self.doc.reset.emit()

    def _first_run(self):
        QMessageBox.information(self, APP_NAME, "Welcome! The CMO install folder was not found automatically. "
                                                "Please choose it so the studio can read the DB3000 databases.")
        self.open_settings()

    def _open_cmo(self):
        if self.settings.cmo_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings.cmo_dir))

    def open_manual(self, which: str = "User") -> None:
        """Open the PDF manual (installed copy, else the one on GitHub)."""
        name = f"CMO-Scenario-Studio-{which}-Manual.pdf"
        pdf = docs_dir() / "manuals" / name
        url = QUrl.fromLocalFile(str(pdf)) if pdf.is_file() else QUrl(f"{REPO_URL}/blob/main/docs/manuals/{name}")
        QDesktopServices.openUrl(url)

    # ------------------------------------------------------------------ DB actions
    def _place_from_db(self, e: DBEntry):
        self.tabs.setCurrentWidget(self.map_page)
        self.map_page.start_place(e)

    def _selected_unit(self) -> Optional[Unit]:
        return self.doc.project.unit(self.doc.selection) if self.doc.selection else None

    def _apply_db(self, e: DBEntry):
        u = self._selected_unit()
        if not u:
            self.statusBar().showMessage("Select a unit first.", 4000)
            return
        if u.type != e.type and QMessageBox.question(
                self, "Change type", f"Change '{u.name}' from {u.type} to {e.type}?") != QMessageBox.StandardButton.Yes:
            return
        with self.doc.modify("Change database entry", "units"):
            u.type, u.dbid, u.db_name = e.type, e.id, e.name
            if e.type == "Aircraft":
                los = self.dbm.db.loadouts(e.id, combat_only=True) if self.dbm.db else []
                u.loadout = los[0].id if los else None
            else:
                u.loadout = None
        self.doc.select(u.id)

    def _loadout_from_db(self, aircraft_id: int, loadout_id: int):
        u = self._selected_unit()
        if not u or u.type != "Aircraft" or int(u.dbid) != int(aircraft_id):
            self.statusBar().showMessage("Select an aircraft of this type first, then double-click a loadout.", 5000)
            return
        with self.doc.modify("Change loadout", "units"):
            u.loadout = loadout_id
        self.doc.select(u.id)
        self.statusBar().showMessage(f"{u.name}: loadout {loadout_id}", 4000)

    def _add_to_base(self, e: DBEntry):
        base = self._selected_unit()
        if not base or base.type not in ("Facility", "Ship", "GroundUnit"):
            QMessageBox.information(self, "Add to base", "Select an airbase (facility) or ship first - on the map or "
                                                         "in the Units tab.")
            return
        from PyQt6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getInt(self, "Squadron", f"How many {e.name} at {base.name}?", 4, 1, 200)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Squadron", "Squadron name (aircraft become '<name> #1'...):",
                                        text=e.name)
        if not ok:
            return
        u = self.map_page.add_unit_from_entry(e, base.side, base.lat, base.lon, host=base.id, count=n)
        with self.doc.modify("Name squadron", "units"):
            u.name = name.strip() or e.name
        self.doc.select(u.id)

    # ------------------------------------------------------------------ navigation
    def goto_object(self, oid: str, line: int = 0) -> None:
        """Show any project object in the tab that edits it."""
        from ..model.project import (Event, Formation, Mission, ReferencePoint, Script, Side, SpecialAction, Unit,
                                     Variant, Zone)
        p = self.doc.project
        obj = p.find(oid)
        if obj is None:
            return
        if isinstance(obj, Unit):
            self.tabs.setCurrentWidget(self.units_page if obj.host else self.map_page)
            self.doc.select(oid)
            return
        if isinstance(obj, (ReferencePoint, Zone)):
            self.tabs.setCurrentWidget(self.map_page)
            self.doc.select(oid)
            return
        if isinstance(obj, Formation):
            self.open_formation(oid)
            return
        target = {Mission: (self.missions_page, "mid"), Event: (self.events_page, "eid"),
                  SpecialAction: (self.specials_page, "aid"), Script: (self.scripts_page, "sid"),
                  Side: (self.sides_page, "sid"), Variant: (self.sides_page, "vid")}.get(type(obj))
        if target is None:
            return
        page, attr = target
        setattr(page, attr, oid)
        self.tabs.setCurrentWidget(page)
        page.refresh()
        if isinstance(obj, Script) and line:
            self.scripts_page.editor.goto_line(line)

    def search_commands(self) -> list:
        tabs = [(f"Go to {self.tabs.tabText(i).replace('&&', '&')}", "tab",
                 lambda k=i: self.tabs.setCurrentIndex(k)) for i in range(self.tabs.count())]
        return tabs + [
            ("Validate project", "F7", lambda: self.run_validation(True)),
            ("Dry-run build", "F5", lambda: (self.tabs.setCurrentWidget(self.export_page), self.export_page._dry())),
            ("Export", "Build & Export tab", lambda: self.tabs.setCurrentWidget(self.export_page)),
            ("Loadout viewer", "Ctrl+L", lambda: self.open_loadout_viewer()),
            ("Create units in formation", "Ctrl+Shift+F",
             lambda: (self.tabs.setCurrentWidget(self.formations_page), self.formations_page.open_creator())),
            ("Edit selected units", "Ctrl+Shift+E", self.bulk_edit_selected),
            ("Assign callsigns", "Ctrl+Shift+C", self.assign_callsigns),
            ("Place unit template", "Ctrl+T", lambda: self.place_template()),
            ("Template library", "Tools menu", self.open_template_library),
            ("Callsign library", "Tools menu", self.open_callsign_library),
            ("Add patrol area from library", "Ctrl+Shift+A", lambda: self.add_library_area()),
            ("Area library", "Tools menu", self.open_area_library),
            ("Fit map to scenario", "Map", lambda: (self.tabs.setCurrentWidget(self.map_page),
                                                    self.map_page.map.fit_project())),
            ("Save", "Ctrl+S", self.save_project),
            ("Settings", "File menu", self.open_settings),
        ] + self._library_area_commands()

    def _library_area_commands(self) -> list:
        """Every predefined patrol area, so Ctrl+K finds 'Biscay' or 'Hormuz' directly."""
        try:
            from .areas_library_ui import current_library
            lib = current_library(self.ctx)[0]
        except Exception:      # noqa: BLE001 - a broken user file must not break search
            return []
        return [(f"Patrol area: {a.name}", f"{a.region} · {a.kind} · area library",
                 lambda aid=a.id: self.add_library_area(aid)) for a in lib.areas]

    def open_search(self) -> None:
        from .search import SearchDialog

        def open_hit(hit):
            if hit.action is not None:
                hit.action()
            else:
                self.goto_object(hit.oid, hit.line)
        dlg = SearchDialog(self.doc.project, self.search_commands(), open_hit, self)
        geo = self.geometry()
        dlg.move(geo.x() + (geo.width() - dlg.width()) // 2, geo.y() + 90)
        dlg.exec()

    def bulk_edit_selected(self, ids: Optional[list] = None) -> None:
        from .bulk_edit import BulkEditDialog
        ids = ids or self.units_page.selected_ids() or ([self.doc.selection] if self.doc.project.unit(
            self.doc.selection) else [])
        if not ids:
            self.statusBar().showMessage("Select units on the Units tab first (Ctrl/Shift-click for several).", 5000)
            return
        BulkEditDialog(self.ctx, ids, self).exec()

    def assign_callsigns(self, ids: Optional[list] = None) -> None:
        """Name the selected aircraft (or every aircraft, if none are selected) from the callsign library."""
        from .callsigns_ui import CallsignAssignDialog
        p = self.doc.project
        ids = ids or self.units_page.selected_ids() or ([self.doc.selection] if p.unit(self.doc.selection) else [])
        ids = [i for i in ids if p.unit(i) and p.unit(i).type == "Aircraft"]
        if not ids:
            ids = [u.id for u in p.units if u.type == "Aircraft"]
            if not ids:
                self.statusBar().showMessage("There are no aircraft in the project yet.", 5000)
                return
        CallsignAssignDialog(self.ctx, ids, self).exec()

    def place_template(self, lat: Optional[float] = None, lon: Optional[float] = None) -> None:
        from .templates_ui import TemplatePlacerDialog
        if not self.doc.project.sides:
            self.statusBar().showMessage("Add a side first (Sides tab).", 5000)
            return
        dlg = TemplatePlacerDialog(self.ctx, lat, lon, self)
        if dlg.exec() and dlg.placed_ids:
            self.tabs.setCurrentWidget(self.map_page)
            first = self.doc.project.unit(dlg.placed_ids[0])
            if first:
                self.map_page.map.center_on(first.lat, first.lon, max(self.map_page.map.zoom, 12))
                self.doc.select(first.id, None)

    def open_template_library(self) -> None:
        from .templates_ui import TemplateLibraryDialog
        TemplateLibraryDialog(self.ctx, self).exec()

    def save_units_as_template(self, ids: list) -> None:
        from .templates_ui import save_units_as_template
        save_units_as_template(self.ctx, ids, self)

    def add_library_area(self, select: str = "") -> None:
        """Browse the predefined patrol areas and add some to the scenario."""
        from .areas_library_ui import AreaBrowserDialog
        if not self.doc.project.sides:
            self.statusBar().showMessage("Add a side first (Sides tab).", 5000)
            return
        dlg = AreaBrowserDialog(self.ctx, self, select=select)
        if dlg.exec() and dlg.added_zone_ids:
            p = self.doc.project
            pts = [(q[0], q[1]) for zid in dlg.added_zone_ids if p.zone(zid) for q in p.zone(zid).points]
            self.tabs.setCurrentWidget(self.map_page)
            self.map_page.map.fit(pts)
            self.doc.select(dlg.added_zone_ids[0], None)

    def open_area_library(self) -> None:
        from .areas_library_ui import AreaLibraryDialog
        AreaLibraryDialog(self.ctx, self).exec()

    def save_zone_to_library(self, zid: str) -> None:
        from .areas_library_ui import save_zone_to_library
        save_zone_to_library(self.ctx, zid, self)

    def open_callsign_library(self) -> None:
        from .callsigns_ui import CallsignLibraryDialog
        CallsignLibraryDialog(self.ctx, self).exec()

    def open_formation(self, fid: str) -> None:
        self.tabs.setCurrentWidget(self.formations_page)
        self.formations_page.select_formation(fid)

    def make_formation(self, unit_ids: list[str]) -> None:
        f = self.formations_page.create_from_units(unit_ids)
        if f is not None:
            self.open_formation(f.id)
            self.statusBar().showMessage(f"Formation '{f.name}' created - choose a layout and spacing.", 6000)

    def open_loadout_viewer(self, aircraft_id: int = 0, loadout_id: int = 0):
        """Open (or bring forward) the Loadout Viewer; defaults to the selected aircraft."""
        from .loadout_viewer import LoadoutViewer
        if not self.dbm.db:
            QMessageBox.information(self, "Loadout viewer", "Open a database first (File > Settings).")
            return
        if self._loadout_viewer is None:
            self._loadout_viewer = LoadoutViewer(self.ctx, self)
            self._loadout_viewer.loadoutChosen.connect(self._loadout_from_db)
            self._loadout_viewer.unitActivated.connect(
                lambda uid: (self.doc.select(uid), self.tabs.setCurrentWidget(self.units_page), self.raise_()))
        if not aircraft_id:
            u = self._selected_unit()
            if u and u.type == "Aircraft":
                aircraft_id, loadout_id = int(u.dbid), int(u.loadout or 0)
        if aircraft_id:
            self._loadout_viewer.show_aircraft(aircraft_id, loadout_id)
        elif loadout_id:
            self._loadout_viewer.show_loadout(loadout_id)
        else:
            self._loadout_viewer.show()
            self._loadout_viewer.raise_()

    def _show_in_browser(self, utype: str, dbid: int):
        self.db_dock.show()
        self.db_browser.set_type(utype)
        self.db_browser.search.setText(str(dbid))
        if self.dbm.db:
            e = self.dbm.db.get(utype, dbid)
            if e:
                self.db_browser.show_entry(e)

    def show_on_map(self, lat: float, lon: float):
        self.tabs.setCurrentWidget(self.map_page)
        self.map_page.map.center_on(lat, lon, max(self.map_page.map.zoom, 8))

    # ------------------------------------------------------------------ validation
    def run_validation(self, show: bool = False):
        self.issues.run()
        if show:
            self.issues_dock.show()
            self.issues_dock.raise_()

    def _jump(self, area: str, oid: str):
        p = self.doc.project
        obj = p.find(oid) if oid else None
        page = {"Scenario": self.scenario_page, "Sides": self.sides_page, "Units": self.units_page,
                "Database": self.units_page, "Areas": self.areas_page, "Missions": self.missions_page,
                "Events": self.events_page, "Special actions": self.specials_page, "Scripts": self.scripts_page,
                "Variants": self.sides_page, "Formations": self.formations_page}.get(area, self.scenario_page)
        if obj is not None and area not in ("Scenario",):
            self.goto_object(oid)
            return
        if obj is not None:
            if area == "Missions":
                self.missions_page.mid = oid
            elif area == "Events":
                self.events_page.eid = oid
            elif area == "Special actions":
                self.specials_page.aid = oid
            elif area == "Scripts":
                self.scripts_page.sid = oid
            elif area == "Variants":
                self.sides_page.vid = oid
            elif area == "Sides":
                self.sides_page.sid = oid
            elif area == "Formations":
                self.formations_page.fid = oid
        self.tabs.setCurrentWidget(page)
        page.refresh()
        if obj is not None and area in ("Units", "Database", "Areas"):
            self.doc.select(oid)

    # ------------------------------------------------------------------ close
    def ask_save_before(self, what: str) -> bool:
        """Before an update: save or discard changes; False if the user cancels."""
        return self._confirm_discard()

    def quit_for_update(self) -> None:
        """The installer has started: close without asking again so it can replace the program files."""
        self._quitting_for_update = True
        self.settings.set_value("window_state", self.saveState())
        self.settings.set_value("window_geometry", self.saveGeometry())
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, e: QCloseEvent):
        if not self._quitting_for_update and not self._confirm_discard():
            e.ignore()
            return
        self.settings.set_value("window_state", self.saveState())
        self.settings.set_value("window_geometry", self.saveGeometry())
        e.accept()


def _writable_dir(d: Path) -> bool:
    """Can files be created in ``d``? (os.access is unreliable on Windows for Program Files.)"""
    import tempfile
    try:
        if not d.is_dir():
            return False
        with tempfile.NamedTemporaryFile(dir=d, prefix=".cmo-studio-", delete=True):
            return True
    except OSError:
        return False
