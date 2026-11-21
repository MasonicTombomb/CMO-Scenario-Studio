"""Pop-out weather forecast editor opened from the Scenario page."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QHeaderView,
                              QLabel, QPushButton, QSpinBox, QTableWidget, QVBoxLayout, QWidget)

from ..model.project import WeatherEntry


class ForecastDialog(QDialog):
    """Modal dialog for editing a sequence of timed weather changes.

    Changes are applied to ``doc.project.forecast`` as a single undo step
    when the user clicks OK.
    """

    def __init__(self, doc, parent: QWidget | None = None):
        super().__init__(parent)
        self._doc = doc
        self.setWindowTitle("Weather Forecast")
        self.setMinimumWidth(640)
        self.setMinimumHeight(300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        v = QVBoxLayout(self)

        v.addWidget(QLabel(
            "Weather changes scheduled after the scenario starts.\n"
            "T+0 initial conditions are set on the Scenario page."
        ))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Offset (min)", "Temp (°C)", "Rain (0-50)", "Cloud (0-1)", "Sea (0-9)"]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for col in range(1, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        v.addWidget(self._table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Change")
        add_btn.clicked.connect(self._on_add)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        v.addWidget(QLabel(
            "Tip: entries are sorted by offset. "
            "Sea state 0 = calm, 9 = phenomenal. Cloud 0 = clear, 1 = overcast."
        ))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        self._load()

    # ------------------------------------------------------------------ load
    def _load(self):
        self._table.setRowCount(0)
        project = self._doc.project
        for entry in sorted(project.forecast, key=lambda e: e.offset_minutes):
            self._insert_row(entry.offset_minutes, entry.temperature,
                             entry.rainfall, entry.cloud, entry.sea_state)

    # ------------------------------------------------------------------ row helpers
    def _insert_row(self, offset_minutes: int = 60, temperature: float = 15.0,
                    rainfall: int = 0, cloud: float = 0.0, sea_state: int = 2):
        row = self._table.rowCount()
        self._table.insertRow(row)

        sp_off = QSpinBox()
        sp_off.setRange(1, 99999)
        sp_off.setValue(int(offset_minutes))
        sp_off.setSuffix(" min")
        self._table.setCellWidget(row, 0, sp_off)

        sp_temp = QDoubleSpinBox()
        sp_temp.setRange(-60.0, 60.0)
        sp_temp.setSuffix(" °C")
        sp_temp.setValue(float(temperature))
        self._table.setCellWidget(row, 1, sp_temp)

        sp_rain = QSpinBox()
        sp_rain.setRange(0, 50)
        sp_rain.setValue(int(rainfall))
        self._table.setCellWidget(row, 2, sp_rain)

        sp_cloud = QDoubleSpinBox()
        sp_cloud.setRange(0.0, 1.0)
        sp_cloud.setSingleStep(0.1)
        sp_cloud.setDecimals(2)
        sp_cloud.setValue(float(cloud))
        self._table.setCellWidget(row, 3, sp_cloud)

        sp_sea = QSpinBox()
        sp_sea.setRange(0, 9)
        sp_sea.setValue(int(sea_state))
        self._table.setCellWidget(row, 4, sp_sea)

    # ------------------------------------------------------------------ actions
    def _on_add(self):
        """Append a new row, inheriting the weather from the last row."""
        n = self._table.rowCount()
        if n > 0:
            off = self._table.cellWidget(n - 1, 0).value() + 60
            temp = self._table.cellWidget(n - 1, 1).value()
            rain = self._table.cellWidget(n - 1, 2).value()
            cloud = self._table.cellWidget(n - 1, 3).value()
            sea = self._table.cellWidget(n - 1, 4).value()
        else:
            w = self._doc.project.weather
            off = 60
            temp, rain, cloud, sea = w.temperature, w.rainfall, w.cloud, w.sea_state
        self._insert_row(off, temp, rain, cloud, sea)
        self._table.scrollToBottom()

    def _on_remove(self):
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()}, reverse=True)
        for row in rows:
            self._table.removeRow(row)

    def _get_entries(self) -> list[WeatherEntry]:
        entries = []
        for row in range(self._table.rowCount()):
            entries.append(WeatherEntry(
                offset_minutes=self._table.cellWidget(row, 0).value(),
                temperature=self._table.cellWidget(row, 1).value(),
                rainfall=self._table.cellWidget(row, 2).value(),
                cloud=self._table.cellWidget(row, 3).value(),
                sea_state=self._table.cellWidget(row, 4).value(),
            ))
        return sorted(entries, key=lambda e: e.offset_minutes)

    def _apply_and_accept(self):
        new_forecast = self._get_entries()
        with self._doc.modify("Edit weather forecast", "weather"):
            self._doc.project.forecast = new_forecast
        self.accept()
