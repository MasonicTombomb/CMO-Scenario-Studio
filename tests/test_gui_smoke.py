"""Open the main window off-screen, visit every page and drive a few edits."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PyQt6.QtCore import QSettings

    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow

    s = AppSettings()
    s.q = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    s.q.setValue("cmo_dir", os.environ.get("CMO_DIR", ""))
    s.tile_source = "None (offline grid)"
    w = MainWindow(s)
    w.show()
    yield w
    w.doc.set_dirty(False)
    w.close()


def test_every_page_refreshes(window, app, sample):
    window.doc.load(sample)
    for i in range(window.tabs.count()):
        window.tabs.setCurrentIndex(i)
        app.processEvents()
    assert "Test Scenario" in window.windowTitle()


def test_edit_undo_redo(window, app, sample):
    from cmo_studio.db.database import DBEntry

    window.doc.load(sample)
    n = len(window.doc.project.units)
    window.map_page.add_unit_from_entry(DBEntry("Ship", 2814, "Test ship"), sample.sides[0].id, 59.0, 24.0)
    assert len(window.doc.project.units) == n + 1
    window.doc.undo()
    assert len(window.doc.project.units) == n
    window.doc.redo()
    assert len(window.doc.project.units) == n + 1


def test_unit_form_edits_name(window, app, sample):
    window.doc.load(sample)
    uid = sample.units[0].id
    form = window.units_page.form
    window.tabs.setCurrentWidget(window.units_page)
    form.set_unit(uid)
    form.name.setText("Renamed AB")
    form.name.editingFinished.emit()
    assert window.doc.project.unit(uid).name == "Renamed AB"
    assert window.doc.dirty


def test_event_template(window, app, sample):
    from cmo_studio.ui.pages.events_page import TEMPLATES, make_template

    for key, _label in TEMPLATES:
        e = make_template(sample, key)
        assert e.triggers and e.actions


def test_no_first_run_dialog_offscreen(tmp_path, monkeypatch):
    """Without a CMO install the first-run prompt must not be scheduled on a headless display (CI hang)."""
    from PyQt6.QtCore import QSettings
    from PyQt6.QtWidgets import QMessageBox

    import cmo_studio.settings as settings_mod
    from cmo_studio.settings import AppSettings
    from cmo_studio.ui.main_window import MainWindow
    monkeypatch.setattr(settings_mod, "detect_cmo_dir", lambda: None)
    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a)))
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    s = AppSettings()
    s.q = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    w = MainWindow(s)
    from PyQt6.QtTest import QTest
    QTest.qWait(500)
    assert not shown
    w.doc.set_dirty(False)
    w.close()
