"""Reusable widgets: code editor + highlighters, coordinate field, combos, pickers, tables."""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Optional

from PyQt6.QtCore import QRect, QRegularExpression, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QPainter, QSyntaxHighlighter, QTextCharFormat,
                         QTextCursor, QTextFormat)
from PyQt6.QtWidgets import (QAbstractItemView, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QToolButton,
                             QVBoxLayout, QWidget)

from ..geo import format_latlon, parse_latlon


def mono_font(size: int = 10) -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    f.setFamilies(["Cascadia Mono", "Consolas", f.family()])
    f.setPointSize(size)
    return f


def hint_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setProperty("hint", True)
    lab.setWordWrap(True)
    return lab


def heading_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setProperty("heading", True)
    return lab


# =============================================================================== highlighters
def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class LuaHighlighter(QSyntaxHighlighter):
    KEYWORDS = ("and break do else elseif end false for function goto if in local nil not or repeat return then "
                "true until while").split()

    def __init__(self, doc):
        super().__init__(doc)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self.rules.append((QRegularExpression(r"\b(" + "|".join(self.KEYWORDS) + r")\b"), _fmt("#c792ea", True)))
        self.rules.append((QRegularExpression(r"\b(ScenEdit_\w+|VP_\w+|World_\w+|Tool_\w+|Studio\w+)\b"),
                           _fmt("#82aaff")))
        self.rules.append((QRegularExpression(r"\b(print|pairs|ipairs|tostring|tonumber|type|pcall|error|"
                                              r"string|table|math|os|select|next|setmetatable|getmetatable)\b"),
                           _fmt("#89ddff")))
        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), _fmt("#f78c6c")))
        self.rules.append((QRegularExpression(r"\"([^\"\\\\]|\\\\.)*\"|'([^'\\\\]|\\\\.)*'"), _fmt("#c3e88d")))
        self.comment = _fmt("#6a737d", italic=True)
        self.long = _fmt("#c3e88d")

    def highlightBlock(self, text: str) -> None:
        for rx, fmt in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
        # block comments and long strings (state 1 = inside --[[ ]], 2 = inside [[ ]])
        self.setCurrentBlockState(0)
        start = 0
        state = self.previousBlockState()
        if state in (1, 2):
            end = text.find("]]")
            fmt = self.comment if state == 1 else self.long
            if end < 0:
                self.setFormat(0, len(text), fmt)
                self.setCurrentBlockState(state)
                return
            self.setFormat(0, end + 2, fmt)
            start = end + 2
        i = start
        while i < len(text):
            if text.startswith("--[[", i) or text.startswith("--[==[", i):
                end = text.find("]]", i + 4)
                if end < 0:
                    self.setFormat(i, len(text) - i, self.comment)
                    self.setCurrentBlockState(1)
                    return
                self.setFormat(i, end + 2 - i, self.comment)
                i = end + 2
            elif text.startswith("--", i):
                self.setFormat(i, len(text) - i, self.comment)
                return
            elif text.startswith("[[", i):
                end = text.find("]]", i + 2)
                if end < 0:
                    self.setFormat(i, len(text) - i, self.long)
                    self.setCurrentBlockState(2)
                    return
                self.setFormat(i, end + 2 - i, self.long)
                i = end + 2
            else:
                i += 1


class HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.tag = _fmt("#82aaff")
        self.attr = _fmt("#ffcb6b")
        self.value = _fmt("#c3e88d")
        self.entity = _fmt("#f78c6c")

    def highlightBlock(self, text: str) -> None:
        for m in re.finditer(r"</?[A-Za-z0-9]+|/?>", text):
            self.setFormat(m.start(), m.end() - m.start(), self.tag)
        for m in re.finditer(r"\s([A-Za-z-]+)=", text):
            self.setFormat(m.start(1), len(m.group(1)), self.attr)
        for m in re.finditer(r"\"[^\"]*\"", text):
            self.setFormat(m.start(), m.end() - m.start(), self.value)
        for m in re.finditer(r"&[#A-Za-z0-9]+;", text):
            self.setFormat(m.start(), m.end() - m.start(), self.entity)


# =============================================================================== code editor
class _LineNumbers(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.number_width(), 0)

    def paintEvent(self, event) -> None:
        self.editor.paint_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Plain-text editor with line numbers, current-line highlight and soft tabs."""

    def __init__(self, language: str = "lua", parent=None):
        super().__init__(parent)
        self.setFont(mono_font(10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 2)
        self._numbers = _LineNumbers(self)
        self.blockCountChanged.connect(self._update_width)
        self.updateRequest.connect(self._update_area)
        self.cursorPositionChanged.connect(self._highlight_line)
        self._update_width()
        self._highlight_line()
        self.highlighter = (LuaHighlighter(self.document()) if language == "lua"
                            else HtmlHighlighter(self.document()) if language == "html" else None)
        if language == "html":
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def number_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_width(self, *_):
        self.setViewportMargins(self.number_width(), 0, 0, 0)

    def _update_area(self, rect, dy):
        if dy:
            self._numbers.scroll(0, dy)
        else:
            self._numbers.update(0, rect.y(), self._numbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._numbers.setGeometry(QRect(cr.left(), cr.top(), self.number_width(), cr.height()))

    def paint_numbers(self, event):
        painter = QPainter(self._numbers)
        painter.fillRect(event.rect(), QColor("#1a1b1e"))
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        painter.setPen(QColor("#5c6370"))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(0, top, self._numbers.width() - 6, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, str(num + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            num += 1

    def _highlight_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#25272b"))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.insertPlainText("  ")
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # keep indentation
            line = self.textCursor().block().text()
            indent = re.match(r"\s*", line).group(0)
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        super().keyPressEvent(event)

    def goto_line(self, line: int) -> None:
        block = self.document().findBlockByLineNumber(max(0, line - 1))
        cur = QTextCursor(block)
        self.setTextCursor(cur)
        self.centerCursor()
        self.setFocus()

    def set_text_keep(self, text: str) -> None:
        """Replace the text without moving the view if it is unchanged."""
        if self.toPlainText() != text:
            self.setPlainText(text)


# =============================================================================== small inputs
class CoordEdit(QLineEdit):
    """'lat, lon' in decimal or DMS. Emits coordsEdited(lat, lon) on a valid edit."""

    coordsEdited = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("59.377, 28.190  or  59°22'N 28°11'E")
        self.editingFinished.connect(self._done)

    def set_coords(self, lat: float, lon: float) -> None:
        self.setText(format_latlon(lat, lon))
        self.setStyleSheet("")

    def _done(self):
        v = parse_latlon(self.text())
        if v is None:
            self.setStyleSheet("border: 1px solid #e5484d;")
            return
        self.setStyleSheet("")
        self.coordsEdited.emit(*v)


class ColorButton(QToolButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, color: str = "#4a90d9", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(28, 22)
        self.clicked.connect(self._pick)
        self._paint()

    def color(self) -> str:
        return self._color

    def set_color(self, c: str) -> None:
        self._color = c or "#4a90d9"
        self._paint()

    def _paint(self):
        self.setStyleSheet(f"background:{self._color}; border:1px solid #666; border-radius:3px;")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Choose colour")
        if c.isValid():
            self.set_color(c.name())
            self.colorChanged.emit(self._color)


class IdCombo(QComboBox):
    """Combo of (label, id) pairs; ``current_id()`` / ``set_current_id()``."""

    def set_items(self, items: Iterable[tuple[str, str]], blank: Optional[str] = None, keep: bool = True) -> None:
        cur = self.current_id() if keep else None
        self.blockSignals(True)
        self.clear()
        if blank is not None:
            self.addItem(blank, "")
        for label, oid in items:
            self.addItem(label, oid)
        if cur is not None:
            self.set_current_id(cur)
        self.blockSignals(False)

    def current_id(self) -> str:
        v = self.currentData()
        return v if isinstance(v, str) else ""

    def set_current_id(self, oid: str) -> None:
        i = self.findData(oid or "")
        self.blockSignals(True)
        self.setCurrentIndex(max(0, i) if self.count() else -1)
        self.blockSignals(False)


class PickerDialog(QDialog):
    """Filterable multi-select list of (label, id)."""

    def __init__(self, title: str, items: list[tuple[str, str]], selected: Iterable[str] = (), parent=None,
                 multi: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(460, 520)
        lay = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter...")
        self.filter.textChanged.connect(self._filter)
        lay.addWidget(self.filter)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection if multi
                                   else QAbstractItemView.SelectionMode.SingleSelection)
        sel = set(selected)
        for label, oid in items:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, oid)
            self.list.addItem(it)
            if oid in sel:
                it.setSelected(True)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        lay.addWidget(self.list)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _filter(self, text: str):
        words = text.lower().split()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(not all(w in it.text().lower() for w in words))

    def selected_ids(self) -> list[str]:
        return [it.data(Qt.ItemDataRole.UserRole) for it in self.list.selectedItems()]


class IdListEditor(QWidget):
    """A list of object ids with Add.../Remove buttons. Emits idsChanged(list)."""

    idsChanged = pyqtSignal(list)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._ids: list[str] = []
        self._source: Callable[[], list[tuple[str, str]]] = lambda: []
        self._labels: dict[str, str] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lay.addWidget(self.list)
        row = QHBoxLayout()
        self.add_btn = QPushButton("Add...")
        self.del_btn = QPushButton("Remove")
        self.add_btn.clicked.connect(self._add)
        self.del_btn.clicked.connect(self._remove)
        row.addWidget(self.add_btn)
        row.addWidget(self.del_btn)
        row.addStretch()
        lay.addLayout(row)

    def set_source(self, fn: Callable[[], list[tuple[str, str]]]) -> None:
        self._source = fn

    def set_ids(self, ids: list[str], labels: dict[str, str]) -> None:
        self._ids = list(ids)
        self._labels = labels
        self.list.clear()
        for oid in self._ids:
            it = QListWidgetItem(labels.get(oid, f"(missing {oid})"))
            it.setData(Qt.ItemDataRole.UserRole, oid)
            self.list.addItem(it)

    def ids(self) -> list[str]:
        return list(self._ids)

    def _add(self):
        items = [(lab, oid) for lab, oid in self._source() if oid not in self._ids]
        dlg = PickerDialog(self.title, items, parent=self)
        if dlg.exec():
            new = [x for x in dlg.selected_ids() if x not in self._ids]
            if new:
                self.idsChanged.emit(self._ids + new)

    def _remove(self):
        gone = {it.data(Qt.ItemDataRole.UserRole) for it in self.list.selectedItems()}
        if gone:
            self.idsChanged.emit([x for x in self._ids if x not in gone])


def parse_lua_scalar(text: str) -> Any:
    """'true' -> True, '12' -> 12, '1.5' -> 1.5, anything else -> the string."""
    t = text.strip()
    if t.lower() == "true":
        return True
    if t.lower() == "false":
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        return t


def scalar_text(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


class KeyValueTable(QWidget):
    """Edit a flat dict. Values typed true/false/numbers become those types. Emits dataChanged(dict)."""

    dataChanged = pyqtSignal(dict)

    def __init__(self, key_label: str = "Key", value_label: str = "Value", parent=None, typed: bool = True):
        super().__init__(parent)
        self.typed = typed
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([key_label, value_label])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._changed)
        lay.addWidget(self.table)
        row = QHBoxLayout()
        add = QPushButton("Add")
        rem = QPushButton("Remove")
        add.clicked.connect(self._add)
        rem.clicked.connect(self._remove)
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch()
        lay.addLayout(row)

    def set_data(self, d: dict) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for k, v in d.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(k)))
            self.table.setItem(r, 1, QTableWidgetItem(scalar_text(v)))
        self.table.blockSignals(False)

    def data(self) -> dict:
        out = {}
        for r in range(self.table.rowCount()):
            k = self.table.item(r, 0)
            v = self.table.item(r, 1)
            if k and k.text().strip():
                txt = v.text() if v else ""
                out[k.text().strip()] = parse_lua_scalar(txt) if self.typed else txt
        return out

    def _changed(self, *_):
        self.dataChanged.emit(self.data())

    def _add(self):
        self.table.blockSignals(True)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(f"key{r + 1}"))
        self.table.setItem(r, 1, QTableWidgetItem(""))
        self.table.blockSignals(False)
        self._changed()
        self.table.editItem(self.table.item(r, 0))

    def _remove(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        if rows:
            self._changed()
