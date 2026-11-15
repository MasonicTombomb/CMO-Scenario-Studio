"""Check for updates on GitHub, show what's new, download and run the installer."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QProgressDialog,
                             QPushButton, QTextBrowser, QVBoxLayout)

from .. import APP_NAME, __version__
from .. import updater
from ..updater import ReleaseInfo, UpdateError


class _Worker(QObject):
    """Runs a function on a thread and reports back on the GUI thread."""
    done = pyqtSignal(object, object)          # result, error
    progress = pyqtSignal(int, int)

    def run(self, fn, *args):
        def target():
            try:
                res, err = fn(*args), None
            except Exception as exc:  # noqa: BLE001
                res, err = None, exc
            self.done.emit(res, err)
        threading.Thread(target=target, daemon=True).start()


class UpdateDialog(QDialog):
    """'Version X is available': release notes, Install / Skip this version / Later."""

    INSTALL, SKIP, LATER = 1, 2, 3

    def __init__(self, release: ReleaseInfo, mode: str, parent=None):
        super().__init__(parent)
        self.release = release
        self.choice = self.LATER
        self.setWindowTitle("Update available")
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        head = QLabel(f"<b>{APP_NAME} {release.version}</b> is available - you have {__version__}.")
        head.setProperty("heading", True)
        lay.addWidget(head)
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(release.notes or "(no release notes)")
        lay.addWidget(notes, 1)
        bb = QDialogButtonBox()
        if mode == "installed" and release.installer:
            msg = ("The installer is downloaded from GitHub, checked against the release's SHA-256 checksum and run. "
                   f"{APP_NAME} closes while it updates and starts again afterwards; Windows asks for permission "
                   "to change Program Files. Your settings, libraries and projects are kept.")
            install = bb.addButton("Download and install", QDialogButtonBox.ButtonRole.AcceptRole)
            install.setProperty("primary", True)
            install.clicked.connect(lambda: self._done(self.INSTALL))
        else:
            msg = ("This copy was not installed with the setup (it is a portable zip or a source checkout), so it "
                   "cannot update itself. Download the new version from the release page." if mode != "source" else
                   "You are running from source: update with git pull (or download the release).")
            page = bb.addButton("Open release page", QDialogButtonBox.ButtonRole.AcceptRole)
            page.setProperty("primary", True)
            page.clicked.connect(lambda: (QDesktopServices.openUrl(QUrl(release.page)), self._done(self.LATER)))
        skip = bb.addButton("Skip this version", QDialogButtonBox.ButtonRole.RejectRole)
        skip.clicked.connect(lambda: self._done(self.SKIP))
        later = bb.addButton("Later", QDialogButtonBox.ButtonRole.RejectRole)
        later.clicked.connect(lambda: self._done(self.LATER))
        hint = QLabel(msg)
        hint.setWordWrap(True)
        hint.setProperty("hint", True)
        lay.addWidget(hint)
        lay.addWidget(bb)

    def _done(self, choice: int):
        self.choice = choice
        self.accept()


class Updater(QObject):
    """Owned by the main window: background check at startup and Help > Check for updates."""

    def __init__(self, window):
        super().__init__(window)
        self.w = window
        self._busy = False
        self._workers: list[_Worker] = []

    # ------------------------------------------------------------------ checking
    def check(self, manual: bool) -> None:
        if self._busy:
            return
        self._busy = True
        if manual:
            self.w.statusBar().showMessage("Checking GitHub for updates...")
        worker = _Worker()
        self._workers.append(worker)
        worker.done.connect(lambda res, err, m=manual, wk=worker: self._checked(res, err, m, wk))
        worker.run(updater.fetch_latest)

    def _checked(self, release: Optional[ReleaseInfo], err, manual: bool, worker) -> None:
        self._busy = False
        self._workers.remove(worker)
        s = self.w.settings
        if err is not None:
            if manual:
                QMessageBox.warning(self.w, "Check for updates", str(err))
            return
        if not release.is_newer:
            if manual:
                QMessageBox.information(self.w, "Check for updates",
                                        f"You have the latest version ({__version__}).")
            else:
                self.w.statusBar().showMessage(f"{APP_NAME} is up to date ({__version__}).", 4000)
            return
        if not manual and s.skipped_version == release.version:
            return
        dlg = UpdateDialog(release, updater.install_mode(), self.w)
        dlg.exec()
        if dlg.choice == UpdateDialog.SKIP:
            s.skipped_version = release.version
        elif dlg.choice == UpdateDialog.INSTALL:
            self.install(release)

    # ------------------------------------------------------------------ installing
    def install(self, release: ReleaseInfo) -> None:
        if not self.w.ask_save_before("Update"):
            return
        prog = QProgressDialog(f"Downloading {release.installer.name}...", "Cancel", 0, 100, self.w)
        prog.setWindowTitle("Updating")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        cancelled = {"flag": False}
        prog.canceled.connect(lambda: cancelled.__setitem__("flag", True))
        worker = _Worker()
        self._workers.append(worker)
        worker.progress.connect(lambda d, t: prog.setValue(int(d * 100 / t)) if t else None)

        def progress(done, total):
            worker.progress.emit(done, total)
            return not cancelled["flag"]

        def finished(res, err):
            self._workers.remove(worker)
            prog.close()
            if err is not None:
                if not cancelled["flag"]:
                    QMessageBox.critical(self.w, "Update", str(err))
                return
            setup, sig = res
            who = f"signed by {sig.subject}" if sig.valid else "not code-signed"
            if QMessageBox.question(self.w, "Update",
                                    f"{setup.name} downloaded and its checksum verified ({who}).\n\nInstall it now? "
                                    f"{APP_NAME} will close and restart.") != QMessageBox.StandardButton.Yes:
                return
            try:
                updater.launch_installer(Path(setup))
            except UpdateError as exc:
                QMessageBox.critical(self.w, "Update", str(exc))
                return
            self.w.quit_for_update()

        worker.done.connect(finished)
        worker.run(updater.prepare_update, release, progress)
