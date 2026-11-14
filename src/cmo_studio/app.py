"""Application entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmo-studio", description="CMO Scenario Studio")
    parser.add_argument("project", nargs="?", help="a .cmoproj file to open")
    parser.add_argument("--cmo", help="CMO install folder (overrides the saved setting)")
    parser.add_argument("--export", metavar="DIR", help="export the project to DIR without opening the window")
    parser.add_argument("--dry-run", action="store_true", help="dry-run the build in CMO's Lua and print the report")
    args = parser.parse_args(argv)

    if args.export or args.dry_run:
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
    icon = Path(__file__).with_name("resources") / "icon.svg"
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    apply_dark_theme(app)
    settings = AppSettings()
    if args.cmo:
        settings.cmo_dir = args.cmo
    win = MainWindow(settings)
    win.show()
    if args.project:
        win.open_project(args.project)
    return app.exec()


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
