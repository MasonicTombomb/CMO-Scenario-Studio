# PyInstaller spec for CMO Scenario Studio (one-folder Windows build).
# Use packaging/build_release.py rather than running this directly; it also writes version_info.txt.
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

HERE = Path(SPECPATH)
ROOT = HERE.parent
SRC = ROOT / "src"
PKG = SRC / "cmo_studio"

datas = [
    (str(PKG / "export" / "lua" / "*.lua"), "cmo_studio/export/lua"),
    (str(PKG / "resources" / "*"), "cmo_studio/resources"),
]

# Qt modules the studio never imports; leaving them out keeps the download small.
excludes = [
    "tkinter", "unittest", "pydoc", "pytest",
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineQuick", "PyQt6.QtWebChannel",
    "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuickWidgets", "PyQt6.Qt3DCore", "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets", "PyQt6.QtBluetooth", "PyQt6.QtNfc", "PyQt6.QtPositioning", "PyQt6.QtSensors",
    "PyQt6.QtSerialPort", "PyQt6.QtSql", "PyQt6.QtDesigner", "PyQt6.QtHelp", "PyQt6.QtPdf", "PyQt6.QtPdfWidgets",
    "PyQt6.QtCharts", "PyQt6.QtDataVisualization", "PyQt6.QtRemoteObjects", "PyQt6.QtSpatialAudio",
    "PyQt6.QtTextToSpeech", "PyQt6.QtWebSockets", "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
]

a = Analysis(
    [str(HERE / "entry.py")],
    pathex=[str(SRC)],
    datas=datas,
    hiddenimports=["PyQt6.QtSvg"],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CMO-Scenario-Studio",
    icon=str(HERE / "icon.ico"),
    version=str(HERE / "version_info.txt"),
    console=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="CMO-Scenario-Studio",
    upx=False,
)
