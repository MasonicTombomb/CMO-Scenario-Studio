"""Print an HTML page to PDF.

Uses Microsoft Edge (part of every Windows 10/11 install) or Google Chrome in headless mode, which honours print CSS
(page size, margins, the running EXERCISE banners and page numbers). Without either, Qt prints a plainer version.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

BROWSERS = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")


def find_browser() -> Optional[str]:
    for c in (os.environ.get("CHROME", ""), shutil.which("msedge") or "", shutil.which("chrome") or "", *BROWSERS):
        if c and Path(c).is_file():
            return c
    return None


def html_to_pdf(page_html: str, out: str | Path, timeout: int = 120) -> str:
    """Write ``out``; returns how ('browser' or 'qt'). Raises RuntimeError if nothing could print it."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    if browser:
        with tempfile.TemporaryDirectory(prefix="cmo_studio_pdf_") as tmp:
            src = Path(tmp) / "page.html"
            src.write_text(page_html, encoding="utf-8")
            cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                   f"--user-data-dir={Path(tmp) / 'profile'}", "--no-pdf-header-footer",
                   "--allow-file-access-from-files", f"--print-to-pdf={out}", src.as_uri()]
            try:
                subprocess.run(cmd, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.TimeoutExpired):
                pass
        if out.is_file() and out.stat().st_size > 1000:
            return "browser"
    return _qt_pdf(page_html, out)


def _qt_pdf(page_html: str, out: Path) -> str:
    try:
        from PyQt6.QtCore import QMarginsF
        from PyQt6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument
    except ImportError as exc:     # pragma: no cover - the app always has Qt
        raise RuntimeError("No browser or Qt available to print the PDF") from exc
    w = QPdfWriter(str(out))
    w.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    w.setPageMargins(QMarginsF(18, 20, 18, 20), QPageLayout.Unit.Millimeter)
    doc = QTextDocument()
    doc.setHtml(page_html)
    doc.print(w)
    if not out.is_file():
        raise RuntimeError(f"Could not write {out}")
    return "qt"
