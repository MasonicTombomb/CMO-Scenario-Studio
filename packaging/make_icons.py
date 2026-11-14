"""Render src/cmo_studio/resources/icon.svg to icon.png (window icon) and packaging/icon.ico (exe icon)."""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "src" / "cmo_studio" / "resources" / "icon.svg"


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(SVG)).render(p)
    p.end()
    return img


def main() -> int:
    QGuiApplication(sys.argv[:1])
    render(256).save(str(SVG.with_name("icon.png")))
    # Qt's ICO writer stores one image per file, so write the largest; Windows scales it down.
    ico = ROOT / "packaging" / "icon.ico"
    if not render(256).save(str(ico), "ICO"):
        print("ICO writer unavailable", file=sys.stderr)
        return 1
    print("wrote", SVG.with_name("icon.png"), ico)
    return 0


if __name__ == "__main__":
    sys.exit(main())
