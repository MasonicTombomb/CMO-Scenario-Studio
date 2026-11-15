"""Loadout Viewer: browse an aircraft's loadouts, what each one carries, and every linked weapon detail.

Everything is linked: click a weapon to see its ranges, warheads, seekers and targets; double-click
"Carried by" or "Also in loadouts" to jump to another aircraft/loadout; Back/Forward retrace the path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSplitter,
                             QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser, QToolButton, QVBoxLayout,
                             QWidget)

from ..db.loadouts import ROLE_GROUPS, hhmm, loadout_details, loadouts_with_weapon, role_group, weapon_details
from .widgets import hint_label

NON_COMBAT = (9001, 9002, 9003, 9005)


@dataclass(frozen=True)
class _Place:
    aircraft: int
    loadout: int
    weapon: int


class _Num(QTableWidgetItem):
    def __init__(self, value, text: Optional[str] = None):
        super().__init__(text if text is not None else (f"{value:g}" if isinstance(value, float) else str(value)))
        self.setData(Qt.ItemDataRole.UserRole + 1, value)
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole + 1), other.data(Qt.ItemDataRole.UserRole + 1)
        try:
            return float(a or 0) < float(b or 0)
        except (TypeError, ValueError):
            return super().__lt__(other)


def _table(headers: list[str], stretch: int = 1) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    hh.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return t


def _clear_form(form: QFormLayout) -> None:
    while form.rowCount():
        form.removeRow(0)


def _value_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


class LoadoutViewer(QDialog):
    #: aircraft DBID, loadout id - "use this loadout for the selected aircraft"
    loadoutChosen = pyqtSignal(int, int)
    #: project unit id to select
    unitActivated = pyqtSignal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Loadout Viewer")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1550, 860)
        self.place = _Place(0, 0, 0)
        self._back: list[_Place] = []
        self._fwd: list[_Place] = []
        self._navigating = False

        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.back_btn = QToolButton(text="◀ Back")
        self.fwd_btn = QToolButton(text="Forward ▶")
        self.back_btn.clicked.connect(self.go_back)
        self.fwd_btn.clicked.connect(self.go_forward)
        bar.addWidget(self.back_btn)
        bar.addWidget(self.fwd_btn)
        self.crumb = QLabel("")
        self.crumb.setProperty("hint", True)
        bar.addWidget(self.crumb, 1)
        self.use_btn = QPushButton("Use for selected aircraft")
        self.use_btn.setProperty("primary", True)
        self.use_btn.setToolTip("Give the aircraft selected in the project this loadout (same aircraft type only)")
        self.use_btn.clicked.connect(self._use)
        copy = QPushButton("Copy loadout ID")
        copy.clicked.connect(lambda: self.place.loadout and QGuiApplication.clipboard().setText(str(self.place.loadout)))
        bar.addWidget(copy)
        bar.addWidget(self.use_btn)
        lay.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_middle())
        split.addWidget(self._build_right())
        split.setSizes([420, 620, 500])
        lay.addWidget(split, 1)

        ctx.dbm.changed.connect(self._db_changed)
        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._search_aircraft)
        self._search_aircraft()
        self._update_nav()

    # ================================================================== panes
    def _build_left(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel("<b>Aircraft</b>"))
        self.ac_search = QLineEdit()
        self.ac_search.setPlaceholderText("Search aircraft name or DBID...")
        self.ac_search.setClearButtonEnabled(True)
        self.ac_search.textChanged.connect(lambda *_: self._timer.start())
        v.addWidget(self.ac_search)
        self.ac_year = QCheckBox("In service in scenario year")
        self.ac_year.toggled.connect(self._search_aircraft)
        v.addWidget(self.ac_year)
        self.ac_list = QListWidget()
        self.ac_list.setMaximumHeight(220)
        self.ac_list.currentItemChanged.connect(self._aircraft_picked)
        v.addWidget(self.ac_list)

        self.lo_title = QLabel("<b>Loadouts</b>")
        v.addWidget(self.lo_title)
        row = QHBoxLayout()
        self.role = QComboBox()
        self.role.addItem("All roles", "")
        for g in ROLE_GROUPS:
            self.role.addItem(g, g)
        self.role.currentIndexChanged.connect(self._fill_loadouts)
        row.addWidget(self.role, 1)
        self.lo_filter = QLineEdit()
        self.lo_filter.setPlaceholderText("Filter (e.g. AIM-120, JASSM)")
        self.lo_filter.setClearButtonEnabled(True)
        self.lo_filter.textChanged.connect(self._fill_loadouts)
        row.addWidget(self.lo_filter, 1)
        v.addLayout(row)
        row = QHBoxLayout()
        self.non_combat = QCheckBox("Ferry / reserve")
        self.non_combat.toggled.connect(self._fill_loadouts)
        self.lo_dep = QCheckBox("Deprecated")
        self.lo_dep.toggled.connect(self._fill_loadouts)
        row.addWidget(self.non_combat)
        row.addWidget(self.lo_dep)
        row.addStretch()
        v.addLayout(row)
        self.lo_table = _table(["ID", "Name", "Role", "Radius", "TOS"], stretch=1)
        self.lo_table.setSortingEnabled(True)
        self.lo_table.itemSelectionChanged.connect(self._loadout_picked)
        self.lo_table.itemDoubleClicked.connect(lambda *_: self._use())
        v.addWidget(self.lo_table, 1)
        v.addWidget(hint_label("Radius in nm, time on station in minutes. Double-click a loadout to give it to the "
                               "selected aircraft."))
        return w

    def _build_middle(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        self.lo_name = QLabel("Choose an aircraft and a loadout")
        self.lo_name.setProperty("heading", True)
        self.lo_name.setWordWrap(True)
        self.lo_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(self.lo_name)
        self.lo_form = QFormLayout()
        self.lo_form.setVerticalSpacing(2)
        v.addLayout(self.lo_form)
        v.addWidget(QLabel("<b>Weapons and stores</b>  (click one for details)"))
        self.wp_table = _table(["Weapon", "Qty", "Max", "Type", "Air nm", "Surf nm", "Land nm", "Sub nm",
                                "kg each", "Carried"], stretch=0)
        self.wp_table.itemSelectionChanged.connect(self._weapon_picked)
        v.addWidget(self.wp_table, 1)
        self.payload = QLabel("")
        self.payload.setProperty("hint", True)
        v.addWidget(self.payload)
        self.mid_tabs = QTabWidget()
        self.carried_by = QListWidget()
        self.carried_by.setToolTip("Double-click to view that aircraft with this loadout")
        self.carried_by.itemDoubleClicked.connect(
            lambda it: self.navigate(_Place(it.data(Qt.ItemDataRole.UserRole), self.place.loadout, 0)))
        self.in_project = QListWidget()
        self.in_project.setToolTip("Double-click to select the unit in the project")
        self.in_project.itemDoubleClicked.connect(lambda it: self.unitActivated.emit(it.data(Qt.ItemDataRole.UserRole)))
        self.mid_tabs.addTab(self.carried_by, "Carried by")
        self.mid_tabs.addTab(self.in_project, "In this project")
        v.addWidget(self.mid_tabs, 1)
        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.wp_image = QLabel("")
        self.wp_image.setFixedSize(200, 130)
        self.wp_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wp_image.setStyleSheet("background:#151618; border:1px solid #333;")
        top.addWidget(self.wp_image)
        self.wp_name = QLabel("No weapon selected")
        self.wp_name.setProperty("heading", True)
        self.wp_name.setWordWrap(True)
        self.wp_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        top.addWidget(self.wp_name, 1)
        v.addLayout(top)
        self.wp_form = QFormLayout()
        self.wp_form.setVerticalSpacing(1)
        v.addLayout(self.wp_form)
        self.wp_tabs = QTabWidget()
        self.wp_targets = QListWidget()
        self.wp_warheads = QListWidget()
        self.wp_seekers = QListWidget()
        self.wp_codes = QListWidget()
        self.wp_uses = _table(["Aircraft", "Country", "Loadout", "Role"], stretch=2)
        self.wp_uses.setToolTip("Double-click to open that aircraft and loadout")
        self.wp_uses.itemDoubleClicked.connect(self._use_row_activated)
        self.wp_desc = QTextBrowser()
        for wdg, name in ((self.wp_targets, "Targets"), (self.wp_warheads, "Warheads"), (self.wp_seekers, "Seekers"),
                          (self.wp_codes, "Capabilities"), (self.wp_uses, "Also in loadouts"),
                          (self.wp_desc, "Description")):
            self.wp_tabs.addTab(wdg, name)
        v.addWidget(self.wp_tabs, 1)
        return w

    # ================================================================== navigation
    def navigate(self, place: _Place, record: bool = True) -> None:
        if record and place != self.place and (self.place.aircraft or self.place.loadout):
            self._back.append(self.place)
            self._fwd.clear()
        self.place = place
        self._navigating = True
        try:
            self._show_aircraft(place.aircraft)
            self._select_loadout(place.loadout)
            self._show_loadout(place.loadout)
            self._select_weapon(place.weapon)
            self._show_weapon(place.weapon)
        finally:
            self._navigating = False
        self._update_nav()

    def go_back(self):
        if self._back:
            self._fwd.append(self.place)
            self.navigate(self._back.pop(), record=False)

    def go_forward(self):
        if self._fwd:
            self._back.append(self.place)
            self.navigate(self._fwd.pop(), record=False)

    def _update_nav(self):
        self.back_btn.setEnabled(bool(self._back))
        self.fwd_btn.setEnabled(bool(self._fwd))
        db = self.ctx.db
        parts = []
        if db and self.place.aircraft:
            parts.append(db.name_of("Aircraft", self.place.aircraft))
        if db and self.place.loadout:
            parts.append(f"loadout {self.place.loadout}")
        if db and self.place.weapon:
            parts.append(db.name_of("Weapon", self.place.weapon))
        self.crumb.setText("  ›  ".join(parts))
        self.use_btn.setEnabled(bool(self.place.loadout and self.place.aircraft))

    # public entry points
    def show_aircraft(self, aircraft_id: int, loadout_id: int = 0) -> None:
        self.navigate(_Place(int(aircraft_id or 0), int(loadout_id or 0), 0))
        self.show()
        self.raise_()
        self.activateWindow()

    def show_loadout(self, loadout_id: int) -> None:
        """Open a loadout without knowing the aircraft (picks the first aircraft that carries it)."""
        from ..db.loadouts import aircraft_with_loadout
        db = self.ctx.db
        ac = aircraft_with_loadout(db, loadout_id) if db else []
        self.show_aircraft(ac[0].id if ac else 0, loadout_id)

    # ================================================================== aircraft
    def _db_changed(self):
        self._back.clear()
        self._fwd.clear()
        self.place = _Place(0, 0, 0)
        self._search_aircraft()
        self.navigate(self.place, record=False)

    def _search_aircraft(self, *_):
        db = self.ctx.db
        self.ac_list.blockSignals(True)
        self.ac_list.clear()
        if db:
            year = self.ctx.project.scenario_year() if self.ac_year.isChecked() else None
            for e in db.search("Aircraft", self.ac_search.text(), year=year, limit=400):
                it = QListWidgetItem(f"{e.name}  ·  {e.country}  ·  {e.id}")
                it.setData(Qt.ItemDataRole.UserRole, e.id)
                self.ac_list.addItem(it)
                if e.id == self.place.aircraft:
                    self.ac_list.setCurrentItem(it)
        self.ac_list.blockSignals(False)

    def _aircraft_picked(self, cur, _prev=None):
        if cur is not None and not self._navigating:
            self.navigate(_Place(cur.data(Qt.ItemDataRole.UserRole), 0, 0))

    def _show_aircraft(self, aid: int):
        db = self.ctx.db
        self._loadouts = db.loadouts(aid, include_deprecated=True) if (db and aid) else []
        if db and aid:
            e = db.get("Aircraft", aid)
            self.lo_title.setText(f"<b>Loadouts</b> of {e.name if e else aid} ({e.country if e else ''}, "
                                  f"DBID {aid})")
            # make sure the aircraft is visible/selected in the list
            found = False
            for i in range(self.ac_list.count()):
                if self.ac_list.item(i).data(Qt.ItemDataRole.UserRole) == aid:
                    self.ac_list.blockSignals(True)
                    self.ac_list.setCurrentRow(i)
                    self.ac_list.blockSignals(False)
                    found = True
                    break
            if not found and e:
                self.ac_list.blockSignals(True)
                it = QListWidgetItem(f"{e.name}  ·  {e.country}  ·  {e.id}")
                it.setData(Qt.ItemDataRole.UserRole, e.id)
                self.ac_list.insertItem(0, it)
                self.ac_list.setCurrentRow(0)
                self.ac_list.blockSignals(False)
        else:
            self.lo_title.setText("<b>Loadouts</b>")
        self._fill_loadouts()

    def _fill_loadouts(self, *_):
        group = self.role.currentData()
        words = self.lo_filter.text().lower().split()
        self.lo_table.setSortingEnabled(False)
        self.lo_table.blockSignals(True)
        self.lo_table.setRowCount(0)
        db = self.ctx.db
        for lo in getattr(self, "_loadouts", []):
            if lo.role_id in NON_COMBAT and not self.non_combat.isChecked() and lo.id != self.place.loadout:
                continue
            if lo.deprecated and not self.lo_dep.isChecked() and lo.id != self.place.loadout:
                continue
            if group and role_group(lo.role_id) != group:
                continue
            if words:
                hay = f"{lo.id} {lo.name} {lo.role}".lower()
                if not all(w in hay for w in words):
                    if not (db and all(any(w in x.lower() for x in db.loadout_weapons(lo.id)) for w in words)):
                        continue
            r = self.lo_table.rowCount()
            self.lo_table.insertRow(r)
            idi = _Num(lo.id)
            idi.setData(Qt.ItemDataRole.UserRole, lo.id)
            name = QTableWidgetItem(lo.name + ("  [deprecated]" if lo.deprecated else ""))
            name.setToolTip(lo.name)
            if lo.deprecated:
                name.setForeground(QColor("#888"))
            self.lo_table.setItem(r, 0, idi)
            self.lo_table.setItem(r, 1, name)
            self.lo_table.setItem(r, 2, QTableWidgetItem(lo.role))
            self.lo_table.setItem(r, 3, _Num(lo.radius))
            self.lo_table.setItem(r, 4, _Num(lo.time_on_station))
        self.lo_table.blockSignals(False)
        self.lo_table.setSortingEnabled(True)
        self._select_loadout(self.place.loadout)

    def _select_loadout(self, lid: int):
        self.lo_table.blockSignals(True)
        self.lo_table.clearSelection()
        for r in range(self.lo_table.rowCount()):
            if self.lo_table.item(r, 0).data(Qt.ItemDataRole.UserRole) == lid:
                self.lo_table.selectRow(r)
                self.lo_table.scrollToItem(self.lo_table.item(r, 0))
                break
        self.lo_table.blockSignals(False)

    def _loadout_picked(self):
        if self._navigating:
            return
        rows = self.lo_table.selectionModel().selectedRows()
        if rows:
            lid = self.lo_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
            self.navigate(_Place(self.place.aircraft, lid, 0))

    # ================================================================== loadout
    def _show_loadout(self, lid: int):
        db = self.ctx.db
        _clear_form(self.lo_form)
        self.wp_table.setRowCount(0)
        self.carried_by.clear()
        self.in_project.clear()
        self.payload.setText("")
        d = loadout_details(db, lid) if (db and lid) else None
        if d is None:
            self.lo_name.setText("Choose an aircraft and a loadout")
            return
        flags = [x for x, on in (("deprecated", d.deprecated), ("hypothetical", d.hypothetical),
                                 ("needs buddy illumination", d.buddy_illumination)) if on]
        self.lo_name.setText(f"{d.name}\nLoadout {d.id}" + (f"  ·  {', '.join(flags)}" if flags else ""))
        rows = [("Role", f"{d.role}  ({role_group(d.role_id)})"),
                ("Conditions", f"{d.time_of_day}, {d.weather}"),
                ("Combat radius", f"{d.radius_nm} nm" if d.radius_nm else "-"),
                ("Time on station", hhmm(d.time_on_station_min)),
                ("Ready time", f"{hhmm(d.ready_min)}   sustained {hhmm(d.ready_sustained_min)}"),
                ("Quick turnaround", (f"yes - ready {hhmm(d.qt_ready_min)}, up to {d.qt_max_sorties} sorties, "
                                      f"airborne {hhmm(d.qt_airborne_min)}, {d.qt_time_of_day}")
                 if d.quick_turnaround else "no"),
                ("Mission profile", d.mission_profile or "-"),
                ("Winchester / Shotgun", d.winchester or "-"),
                ("Drag modifier", f"{d.drag_modifier:g}" if d.drag_modifier else "-")]
        if d.comments:
            rows.append(("DB comments", d.comments))
        for k, val in rows:
            self.lo_form.addRow(k + ":", _value_label(val))
        for w in d.weapons:
            r = self.wp_table.rowCount()
            self.wp_table.insertRow(r)
            name = QTableWidgetItem(w.name)
            name.setData(Qt.ItemDataRole.UserRole, w.weapon_id)
            carried = ", ".join(x for x, on in (("internal", w.internal), ("optional", w.optional)) if on) or "external"
            cells = [name, _Num(w.qty), _Num(w.max_qty), QTableWidgetItem(w.wtype), _Num(w.air_range, _r(w.air_range)),
                     _Num(w.surface_range, _r(w.surface_range)), _Num(w.land_range, _r(w.land_range)),
                     _Num(w.sub_range, _r(w.sub_range)), _Num(w.weight_kg, _r(w.weight_kg)),
                     QTableWidgetItem(carried)]
            for c, it in enumerate(cells):
                self.wp_table.setItem(r, c, it)
        if not d.weapons:
            self.wp_table.insertRow(0)
            self.wp_table.setItem(0, 0, QTableWidgetItem("(no weapons - sensors, pods or cargo only)"))
        self.payload.setText(f"Weapons payload ≈ {d.payload_kg:,.0f} kg ({len(d.weapons)} store type(s))")
        from ..db.loadouts import aircraft_with_loadout
        carriers = aircraft_with_loadout(db, lid)
        for e in carriers:
            it = QListWidgetItem(f"{e.name}  ·  {e.country}  ·  DBID {e.id}" + ("  (this aircraft)"
                                                                               if e.id == self.place.aircraft else ""))
            it.setData(Qt.ItemDataRole.UserRole, e.id)
            self.carried_by.addItem(it)
        p = self.ctx.project
        users = [u for u in p.units if u.type == "Aircraft" and u.loadout == lid]
        for u in users:
            it = QListWidgetItem(f"{u.display_name()}  ({p.side_name(u.side)})")
            it.setData(Qt.ItemDataRole.UserRole, u.id)
            self.in_project.addItem(it)
        self.mid_tabs.setTabText(0, f"Carried by ({len(carriers)})")
        self.mid_tabs.setTabText(1, f"In this project ({len(users)})")

    def _select_weapon(self, wid: int):
        self.wp_table.blockSignals(True)
        self.wp_table.clearSelection()
        for r in range(self.wp_table.rowCount()):
            it = self.wp_table.item(r, 0)
            if it and it.data(Qt.ItemDataRole.UserRole) == wid:
                self.wp_table.selectRow(r)
                break
        self.wp_table.blockSignals(False)

    def _weapon_picked(self):
        if self._navigating:
            return
        rows = self.wp_table.selectionModel().selectedRows()
        if rows:
            wid = self.wp_table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
            if wid:
                self.navigate(_Place(self.place.aircraft, self.place.loadout, wid))

    # ================================================================== weapon
    def _show_weapon(self, wid: int):
        db = self.ctx.db
        _clear_form(self.wp_form)
        for lw in (self.wp_targets, self.wp_warheads, self.wp_seekers, self.wp_codes):
            lw.clear()
        self.wp_uses.setRowCount(0)
        self.wp_desc.clear()
        self.wp_image.setPixmap(QPixmap())
        d = weapon_details(db, wid) if (db and wid) else None
        if d is None:
            self.wp_name.setText("No weapon selected")
            self.wp_image.setText("")
            return
        self.wp_name.setText(f"{d.entry.name}\nWeapon DBID {wid}" + ("  ·  hypothetical" if d.entry.hypothetical
                                                                     else ""))
        for k, val in d.stats:
            self.wp_form.addRow(k + ":", _value_label(val))
        img = db.image_path("Weapon", wid)
        if img:
            self.wp_image.setPixmap(QPixmap(str(img)).scaled(self.wp_image.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                             Qt.TransformationMode.SmoothTransformation))
        else:
            self.wp_image.setText("no image")
        for lw, items in ((self.wp_targets, d.targets), (self.wp_warheads, d.warheads), (self.wp_seekers, d.seekers),
                          (self.wp_codes, d.codes)):
            lw.addItems(items or ["(none listed)"])
        uses = loadouts_with_weapon(db, wid)
        for u in uses:
            r = self.wp_uses.rowCount()
            self.wp_uses.insertRow(r)
            a = QTableWidgetItem(u.aircraft_name)
            a.setData(Qt.ItemDataRole.UserRole, (u.aircraft_id, u.loadout_id))
            for c, it in enumerate((a, QTableWidgetItem(u.country), QTableWidgetItem(f"{u.loadout_id}  {u.loadout_name}"),
                                    QTableWidgetItem(u.role))):
                self.wp_uses.setItem(r, c, it)
        self.wp_tabs.setTabText(4, f"Also in loadouts ({len(uses)}{'+' if len(uses) >= 2000 else ''})")
        text = db.description("Weapon", wid)
        self.wp_desc.setPlainText((text or "(no description in the database)") +
                                  (f"\n\nDB comments: {d.comments}" if d.comments else ""))

    def _use_row_activated(self, item: QTableWidgetItem):
        data = self.wp_uses.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if data:
            aid, lid = data
            self.navigate(_Place(aid, lid, self.place.weapon))

    # ================================================================== actions
    def _use(self):
        if self.place.aircraft and self.place.loadout:
            self.loadoutChosen.emit(self.place.aircraft, self.place.loadout)


def _r(x: float) -> str:
    return f"{x:g}" if x else "-"
