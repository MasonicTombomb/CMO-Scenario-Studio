"""Base class for editor pages and a small widget<->attribute binder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit, QSpinBox, QWidget)

from ..document import ProjectDocument


@dataclass
class AppContext:
    """What every page needs: the document, the database, settings and the main window."""
    doc: ProjectDocument
    dbm: Any            # DBManager
    settings: Any       # AppSettings
    window: Any = None  # MainWindow

    @property
    def project(self):
        return self.doc.project

    @property
    def db(self):
        return self.dbm.db

    def status(self, text: str, ms: int = 5000) -> None:
        if self.window is not None:
            self.window.statusBar().showMessage(text, ms)


class Page(QWidget):
    """Refreshes from the document when something else changed it (lazily while hidden)."""

    title = "Page"

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.doc = ctx.doc
        self._stale = True
        self.doc.changed.connect(self._on_changed)
        self.doc.reset.connect(self._on_reset)

    @property
    def project(self):
        return self.doc.project

    def edit(self, label: str, kind: str = "", merge: Optional[str] = None):
        return self.doc.modify(label, kind, self, merge)

    def _on_changed(self, kind: str, source: Any) -> None:
        if source is self:
            return
        self.mark_stale()

    def _on_reset(self) -> None:
        self.mark_stale()

    def mark_stale(self) -> None:
        if self.isVisible():
            self._stale = False
            self.refresh()
        else:
            self._stale = True

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self._stale:
            self._stale = False
            self.refresh()

    def refresh(self) -> None:  # pragma: no cover - overridden
        pass


class Binder:
    """Binds widgets to attributes of the object returned by ``getter``.

    Each change becomes an undoable edit through ``owner.edit``. ``load()`` copies
    the object's values into the widgets without triggering edits.
    """

    def __init__(self, owner: Page | QWidget, getter: Callable[[], Any], kind: str = "",
                 on_change: Optional[Callable[[str], None]] = None):
        self.owner = owner
        self.getter = getter
        self.kind = kind
        self.on_change = on_change
        self._loaders: list[Callable[[Any], None]] = []
        self._loading = False
        self._loaded = False       # widgets fire signals while being set up; ignore them until load()

    def _set(self, attr: str, value: Any, merge: bool = False) -> None:
        if self._loading or not self._loaded:
            return
        obj = self.getter()
        if obj is None or getattr(obj, attr) == value:
            return
        label = f"Edit {attr.replace('_', ' ')}"
        with self.owner.doc.modify(label, self.kind, self.owner, merge=(f"{id(obj)}.{attr}" if merge else None)):
            obj = self.getter()          # same object (modify does not replace the project)
            setattr(obj, attr, value)
        if self.on_change:
            self.on_change(attr)

    def load(self) -> None:
        obj = self.getter()
        self._loading = True
        self._loaded = True
        try:
            for fn in self._loaders:
                fn(obj)
        finally:
            self._loading = False

    # ------------------------------------------------------------------ binders
    def line(self, w: QLineEdit, attr: str, strip: bool = True) -> QLineEdit:
        def commit():
            v = w.text().strip() if strip else w.text()
            self._set(attr, v)
        w.editingFinished.connect(commit)
        self._loaders.append(lambda o: w.setText("" if o is None else str(getattr(o, attr))))
        return w

    def text(self, w: QPlainTextEdit, attr: str) -> QPlainTextEdit:
        w.textChanged.connect(lambda: self._set(attr, w.toPlainText(), merge=True))

        def load(o):
            v = "" if o is None else getattr(o, attr)
            if w.toPlainText() != v:
                w.blockSignals(True)
                w.setPlainText(v)
                w.blockSignals(False)
        self._loaders.append(load)
        return w

    def spin(self, w: QSpinBox | QDoubleSpinBox, attr: str, cast=None) -> QSpinBox | QDoubleSpinBox:
        cast = cast or (int if isinstance(w, QSpinBox) else float)
        w.valueChanged.connect(lambda v: self._set(attr, cast(v), merge=True))

        def load(o):
            w.blockSignals(True)
            w.setValue(cast(getattr(o, attr)) if o is not None else w.minimum())
            w.blockSignals(False)
        self._loaders.append(load)
        return w

    def opt_spin(self, w: QSpinBox | QDoubleSpinBox, attr: str, cast=float) -> QSpinBox | QDoubleSpinBox:
        """Spin box whose minimum value means None (shown with the special value text)."""
        w.valueChanged.connect(lambda v: self._set(attr, None if v == w.minimum() else cast(v), merge=True))

        def load(o):
            v = getattr(o, attr) if o is not None else None
            w.blockSignals(True)
            w.setValue(w.minimum() if v is None else cast(v))
            w.blockSignals(False)
        self._loaders.append(load)
        return w

    def check(self, w: QCheckBox, attr: str) -> QCheckBox:
        w.toggled.connect(lambda v: self._set(attr, bool(v)))

        def load(o):
            w.blockSignals(True)
            w.setChecked(bool(getattr(o, attr)) if o is not None else False)
            w.blockSignals(False)
        self._loaders.append(load)
        return w

    def combo(self, w: QComboBox, attr: str, use_data: bool = True) -> QComboBox:
        def commit(_i):
            v = w.currentData() if use_data else w.currentText()
            if v is None:
                v = w.currentText()
            self._set(attr, v)
        w.currentIndexChanged.connect(commit)

        def load(o):
            v = getattr(o, attr) if o is not None else ""
            w.blockSignals(True)
            i = w.findData(v) if use_data else w.findText(str(v))
            if i < 0 and w.isEditable():
                w.setEditText(str(v))
            else:
                w.setCurrentIndex(max(0, i))
            w.blockSignals(False)
        self._loaders.append(load)
        return w

    def custom(self, load: Callable[[Any], None]) -> None:
        self._loaders.append(load)
