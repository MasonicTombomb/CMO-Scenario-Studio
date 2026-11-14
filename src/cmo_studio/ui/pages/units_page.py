"""Order of battle: every unit in a sortable, filterable table with bulk actions."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                             QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from ...model.enums import UNIT_TYPES
from ..forms import UnitForm
from ..widgets import IdCombo, PickerDialog
from .base import AppContext, Page

COLUMNS = ["Name", "Side", "Type", "Class (database)", "DBID", "Count", "Starts at", "Group", "Loadout", "Flags"]


class UnitsPage(Page):
    title = "Units"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(ctx, parent)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter by name, class, group...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(lambda *_: self.refresh_table())
        row.addWidget(self.filter, 2)
        self.side_f = IdCombo()
        self.side_f.currentIndexChanged.connect(lambda *_: self.refresh_table())
        row.addWidget(self.side_f, 1)
        self.type_f = QComboBox()
        self.type_f.addItem("All types", "")
        for t in UNIT_TYPES:
            self.type_f.addItem(t, t)
        self.type_f.currentIndexChanged.connect(lambda *_: self.refresh_table())
        row.addWidget(self.type_f, 1)
        lay.addLayout(row)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        ll.addWidget(self.table)
        bulk = QHBoxLayout()
        edit_btn = QPushButton("Edit selected...")
        edit_btn.setProperty("primary", True)
        edit_btn.setToolTip("Change fields on every selected unit at once (Ctrl+Shift+E)")
        edit_btn.clicked.connect(self._bulk_edit)
        bulk.addWidget(edit_btn)
        cs_btn = QPushButton("Callsigns...")
        cs_btn.setToolTip("Name the selected aircraft from the callsign library (Ctrl+Shift+C)")
        cs_btn.clicked.connect(self._callsigns)
        bulk.addWidget(cs_btn)
        for text, fn in (("Assign to mission...", self._assign), ("Make formation", self._formation),
                         ("Set group...", self._group),
                         ("Toggle reinforcement", self._toggle_reserve), ("Delete selected", self._delete)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            bulk.addWidget(b)
        bulk.addStretch()
        self.summary = QPushButton("")
        self.summary.setFlat(True)
        bulk.addWidget(self.summary)
        ll.addLayout(bulk)
        split.addWidget(left)
        self.form = UnitForm(ctx)
        self.form.setMinimumWidth(340)
        split.addWidget(self.form)
        split.setStretchFactor(0, 1)
        split.setSizes([900, 380])
        lay.addWidget(split, 1)
        self.doc.selected.connect(self._external_select)
        self._selecting = False
        self._table_timer = QTimer(self, singleShot=True, interval=300)
        self._table_timer.timeout.connect(self.refresh_table)

    def _on_changed(self, kind, source):
        if source is self.form:          # typing in the form: just update the table, a little later
            if self.isVisible():
                self._table_timer.start()
            else:
                self._stale = True
            return
        super()._on_changed(kind, source)

    def refresh(self) -> None:
        self.refresh_table()
        self.form.set_unit(self.doc.selection if self.project.unit(self.doc.selection) else "")

    def refresh_table(self) -> None:
        p = self.project
        self.side_f.set_items([(s.name, s.id) for s in p.sides], blank="All sides")
        text = self.filter.text().lower().split()
        sid = self.side_f.current_id()
        typ = self.type_f.currentData()
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        rows = 0
        for u in p.units:
            if sid and u.side != sid:
                continue
            if typ and u.type != typ:
                continue
            hay = f"{u.name} {u.db_name} {u.group} {u.dbid}".lower()
            if text and not all(w in hay for w in text):
                continue
            host = p.unit(u.host) if u.host else None
            flags = " ".join(x for x, on in (("radar", u.radar_active), ("hold", u.hold_position),
                                              ("REINF", u.reserve)) if on)
            loadout = str(u.loadout or "") if u.type == "Aircraft" else ""
            values = [u.name, p.side_name(u.side), u.type, u.db_name, str(u.dbid), str(u.count),
                      host.name if host else f"{u.lat:.3f}, {u.lon:.3f}", u.group, loadout, flags]
            self.table.insertRow(rows)
            side = p.side(u.side)
            for c, v in enumerate(values):
                it = QTableWidgetItem(v)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, u.id)
                if c == 1 and side:
                    it.setForeground(QColor(side.color))
                if c in (4, 5):
                    it.setData(Qt.ItemDataRole.DisplayRole, int(v or 0))
                self.table.setItem(rows, c, it)
            if u.id == self.doc.selection:
                self.table.selectRow(rows)
            rows += 1
        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        total = sum(u.count for u in p.units)
        self.summary.setText(f"{rows} shown · {len(p.units)} entries · {total} units")

    def _selected_ids(self) -> list[str]:
        ids = []
        for idx in self.table.selectionModel().selectedRows():
            it = self.table.item(idx.row(), 0)
            if it:
                ids.append(it.data(Qt.ItemDataRole.UserRole))
        return ids

    def _selection(self):
        ids = self._selected_ids()
        if len(ids) == 1:
            self._selecting = True
            self.doc.select(ids[0], self)
            self._selecting = False
            self.form.set_unit(ids[0])

    def _external_select(self, oid: str, source):
        if source is self or not self.isVisible():
            return
        if self.project.unit(oid):
            self.form.set_unit(oid)
            for r in range(self.table.rowCount()):
                if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == oid:
                    self.table.blockSignals(True)
                    self.table.selectRow(r)
                    self.table.blockSignals(False)
                    self.table.scrollToItem(self.table.item(r, 0))
                    break

    def _assign(self):
        ids = self._selected_ids()
        if not ids:
            return
        sides = {self.project.unit(i).side for i in ids}
        missions = [(f"{m.name}  ({self.project.side_name(m.side)}, {m.mclass})", m.id)
                    for m in self.project.missions if m.side in sides]
        if not missions:
            QMessageBox.information(self, "Assign", "No missions for these units' side yet (Missions tab).")
            return
        dlg = PickerDialog("Assign to mission", missions, parent=self, multi=False)
        if dlg.exec() and dlg.selected_ids():
            m = self.project.mission(dlg.selected_ids()[0])
            with self.edit("Assign units to mission", "missions"):
                for uid in ids:
                    if uid not in m.units and self.project.unit(uid).side == m.side:
                        m.units.append(uid)
            self.ctx.status(f"Assigned {len(ids)} unit(s) to {m.name}")

    def selected_ids(self) -> list[str]:
        return self._selected_ids() if self.isVisible() else []

    def _bulk_edit(self):
        ids = self._selected_ids()
        if ids and self.ctx.window is not None:
            self.ctx.window.bulk_edit_selected(ids)
            self.refresh_table()

    def _callsigns(self):
        if self.ctx.window is not None:
            self.ctx.window.assign_callsigns(self._selected_ids())
            self.refresh_table()

    def _context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        ids = self._selected_ids()
        if not ids:
            return
        menu = QMenu(self)
        menu.addAction(f"Edit {len(ids)} selected unit(s)...", self._bulk_edit)
        menu.addAction("Assign callsigns...", self._callsigns)
        menu.addAction("Assign to mission...", self._assign)
        menu.addAction("Make formation", self._formation)
        menu.addAction("Toggle reinforcement", self._toggle_reserve)
        menu.addSeparator()
        if len(ids) == 1 and self.ctx.window is not None:
            menu.addAction("Show on map", lambda: self.ctx.window.goto_object(ids[0]))
        menu.addAction("Delete selected", self._delete)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _formation(self):
        ids = self._selected_ids()
        if ids and self.ctx.window is not None:
            self.ctx.window.make_formation(ids)

    def _group(self):
        ids = self._selected_ids()
        if not ids:
            return
        g, ok = QInputDialog.getText(self, "Group", "Group tag:")
        if ok:
            with self.edit("Set group", "units"):
                for uid in ids:
                    self.project.unit(uid).group = g.strip()
            self.refresh_table()

    def _toggle_reserve(self):
        ids = self._selected_ids()
        if ids:
            with self.edit("Toggle reinforcement", "units"):
                for uid in ids:
                    u = self.project.unit(uid)
                    u.reserve = not u.reserve
            self.refresh_table()

    def _delete(self):
        ids = self._selected_ids()
        if not ids:
            return
        if QMessageBox.question(self, "Delete", f"Delete {len(ids)} unit(s) and anything they host?") != \
                QMessageBox.StandardButton.Yes:
            return
        with self.edit(f"Delete {len(ids)} units", "units"):
            for uid in ids:
                self.project.remove_unit(uid)
        self.doc.select("")
        self.refresh()
