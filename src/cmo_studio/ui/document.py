"""The open project plus undo/redo, dirty state and the shared selection.

Every edit goes through :meth:`ProjectDocument.modify`, which snapshots the
project first (so it can be undone) and emits :attr:`changed` afterwards.
Editors keep object *ids*, never object references, because undo replaces the
whole project.
"""

from __future__ import annotations

import copy
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..model.project import Project

MAX_UNDO = 200
MERGE_SECONDS = 1.5


class ProjectDocument(QObject):
    #: (kind, source) - kind is a hint like 'units', 'zones', 'meta'; source is the editor that made the change
    changed = pyqtSignal(str, object)
    #: the whole project was replaced (open, new, undo, redo)
    reset = pyqtSignal()
    #: an object id was selected somewhere (map, list, issue); '' clears
    selected = pyqtSignal(str, object)
    dirtyChanged = pyqtSignal(bool)
    pathChanged = pyqtSignal(str)

    def __init__(self, project: Optional[Project] = None, parent=None):
        super().__init__(parent)
        self.project = project or Project()
        self.path: Optional[Path] = None
        self._dirty = False
        self._undo: list[tuple[str, dict]] = []
        self._redo: list[tuple[str, dict]] = []
        self._merge_key: Optional[str] = None
        self._merge_time = 0.0
        self._depth = 0
        self.selection = ""

    # ------------------------------------------------------------------ state
    @property
    def dirty(self) -> bool:
        return self._dirty

    def set_dirty(self, value: bool) -> None:
        if value != self._dirty:
            self._dirty = value
            self.dirtyChanged.emit(value)

    def load(self, project: Project, path: Optional[Path] = None) -> None:
        self.project = project
        self.path = Path(path) if path else None
        self._undo.clear()
        self._redo.clear()
        self._merge_key = None
        self.selection = ""
        self.set_dirty(False)
        self.pathChanged.emit(str(self.path or ""))
        self.reset.emit()

    def save(self, path: Optional[Path] = None) -> Path:
        path = Path(path or self.path)
        self.project.save(path)
        self.path = path
        self.set_dirty(False)
        self.pathChanged.emit(str(path))
        return path

    # ------------------------------------------------------------------ editing
    @contextmanager
    def modify(self, label: str, kind: str = "", source: Any = None, merge: Optional[str] = None):
        """Snapshot, let the caller edit ``self.project``, then announce the change.

        ``merge``: edits with the same key within 1.5 s share one undo step (typing in a field).
        """
        outer = self._depth == 0
        if outer:
            now = time.monotonic()
            if not (merge and merge == self._merge_key and now - self._merge_time < MERGE_SECONDS):
                self._undo.append((label, copy.deepcopy(self.project.to_dict())))
                del self._undo[:-MAX_UNDO]
                self._redo.clear()
            self._merge_key, self._merge_time = merge, now
        self._depth += 1
        try:
            yield self.project
        finally:
            self._depth -= 1
        if outer:
            self.set_dirty(True)
            self.changed.emit(kind, source)

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo_label(self) -> str:
        return self._undo[-1][0] if self._undo else ""

    def redo_label(self) -> str:
        return self._redo[-1][0] if self._redo else ""

    def undo(self) -> None:
        if not self._undo:
            return
        label, snap = self._undo.pop()
        self._redo.append((label, self.project.to_dict()))
        self._restore(snap)

    def redo(self) -> None:
        if not self._redo:
            return
        label, snap = self._redo.pop()
        self._undo.append((label, self.project.to_dict()))
        self._restore(snap)

    def _restore(self, snap: dict) -> None:
        self.project = Project.from_dict(snap)
        self._merge_key = None
        self.set_dirty(True)
        self.reset.emit()

    # ------------------------------------------------------------------ selection
    def select(self, oid: str, source: Any = None) -> None:
        self.selection = oid or ""
        self.selected.emit(self.selection, source)
