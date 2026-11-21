"""Build the PDF manuals from Markdown (maintainer tool).

    python tools/make_manuals.py            all manuals
    python tools/make_manuals.py user       just the User Manual

Sources: docs/manual/<manual>/NN-*.md, joined in name order (Markdown with tables, fenced code,
'!!! tip "Title"' call-out boxes and images); the Reference Manual also uses the reference docs in docs/.
Output:  docs/manuals/CMO-Scenario-Studio-<Name>.pdf

Markdown -> HTML (python-markdown) with a print stylesheet -> PDF with headless Chrome or Edge, which handles the
A4 pages, running footer with page numbers, clickable contents and PDF bookmarks. Needs: pip install markdown, and
Chrome or Edge (set CHROME to the executable if it is somewhere unusual).
"""

from __future__ import annotations

import datetime
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cmo_studio import APP_NAME, __version__  # noqa: E402

SRC = ROOT / "docs" / "manual"
OUT = ROOT / "docs" / "manuals"

MANUALS = {
    "user": ("user", "User Manual", "CMO-Scenario-Studio-User-Manual.pdf",
             "Everything you need to build, test and play your own Command: Modern Operations scenarios - "
             "step by step, from installing the studio to sharing a finished scenario."),
    # the reference mixes its own chapters with the reference docs in docs/ (one source for both)
    "reference": (["reference/00-about.md", "reference/01-files-cli.md", "../PROJECT_FORMAT.md",
                   "../EXPORT_FORMAT.md", "reference/04-events-lua.md", "reference/05-formation-layouts.md",
                   "../TEMPLATES.md", "../AREAS.md", "../CALLSIGNS.md", "../DATABASE.md",
                   "reference/10-importing.md", "../RELEASING.md"],
                  "Reference Manual", "CMO-Scenario-Studio-Reference-Manual.pdf",
                  "Libraries, file formats, the exported Lua and the studio runtime API, events in depth, the "
                  "database and the command line - for advanced users, modders and contributors."),
}

CSS = r"""
@page {
  size: A4;
  margin: 20mm 17mm 20mm 17mm;
  @bottom-left { content: "%(app)s - %(manual)s"; font: 8pt 'Segoe UI', sans-serif; color: #7a8594; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt 'Segoe UI', sans-serif;
                  color: #7a8594; }
  @top-right { content: "Version %(version)s"; font: 8pt 'Segoe UI', sans-serif; color: #a0a8b4; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; }
               @top-right { content: none; } }
* { box-sizing: border-box; }
html { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 10.2pt; color: #1d2633;
       line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; }
h1, h2, h3, h4 { font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif; color: #10233f; line-height: 1.25;
                 break-after: avoid; }
h1 { font-size: 22pt; margin: 0 0 6mm; padding-bottom: 3mm; border-bottom: 2.5pt solid #2f6fd0;
     break-before: page; }
h1 .chapter { display: block; font-size: 10pt; letter-spacing: 2pt; color: #2f6fd0; text-transform: uppercase;
              margin-bottom: 1mm; }
h2 { font-size: 14.5pt; margin: 7mm 0 2.5mm; color: #183b6e; }
h3 { font-size: 11.8pt; margin: 5mm 0 2mm; color: #1f4f91; }
h4 { font-size: 10.5pt; margin: 4mm 0 1.5mm; }
p { margin: 0 0 2.6mm; orphans: 3; widows: 3; }
a { color: #1f5fbf; text-decoration: none; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin: 0 0 1.2mm; }
li > p { margin: 0 0 1mm; }
strong { color: #0d1b30; }
code { font-family: 'Cascadia Mono', Consolas, monospace; font-size: 8.8pt; background: #eef2f8;
       border: 0.5pt solid #d6deea; border-radius: 2pt; padding: 0 1.2pt; }
pre { background: #0f1722; color: #e6edf6; border-radius: 4pt; padding: 3mm 4mm; font-size: 8.4pt;
      line-height: 1.45; white-space: pre-wrap; word-break: break-word; break-inside: avoid; margin: 0 0 3.5mm; }
pre code { background: none; border: 0; color: inherit; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%%; margin: 1mm 0 4mm; font-size: 9pt; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #1f3f6e; color: #fff; text-align: left; font-weight: 600; padding: 1.6mm 2.2mm; }
td { border-bottom: 0.5pt solid #d5dce6; padding: 1.5mm 2.2mm; vertical-align: top; }
tr:nth-child(even) td { background: #f5f8fc; }
img { max-width: 100%%; display: block; margin: 2mm auto 1mm; border: 0.6pt solid #b9c3d1; border-radius: 3pt; }
figure { margin: 2mm 0 5mm; break-inside: avoid; }
figcaption { text-align: center; font-size: 8.6pt; color: #5b6676; font-style: italic; margin-top: 1mm; }
.admonition { border-radius: 4pt; padding: 2.5mm 4mm 1.2mm; margin: 2mm 0 4mm; break-inside: avoid;
              border-left: 4pt solid; }
.admonition-title { font-weight: 700; margin-bottom: 1mm; }
.admonition.tip { background: #eaf6ee; border-color: #2e9e5b; }
.admonition.tip .admonition-title { color: #1e7a44; }
.admonition.note { background: #eaf1fb; border-color: #2f6fd0; }
.admonition.note .admonition-title { color: #1f4f91; }
.admonition.warning { background: #fdf3e4; border-color: #e08a00; }
.admonition.warning .admonition-title { color: #a35f00; }
.admonition.danger { background: #fdecec; border-color: #d33a3a; }
.admonition.danger .admonition-title { color: #a52222; }
.admonition.example { background: #f3eefb; border-color: #7b4fc9; }
.admonition.example .admonition-title { color: #5b34a0; }
kbd { font-family: 'Segoe UI', sans-serif; font-size: 8.5pt; background: #fff; border: 0.7pt solid #9aa6b6;
      border-bottom-width: 1.6pt; border-radius: 2.5pt; padding: 0 1.6mm; white-space: nowrap; }
.cover { height: 297mm; width: 210mm; position: relative; background: linear-gradient(160deg, #0d1a2e 0%%,
         #16335c 55%%, #1f4f91 100%%); color: #fff; padding: 40mm 22mm 0; break-after: page; }
.cover img { border: 0; width: 34mm; margin: 0 0 12mm; }
.cover .kicker { font-size: 11pt; letter-spacing: 3pt; text-transform: uppercase; color: #9cc2ff; }
.cover .title { font-size: 34pt; font-weight: 700; line-height: 1.1; margin: 3mm 0 4mm; color: #fff; }
.cover .subtitle { font-size: 13pt; color: #d7e5fb; max-width: 150mm; line-height: 1.45; }
.cover .meta { position: absolute; bottom: 24mm; left: 22mm; right: 22mm; font-size: 9.5pt; color: #b8cbe8;
               border-top: 0.8pt solid #4a6ea8; padding-top: 4mm; }
.toc-page { break-after: page; }
.toc-page h1 { break-before: avoid; }
.toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc > ul > li { margin: 2.4mm 0 0.6mm; font-weight: 600; font-size: 10.5pt; }
.toc > ul > li > ul { margin: 0.8mm 0 1.5mm 6mm; columns: 2; column-gap: 8mm; }
.toc > ul > li > ul > li { font-weight: 400; font-size: 9pt; margin: 0 0 0.6mm; break-inside: avoid; }
.toc ul ul ul { display: none; }
.toc a { color: #1d2633; }
"""


def _admonitions_and_figures(md_text: str, base: Path) -> str:
    """Turn '![caption](img.png)' alone on a line into a figure with a caption, and resolve image paths."""
    def fig(m):
        alt, src = m.group(1), m.group(2)
        p = (base / src).resolve()
        uri = p.as_uri() if p.exists() else src
        cap = f"<figcaption>{html.escape(alt)}</figcaption>" if alt else ""
        return f'\n<figure markdown="1"><img src="{uri}" alt="{html.escape(alt)}">{cap}</figure>\n'
    return re.sub(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", fig, md_text, flags=re.M)


def _keys(text: str) -> str:
    """[[Ctrl+S]] -> <kbd>Ctrl</kbd>+<kbd>S</kbd>."""
    def k(m):
        return "+".join(f"<kbd>{html.escape(p)}</kbd>" for p in m.group(1).split("+"))
    # only key-like text ("Ctrl+Shift+A", "F5", "+"), so JSON such as [[lat, lon]] in code samples is left alone
    return re.sub(r"\[\[([A-Za-z0-9]+(?:\+[A-Za-z0-9]+)*|[+-])\]\]", k, text)


def render_html(key: str) -> str:
    src_name, title, _pdf, blurb = MANUALS[key]
    parts = [SRC / x for x in src_name] if isinstance(src_name, list) else sorted((SRC / src_name).glob("*.md"))
    md_text = "\n\n".join(f.read_text(encoding="utf-8") for f in parts)
    # links between the Markdown docs mean nothing in a PDF: keep their text (source paths stay as code)
    md_text = re.sub(r"\[([^\]]+)\]\((?:\.\./)?src/[^)]+\)", r"\1", md_text)
    md_text = re.sub(r"\[([^\]]+)\]\((?!https?:)[^)]*\.md(?:#[^)]*)?\)", r"\1", md_text)
    md_text = _keys(_admonitions_and_figures(md_text, SRC))
    conv = markdown.Markdown(lazy_ol=False, extensions=["tables", "fenced_code", "toc", "attr_list", "admonition",
                                                        "sane_lists",
                                         "md_in_html", "def_list"],
                             extension_configs={"toc": {"toc_depth": "1-2", "permalink": False}})
    body = conv.convert(md_text)
    # number the chapters
    n = 0

    def chap(m):
        nonlocal n
        attrs = m.group(1)
        if "unnumbered" in attrs:          # '# Title {.unnumbered}': front matter and appendices
            return f'<h1{attrs.replace("unnumbered", "").replace(' class=""', '')}>{m.group(2)}</h1>'
        n += 1
        return f'<h1{attrs}><span class="chapter">Chapter {n}</span>{m.group(2)}</h1>'
    body = re.sub(r"<h1([^>]*)>(.*?)</h1>", chap, body)
    # chapter numbers in the contents too
    numbers = {m.group(1): m.group(2) for m in
               re.finditer(r'<h1[^>]*id="([^"]+)"[^>]*><span class="chapter">Chapter (\d+)</span>', body)}
    toc_html = conv.toc
    for hid, num in numbers.items():
        toc_html = toc_html.replace(f'<a href="#{hid}">', f'<a href="#{hid}">{num}.&nbsp; ', 1)
    conv.toc = toc_html
    icon = ROOT / "src" / "cmo_studio" / "resources" / "icon.png"
    today = datetime.date.today().strftime("%d %B %Y").lstrip("0")
    cover = f"""<section class="cover">
  <img src="{icon.as_uri()}" alt="">
  <div class="kicker">{html.escape(APP_NAME)}</div>
  <div class="title">{html.escape(title)}</div>
  <div class="subtitle">{html.escape(blurb)}</div>
  <div class="meta">Version {__version__} &nbsp;·&nbsp; {today} &nbsp;·&nbsp;
  github.com/MasonicTombomb/CMO-Scenario-Studio &nbsp;·&nbsp; Free software under the MIT License.
  Command: Modern Operations is a trademark of its owners; this is an unofficial community tool.</div>
</section>"""
    toc = f'<section class="toc-page"><h1 id="contents">Contents</h1><div class="toc">{conv.toc}</div></section>'
    css = CSS % {"app": APP_NAME, "manual": title, "version": __version__}
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(APP_NAME)} '
            f'{html.escape(title)}</title><style>{css}</style></head><body>{cover}{toc}{body}</body></html>')


def find_chrome() -> str:
    cands = [os.environ.get("CHROME", ""), shutil.which("chrome") or "", shutil.which("msedge") or "",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    for c in cands:
        if c and Path(c).is_file():
            return c
    raise SystemExit("Chrome or Edge is needed to print the PDFs (set CHROME).")


DIGEST = OUT / "manual-sources.sha256"


def source_files() -> list[Path]:
    """Everything the PDFs are made from: the Markdown sources and the pictures."""
    files: set[Path] = set()
    for src, *_rest in MANUALS.values():
        if isinstance(src, list):
            files.update((SRC / x).resolve() for x in src)
        else:
            files.update(p.resolve() for p in (SRC / src).glob("*.md"))
    files.update(p.resolve() for p in (SRC / "img").glob("*.png"))
    return sorted(files)


def sources_digest() -> str:
    """A fingerprint of the sources and the version (shown on every page). Text is hashed with LF line endings, so
    a checkout that converts them (git autocrlf) gives the same digest."""
    import hashlib
    h = hashlib.sha256(f"version {__version__}\n".encode())
    for f in source_files():
        data = f.read_bytes()
        if f.suffix == ".md":
            data = data.replace(b"\r\n", b"\n")
        h.update(f.relative_to(ROOT).as_posix().encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


def build(key: str) -> Path:
    _src, _title, pdf_name, _blurb = MANUALS[key]
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / pdf_name
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / f"{key}.html"
        page.write_text(render_html(key), encoding="utf-8")
        profile = Path(tmp) / "profile"
        cmd = [find_chrome(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={profile}", "--no-pdf-header-footer", "--generate-pdf-document-outline",
               "--allow-file-access-from-files", "--virtual-time-budget=20000",
               f"--print-to-pdf={out}", page.as_uri()]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if not out.is_file() or out.stat().st_size < 10_000:
            raise SystemExit(f"PDF not produced for {key}:\n{res.stdout}\n{res.stderr}")
    print(f"{out.relative_to(ROOT)}  ({out.stat().st_size / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    keys = sys.argv[1:] or list(MANUALS)
    for k in keys:
        build(k)
    if set(keys) == set(MANUALS):     # both built from the current sources: record it for tools/release_check.py
        DIGEST.write_text(sources_digest() + "\n", encoding="utf-8")
        print(f"{DIGEST.relative_to(ROOT)}  (sources fingerprint)")
