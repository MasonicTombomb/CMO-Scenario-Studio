"""Simulated mouse input on the map: draw an area, drag a unit, place a reference point."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtCore import QPoint, QPointF, QSettings, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402


@pytest.fixture
def window(tmp_path, sample):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.resize(1400, 900)
    w.show()
    w.doc.load(sample)
    w.tabs.setCurrentWidget(w.map_page)
    app.processEvents()
    w.map_page.map.center_on(59.5, 25.0, 7)
    yield w
    w.doc.set_dirty(False)
    w.close()


def test_draw_area(window, monkeypatch):
    from cmo_studio.ui.map.map_widget import Tool
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(lambda *a, **k: ("DRAWN", True)))
    m = window.map_page.map
    window.map_page.set_tool(Tool.ZONE)
    n = len(window.doc.project.zones)
    for x, y in ((100, 100), (220, 100), (220, 220)):
        QTest.mouseClick(m, Qt.MouseButton.LeftButton, pos=QPoint(x, y))
    QTest.keyClick(m, Qt.Key.Key_Return)
    zones = window.doc.project.zones
    assert len(zones) == n + 1 and zones[-1].name == "DRAWN" and len(zones[-1].points) == 3


def test_drag_unit(window):
    m = window.map_page.map
    u = next(x for x in window.doc.project.units if x.type == "Ship")
    start = m.to_screen(u.lat, u.lon).toPoint()
    end = start + QPoint(80, 40)
    QTest.mousePress(m, Qt.MouseButton.LeftButton, pos=start)
    for i in range(1, 6):
        ev_pos = start + (end - start) * i / 5
        QTest.mouseMove(m, ev_pos)
        m.mouseMoveEvent(_move_event(ev_pos))
    QTest.mouseRelease(m, Qt.MouseButton.LeftButton, pos=end)
    moved = window.doc.project.unit(u.id)
    lat, lon = m.to_latlon(QPointF(end))
    assert moved.lat == pytest.approx(lat, abs=0.01) and moved.lon == pytest.approx(lon, abs=0.01)


def test_place_rp(window):
    from cmo_studio.ui.map.map_widget import Tool
    m = window.map_page.map
    window.map_page.set_tool(Tool.RP)
    n = len(window.doc.project.reference_points)
    QTest.mouseClick(m, Qt.MouseButton.LeftButton, pos=QPoint(300, 300))
    assert len(window.doc.project.reference_points) == n + 1


def _move_event(pos):
    from PyQt6.QtGui import QMouseEvent
    p = QPointF(pos)
    return QMouseEvent(QMouseEvent.Type.MouseMove, p, p, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)
