"""Database browser dock: search DB3000/CWDB, inspect an entry, and send it to the map/units."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSplitter, QTableWidget,
                             QTableWidgetItem, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from ..db.database import BROWSABLE, Database, DBEntry, find_databases
from ..model.enums import UNIT_TYPES
from .widgets import hint_label

TYPE_LABELS = {"GroundUnit": "Ground unit"}


class DBManager(QObject):
    """Owns the open database; everyone else listens to ``changed``."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db: Optional[Database] = None
        self.cmo_dir = ""
        self.error = ""

    def available(self) -> list[Path]:
        return find_databases(self.cmo_dir) if self.cmo_dir else []

    def open(self, path: str | Path) -> bool:
        try:
            db = Database(path)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.error = str(exc)
            return False
        if self.db:
            self.db.close()
        self.db = db
        self.error = ""
        self.changed.emit()
        return True


class _NumItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return int(self.text() or 0) < int(other.text() or 0)
        except ValueError:
            return super().__lt__(other)


class DBBrowser(QWidget):
    placeRequested = pyqtSignal(object)         # DBEntry
    applyRequested = pyqtSignal(object)         # DBEntry -> selected unit
    loadoutRequested = pyqtSignal(int, int)     # aircraft dbid, loadout id
    addToBaseRequested = pyqtSignal(object)     # DBEntry (aircraft) -> selected base

    def __init__(self, manager: DBManager, year_fn=lambda: 2030, parent=None):
        super().__init__(parent)
        self.m = manager
        self.year_fn = year_fn
        self.current: Optional[DBEntry] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        row = QHBoxLayout()
        self.db_combo = QComboBox()
        self.db_combo.setToolTip("Database file in [CMO]\\DB")
        self.db_combo.currentIndexChanged.connect(self._db_chosen)
        row.addWidget(self.db_combo, 2)
        self.type_combo = QComboBox()
        for t in BROWSABLE:
            self.type_combo.addItem(TYPE_LABELS.get(t, t), t)
        self.type_combo.currentIndexChanged.connect(self._search_now)
        row.addWidget(self.type_combo, 1)
        lay.addLayout(row)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or DBID (all words)...")
        self.search.setClearButtonEnabled(True)
        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._search_now)
        self.search.textChanged.connect(lambda *_: self._timer.start())
        row.addWidget(self.search, 2)
        self.country = QComboBox()
        self.country.setEditable(True)
        self.country.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.country.setToolTip("Operator country")
        self.country.currentTextChanged.connect(lambda *_: self._timer.start())
        row.addWidget(self.country, 1)
        lay.addLayout(row)

        row = QHBoxLayout()
        self.in_service = QCheckBox("In service in scenario year")
        self.in_service.setChecked(True)
        self.in_service.toggled.connect(self._search_now)
        self.deprecated = QCheckBox("Show deprecated")
        self.deprecated.toggled.connect(self._search_now)
        row.addWidget(self.in_service)
        row.addWidget(self.deprecated)
        row.addStretch()
        self.count_label = QLabel("")
        self.count_label.setProperty("hint", True)
        row.addWidget(self.count_label)
        lay.addLayout(row)

        split = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["DBID", "Name", "Country", "Type", "Years"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (0, 2, 3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._selected)
        self.table.itemDoubleClicked.connect(lambda *_: self._place())
        split.addWidget(self.table)

        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(0, 4, 0, 0)
        top = QHBoxLayout()
        self.image = QLabel()
        self.image.setFixedSize(220, 140)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet("background:#151618; border:1px solid #333;")
        top.addWidget(self.image)
        info = QVBoxLayout()
        self.title = QLabel("Select an entry")
        self.title.setWordWrap(True)
        self.title.setProperty("heading", True)
        info.addWidget(self.title)
        self.stats = QFormLayout()
        self.stats.setVerticalSpacing(1)
        info.addLayout(self.stats)
        info.addStretch()
        top.addLayout(info, 1)
        dl.addLayout(top)

        btns = QHBoxLayout()
        self.place_btn = QPushButton("Place on map")
        self.place_btn.setProperty("primary", True)
        self.place_btn.setToolTip("Click the map to place this unit (double-click a row does the same)")
        self.place_btn.clicked.connect(self._place)
        self.base_btn = QPushButton("Add to selected base")
        self.base_btn.setToolTip("Add a squadron of this aircraft to the selected airbase/ship")
        self.base_btn.clicked.connect(lambda: self.current and self.addToBaseRequested.emit(self.current))
        self.apply_btn = QPushButton("Use for selected unit")
        self.apply_btn.setToolTip("Change the selected unit's database entry to this one")
        self.apply_btn.clicked.connect(lambda: self.current and self.applyRequested.emit(self.current))
        for b in (self.place_btn, self.base_btn, self.apply_btn):
            btns.addWidget(b)
        btns.addStretch()
        dl.addLayout(btns)

        self.tabs = QTabWidget()
        self.sensors = QListWidget()
        self.weapons = QListWidget()
        self.loadouts = QListWidget()
        self.loadouts.setToolTip("Double-click to use this loadout for the selected aircraft")
        self.loadouts.itemDoubleClicked.connect(self._loadout_chosen)
        self.loadouts.currentItemChanged.connect(self._loadout_preview)
        self.hosting = QListWidget()
        self.desc = QTextBrowser()
        self.tabs.addTab(self.sensors, "Sensors")
        self.tabs.addTab(self.weapons, "Weapons")
        self.tabs.addTab(self.loadouts, "Loadouts")
        self.tabs.addTab(self.hosting, "Facilities")
        self.tabs.addTab(self.desc, "Description")
        dl.addWidget(self.tabs, 1)
        split.addWidget(detail)
        split.setSizes([300, 360])
        lay.addWidget(split, 1)
        lay.addWidget(hint_label("Database values are read-only and come straight from your CMO install."))

        self.m.changed.connect(self._db_changed)
        self.refresh_db_list()

    # ------------------------------------------------------------------ database list
    def refresh_db_list(self) -> None:
        self.db_combo.blockSignals(True)
        self.db_combo.clear()
        for p in self.m.available():
            self.db_combo.addItem(p.name, str(p))
        if self.m.db:
            i = self.db_combo.findText(self.m.db.path.name)
            if i >= 0:
                self.db_combo.setCurrentIndex(i)
        self.db_combo.blockSignals(False)
        if not self.m.available():
            self.count_label.setText("Set the CMO folder in Settings")

    def _db_chosen(self, *_):
        path = self.db_combo.currentData()
        if path and (not self.m.db or str(self.m.db.path) != path):
            self.m.open(path)

    def _db_changed(self):
        self.refresh_db_list()
        db = self.m.db
        self.country.blockSignals(True)
        self.country.clear()
        self.country.addItem("")
        if db:
            self.country.addItems(db.countries())
        self.country.blockSignals(False)
        self._search_now()

    def set_type(self, utype: str) -> None:
        i = self.type_combo.findData(utype)
        if i >= 0:
            self.type_combo.setCurrentIndex(i)

    # ------------------------------------------------------------------ search
    def _search_now(self, *_):
        db = self.m.db
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if not db:
            self.count_label.setText("No database open")
            return
        utype = self.type_combo.currentData()
        year = self.year_fn() if self.in_service.isChecked() else None
        try:
            rows = db.search(utype, self.search.text(), self.country.currentText().strip(), year,
                             self.deprecated.isChecked(), limit=3000)
        except Exception as exc:  # noqa: BLE001
            self.count_label.setText(f"Error: {exc}")
            return
        self.table.setRowCount(len(rows))
        for r, e in enumerate(rows):
            years = f"{e.year or ''}-{e.year_end or ''}" if (e.year or e.year_end) else ""
            idi = _NumItem(str(e.id))
            idi.setData(Qt.ItemDataRole.UserRole, e)
            name = QTableWidgetItem(e.name + ("  [deprecated]" if e.deprecated else "") +
                                    ("  [hypothetical]" if e.hypothetical else ""))
            if e.deprecated:
                name.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(r, 0, idi)
            self.table.setItem(r, 1, name)
            self.table.setItem(r, 2, QTableWidgetItem(e.country))
            self.table.setItem(r, 3, QTableWidgetItem(e.subtype or e.category))
            self.table.setItem(r, 4, QTableWidgetItem(years))
        self.table.setSortingEnabled(True)
        self.count_label.setText(f"{len(rows)} result{'s' if len(rows) != 1 else ''}"
                                 + (" (limit reached)" if len(rows) >= 3000 else ""))
        placeable = utype in UNIT_TYPES
        self.place_btn.setEnabled(placeable)
        self.apply_btn.setEnabled(placeable)
        self.base_btn.setEnabled(utype == "Aircraft")

    def _selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        e: DBEntry = item.data(Qt.ItemDataRole.UserRole)
        self.show_entry(e)

    def show_entry(self, e: DBEntry) -> None:
        self.current = e
        db = self.m.db
        if not db:
            return
        d = db.details(e.type, e.id)
        self.title.setText(f"{e.name}\n{e.country}  ·  DBID {e.id}" + (f"  ·  {d.service}" if d and d.service else ""))
        while self.stats.rowCount():
            self.stats.removeRow(0)
        if d:
            self.stats.addRow("Type:", QLabel(" / ".join(x for x in (e.category, e.subtype) if x and x != "None")))
            if e.year or e.year_end:
                self.stats.addRow("In service:", QLabel(f"{e.year or '?'} - {e.year_end or ''}"))
            for k, v in d.stats[:7]:
                self.stats.addRow(k + ":", QLabel(v))
        img = db.image_path(e.type, e.id)
        if img:
            pm = QPixmap(str(img))
            self.image.setPixmap(pm.scaled(self.image.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        else:
            self.image.setPixmap(QPixmap())
            self.image.setText("no image")
        for lw, items in ((self.sensors, d.sensors if d else []), (self.weapons, d.weapons if d else []),
                          (self.hosting, d.hosts if d else [])):
            lw.clear()
            lw.addItems(items or ["(none)"])
        self.loadouts.clear()
        for lo in (d.loadouts if d else []):
            it = QListWidgetItem(f"{lo.id:>6}  [{lo.role}]  {lo.name}")
            it.setData(Qt.ItemDataRole.UserRole, lo.id)
            it.setToolTip(f"Radius {lo.radius} nm, time on station {lo.time_on_station} min")
            self.loadouts.addItem(it)
        self.tabs.setTabText(2, f"Loadouts ({self.loadouts.count()})")
        text = db.description(e.type, e.id)
        comments = d.comments if d else ""
        self.desc.setPlainText((text or "") + (("\n\nDB comments: " + comments) if comments and comments != "-" else ""))

    def _loadout_preview(self, cur, _prev=None):
        if cur is None or not self.m.db:
            return
        weapons = self.m.db.loadout_weapons(cur.data(Qt.ItemDataRole.UserRole))
        cur.setToolTip(cur.toolTip().split("\n")[0] + ("\n" + "\n".join(weapons) if weapons else ""))

    def _loadout_chosen(self, item: QListWidgetItem):
        if self.current and self.current.type == "Aircraft":
            self.loadoutRequested.emit(self.current.id, item.data(Qt.ItemDataRole.UserRole))

    def _place(self):
        if self.current and self.current.type in UNIT_TYPES:
            self.placeRequested.emit(self.current)
