"""Build & export: validation, dry-run build in CMO's Lua, file preview and writing the folder/zip."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
                             QRadioButton, QSplitter, QVBoxLayout, QWidget)

from ...export import Exporter
from ...model.validation import ERROR, WARNING, validate
from ...tools.lua_engine import LuaUnavailable, check_syntax, dry_run_build, find_lua_dll
from ..widgets import CodeEditor, hint_label, mono_font
from .base import AppContext, Page


class ExportPage(Page):
    title = "Build && Export"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        lay = QHBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        g = QGroupBox("1. Check")
        gl = QVBoxLayout(g)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        gl.addWidget(self.summary)
        row = QHBoxLayout()
        val = QPushButton("Validate")
        val.clicked.connect(self._validate)
        syn = QPushButton("Check Lua syntax")
        syn.clicked.connect(self._syntax)
        row.addWidget(val)
        row.addWidget(syn)
        gl.addLayout(row)
        row = QHBoxLayout()
        self.variant = QComboBox()
        dry = QPushButton("Dry-run build")
        dry.setToolTip("Runs Build_Scenario.lua and every event script in CMO's own Lua 5.4 against a strict "
                       "mock of the ScenEdit API - no CMO needed")
        dry.clicked.connect(self._dry)
        row.addWidget(QLabel("Version:"))
        row.addWidget(self.variant, 1)
        row.addWidget(dry)
        gl.addLayout(row)
        ll.addWidget(g)

        g = QGroupBox("2. Export")
        gl = QVBoxLayout(g)
        self.mode = QButtonGroup(self)
        self.r_cmo = QRadioButton("Install into the CMO folder")
        self.r_dir = QRadioButton("Export to a folder (e.g. a git repository)")
        self.r_zip = QRadioButton("Export as a .zip")
        for i, r in enumerate((self.r_cmo, self.r_dir, self.r_zip)):
            self.mode.addButton(r, i)
            gl.addWidget(r)
        self.r_cmo.setChecked(True)
        self.cmo_label = hint_label("")
        gl.addWidget(self.cmo_label)
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(ctx.settings.export_dir)
        self.dir_edit.setPlaceholderText("Export folder")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(browse)
        gl.addLayout(row)
        self.backup = QCheckBox("Back up files that will be replaced (zip in the studio's data folder)")
        self.backup.setChecked(True)
        self.clean = QCheckBox("Remove files the studio wrote last time that are no longer generated")
        self.clean.setChecked(True)
        gl.addWidget(self.backup)
        gl.addWidget(self.clean)
        row = QHBoxLayout()
        exp = QPushButton("Export")
        exp.setProperty("primary", True)
        exp.clicked.connect(self._export)
        self.open_btn = QPushButton("Open folder")
        self.open_btn.clicked.connect(self._open_folder)
        row.addWidget(exp)
        row.addWidget(self.open_btn)
        row.addStretch()
        gl.addLayout(row)
        ll.addWidget(g)

        g = QGroupBox("3. In CMO")
        gl = QVBoxLayout(g)
        self.steps = QPlainTextEdit()
        self.steps.setReadOnly(True)
        self.steps.setFont(mono_font(9))
        self.steps.setMaximumHeight(170)
        self.steps.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        gl.addWidget(self.steps)
        copy = QPushButton("Copy the console command")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(
            f"ScenEdit_RunScript('/{self.project.meta.folder()}/Build_Scenario.lua')"))
        gl.addWidget(copy, 0, Qt.AlignmentFlag.AlignLeft)
        ll.addWidget(g)
        ll.addStretch()
        split.addWidget(left)

        right = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(QLabel("Generated files (preview):"))
        fs = QSplitter(Qt.Orientation.Horizontal)
        self.files = QListWidget()
        self.files.currentItemChanged.connect(self._show_file)
        fs.addWidget(self.files)
        self.viewer = CodeEditor("lua")
        self.viewer.setReadOnly(True)
        fs.addWidget(self.viewer)
        fs.setSizes([280, 700])
        tl.addWidget(fs, 1)
        right.addWidget(top)
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(QLabel("Output:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(mono_font(9))
        bl.addWidget(self.log)
        right.addWidget(bottom)
        right.setSizes([520, 260])
        split.addWidget(right)
        split.setSizes([420, 900])
        self._files: dict[str, str] = {}

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        p = self.project
        cmo = self.ctx.settings.cmo_dir
        self.cmo_label.setText(f"CMO folder: {cmo or '(not set - Settings)'}")
        self.r_cmo.setEnabled(bool(cmo))
        if not cmo and self.r_cmo.isChecked():
            self.r_dir.setChecked(True)
        self.variant.clear()
        self.variant.addItem("Standard", "")
        for v in p.variants:
            self.variant.addItem(v.name, v.key)
        issues = validate(p, self.ctx.db)
        e = sum(1 for i in issues if i.level == ERROR)
        w = sum(1 for i in issues if i.level == WARNING)
        total = sum(u.count for u in p.units)
        self.summary.setText(
            f"<b>{p.meta.title}</b><br>{len(p.sides)} sides · {total} units ({len(p.units)} entries) · "
            f"{len(p.zones)} areas · {len(p.reference_points)} ref. points · {len(p.missions)} missions · "
            f"{len(p.events)} events · {len(p.special_actions)} special actions · {len(p.scripts)} scripts<br>"
            + (f"<span style='color:#e5484d'>{e} error(s)</span>, " if e else "<span style='color:#30a46c'>"
                                                                              "no errors</span>, ")
            + f"{w} warning(s) - see the Issues panel.")
        self.steps.setPlainText(Exporter(p).instructions_text())
        self._preview()

    def _preview(self):
        try:
            self._files = Exporter(self.project).build_files()
        except Exception as exc:  # noqa: BLE001
            self._files = {}
            self.log.appendPlainText(f"Cannot generate files: {exc}")
        cur = self.files.currentItem().text() if self.files.currentItem() else ""
        self.files.blockSignals(True)
        self.files.clear()
        for rel in self._files:
            it = QListWidgetItem(rel)
            self.files.addItem(it)
            if rel == cur:
                self.files.setCurrentItem(it)
        self.files.blockSignals(False)
        if self.files.currentItem() is None and self.files.count():
            self.files.setCurrentRow(0)
        else:
            self._show_file(self.files.currentItem())

    def _show_file(self, cur, _prev=None):
        if cur is None:
            return
        text = self._files.get(cur.text(), "")
        self.viewer.setPlainText(text.replace("\r\n", "\n"))

    # ------------------------------------------------------------------ checks
    def _validate(self):
        if self.ctx.window:
            self.ctx.window.run_validation(show=True)
        self.refresh()

    def _dll(self):
        dll = find_lua_dll(self.ctx.settings.cmo_dir)
        if not dll:
            QMessageBox.information(self, "Lua", "CMO's lua54.dll was not found. Set the CMO folder in Settings.")
        return dll

    def _syntax(self):
        dll = self._dll()
        if not dll:
            return
        lua = {k: v for k, v in Exporter(self.project).build_files().items() if k.endswith(".lua")}
        try:
            errs = check_syntax(dll, lua)
        except LuaUnavailable as exc:
            QMessageBox.warning(self, "Lua", str(exc))
            return
        self.log.appendPlainText(f"--- Syntax check ({len(lua)} files)")
        if errs:
            for k, v in errs.items():
                self.log.appendPlainText(f"ERROR {k}: {v}")
        else:
            self.log.appendPlainText("All Lua files compile.")

    def _dry(self):
        dll = self._dll()
        if not dll:
            return
        key = self.variant.currentData() or None
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            res = dry_run_build(self.project, dll, key, db=self.ctx.db)
        except LuaUnavailable as exc:
            QMessageBox.warning(self, "Lua", str(exc))
            return
        finally:
            QGuiApplication.restoreOverrideCursor()
        self.log.appendPlainText(f"--- Dry-run build ({self.variant.currentText()})")
        self.log.appendPlainText(res.output)
        self.log.appendPlainText("RESULT: " + ("OK - the build ran cleanly against the mock API." if res.ok else
                                               f"PROBLEMS ({len(res.errors)}) - see above."))

    # ------------------------------------------------------------------ export
    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Export folder", self.dir_edit.text() or str(Path.home()))
        if d:
            self.dir_edit.setText(d)
            self.ctx.settings.export_dir = d

    def _target(self) -> Path | None:
        if self.r_cmo.isChecked():
            return Path(self.ctx.settings.cmo_dir) if self.ctx.settings.cmo_dir else None
        if self.r_dir.isChecked():
            return Path(self.dir_edit.text()) if self.dir_edit.text().strip() else None
        return None

    def _export(self):
        p = self.project
        issues = validate(p, self.ctx.db)
        errors = [i for i in issues if i.level == ERROR]
        if errors and QMessageBox.question(
                self, "Export", f"The project has {len(errors)} error(s), e.g.\n\n{errors[0]}\n\nExport anyway?") != \
                QMessageBox.StandardButton.Yes:
            return
        exp = Exporter(p)
        if self.r_zip.isChecked():
            path, _ = QFileDialog.getSaveFileName(self, "Export zip", str(Path(self.dir_edit.text() or Path.home())
                                                                          / f"{p.meta.folder()}.zip"), "Zip (*.zip)")
            if not path:
                return
            exp.write_zip(path)
            self.log.appendPlainText(f"--- Wrote {path}")
            self.ctx.status(f"Exported {path}")
            return
        root = self._target()
        if root is None:
            QMessageBox.warning(self, "Export", "Choose an export folder first.")
            return
        if self.r_dir.isChecked():
            self.ctx.settings.export_dir = str(root)
        existing, managed = exp.preflight(root)
        if existing and not managed:
            names = "\n".join(str(x.relative_to(root)) for x in existing[:12])
            if QMessageBox.warning(
                    self, "Folder not created by the studio",
                    f"Lua\\{exp.folder} already exists and was not written by CMO Scenario Studio.\n\n"
                    f"These files would be replaced:\n{names}\n\n"
                    + ("A backup zip is made first. " if self.backup.isChecked() else "NO backup will be made. ")
                    + "Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        try:
            res = exp.write(root, backup_dir=self.ctx.settings.backup_dir() if self.backup.isChecked() else None,
                            clean=self.clean.isChecked(), include_readme=not self.r_cmo.isChecked())
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.log.appendPlainText(f"--- Exported {len(res.written)} file(s) to {root}")
        for f in res.written:
            self.log.appendPlainText(f"  wrote   {f.relative_to(root)}")
        for f in res.removed:
            self.log.appendPlainText(f"  removed {f.relative_to(root)}")
        if res.backup:
            self.log.appendPlainText(f"  backup  {res.backup}")
        self.log.appendPlainText(f"Next: in CMO's Lua console run  ScenEdit_RunScript('/{exp.folder}/"
                                 f"Build_Scenario.lua')")
        self._last_root = root
        self.ctx.status(f"Exported to {root}")

    def _open_folder(self):
        root = self._target()
        if not root:
            return
        p = root / "Lua" / self.project.meta.folder()
        target = p if p.is_dir() else root
        if target.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
