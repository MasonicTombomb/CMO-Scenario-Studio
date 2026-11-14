"""Application entry point."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmo-studio", description="CMO Scenario Studio")
    parser.add_argument("project", nargs="?", help="a .cmoproj file to open")
    parser.add_argument("--cmo", help="CMO install folder (overrides the saved setting)")
    parser.add_argument("--export", metavar="DIR", help="export the project to DIR without opening the window")
    parser.add_argument("--dry-run", action="store_true", help="dry-run the build in CMO's Lua and print the report")
    if sys.stdout is None and any(a in (argv or sys.argv) for a in ("-h", "--help", "--export", "--dry-run")):
        _attach_console()
    args = parser.parse_args(argv)

    if args.export or args.dry_run:
        _attach_console()
        return _headless(args)

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from . import APP_NAME, ORG_NAME
    from .settings import AppSettings
    from .ui.main_window import MainWindow
    from .ui.theme import apply_dark_theme

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    from .paths import resource
    icon = resource("icon.png")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    if sys.platform == "win32":   # own taskbar group and icon instead of python.exe's
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CMOScenarioStudio.App")
        except (AttributeError, OSError):
            pass
    apply_dark_theme(app)
    _install_error_handler(AppSettings.data_dir())
    settings = AppSettings()
    if args.cmo:
        settings.cmo_dir = args.cmo
    win = MainWindow(settings)
    win.show()
    if args.project:
        win.open_project(args.project)
    return app.exec()


def _attach_console() -> None:
    """The packaged .exe is a windowed app; borrow the calling console so --export/--dry-run can print."""
    if sys.platform != "win32" or (sys.stdout is not None and sys.stdout.isatty()):
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):   # ATTACH_PARENT_PROCESS
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            sys.stderr = sys.stdout
            print()
    except (AttributeError, OSError):
        pass
    if sys.stdout is None:   # no console at all: discard output rather than crash on print()
        import os
        sys.stdout = sys.stderr = open(os.devnull, "w")


def _install_error_handler(log_dir) -> None:
    """Log unhandled exceptions and show them, instead of PyQt6's default of aborting the app."""
    import datetime
    import traceback

    log = log_dir / "error.log"

    def hook(etype, value, tb):
        text = "".join(traceback.format_exception(etype, value, tb))
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now().isoformat(timespec='seconds')}\n{text}")
        except OSError:
            pass
        if sys.stderr is not None:
            sys.stderr.write(text)
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is not None:
                box = QMessageBox(QMessageBox.Icon.Critical, "Unexpected error",
                                  f"{etype.__name__}: {value}\n\nThe studio is still running; save your work. "
                                  f"Details were written to:\n{log}")
                box.setDetailedText(text)
                box.exec()
        except Exception:  # noqa: BLE001 - never let the handler itself fail
            pass

    sys.excepthook = hook


def _headless(args) -> int:
    from .export import Exporter
    from .model.project import Project
    from .model.validation import ERROR, validate
    from .settings import detect_cmo_dir

    if not args.project:
        print("A project file is required.", file=sys.stderr)
        return 2
    p = Project.load(args.project)
    issues = validate(p)
    for i in issues:
        if i.level != "info":
            print(i)
    if args.dry_run:
        from .tools.lua_engine import dry_run_build, find_lua_dll
        cmo = args.cmo or detect_cmo_dir()
        dll = find_lua_dll(cmo)
        if not dll:
            print("lua54.dll not found - pass --cmo <CMO folder>", file=sys.stderr)
            return 2
        res = dry_run_build(p, dll)
        print(res.output)
        if not res.ok:
            return 1
    if args.export:
        res = Exporter(p).write(args.export, clean=True)
        print(f"Wrote {len(res.written)} file(s) to {res.root}")
    return 1 if any(i.level == ERROR for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
