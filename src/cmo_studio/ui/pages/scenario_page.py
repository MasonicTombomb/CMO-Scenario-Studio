"""Scenario page: title, database, clock, weather, build options, initial key values."""

from __future__ import annotations

from PyQt6.QtCore import QDateTime, Qt, QTimeZone
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QDoubleSpinBox, QFormLayout, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QSpinBox,
                             QVBoxLayout, QWidget)

from ...model.project import safe_folder_name, safe_prefix
from ..widgets import KeyValueTable, hint_label
from .base import AppContext, Binder, Page


class ScenarioPage(Page):
    title = "Scenario"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        grid = QGridLayout(body)

        m = Binder(self, lambda: self.project.meta, "meta", lambda a: self._update_paths())
        c = Binder(self, lambda: self.project.clock, "clock")
        w = Binder(self, lambda: self.project.weather, "weather")
        b = Binder(self, lambda: self.project.build, "build")
        self.binders = [m, c, w, b]

        g = QGroupBox("Scenario")
        f = QFormLayout(g)
        self.title_edit = m.line(QLineEdit(), "title")
        f.addRow("Title:", self.title_edit)
        self.setting = m.line(QLineEdit(), "setting")
        self.setting.setPlaceholderText("e.g. 'Baltic Sea / Estonia' (shown in CMO's scenario list)")
        f.addRow("Setting:", self.setting)
        self.location = m.line(QLineEdit(), "location")
        f.addRow("Location:", self.location)
        self.author = m.line(QLineEdit(), "author")
        f.addRow("Author:", self.author)
        self.inspired = m.line(QLineEdit(), "inspired_by")
        self.inspired.setPlaceholderText("optional, HTML allowed (e.g. <I>Book title</I>)")
        f.addRow("Inspired by:", self.inspired)
        row = QHBoxLayout()
        self.complexity = m.spin(QSpinBox(), "complexity")
        self.complexity.setRange(1, 5)
        self.difficulty = m.spin(QSpinBox(), "difficulty")
        self.difficulty.setRange(1, 5)
        row.addWidget(QLabel("Complexity"))
        row.addWidget(self.complexity)
        row.addWidget(QLabel("Difficulty"))
        row.addWidget(self.difficulty)
        row.addStretch()
        f.addRow("Rating:", row)
        self.hypo = m.line(QLineEdit(), "hypothetical_note")
        self.hypo.setPlaceholderText("e.g. 'This is a hypothetical scenario.'")
        f.addRow("Note:", self.hypo)
        grid.addWidget(g, 0, 0)

        g = QGroupBox("Files and database")
        f = QFormLayout(g)
        self.folder = m.line(QLineEdit(), "folder_name")
        f.addRow("Folder name:", self.folder)
        self.prefix = m.line(QLineEdit(), "file_prefix")
        f.addRow("Page prefix:", self.prefix)
        self.paths = hint_label("")
        f.addRow("", self.paths)
        self.db_combo = QComboBox()
        self.db_combo.setEditable(True)
        m.combo(self.db_combo, "db_file", use_data=False)
        f.addRow("Database:", self.db_combo)
        f.addRow("", hint_label("Create the blank scenario in CMO with this database before running the "
                                "build script. The DB browser can show a different file."))
        grid.addWidget(g, 0, 1)

        g = QGroupBox("Time (Zulu)")
        f = QFormLayout(g)
        self.start = QDateTimeEdit()
        self.start.setDisplayFormat("yyyy-MM-dd  HH:mm:ss 'Z'")
        self.start.setCalendarPopup(True)
        self.start.setTimeZone(QTimeZone.utc())
        self.start.dateTimeChanged.connect(self._start_changed)
        c.custom(lambda o: self._load_start(o.start))
        f.addRow("Start:", self.start)
        row = QHBoxLayout()
        for attr, label, hi in (("duration_days", "days", 365), ("duration_hours", "h", 23),
                                ("duration_minutes", "min", 59)):
            sp = c.spin(QSpinBox(), attr)
            sp.setRange(0, hi)
            sp.setSuffix(" " + label)
            row.addWidget(sp)
        row.addStretch()
        f.addRow("Duration:", row)
        grid.addWidget(g, 1, 0)

        g = QGroupBox("Weather at start")
        f = QFormLayout(g)
        t = w.spin(QDoubleSpinBox(), "temperature")
        t.setRange(-60, 60)
        t.setSuffix(" °C")
        f.addRow("Temperature:", t)
        r = w.spin(QSpinBox(), "rainfall")
        r.setRange(0, 50)
        f.addRow("Rainfall (0-50):", r)
        cl = w.spin(QDoubleSpinBox(), "cloud")
        cl.setRange(0, 1)
        cl.setSingleStep(0.1)
        f.addRow("Cloud (0-1):", cl)
        s = w.spin(QSpinBox(), "sea_state")
        s.setRange(0, 9)
        f.addRow("Sea state (0-9):", s)
        grid.addWidget(g, 1, 1)

        g = QGroupBox("Build options")
        f = QFormLayout(g)
        f.addRow(b.check(QCheckBox("Aircraft start armed with their chosen loadout (otherwise in reserve)"),
                         "armed_start"))
        lo = b.spin(QSpinBox(), "default_loadout")
        lo.setRange(0, 999999)
        f.addRow("Reserve loadout id:", lo)
        vb = b.spin(QSpinBox(), "verbose")
        vb.setRange(0, 2)
        f.addRow("Console detail (0-2):", vb)
        f.addRow(b.check(QCheckBox("Build even if the sides already have units (FORCE_REBUILD)"), "force_rebuild"))
        grid.addWidget(g, 2, 0)

        g = QGroupBox("Initial key values (ScenEdit_SetKeyValue)")
        v = QVBoxLayout(g)
        self.kv = KeyValueTable("Key", "Value", typed=False)
        self.kv.dataChanged.connect(self._kv)
        v.addWidget(self.kv)
        v.addWidget(hint_label("Read them in Lua with StudioGetKV('KEY', default)."))
        grid.addWidget(g, 2, 1)

        g = QGroupBox("Designer notes (never exported)")
        v = QVBoxLayout(g)
        self.notes = m.text(QPlainTextEdit(), "designer_notes")
        self.notes.setMinimumHeight(110)
        v.addWidget(self.notes)
        grid.addWidget(g, 3, 0, 1, 2)
        grid.setRowStretch(4, 1)

    def refresh(self) -> None:
        self.db_combo.blockSignals(True)
        self.db_combo.clear()
        self.db_combo.addItems([p.name for p in self.ctx.dbm.available()])
        self.db_combo.blockSignals(False)
        for b in self.binders:
            b.load()
        self.kv.set_data(self.project.key_values)
        self._update_paths()

    def _update_paths(self):
        m = self.project.meta
        self.folder.setPlaceholderText(safe_folder_name(m.title))
        self.prefix.setPlaceholderText(safe_prefix(m.title))
        self.paths.setText(f"Lua\\{m.folder()}\\   and   Scenarios\\{m.folder()}\\{m.prefix()}_Desc.html")

    def _load_start(self, iso: str):
        dt = QDateTime.fromString(iso.replace("Z", ""), Qt.DateFormat.ISODate)
        dt.setTimeZone(QTimeZone.utc())
        self.start.blockSignals(True)
        self.start.setDateTime(dt)
        self.start.blockSignals(False)

    def _start_changed(self, dt: QDateTime):
        iso = dt.toTimeZone(QTimeZone.utc()).toString("yyyy-MM-ddTHH:mm:ss")
        if iso != self.project.clock.start:
            with self.edit("Change start time", "clock", merge="clock.start"):
                self.project.clock.start = iso

    def _kv(self, data: dict):
        with self.edit("Edit key values", "meta", merge="kv"):
            self.project.key_values = {k: str(v) for k, v in data.items()}
