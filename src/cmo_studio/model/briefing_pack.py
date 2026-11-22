"""Briefing packs: a flight schedule, and a NATO-style operation order with an intelligence summary, for one side.

Everything is generated from the scenario: forces, bases, missions, courses (timings, times on target, signals),
weather and the forecast, doctrine. The side's :class:`~.project.Orders` text replaces or adds to the generated
paragraphs. The layout follows the five-paragraph operation order (Situation, Mission, Execution, Service Support,
Command and Signal) with annexes, and every page carries an EXERCISE banner: these are game documents.

Pure Python: :func:`opord_html` returns a complete HTML page; ``export.pdf`` prints it to PDF.
"""

from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .course_plan import CoursePlan, hms, plan_course
from .enums import HOST_TYPES
from .project import Orders, Project, Unit

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
DEFAULT_BANNER = "EXERCISE EXERCISE EXERCISE - UNCLASSIFIED - FICTIONAL SCENARIO"

#: doctrinal wording for the studio's mission classes
MISSION_TERMS = {
    ("patrol", "aaw"): "defensive counter-air (DCA) combat air patrol",
    ("patrol", "asw"): "anti-submarine warfare (ASW) patrol",
    ("patrol", "naval"): "maritime (anti-surface) patrol",
    ("patrol", "land"): "armed reconnaissance over land",
    ("patrol", "mixed"): "mixed patrol",
    ("patrol", "sead"): "suppression of enemy air defences (SEAD)",
    ("intercept", ""): "quick reaction alert (QRA) / ground alert intercept",
    ("strike", "air"): "offensive counter-air (OCA) sweep",
    ("strike", "land"): "air interdiction / strike",
    ("strike", "sea"): "anti-surface warfare (ASuW) strike",
    ("strike", "sub"): "anti-submarine strike",
    ("support", ""): "support (AEW, air-to-air refuelling, ISR orbit)",
    ("ferry", ""): "ferry / redeployment",
    ("mining", ""): "offensive mining",
    ("mineclearing", ""): "mine countermeasures",
    ("cargo", ""): "logistic movement",
}

_AIR_DEFENCE = re.compile(r"\bSAM\b|S-\d{2,3}|Patriot|NASAMS|Buk|\bTor\b|Pantsir|HQ-9|Sky Sabre|Rapier|SA-\d+|"
                          r"Air Defen[cs]e|IRIS-T|CAMM|Aster|SAMP/T|Hawk", re.I)
_HQ = re.compile(r"\bHQ\b|Headquarters|Command|Northwood|High Wycombe|Main Building|C2|C3", re.I)
_RADAR = re.compile(r"Radar|Remote Radar Head|\bRRH\b|Fylingdales|Early Warning", re.I)


def dtg(epoch: int) -> str:
    """NATO date-time group, e.g. 120400Z MAY 30."""
    d = datetime.fromtimestamp(epoch, timezone.utc)
    return f"{d.day:02d}{d.hour:02d}{d.minute:02d}Z {MONTHS[d.month - 1]} {d.year % 100:02d}"


def _e(text) -> str:
    return html.escape(str(text or ""))


def _paras(text: str) -> str:
    """Designer text: kept as HTML if it looks like HTML, else paragraphs from blank lines."""
    text = (text or "").strip()
    if not text:
        return ""
    if re.search(r"<(p|ul|ol|table|br|b|i)\b", text, re.I):
        return text
    return "".join(f"<p>{_e(par).replace(chr(10), '<br>')}</p>" for par in re.split(r"\n\s*\n", text))


def _side_end(p: Project) -> int:
    c = p.clock
    return p.clock.start_epoch() + 60 * (c.duration_days * 1440 + c.duration_hours * 60 + c.duration_minutes)


def _rel(p: Project, epoch: int) -> str:
    return f"H+{hms(epoch - p.clock.start_epoch())}"


def _kind_of(u: Unit) -> str:
    name = f"{u.name} {u.db_name}"
    if u.type == "Aircraft":
        return "Air"
    if u.type in ("Ship",):
        return "Maritime"
    if u.type == "Submarine":
        return "Sub-surface"
    if _AIR_DEFENCE.search(name):
        return "Air defence"
    if _RADAR.search(name):
        return "Surveillance"
    if _HQ.search(name):
        return "Command"
    if u.type == "GroundUnit":
        return "Land"
    return "Installations"


def enemies_of(p: Project, sid: str) -> list[str]:
    s = p.side(sid)
    return [o for o, posture in (s.postures.items() if s else []) if posture in ("H", "U") and p.side(o)]


def friends_of(p: Project, sid: str) -> list[str]:
    s = p.side(sid)
    return [o for o, posture in (s.postures.items() if s else []) if posture == "F" and p.side(o)]


# ================================================================== flight schedule
@dataclass
class Flight:
    unit: Unit
    plan: CoursePlan
    callsign: str
    airframe: str
    count: int
    base: str
    depart: int                     # epoch
    tots: list[tuple[str, int, int]] = field(default_factory=list)   # (waypoint, target epoch, seconds late)
    recovery: str = ""
    end: int = 0
    signals: list[str] = field(default_factory=list)
    route: str = ""


def flight_schedule(p: Project, sid: str, db=None) -> list[Flight]:
    """Every unit of the side with a course, in departure order: an air tasking / movement table."""
    start = p.clock.start_epoch()
    out = []
    for u in p.units:
        if u.side != sid:
            continue
        plan = plan_course(p, u, db)
        if plan is None:
            continue
        legs = plan.route_legs
        rec = plan.finish
        if rec.startswith("Lands at "):
            rec = rec[len("Lands at "):]
        elif u.course.finish == "rtb":
            rec = plan.origin if plan.hosted else "Nearest suitable base"
        elif u.course.finish == "repeat":
            rec = "Repeats the route"
        else:
            rec = "-"
        out.append(Flight(
            unit=u, plan=plan, callsign=u.name, airframe=u.db_name or u.type, count=max(1, u.count),
            base=plan.origin if plan.hosted else f"Under way ({u.type.lower()})",
            depart=start + plan.depart_s,
            tots=[(lg.label, start + lg.target_s, lg.diff_s) for lg in legs if lg.target_s is not None],
            recovery=rec, end=start + plan.end_s, signals=[lg.signal for lg in legs if lg.signal],
            route=" - ".join(lg.label for lg in legs)))
    out.sort(key=lambda f: (f.depart, f.callsign))
    return out


def flight_schedule_html(p: Project, sid: str, db=None, title: bool = False) -> str:
    """The schedule as an HTML table (for a CMO briefing, or Annex B of the operation order)."""
    flights = flight_schedule(p, sid, db)
    if not flights:
        return "<p>No units of this side have a plotted course.</p>"
    rows = []
    for f in flights:
        tot = "<br>".join(f"{_e(name)} {dtg(t)[2:6]}Z ({_rel(p, t)})" + (" LATE" if late > 120 else "")
                          for name, t, late in f.tots) or "-"
        dep = "In the air at H-hour" if f.depart <= p.clock.start_epoch() and not f.plan.hosted else \
            f"{dtg(f.depart)[2:6]}Z ({_rel(p, f.depart)})"
        rows.append(f"<tr><td><b>{_e(f.callsign)}</b></td><td>{f.count} x {_e(f.airframe)}</td><td>{_e(f.base)}</td>"
                    f"<td>{dep}</td><td>{_e(f.route)}</td><td>{tot}</td><td>{_e(f.recovery)}</td>"
                    f"<td>{dtg(f.end)[2:6]}Z ({_rel(p, f.end)})</td><td>{_e(', '.join(f.signals)) or '-'}</td></tr>")
    head = "<h3>Flight schedule</h3>\n" if title else ""
    return (head + '<table class="schedule"><tr><th>Callsign / unit</th><th>No. x type</th><th>Departs from</th>'
            "<th>Off</th><th>Route</th><th>Time on target</th><th>Recovers to</th><th>Ends</th><th>Codewords</th>"
            "</tr>\n" + "\n".join(rows) + "</table>\n"
            "<p><small>Times are Zulu, planned from the courses (estimates). H-hour is the scenario start.</small></p>")


# ================================================================== forces
def _location(p: Project, u: Unit, exact: bool) -> str:
    host = p.unit(u.host) if u.host else None
    if host is not None:
        return f"at {host.name}" if exact else f"based at {(host.group or host.name)}"
    if exact:
        return f"{u.lat:.2f}N {u.lon:.2f}E".replace("-", "") if u.lat >= 0 and u.lon >= 0 else \
            f"{abs(u.lat):.2f}{'N' if u.lat >= 0 else 'S'} {abs(u.lon):.2f}{'E' if u.lon >= 0 else 'W'}"
    zone = next((z for z in p.zones if len(z.points) >= 3 and _inside(u.lat, u.lon, z.points)), None)
    if zone is not None:
        return f"in the {zone.name} area"
    return f"vicinity {abs(round(u.lat, 0)):.0f}{'N' if u.lat >= 0 else 'S'} " \
           f"{abs(round(u.lon, 0)):.0f}{'E' if u.lon >= 0 else 'W'}"


def _inside(lat: float, lon: float, pts) -> bool:
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        yi, xi = pts[i]
        yj, xj = pts[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def orbat_rows(p: Project, sid: str, exact: bool) -> list[tuple[str, str, int, str]]:
    """(category, equipment, number, where) for a side; sites made of many parts are summed by equipment."""
    groups: dict[tuple[str, str, str], int] = defaultdict(int)
    for u in p.units:
        if u.side != sid or u.reserve:
            continue
        kind = _kind_of(u)
        if kind == "Installations" and u.type == "Facility" and not (u.type in HOST_TYPES and
                                                                     any(x.host == u.id for x in p.units)):
            continue      # runways, taps and sheds are not order of battle
        groups[(kind, u.db_name or u.name, _location(p, u, exact))] += max(1, u.count)
    order = ("Air", "Maritime", "Sub-surface", "Air defence", "Surveillance", "Command", "Land", "Installations")
    return sorted(((k, e, n, w) for (k, e, w), n in groups.items()),
                  key=lambda r: (order.index(r[0]) if r[0] in order else 99, r[1], r[3]))


def _orbat_table(rows) -> str:
    if not rows:
        return "<p>No forces identified.</p>"
    body = "".join(f"<tr><td>{_e(k)}</td><td>{_e(e)}</td><td class='n'>{n}</td><td>{_e(w)}</td></tr>"
                   for k, e, n, w in rows)
    return ("<table><tr><th>Category</th><th>Equipment</th><th>No.</th><th>Location</th></tr>" + body + "</table>")


def _summary_counts(p: Project, sid: str) -> str:
    c = Counter(_kind_of(u) for u in p.units if u.side == sid and not u.reserve for _ in range(max(1, u.count)))
    bits = [f"{n} {k.lower()}" for k, n in c.items() if k != "Installations"]
    return ", ".join(bits) if bits else "no forces"


# ================================================================== weather
def _rain(r: int) -> str:
    return "dry" if r <= 0 else "light rain" if r < 10 else "moderate rain" if r < 25 else "heavy rain"


def _cloud(c: float) -> str:
    okta = round(c * 8)
    return "clear (SKC)" if okta == 0 else f"{okta}/8 cloud" + (" (overcast)" if okta == 8 else "")


SEA = ("calm (glassy)", "calm (rippled)", "smooth", "slight", "moderate", "rough", "very rough", "high",
       "very high", "phenomenal")


def weather_html(p: Project) -> str:
    w = p.weather
    start = p.clock.start_epoch()
    rows = [(dtg(start), "H-hour", w.temperature, w.rainfall, w.cloud, w.sea_state)]
    for e in sorted((e for e in p.forecast if e.offset_minutes > 0), key=lambda e: e.offset_minutes):
        t = start + 60 * e.offset_minutes
        rows.append((dtg(t), _rel(p, t), e.temperature, e.rainfall, e.cloud, e.sea_state))
    body = "".join(f"<tr><td>{d}</td><td>{r}</td><td class='n'>{t:g} &deg;C</td><td>{_rain(rn)}</td>"
                   f"<td>{_cloud(c)}</td><td>{s} - {SEA[max(0, min(9, int(s)))]}</td></tr>"
                   for d, r, t, rn, c, s in rows)
    return ("<table><tr><th>DTG</th><th>Time</th><th>Temp</th><th>Precipitation</th><th>Cloud</th><th>Sea state</th>"
            "</tr>" + body + "</table>")


# ================================================================== the operation order
CSS = """
@page { size: A4; margin: 22mm 18mm 20mm 18mm;
  @top-center { content: "%(banner)s"; font: bold 9pt Arial, sans-serif; color: #b00000; }
  @bottom-center { content: "%(banner)s"; font: bold 9pt Arial, sans-serif; color: #b00000; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt Arial, sans-serif; } }
body { font: 10.5pt "Times New Roman", Times, serif; color: #000; line-height: 1.35; }
h1 { font: bold 15pt Arial, sans-serif; text-align: center; margin: 2mm 0 1mm; }
h2 { font: bold 11.5pt Arial, sans-serif; margin: 6mm 0 2mm; text-transform: uppercase; border-bottom: 1px solid #000; }
h3 { font: bold 10.5pt Arial, sans-serif; margin: 4mm 0 1.5mm; }
.banner { text-align: center; font: bold 10pt Arial, sans-serif; color: #b00000; border: 2px solid #b00000;
          padding: 1.5mm; margin-bottom: 4mm; }
.meta { width: 100%%; border-collapse: collapse; margin: 2mm 0 4mm; }
.meta td { padding: 0.5mm 2mm; vertical-align: top; border: none; }
.meta td:first-child { width: 32%%; font-weight: bold; }
table { width: 100%%; border-collapse: collapse; margin: 2mm 0 3mm; font-size: 9pt; page-break-inside: auto; }
th { background: #e6e6e6; text-align: left; }
th, td { border: 0.6pt solid #555; padding: 1mm 1.5mm; vertical-align: top; }
td.n { text-align: right; white-space: nowrap; }
.annex { page-break-before: always; }
.auto { color: #555; font-style: italic; font-size: 9pt; }
p { margin: 1.5mm 0; }
ol.para { padding-left: 6mm; } ol.para > li { margin: 1.5mm 0; }
small { font-size: 8pt; }
"""


@dataclass
class Section:
    title: str
    body: str


def _missions_of(p: Project, sid: str):
    return [m for m in p.missions if m.side == sid]


def _term(m) -> str:
    return MISSION_TERMS.get((m.mclass, m.subtype or ""), MISSION_TERMS.get((m.mclass, ""), m.mclass))


def default_mission(p: Project, sid: str) -> str:
    side = p.side_name(sid)
    terms = list(dict.fromkeys(_term(m) for m in _missions_of(p, sid)))
    start, end = p.clock.start_epoch(), _side_end(p)
    where = p.meta.location or p.meta.setting or "the area of operations"
    tasks = (", ".join(terms[:-1]) + (" and " if len(terms) > 1 else "") + terms[-1]) if terms else \
        "operations as directed in paragraph 3"
    return (f"{side} forces conduct {tasks} in {where} from {dtg(start)} to {dtg(end)} in order to retain control of "
            f"the area and defeat hostile forces that enter it.")


def default_intent(p: Project, sid: str) -> str:
    enemies = ", ".join(p.side_name(e) for e in enemies_of(p, sid)) or "hostile forces"
    return (f"<p><b>Purpose.</b> To deny {_e(enemies)} freedom of action in {_e(p.meta.location or p.meta.setting or 'the area')}."
            f"</p><p><b>Method.</b> Hold defensive patrols over key areas, keep reserves ready to react, and strike "
            f"only when the enemy commits.</p><p><b>End state.</b> Our forces intact and in control of the area at "
            f"{dtg(_side_end(p))}, with enemy forces destroyed or withdrawn.</p>")


def _roe(p: Project, sid: str) -> str:
    d = p.side(sid).doctrine if p.side(sid) else {}
    names = (("weapon_control_status_air", "Air"), ("weapon_control_status_surface", "Surface"),
             ("weapon_control_status_subsurface", "Sub-surface"), ("weapon_control_status_land", "Land"))
    meaning = {"Free": "Weapons FREE: engage any target not positively identified as friendly",
               "Tight": "Weapons TIGHT: engage only targets positively identified as hostile",
               "Hold": "Weapons HOLD: fire only in self-defence or when ordered"}
    rows = "".join(f"<tr><td>{n}</td><td>{_e(meaning.get(d.get(k, ''), 'As set by higher command (default)'))}</td></tr>"
                   for k, n in names)
    extra = ""
    if d.get("ignore_plotted_course") == "yes":
        extra = "<p>Units may leave their planned route to engage targets of opportunity.</p>"
    elif d.get("ignore_plotted_course") == "no":
        extra = "<p>Units are to remain on their planned route unless attacked.</p>"
    return ("<table><tr><th>Domain</th><th>Weapon control status</th></tr>" + rows + "</table>" + extra +
            "<p>Leg-by-leg changes to weapon control and emissions for individual flights are in Annex B.</p>")


def _codewords(p: Project, sid: str) -> list[tuple[str, str]]:
    out = []
    for u in p.units:
        if u.side == sid and u.course:
            for i, w in enumerate(u.course.waypoints, 1):
                if w.signal:
                    out.append((w.signal, f"{u.name} has reached {w.name or f'waypoint {i}'}"))
    for e in p.events:
        for c in e.conditions:
            if c.type == "FlagSet" and c.params.get("Key"):
                out.append((c.params["Key"], f"triggers '{e.name}'"))
        for a in e.actions:
            if a.type == "SetFlag" and a.params.get("Key"):
                out.append((a.params["Key"], f"set by '{e.name}'"))
    seen: dict[str, list[str]] = defaultdict(list)
    for k, v in out:
        if v not in seen[k]:
            seen[k].append(v)
    return [(k, "; ".join(v)) for k, v in seen.items()]


def _bases(p: Project, sid: str) -> list[tuple[str, int]]:
    c: Counter = Counter()
    for u in p.units:
        if u.side == sid and u.host and u.type == "Aircraft":
            host = p.unit(u.host)
            if host is not None:
                c[host.group or host.name] += max(1, u.count)
    return c.most_common()


def opord_sections(p: Project, sid: str, db=None) -> tuple[list[Section], list[Section]]:
    """The five paragraphs and the annexes, as HTML bodies."""
    o: Orders = p.side(sid).orders
    side = p.side_name(sid)
    start, end = p.clock.start_epoch(), _side_end(p)
    enemy_ids, friend_ids = enemies_of(p, sid), friends_of(p, sid)
    auto = "<p class='auto'>Generated from the scenario.</p>"

    # 1 SITUATION
    enemy = "".join(f"<p><b>{_e(p.side_name(e))}:</b> {_summary_counts(p, e)} assessed in the area. See Annex A.</p>"
                    for e in enemy_ids) or "<p>No hostile forces are expected.</p>"
    friendly = f"<p><b>{_e(side)}:</b> {_summary_counts(p, sid)}.</p>" + "".join(
        f"<p><b>{_e(p.side_name(f))} (friendly):</b> {_summary_counts(p, f)}.</p>" for f in friend_ids)
    w = p.weather
    sit = (_paras(o.situation) +
           f"<h3>a. Enemy forces</h3>{enemy}" + (_paras(o.enemy_assessment) if o.enemy_assessment else "") +
           f"<h3>b. Friendly forces</h3>{friendly}"
           f"<h3>c. Environment</h3><p>Area: {_e(p.meta.location or p.meta.setting or 'see map')}. Weather at H-hour: "
           f"{w.temperature:g} &deg;C, {_rain(w.rainfall)}, {_cloud(w.cloud)}, sea state {w.sea_state} "
           f"({SEA[max(0, min(9, int(w.sea_state)))]})" + (". Changes are forecast: see Annex C.</p>" if p.forecast else
                                                          ". No significant change forecast.</p>"))
    # 2 MISSION
    mission = f"<p><b>{_e(o.mission)}</b></p>" if o.mission.strip() else \
        f"<p><b>{_e(default_mission(p, sid))}</b></p>{auto}"
    # 3 EXECUTION
    intent = _paras(o.intent) or default_intent(p, sid) + auto
    concept = _paras(o.concept) or (
        "<p>Operations are conducted in the phases set by the timings below: forces deploy to their patrol areas from "
        "H-hour, flights launch to the air tasking in Annex B, and reserves are held at readiness to react to "
        "enemy action.</p>" + auto)
    tasks = []
    for m in _missions_of(p, sid):
        units = [p.unit(i) for i in m.units if p.unit(i)]
        if m.mclass == "intercept":
            from .intercept import describe
            tasks.append(f"<li><b>{_e(m.name)}</b> - {_e(_term(m))}. Forces: "
                         f"{_e(', '.join(f'{u.name} ({max(1, u.count)})' for u in units) or 'none assigned')}. "
                         f"{_e(describe(p, m))}</li>")
            continue
        area = p.zone(m.zone).name if m.zone and p.zone(m.zone) else "as directed"
        when = ""
        if m.options.get("starttime") or m.options.get("endtime"):
            when = f" Time: {_e(m.options.get('starttime') or 'H-hour')} to {_e(m.options.get('endtime') or 'end')}."
        active = "" if m.options.get("isactive", True) is not False else " On order (not active at H-hour)."
        tasks.append(f"<li><b>{_e(m.name)}</b> - {_e(_term(m))}. Area: {_e(area)}. Forces: "
                     f"{_e(', '.join(f'{u.name} ({max(1, u.count)})' for u in units) or 'none assigned')}.{when}"
                     f"{active}</li>")
    flights = flight_schedule(p, sid, db)
    if flights:
        tasks.append(f"<li><b>Routed flights and movements</b> - {len(flights)} unit(s) fly or sail planned routes: "
                     "see Annex B.</li>")
    tots = [(f.callsign, n, t, late) for f in flights for n, t, late in f.tots]
    coord = (f"<p><b>Timings.</b> H-hour is {dtg(start)}. The operation ends at {dtg(end)} ({_rel(p, end)}). All times "
             "are Zulu.</p>")
    if tots:
        coord += "<p><b>Times on target.</b></p><ul>" + "".join(
            f"<li>{_e(c)} at {_e(n)}: {dtg(t)} ({_rel(p, t)})" + (" - <b>currently planned late</b>" if late > 120 else "")
            + "</li>" for c, n, t, late in tots) + "</ul>"
    coord += f"<p><b>Rules of engagement.</b></p>{_roe(p, sid)}" + _paras(o.roe)
    radar_on = sum(1 for u in p.units if u.side == sid and u.radar_active)
    coord += (f"<p><b>Emission control.</b> {radar_on} unit(s) start with radars active; all others are silent until "
              "ordered or until their route says otherwise (Annex B).</p>")
    execution = (f"<h3>a. Commander's intent</h3>{intent}<h3>b. Concept of operations</h3>{concept}"
                 f"<h3>c. Tasks</h3>" + (f"<ol type='1'>{''.join(tasks)}</ol>" if tasks else
                                         "<p>No missions are tasked yet.</p>") +
                 f"<h3>d. Coordinating instructions</h3>{coord}")
    # 4 SERVICE SUPPORT
    bases = _bases(p, sid)
    support = ("<p><b>Bases.</b></p><ul>" + "".join(f"<li>{_e(b)}: {n} aircraft</li>" for b, n in bases) + "</ul>"
               if bases else "<p>No aircraft are based ashore or afloat.</p>")
    short = [f for f in flights if f.plan.range_nm is not None and f.plan.fuel_nm > f.plan.range_nm]
    if short:
        support += "<p><b>Fuel.</b> The following routes exceed the estimated range and need air-to-air refuelling " \
                   "or a shorter route:</p><ul>" + "".join(
                       f"<li>{_e(f.callsign)}: about {f.plan.fuel_nm:,.0f} nm planned, about {f.plan.range_nm:,.0f} nm "
                       "available</li>" for f in short) + "</ul>"
    support += _paras(o.sustainment)
    # 5 COMMAND AND SIGNAL
    hqs = [u.name for u in p.units if u.side == sid and _HQ.search(f"{u.name} {u.db_name}")]
    command = _paras(o.command) or (
        f"<p><b>Command.</b> {_e(o.originator or f'{side} joint force commander')}." +
        (f" Headquarters: {_e(', '.join(hqs[:6]))}." if hqs else "") + "</p>")
    words = _codewords(p, sid)
    signal = ("<p><b>Codewords.</b></p><table><tr><th>Codeword</th><th>Meaning</th></tr>" +
              "".join(f"<tr><td><b>{_e(k)}</b></td><td>{_e(v)}</td></tr>" for k, v in words) + "</table>"
              if words else "<p><b>Codewords.</b> None allocated.</p>")
    paragraphs = [Section("1. Situation", sit), Section("2. Mission", mission), Section("3. Execution", execution),
                  Section("4. Service support", support), Section("5. Command and signal", command + signal)]

    # ANNEX A - INTSUM
    exact = o.exact_positions
    intsum = (f"<p>Period covered: up to {dtg(start)}. Source: scenario intelligence. Positions are "
              f"{'exact' if exact else 'approximate (nearest named area or whole degree)'}.</p>")
    intsum += "<h3>1. General situation</h3>" + (_paras(o.enemy_assessment) or (
        "<p>" + _e(", ".join(p.side_name(e) for e in enemy_ids) or "No hostile side") +
        " forces are deployed in and around the area of operations and are assessed as capable of contesting it "
        "from H-hour.</p>" + auto))
    for e in enemy_ids:
        rows = orbat_rows(p, e, exact)
        intsum += f"<h3>2. {_e(p.side_name(e))} order of battle</h3>{_orbat_table(rows)}"
        ad = [r for r in rows if r[0] == "Air defence"]
        intsum += "<h3>3. Air defence threat</h3>" + (
            "<ul>" + "".join(f"<li>{_e(eq)} ({n}) {_e(wh)}</li>" for _k, eq, n, wh in ad) + "</ul>"
            "<p>Plan routes to stay outside their engagement zones or to suppress them first.</p>"
            if ad else "<p>No surface-to-air threat identified.</p>")
    intsum += "<h3>4. Enemy courses of action</h3>"
    intsum += "<p><b>Most likely (MLCOA).</b></p>" + (_paras(o.mlcoa) or (
        "<p>The enemy holds defensive patrols over its own bases and reacts to our incursions with fighters and "
        "surface-to-air systems.</p>" + auto))
    intsum += "<p><b>Most dangerous (MDCOA).</b></p>" + (_paras(o.mdcoa) or (
        "<p>The enemy mounts a coordinated strike on our bases and high-value assets early in the operation, before "
        "our patrols are established.</p>" + auto))
    aware = p.side(sid).awareness if p.side(sid) else "Normal"
    intsum += ("<h3>5. Intelligence gaps</h3><p>" + {
        "Blind": "Our picture is very limited: expect surprise. Enemy units must be found before they can be engaged.",
        "Normal": "Enemy units must be detected and identified by our sensors before they are engaged.",
    }.get(aware, "Our picture of enemy forces is good (enhanced awareness).") + "</p>")
    annexes = [Section("Annex A - Intelligence summary (INTSUM)", intsum),
               Section("Annex B - Air tasking and movement schedule", flight_schedule_html(p, sid, db) + (
                   _leg_details(p, flights))),
               Section("Annex C - Meteorology (METOC)", weather_html(p))]
    return paragraphs, annexes


def _leg_details(p: Project, flights: list[Flight]) -> str:
    """Per-flight leg orders: altitude/speed, emissions, weapons, waits."""
    out = []
    for f in flights:
        rows = []
        for lg in f.plan.route_legs:
            alt = f"{lg.alt:,.0f} m" if lg.alt is not None and f.plan.air else (
                f"{lg.depth:,.0f} m deep" if lg.depth is not None and f.plan.sub else "-")
            emis = ", ".join(x for x in (
                "radar ON" if lg.radar else "radar OFF" if lg.radar is False else "",
                "jammers ON" if lg.ecm else "", "sonar ACTIVE" if lg.sonar else "") if x) or "-"
            rows.append(f"<tr><td>{lg.n}</td><td>{_e(lg.label)}</td><td>{alt}</td><td class='n'>{lg.speed:,.0f} kn</td>"
                        f"<td>{emis}</td><td>{_e((lg.weapons or 'doctrine').upper())}</td>"
                        f"<td>{(str(lg.wait) + ' min') if lg.wait else '-'}</td>"
                        f"<td>{dtg(p.clock.start_epoch() + lg.t1)[2:6]}Z</td></tr>")
        out.append(f"<h3>{_e(f.callsign)} - leg orders</h3><table><tr><th>WP</th><th>Name</th><th>Alt / depth</th>"
                   "<th>Speed</th><th>Emissions</th><th>Weapons</th><th>Hold</th><th>ETA</th></tr>" + "".join(rows) +
                   "</table>")
    return "".join(out)


def opord_html(p: Project, sid: str, db=None, number: int = 1) -> str:
    """The complete operation order for a side, as one printable HTML page."""
    side = p.side(sid)
    o = side.orders
    banner = (o.classification or DEFAULT_BANNER).replace('"', "'")
    start = p.clock.start_epoch()
    issued = start - 6 * 3600
    op = o.operation or f"OPERATION {p.meta.title.upper()}"
    paragraphs, annexes = opord_sections(p, sid, db)
    head = (f"<div class='banner'>{_e(banner)}</div>"
            f"<h1>OPERATION ORDER {number:02d}/{datetime.fromtimestamp(start, timezone.utc).year % 100:02d}</h1>"
            f"<h1>{_e(op)}</h1>"
            "<table class='meta'>"
            f"<tr><td>Copy</td><td>1 of 1</td></tr>"
            f"<tr><td>Issuing headquarters</td><td>{_e(o.originator or f'{side.name} Joint Force Headquarters')}</td></tr>"
            f"<tr><td>Date-time group</td><td>{dtg(issued)}</td></tr>"
            f"<tr><td>Reference</td><td>{_e(p.meta.title)} scenario; map of {_e(p.meta.location or p.meta.setting or 'the area')}</td></tr>"
            f"<tr><td>Time zone used throughout</td><td>ZULU</td></tr>"
            f"<tr><td>Task organisation</td><td>{_e(_summary_counts(p, sid))}</td></tr>"
            "</table>")
    body = head + "".join(f"<h2>{_e(s.title)}</h2>{s.body}" for s in paragraphs)
    body += (f"<p style='margin-top:8mm'><b>ACKNOWLEDGE.</b></p><p>{_e(o.originator or side.name + ' Commander')}</p>"
             f"<p><b>Annexes:</b> A - Intelligence summary. B - Air tasking and movement schedule. C - Meteorology.</p>")
    body += "".join(f"<div class='annex'><div class='banner'>{_e(banner)}</div><h2>{_e(s.title)}</h2>{s.body}</div>"
                    for s in annexes)
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{_e(op)} - {_e(side.name)}</title><style>{CSS % {'banner': banner}}</style></head>"
            f"<body>{body}</body></html>")


def cmo_briefing_html(p: Project, sid: str, db=None) -> str:
    """A shorter version for CMO's in-game side briefing (no page styling): situation, mission, tasks, schedule."""
    paragraphs, annexes = opord_sections(p, sid, db)
    keep = [s for s in paragraphs if s.title[0] in "123"]
    return ("".join(f"<h1>{_e(s.title)}</h1>{s.body}" for s in keep) +
            f"<h1>Air tasking and movements</h1>{annexes[1].body}")


__all__ = ["dtg", "flight_schedule", "flight_schedule_html", "opord_html", "cmo_briefing_html", "orbat_rows",
           "enemies_of", "DEFAULT_BANNER"]
