"""HTML pages for the scenario description and side briefings.

CMO shows these with ``[LOADDOC]file.html[/LOADDOC]`` from the scenario folder,
exactly like the official scenarios. The stylesheet below is the studio's own
dark theme (the game's own stylesheet is not redistributed).
"""

from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..model.project import Project, Side, Variant

CSS_FILE = "briefing_style_dark.css"

BRIEFING_CSS = """body{
\tfont-family: Calibri, Arial, sans-serif;
\tfont-size: 16px;
\tbackground-color: #383838;
\tcolor: whitesmoke;
}

a { color: #8ab4f8; }

img {
\tdisplay: block;
\tmargin-left: auto;
\tmargin-right: auto;
\tmax-width: 100%;
}

h1 { margin: 0px; font-size: 22px; }
h2 { margin: 0px; font-size: 20px; }
h3 { margin: 0px; font-size: 16px; font-weight: 600; text-decoration: underline; }
h4 { margin: 0px; margin-bottom: 0.2em; }
h5 { margin: 0px; margin-left: 1em; }
p  { margin: 0px; margin-bottom: 1em; }
ul, ol { margin: 0px; margin-bottom: 1em; }
table { border-collapse: collapse; margin-bottom: 1em; }
td, th { border: 1px solid #666; padding: 2px 6px; }
"""


def crlf(text: str) -> str:
    """CMO's own pages use Windows line endings."""
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def page(title: str, body: str) -> str:
    """A complete page around ``body`` (HTML fragment)."""
    body = "\n".join(("\t\t" + line) if line.strip() else "" for line in body.strip("\n").split("\n"))
    text = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n\t<head>\n\t\t<meta charset=\"UTF-8\">\n"
        f"\t\t<title>{html.escape(title)}</title>\n"
        f"\t\t<link rel=\"stylesheet\" type=\"text/css\" href=\"{CSS_FILE}\">\n"
        "\t</head>\n\t<body>\n" + body + "\n\t</body>\n</html>\n"
    )
    return crlf(text)


def _date_text(project: "Project") -> str:
    dt = project.clock.start_dt()
    day = dt.day
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{dt.strftime('%B')} {day}{suffix} {dt.year}"


def description_header(project: "Project", variant: "Variant | None" = None) -> str:
    m = project.meta
    lines = ["<BR>"]
    first = []
    if m.author:
        first.append(f"<B>Scenario By:</B> {html.escape(m.author)}")
    if m.inspired_by:
        first.append(f"<B>Inspired By:</B> {m.inspired_by}")
    if first:
        lines.append("<P>" + " <BR>\n".join(first) + "</P>")
    playable = playable_sides(project, variant)
    info = [f"<B>Date:</B> {_date_text(project)}"]
    if m.location:
        info.append(f"<B>Location:</B> {html.escape(m.location)}")
    if len(playable) == 1:
        others = [s.name for s in project.sides if s.name not in playable and not s.computer_only]
        note = f" ({', '.join(others)} {'is' if len(others) == 1 else 'are'} computer-controlled)" if others else ""
        info.append(f"<B>Playable Side:</B> {html.escape(playable[0])}{html.escape(note)}")
    elif playable:
        info.append(f"<B>Playable Sides:</B> {html.escape(', '.join(playable))}")
    info.append(f"<B>Duration:</B> {project.clock.duration_text()}")
    info.append(f"<B>Complexity:</B> {_stars(m.complexity)} &nbsp; <B>Difficulty:</B> {_stars(m.difficulty)}")
    lines.append("<P>" + " <BR>\n".join(info) + "</P>")
    if m.hypothetical_note:
        lines.append(f"<P>{m.hypothetical_note}</P>")
    return "\n".join(lines)


def _stars(n: int) -> str:
    n = max(1, min(5, int(n or 1)))
    return "&#9733;" * n + "&#9734;" * (5 - n)


def playable_sides(project: "Project", variant: "Variant | None" = None) -> list[str]:
    ai = {s.id for s in project.sides if s.computer_only}
    if variant:
        ai |= set(variant.computer_sides)
    return [s.name for s in project.sides if s.id not in ai]


def description_page(project: "Project", variant: "Variant | None" = None) -> str:
    m = project.meta
    body = m.description_html.strip()
    if variant and variant.description_html.strip():
        body = body + "\n\n" + variant.description_html.strip()
    if m.auto_header:
        body = description_header(project, variant) + "\n\n" + body
    title = m.title + (variant.scen_suffix if variant else "")
    return page(title, body)


def briefing_page(project: "Project", side: "Side") -> str:
    return page(f"{project.meta.title} - {side.name} Briefing", side.briefing_html)


# ------------------------------------------------------------------ OOB helper
_TYPE_HEADINGS = {"Aircraft": "Air", "Ship": "Surface", "Submarine": "Submarine",
                  "Facility": "Ground / Facilities", "GroundUnit": "Ground"}


def _clean_class(name: str) -> str:
    """'MPK Steregushchiy [Pr.20380]' -> 'MPK Steregushchiy [Pr.20380]'; strip trailing '#n' copies."""
    return re.sub(r"\s+#\d+$", "", name or "").strip()


def oob_html(project: "Project", side_id: str, skip_infrastructure: bool = True) -> str:
    """An order-of-battle list (h4 per category, bullet per class) for a briefing."""
    groups: dict[str, Counter] = defaultdict(Counter)
    for u in project.units:
        if u.side != side_id:
            continue
        cls = _clean_class(u.db_name or u.name)
        if skip_infrastructure and u.type == "Facility" and re.search(r"airfield|air base|runway|heliport|port|"
                                                                      r"pier|building|hangar", cls, re.I):
            continue
        groups[_TYPE_HEADINGS.get(u.type, u.type)][cls] += max(1, u.count)
    out = []
    for heading in ("Air", "Surface", "Submarine", "Ground", "Ground / Facilities"):
        if heading not in groups:
            continue
        out.append(f"<h4>{heading}</h4>\n<ul>")
        for cls, n in sorted(groups[heading].items()):
            out.append(f"\t<li>{html.escape(cls)}{f' (x{n})' if n > 1 else ''}</li>")
        out.append("</ul>")
    return "\n".join(out)
