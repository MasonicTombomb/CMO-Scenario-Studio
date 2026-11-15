"""Settings, new-project and about dialogs, and the issues panel."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .. import APP_NAME, __version__
from ..db.database import find_databases
from ..model.validation import ERROR, INFO, WARNING, validate
from ..settings import detect_cmo_dir, looks_like_cmo
from .widgets import hint_label


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle("Settings")
        self.resize(640, 260)
        lay = QVBoxLayout(self)
        f = QFormLayout()
        row = QHBoxLayout()
        self.cmo = QLineEdit(settings.cmo_dir)
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        d = QPushButton("Detect")
        d.clicked.connect(self._detect)
        row.addWidget(self.cmo, 1)
        row.addWidget(b)
        row.addWidget(d)
        f.addRow("CMO folder:", row)
        self.cmo_status = hint_label("")
        f.addRow("", self.cmo_status)
        self.autosave = QSpinBox()
        self.autosave.setRange(0, 60)
        self.autosave.setSuffix(" min")
        self.autosave.setSpecialValueText("off")
        self.autosave.setValue(settings.autosave_minutes)
        f.addRow("Autosave (to a .autosave copy):", self.autosave)
        self.tile_url = QLineEdit(settings.custom_tile_url)
        self.tile_url.setPlaceholderText("https://example.com/{z}/{x}/{y}.png")
        f.addRow("Custom map tiles:", self.tile_url)
        self.updates = QCheckBox("Check GitHub for a new version when the studio starts")
        self.updates.setChecked(settings.check_updates)
        f.addRow("Updates:", self.updates)
        lay.addLayout(f)
        lay.addWidget(hint_label("The CMO folder is the one containing Command.exe, DB\\, Lua\\ and Scenarios\\. "
                                 "The studio reads the databases read-only and only writes into Lua\\<folder> and "
                                 "Scenarios\\<folder> when you export there."))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.cmo.textChanged.connect(self._check)
        self._check()

    def _check(self, *_):
        p = self.cmo.text().strip()
        if looks_like_cmo(p):
            n = len(find_databases(p))
            self.cmo_status.setText(f"OK - {n} database file(s) found.")
        else:
            self.cmo_status.setText("This does not look like a CMO install folder.")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "CMO folder", self.cmo.text() or "C:\\")
        if d:
            self.cmo.setText(d)

    def _detect(self):
        found = detect_cmo_dir()
        if found:
            self.cmo.setText(str(found))
        else:
            self.cmo_status.setText("Not found automatically - browse to it.")

    def _ok(self):
        self.s.cmo_dir = self.cmo.text().strip()
        self.s.autosave_minutes = self.autosave.value()
        self.s.custom_tile_url = self.tile_url.text().strip()
        self.s.check_updates = self.updates.isChecked()
        self.accept()


class NewProjectDialog(QDialog):
    def __init__(self, dbs: list[str], default_db: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("New scenario")
        self.resize(460, 200)
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.title = QLineEdit("New Scenario")
        f.addRow("Title:", self.title)
        self.db = QComboBox()
        self.db.setEditable(True)
        self.db.addItems(dbs)
        if default_db:
            self.db.setCurrentText(default_db)
        f.addRow("Database:", self.db)
        self.template = QComboBox()
        self.template.addItems(["Two hostile sides (Blue / Red)", "Two sides + neutral civilians", "Empty"])
        f.addRow("Start with:", self.template)
        lay.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        lay = QVBoxLayout(self)
        lab = QLabel(f"<h2>{APP_NAME} {__version__}</h2>"
                     "<p>A scenario creation suite for <i>Command: Modern Operations</i>.</p>"
                     "<p>Builds scenarios through CMO's Lua API from a project you edit here, and exports the "
                     "same folder layout as the official Lua-driven scenarios.</p>"
                     "<p>Not affiliated with or endorsed by Matrix Games or WarfareSims. Database values are read "
                     "from your own CMO installation and are not redistributed.</p>"
                     "<p>Map tiles © their providers (Esri, OpenStreetMap contributors, OpenTopoMap).</p>")
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(lab)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class IssuesPanel(QWidget):
    """Validation results; double-click jumps to the object."""

    jumpTo = pyqtSignal(str, str)    # area, object id

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        row = QHBoxLayout()
        self.label = QLabel("")
        row.addWidget(self.label)
        row.addStretch()
        self.filter = QComboBox()
        self.filter.addItems(["Errors and warnings", "Everything", "Errors only"])
        self.filter.currentIndexChanged.connect(self.run)
        row.addWidget(self.filter)
        b = QPushButton("Re-check")
        b.clicked.connect(self.run)
        row.addWidget(b)
        lay.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Level", "Area", "Problem"])
        self.tree.setRootIsDecorated(False)
        self.tree.setColumnWidth(0, 80)
        self.tree.setColumnWidth(1, 120)
        self.tree.itemDoubleClicked.connect(self._jump)
        lay.addWidget(self.tree)
        self._timer = QTimer(self, singleShot=True, interval=800)
        self._timer.timeout.connect(self.run)
        ctx.doc.changed.connect(lambda *_: self._timer.start())
        ctx.doc.reset.connect(self._timer.start)
        ctx.dbm.changed.connect(self._timer.start)

    def run(self, *_):
        issues = validate(self.ctx.project, self.ctx.db)
        mode = self.filter.currentIndex()
        levels = {0: (ERROR, WARNING), 1: (ERROR, WARNING, INFO), 2: (ERROR,)}[mode]
        self.tree.clear()
        colors = {ERROR: "#e5484d", WARNING: "#f5a524", INFO: "#8a8f99"}
        for i in issues:
            if i.level not in levels:
                continue
            it = QTreeWidgetItem([i.level.upper(), i.area, i.message])
            it.setForeground(0, QColor(colors[i.level]))
            it.setData(0, Qt.ItemDataRole.UserRole, (i.area, i.obj_id))
            it.setToolTip(2, i.message)
            self.tree.addTopLevelItem(it)
        e = sum(1 for i in issues if i.level == ERROR)
        w = sum(1 for i in issues if i.level == WARNING)
        n = sum(1 for i in issues if i.level == INFO)
        self.label.setText(f"{e} error(s), {w} warning(s), {n} note(s)")
        return issues

    def _jump(self, item, _col):
        area, oid = item.data(0, Qt.ItemDataRole.UserRole)
        self.jumpTo.emit(area, oid or "")
