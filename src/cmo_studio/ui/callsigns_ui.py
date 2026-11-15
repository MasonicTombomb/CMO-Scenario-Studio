"""Assign callsigns to aircraft, and edit the callsign library (a standalone JSON file)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..model.callsigns import (Allocator, CountryCallsigns, Library, PlanRow, Squadron, apply_callsigns,
                               default_library, detect_role, flight_format, load_library)
from .widgets import hint_label


def library_path(ctx) -> Path:
    return ctx.settings.data_dir() / "callsigns.json"


def current_library(ctx) -> tuple[Library, str]:
    return load_library(library_path(ctx))


# =============================================================================== assign
class CallsignAssignDialog(QDialog):
    """Detect country and role for each selected aircraft and name them from the library."""

    COLS = ["Unit", "Aircraft", "Count", "Country", "Role", "Squadron", "Callsigns"]

    def __init__(self, ctx, unit_ids: list[str], parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Assign callsigns")
        self.resize(1250, 640)
        self.lib, self.source = current_library(ctx)
        p = ctx.project
        self.unit_ids = [u for u in unit_ids if p.unit(u) and p.unit(u).type == "Aircraft"]
        lay = QVBoxLayout(self)
        lay.addWidget(hint_label(
            "Country comes from the aircraft's operator in the database, role from its type and loadout - change "
            "either per row. Each unit starts a new flight; aircraft in a flight are numbered 1, 2, 3... "
            f"Library: {self.source}"))
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.split = QCheckBox("Split counted units into single aircraft (one callsign each)")
        self.split.setChecked(True)
        self.group = QCheckBox("Put the squadron name in each unit's group tag")
        self.group.setChecked(True)
        for cb in (self.split, self.group):
            cb.toggled.connect(self._preview)
            row.addWidget(cb)
        row.addStretch()
        edit = QPushButton("Edit callsign library...")
        edit.clicked.connect(self._edit_library)
        row.addWidget(edit)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok = bb.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok.setProperty("primary", True)
        bb.accepted.connect(self._apply)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._fill()

    # ------------------------------------------------------------------ table
    def _detect(self, u) -> tuple[CountryCallsigns, str]:
        db = self.ctx.db
        country, role = self.lib.generic(), "FIGHTER"
        if db is not None:
            e = db.get("Aircraft", int(u.dbid))
            if e is not None:
                country = self.lib.country_for(e.country)
                rid = 0
                if u.loadout:
                    r = db.conn.execute("select LoadoutRole from DataLoadout where ID=?", (int(u.loadout),)).fetchone()
                    rid = r[0] if r else 0
                role = detect_role(e.category, e.subtype, rid)
        return country, role

    def _fill(self) -> None:
        p = self.ctx.project
        self.table.setRowCount(0)
        for uid in self.unit_ids:
            u = p.unit(uid)
            country, role = self._detect(u)
            r = self.table.rowCount()
            self.table.insertRow(r)
            name = QTableWidgetItem(u.display_name())
            name.setData(Qt.ItemDataRole.UserRole, uid)
            self.table.setItem(r, 0, name)
            self.table.setItem(r, 1, QTableWidgetItem(u.db_name))
            self.table.setItem(r, 2, QTableWidgetItem(str(u.count)))
            cc = QComboBox()
            cc.addItems([c.name for c in self.lib.countries])
            cc.setCurrentText(country.name)
            rc = QComboBox()
            for key, label in self.lib.roles.items():
                rc.addItem(label, key)
            rc.setCurrentIndex(max(0, rc.findData(role)))
            sc = QComboBox()
            self.table.setCellWidget(r, 3, cc)
            self.table.setCellWidget(r, 4, rc)
            self.table.setCellWidget(r, 5, sc)
            cc.currentTextChanged.connect(lambda *_a, row=r: self._squadrons(row))
            rc.currentIndexChanged.connect(lambda *_a, row=r: self._squadrons(row))
            sc.currentIndexChanged.connect(self._preview)
            self._squadrons(r, preview=False)
        self._preview()

    def _squadrons(self, r: int, preview: bool = True) -> None:
        cc, rc, sc = (self.table.cellWidget(r, c) for c in (3, 4, 5))
        country = self.lib.country(cc.currentText()) or self.lib.generic()
        sc.blockSignals(True)
        sc.clear()
        sc.addItem("(automatic)", "")
        for c, s in self.lib.squadrons_for(country, rc.currentData()):
            sc.addItem(f"{s.name}  -  {s.aircraft}" + ("" if c is country else f"  [{c.name}]"), s.name)
        sc.blockSignals(False)
        if preview:
            self._preview()

    def plan(self) -> list[PlanRow]:
        out = []
        for r in range(self.table.rowCount()):
            out.append(PlanRow(self.table.item(r, 0).data(Qt.ItemDataRole.UserRole),
                               self.table.cellWidget(r, 3).currentText(), self.table.cellWidget(r, 4).currentData(),
                               self.table.cellWidget(r, 5).currentData() or ""))
        return out

    def _preview(self, *_):
        p = self.ctx.project
        planned = set(self.unit_ids)
        alloc = Allocator(self.lib, {u.name for u in p.units if u.id not in planned})
        for r, row in enumerate(self.plan()):
            u = p.unit(row.unit_id)
            country = self.lib.country(row.country) or self.lib.generic()
            if u.count > 1 and not (self.split.isChecked() and not u.reserve):
                a = alloc.allocate_flight_name(country, row.role, row.squadron)
                text = f"{a.name} #1..#{u.count}   ({a.squadron or 'no squadron'})"
            else:
                names = alloc.allocate(country, row.role, max(1, u.count), row.squadron)
                text = ", ".join(a.name for a in names[:8]) + (" ..." if len(names) > 8 else "") + \
                    f"   ({names[0].squadron or 'no squadron'})"
            self.table.setItem(r, 6, QTableWidgetItem(text))
        self.ok.setEnabled(self.table.rowCount() > 0)

    # ------------------------------------------------------------------ actions
    def _edit_library(self):
        dlg = CallsignLibraryDialog(self.ctx, self)
        dlg.exec()
        self.lib, self.source = current_library(self.ctx)
        self._fill()

    def _apply(self):
        plan = self.plan()
        if not plan:
            self.reject()
            return
        with self.ctx.doc.modify("Assign callsigns", "units"):
            result = apply_callsigns(self.ctx.project, self.lib, plan, split=self.split.isChecked(),
                                     set_group=self.group.isChecked())
        n = sum(len(v) for v in result.values())
        self.ctx.status(f"Named {n} aircraft from the callsign library.")
        self.accept()


# =============================================================================== library editor
SQ_COLS = ["Squadron", "Service", "Base", "Aircraft", "Roles", "Callsign words"]


class CallsignLibraryDialog(QDialog):
    """Edit the callsign library and save it as the user's JSON file."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Callsign library")
        self.resize(1300, 760)
        self.path = library_path(ctx)
        self.lib, self.source = current_library(ctx)
        self.lib = self.lib.clone()
        self.dirty = False
        self.country_name = ""
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.file_label = QLabel("")
        self.file_label.setProperty("hint", True)
        top.addWidget(self.file_label, 1)
        for text, fn in (("Import...", self._import), ("Export...", self._export), ("Show file", self._show_file),
                         ("Reset to defaults", self._reset)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter countries...")
        self.filter.textChanged.connect(lambda *_: self._fill_countries())
        ll.addWidget(self.filter)
        self.countries = QListWidget()
        self.countries.currentItemChanged.connect(self._pick_country)
        ll.addWidget(self.countries)
        row = QHBoxLayout()
        for text, fn in (("Add", self._add_country), ("Rename", self._rename_country),
                         ("Remove", self._remove_country)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        ll.addLayout(row)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        self.match = QLineEdit()
        self.match.setToolTip("Prefixes of the database operator country, comma separated (e.g. Russia, Soviet Union)")
        self.match.editingFinished.connect(self._country_fields)
        form.addRow("Matches DB countries:", self.match)
        fr = QHBoxLayout()
        self.format = QLineEdit()
        self.format.setToolTip("{word} {flight} {member} {squadron}; numbers accept format specs, e.g. {member:02d}")
        self.format.editingFinished.connect(self._country_fields)
        self.size = QSpinBox()
        self.size.setRange(1, 12)
        self.size.valueChanged.connect(self._country_fields)
        self.example = QLabel("")
        self.example.setProperty("hint", True)
        fr.addWidget(self.format, 1)
        fr.addWidget(QLabel("aircraft per flight"))
        fr.addWidget(self.size)
        fr.addWidget(self.example)
        form.addRow("Name format:", fr)
        self.notes = QLineEdit()
        self.notes.editingFinished.connect(self._country_fields)
        form.addRow("Notes:", self.notes)
        rl.addLayout(form)
        row = QHBoxLayout()
        self.role_filter = QComboBox()
        self.role_filter.addItem("All roles", "")
        for key, label in self.lib.roles.items():
            self.role_filter.addItem(f"{label} ({key})", key)
        self.role_filter.currentIndexChanged.connect(lambda *_: self._fill_squadrons())
        row.addWidget(QLabel("Show:"))
        row.addWidget(self.role_filter)
        row.addStretch()
        for text, fn in (("Add squadron", self._add_squadron), ("Duplicate", self._dup_squadron),
                         ("Remove", self._remove_squadron), ("Up", lambda: self._move_squadron(-1)),
                         ("Down", lambda: self._move_squadron(1))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        rl.addLayout(row)
        self.squadrons = QTableWidget(0, len(SQ_COLS))
        self.squadrons.setHorizontalHeaderLabels(SQ_COLS)
        self.squadrons.verticalHeader().setVisible(False)
        self.squadrons.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.squadrons.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.squadrons.itemChanged.connect(self._squadron_edited)
        rl.addWidget(self.squadrons, 1)
        rl.addWidget(hint_label("Edit cells directly. Roles and callsign words are comma separated. Role keys: " +
                                ", ".join(self.lib.roles) + ". Words are used in order; each word gives "
                                f"{self.lib.max_flights_per_word} flights."))
        split.addWidget(right)
        split.setSizes([280, 1000])
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.save_btn = bb.addButton("Save", QDialogButtonBox.ButtonRole.ApplyRole)
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self.save)
        bb.rejected.connect(self.close)
        lay.addWidget(bb)
        self._fill_countries()
        self._update_label()

    # ------------------------------------------------------------------ state
    def _c(self) -> Optional[CountryCallsigns]:
        return self.lib.country(self.country_name)

    def _touch(self):
        self.dirty = True
        self._update_label()

    def _update_label(self):
        state = "  ·  unsaved changes" if self.dirty else ""
        where = str(self.path) if self.path.is_file() else f"{self.path} (not created yet - Save writes it)"
        n_sq = sum(len(c.squadrons) for c in self.lib.countries)
        n_w = sum(len(s.callsigns) for c in self.lib.countries for s in c.squadrons)
        self.file_label.setText(f"Your library file: {where}{state}\n{len(self.lib.countries)} countries · "
                                f"{n_sq} squadrons · {n_w} callsign words")

    def _fill_countries(self):
        words = self.filter.text().lower().split()
        self.countries.blockSignals(True)
        self.countries.clear()
        for c in self.lib.countries:
            if words and not all(w in (c.name + " " + " ".join(c.match)).lower() for w in words):
                continue
            it = QListWidgetItem(f"{c.name}   ({len(c.squadrons)})")
            it.setData(Qt.ItemDataRole.UserRole, c.name)
            self.countries.addItem(it)
            if c.name == self.country_name:
                self.countries.setCurrentItem(it)
        self.countries.blockSignals(False)
        if self.countries.currentItem() is None and self.countries.count():
            self.countries.setCurrentRow(0)
        else:
            self._load_country()

    def _pick_country(self, cur, _prev=None):
        if cur is not None:
            self.country_name = cur.data(Qt.ItemDataRole.UserRole)
            self._load_country()

    def _load_country(self):
        c = self._c()
        for w in (self.match, self.format, self.size, self.notes, self.squadrons):
            w.setEnabled(c is not None)
        if c is None:
            return
        for w, val in ((self.match, ", ".join(c.match)), (self.format, c.format), (self.notes, c.notes)):
            w.blockSignals(True)
            w.setText(val)
            w.blockSignals(False)
        self.size.blockSignals(True)
        self.size.setValue(c.flight_size)
        self.size.blockSignals(False)
        self._example()
        self._fill_squadrons()

    def _example(self):
        c = self._c()
        if not c:
            return
        word = next((w for s in c.squadrons for w in s.callsigns), "WORD")
        try:
            names = [c.format.format(word=word, flight=1, member=m, squadron="") for m in (1, 2)]
            flight = flight_format(c.format).format(word=word, flight=1, squadron="")
            self.example.setText(f"e.g. {', '.join(names)} ... (flight {flight})")
        except (KeyError, IndexError, ValueError) as exc:
            self.example.setText(f"format error: {exc}")

    def _country_fields(self, *_):
        c = self._c()
        if not c:
            return
        c.match = [m.strip() for m in self.match.text().split(",") if m.strip()]
        c.format = self.format.text().strip() or self.lib.default_format
        c.flight_size = self.size.value()
        c.notes = self.notes.text().strip()
        self._example()
        self._touch()

    # ------------------------------------------------------------------ squadrons
    def _visible_squadrons(self) -> list[Squadron]:
        c = self._c()
        role = self.role_filter.currentData()
        return [s for s in (c.squadrons if c else []) if not role or role in s.roles]

    def _fill_squadrons(self):
        self.squadrons.blockSignals(True)
        self.squadrons.setRowCount(0)
        for s in self._visible_squadrons():
            r = self.squadrons.rowCount()
            self.squadrons.insertRow(r)
            vals = [s.name, s.service, s.base, s.aircraft, ", ".join(s.roles), ", ".join(s.callsigns)]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if col == 0:
                    it.setData(Qt.ItemDataRole.UserRole, id(s))
                self.squadrons.setItem(r, col, it)
        self.squadrons.blockSignals(False)
        self.squadrons.resizeColumnsToContents()

    def _sq_at(self, row: int) -> Optional[Squadron]:
        it = self.squadrons.item(row, 0)
        if it is None:
            return None
        key = it.data(Qt.ItemDataRole.UserRole)
        return next((s for s in (self._c().squadrons if self._c() else []) if id(s) == key), None)

    def _squadron_edited(self, item: QTableWidgetItem):
        s = self._sq_at(item.row())
        if s is None:
            return
        text = item.text().strip()
        col = item.column()
        if col == 0:
            s.name = text
        elif col == 1:
            s.service = text
        elif col == 2:
            s.base = text
        elif col == 3:
            s.aircraft = text
        elif col == 4:
            roles = [r.strip().upper() for r in text.split(",") if r.strip()]
            unknown = [r for r in roles if r not in self.lib.roles]
            if unknown:
                QMessageBox.warning(self, "Roles", f"Unknown role(s): {', '.join(unknown)}\n\n"
                                                   f"Use: {', '.join(self.lib.roles)}")
                roles = [r for r in roles if r in self.lib.roles]
            s.roles = roles
            self.squadrons.blockSignals(True)
            item.setText(", ".join(roles))
            self.squadrons.blockSignals(False)
        else:
            s.callsigns = [w.strip().upper() for w in text.split(",") if w.strip()]
            self.squadrons.blockSignals(True)
            item.setText(", ".join(s.callsigns))
            self.squadrons.blockSignals(False)
        self._touch()

    def _add_squadron(self):
        c = self._c()
        if not c:
            return
        role = self.role_filter.currentData() or "FIGHTER"
        c.squadrons.append(Squadron(name="New Squadron", roles=[role], callsigns=["NEWWORD"]))
        self._fill_squadrons()
        self.squadrons.setCurrentCell(self.squadrons.rowCount() - 1, 0)
        self.squadrons.editItem(self.squadrons.item(self.squadrons.rowCount() - 1, 0))
        self._touch()

    def _dup_squadron(self):
        c = self._c()
        s = self._sq_at(self.squadrons.currentRow())
        if c and s:
            import copy
            d = copy.deepcopy(s)
            d.name += " (copy)"
            c.squadrons.insert(c.squadrons.index(s) + 1, d)
            self._fill_squadrons()
            self._touch()

    def _remove_squadron(self):
        c = self._c()
        rows = sorted({i.row() for i in self.squadrons.selectedIndexes()}, reverse=True)
        doomed = [self._sq_at(r) for r in rows]
        if c and doomed:
            c.squadrons = [s for s in c.squadrons if s not in doomed]
            self._fill_squadrons()
            self._touch()

    def _move_squadron(self, d: int):
        c = self._c()
        s = self._sq_at(self.squadrons.currentRow())
        if not c or not s:
            return
        i = c.squadrons.index(s)
        j = i + d
        if 0 <= j < len(c.squadrons):
            c.squadrons[i], c.squadrons[j] = c.squadrons[j], c.squadrons[i]
            self._fill_squadrons()
            for r in range(self.squadrons.rowCount()):
                if self._sq_at(r) is s:
                    self.squadrons.setCurrentCell(r, 0)
            self._touch()

    # ------------------------------------------------------------------ countries
    def _add_country(self):
        name, ok = QInputDialog.getText(self, "Add country", "Country name (as you want it listed):")
        if not ok or not name.strip():
            return
        if self.lib.country(name.strip()):
            QMessageBox.warning(self, "Add country", "That country exists.")
            return
        c = CountryCallsigns(name=name.strip(), match=[name.strip()], format=self.lib.default_format,
                             flight_size=self.lib.default_flight_size)
        generic = self.lib.country("Generic")
        idx = self.lib.countries.index(generic) if generic else len(self.lib.countries)
        self.lib.countries.insert(idx, c)
        self.country_name = c.name
        self._fill_countries()
        self._touch()

    def _rename_country(self):
        c = self._c()
        if not c:
            return
        name, ok = QInputDialog.getText(self, "Rename country", "New name:", text=c.name)
        if ok and name.strip() and name.strip() != c.name and not self.lib.country(name.strip()):
            c.name = name.strip()
            self.country_name = c.name
            self._fill_countries()
            self._touch()

    def _remove_country(self):
        c = self._c()
        if not c or c.name == "Generic":
            QMessageBox.information(self, "Remove", "The Generic entry is the fallback and cannot be removed.")
            return
        if QMessageBox.question(self, "Remove country", f"Remove {c.name} and its {len(c.squadrons)} squadrons?") \
                == QMessageBox.StandardButton.Yes:
            self.lib.countries.remove(c)
            self.country_name = ""
            self._fill_countries()
            self._touch()

    # ------------------------------------------------------------------ files
    def save(self) -> bool:
        try:
            self.lib.save(self.path)
        except OSError as exc:
            QMessageBox.critical(self, "Save", str(exc))
            return False
        self.dirty = False
        self._update_label()
        self.ctx.status(f"Callsign library saved to {self.path}")
        return True

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import callsign library", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            lib = Library.load(path)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Import", f"Not a valid callsign library:\n{exc}")
            return
        self.lib = lib
        self.country_name = ""
        self._fill_countries()
        self._touch()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export callsign library", str(Path.home() / "callsigns.json"),
                                              "JSON (*.json)")
        if path:
            self.lib.save(path)
            self.ctx.status(f"Exported {path}")

    def _show_file(self):
        if not self.path.is_file():
            if QMessageBox.question(self, "Show file", "Your library file does not exist yet. Save it now so you "
                                                       "can edit it by hand?") != QMessageBox.StandardButton.Yes:
                return
            if not self.save():
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path.parent)))

    def _reset(self):
        if QMessageBox.question(self, "Reset", "Replace the library with the built-in defaults? (Save to keep "
                                               "the change.)") == QMessageBox.StandardButton.Yes:
            self.lib = default_library()
            self.country_name = ""
            self._fill_countries()
            self._touch()

    def closeEvent(self, e):
        if self.dirty:
            r = QMessageBox.question(self, "Callsign library", "Save changes to your callsign library?",
                                     QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                     QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel or (r == QMessageBox.StandardButton.Save and not self.save()):
                e.ignore()
                return
        super().closeEvent(e)

    def reject(self):
        self.close()


__all__ = ["CallsignAssignDialog", "CallsignLibraryDialog", "library_path"]
