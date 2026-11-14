"""Asynchronous XYZ tile loader with memory and disk caches."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ... import __version__

USER_AGENT = f"CMO-Scenario-Studio/{__version__} (desktop scenario editor; PyQt6)"
MAX_PARALLEL = 6
MEMORY_TILES = 600
RETRY_SECONDS = 60


class TileCache(QObject):
    tileReady = pyqtSignal()

    def __init__(self, cache_root: Path, parent=None):
        super().__init__(parent)
        self.root = Path(cache_root)
        self.net = QNetworkAccessManager(self)
        self.net.finished.connect(self._finished)
        self.url = ""
        self.max_zoom = 18
        self._mem: OrderedDict[tuple, QPixmap] = OrderedDict()
        self._pending: set[tuple] = set()
        self._queue: list[tuple] = []
        self._failed: dict[tuple, float] = {}
        self._active = 0
        self.enabled = True

    def set_source(self, url_template: str, max_zoom: int = 18) -> None:
        if url_template == self.url:
            return
        self.url = url_template or ""
        self.max_zoom = max_zoom
        self._mem.clear()
        self._queue.clear()
        self._failed.clear()
        self.tileReady.emit()

    def _disk_path(self, z: int, x: int, y: int) -> Path:
        h = hashlib.sha1(self.url.encode()).hexdigest()[:12]
        return self.root / h / str(z) / str(x) / f"{y}.png"

    def tile(self, z: int, x: int, y: int) -> Optional[QPixmap]:
        if not self.url or not self.enabled:
            return None
        key = (self.url, z, x, y)
        pm = self._mem.get(key)
        if pm is not None:
            self._mem.move_to_end(key)
            return pm
        path = self._disk_path(z, x, y)
        if path.is_file():
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._remember(key, pm)
                return pm
        if key in self._pending:
            return None
        if time.monotonic() - self._failed.get(key, -1e9) < RETRY_SECONDS:
            return None
        self._pending.add(key)
        self._queue.append(key)
        self._pump()
        return None

    def cancel_outside(self, wanted: set[tuple]) -> None:
        """Drop queued (not yet started) requests that are no longer on screen."""
        keep = [k for k in self._queue if k[1:] in wanted]
        for k in self._queue:
            if k[1:] not in wanted:
                self._pending.discard(k)
        self._queue = keep

    def _remember(self, key, pm: QPixmap) -> None:
        self._mem[key] = pm
        self._mem.move_to_end(key)
        while len(self._mem) > MEMORY_TILES:
            self._mem.popitem(last=False)

    def _pump(self) -> None:
        while self._queue and self._active < MAX_PARALLEL:
            key = self._queue.pop()   # newest first: what the user is looking at now
            url, z, x, y = key
            if url != self.url:
                self._pending.discard(key)
                continue
            req = QNetworkRequest(QUrl(url.format(z=z, x=x, y=y, s="a")))
            req.setRawHeader(b"User-Agent", USER_AGENT.encode())
            req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.PreferCache)
            reply = self.net.get(req)
            reply.setProperty("tilekey", list(key))
            self._active += 1

    def _finished(self, reply: QNetworkReply) -> None:
        self._active -= 1
        key = tuple(reply.property("tilekey") or ())
        self._pending.discard(key)
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError and key:
                data = reply.readAll()
                pm = QPixmap()
                if pm.loadFromData(bytes(data)):
                    url, z, x, y = key
                    if url == self.url:
                        path = self._disk_path(z, x, y)
                        try:
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_bytes(bytes(data))
                        except OSError:
                            pass
                        self._remember(key, pm)
                        self.tileReady.emit()
                else:
                    self._failed[key] = time.monotonic()
            elif key:
                self._failed[key] = time.monotonic()
        finally:
            reply.deleteLater()
            self._pump()
