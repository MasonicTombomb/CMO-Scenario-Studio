"""The New Scenario wizard: a few pages of choices, then a working scenario skeleton to edit."""

from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import QDateTime, Qt, QTimeZone
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateTimeEdit, QFormLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QRadioButton, QSpinBox, QVBoxLayout, QWizard, QWizardPage)

from ..model.area_library import default_library as default_areas
from ..model.scenario_wizard import (PRESET_LABELS, PRESETS, WizardSpec, build_scenario, default_areas_for,
                                     default_bases, region_areas, uk_air_bases)
from .widgets import hint_label


def _ticked(w: QListWidget) -> list[str]:
    return [w.item(i).data(Qt.ItemDataRole.UserRole) for i in range(w.count())
            if w.item(i).checkState() == Qt.CheckState.Checked]


class ScenarioWizard(QWizard):
    def __init__(self, dbs: list[str], default_db: str, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.result_ = None
        self.setWindowTitle("New scenario wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(760, 600)

        # 1 - the scenario
        p1 = QWizardPage()
        p1.setTitle("The scenario")
        p1.setSubTitle("Name it, choose the database and when it happens.")
        f = QFormLayout(p1)
        self.title = QLineEdit("New Scenario")
        self.setting = QLineEdit()
        self.setting.setPlaceholderText("e.g. North Sea and Norwegian Sea, March 2030")
        self.dbfile = QComboBox()
        self.dbfile.addItems(dbs or [default_db or ""])
        if default_db:
            self.dbfile.setCurrentText(default_db)
        self.start = QDateTimeEdit(QDateTime(datetime(2030, 3, 1, 6, 0, tzinfo=timezone.utc).astimezone(timezone.utc)))
        self.start.setTimeZone(QTimeZone.utc())
        self.start.setDisplayFormat("yyyy-MM-dd HH:mm 'Z'")
        self.start.setCalendarPopup(True)
        self.hours = QSpinBox()
        self.hours.setRange(1, 24 * 30)
        self.hours.setValue(12)
        self.hours.setSuffix(" hours")
        for label, w in (("Title:", self.title), ("Setting:", self.setting), ("Database:", self.dbfile),
                         ("Starts (Zulu):", self.start), ("Lasts:", self.hours)):
            f.addRow(label, w)
        self.addPage(p1)

        # 2 - sides
        p2 = QWizardPage()
        p2.setTitle("Sides")
        p2.setSubTitle("Who is fighting, and who the player commands. The other side is computer-controlled.")
        f = QFormLayout(p2)
        self.preset = QComboBox()
        for k, label in PRESET_LABELS.items():
            self.preset.addItem(label, k)
        self.preset.currentIndexChanged.connect(self._preset)
        self.side_a, self.side_b = QLineEdit(), QLineEdit()
        self.play_a, self.play_b, self.play_both = (QRadioButton("Side A"), QRadioButton("Side B"),
                                                    QRadioButton("Both (two players, or play either)"))
        self.play_a.setChecked(True)
        self.civilian = QCheckBox("Add a Civilian side (shipping, airliners), computer-controlled")
        f.addRow("Preset:", self.preset)
        f.addRow("Side A (defends):", self.side_a)
        f.addRow("Side B (probes):", self.side_b)
        f.addRow("Player commands:", self.play_a)
        f.addRow("", self.play_b)
        f.addRow("", self.play_both)
        f.addRow("", self.civilian)
        self.addPage(p2)

        # 3 - starter kit
        p3 = QWizardPage()
        p3.setTitle("Starter kit")
        p3.setSubTitle("Bases, fighters, patrol areas and an enemy probe to start from. Change anything later.")
        v = QVBoxLayout(p3)
        f = QFormLayout()
        self.region = QComboBox()
        self.region.addItems(default_areas().all_regions())
        self.region.setCurrentText("United Kingdom")
        self.region.currentTextChanged.connect(self._region)
        f.addRow("Region:", self.region)
        self.squadron = QSpinBox()
        self.squadron.setRange(0, 24)
        self.squadron.setValue(4)
        self.squadron.setSuffix(" fighters per base")
        self.squadron.setSpecialValueText("no fighters")
        f.addRow("Fighters:", self.squadron)
        v.addLayout(f)
        self.bases_label = QLabel("Air bases for side A (real UK sites):")
        v.addWidget(self.bases_label)
        self.bases = QListWidget()
        v.addWidget(self.bases, 1)
        v.addWidget(QLabel("Patrol areas for side A (each gets a combat air patrol with the fighters):"))
        self.areas = QListWidget()
        v.addWidget(self.areas, 1)
        self.probe = QCheckBox("Side B: a pair of bombers probing the area on a plotted course")
        self.probe.setChecked(True)
        self.events = QCheckBox("Standard events: welcome message, points for kills, a 15-minute warning")
        self.events.setChecked(True)
        v.addWidget(self.probe)
        v.addWidget(self.events)
        if db is None:
            v.addWidget(hint_label("No database is open, so aircraft cannot be added. Set the CMO folder in "
                                   "Settings first for fighters and the bomber probe."))
        self.addPage(p3)

        # 4 - summary
        self.p4 = QWizardPage()
        self.p4.setTitle("Ready")
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        QVBoxLayout(self.p4).addWidget(self.summary)
        self.addPage(self.p4)
        self.currentIdChanged.connect(lambda i: i == 3 and self._summarise())
        self._preset()
        self._region(self.region.currentText())

    def _preset(self, *_):
        pr = PRESETS[self.preset.currentData()]
        self.side_a.setText(pr[0])
        self.side_b.setText(pr[1])

    def _region(self, region: str):
        uk = region == "United Kingdom"
        self.bases.clear()
        items = uk_air_bases() if uk else [("ab_main_operating", "Main operating base (generic, placed near the "
                                                                  "patrol areas)"),
                                           ("ab_tactical_has", "Tactical fighter base (generic, with shelters)")]
        for oid, name in items:
            it = QListWidgetItem(name)
            it.setData(Qt.ItemDataRole.UserRole, oid)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if oid in default_bases(region) else Qt.CheckState.Unchecked)
            self.bases.addItem(it)
        self.bases_label.setText("Air bases for side A" + (" (real UK sites):" if uk else " (generic):"))
        self.areas.clear()
        for oid, name in region_areas(region):
            it = QListWidgetItem(name)
            it.setData(Qt.ItemDataRole.UserRole, oid)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if oid in default_areas_for(region) else Qt.CheckState.Unchecked)
            self.areas.addItem(it)

    def spec(self) -> WizardSpec:
        start = self.start.dateTime().toUTC().toPyDateTime().replace(tzinfo=None)
        return WizardSpec(
            title=self.title.text(), setting=self.setting.text(), db_file=self.dbfile.currentText(), start=start,
            duration_hours=self.hours.value(), preset=self.preset.currentData(), side_a=self.side_a.text(),
            side_b=self.side_b.text(), player="a" if self.play_a.isChecked() else "b" if self.play_b.isChecked()
            else "both", civilian=self.civilian.isChecked(), region=self.region.currentText(),
            bases=_ticked(self.bases), squadron=self.squadron.value(), areas=_ticked(self.areas),
            probe=self.probe.isChecked(), events=self.events.isChecked())

    def _summarise(self):
        s = self.spec()
        computer = {"a": s.side_b, "b": s.side_a, "both": "none"}[s.player]
        self.summary.setText(
            f"<b>{s.title}</b>, {s.duration_hours} hours from {self.start.text()}.<br><br>"
            f"Sides: <b>{s.side_a}</b> and <b>{s.side_b}</b> (computer-controlled: {computer})"
            f"{', plus Civilian' if s.civilian else ''}.<br>"
            f"{len(s.bases)} air base(s) with {s.squadron or 'no'} fighters each, {len(s.areas)} patrol area(s) "
            f"with combat air patrols{', a bomber probe' if s.probe else ''}"
            f"{', standard events' if s.events else ''}.<br><br>Click <b>Finish</b> to build it. Then check the "
            "Issues panel, look at the map, and edit anything you like.")

    def accept(self):
        self.result_ = build_scenario(self.spec(), self.db)
        super().accept()


__all__ = ["ScenarioWizard"]
