"""Formation templates and geometry.

A formation is a lead unit plus ordered members. A *preset* names a base generator
and its default parameters; the generator returns member offsets in *spacing units*
(x to the right of the formation heading, y ahead of it, plus an altitude offset).
Offsets are scaled by the spacing, rotated by the heading and turned into
lat/lon positions and CMO formation stations (bearing + distance from the lead).

In CMO the stations are set with ``ScenEdit_SetUnit({guid=, formation={bearing=, distance=}})``
after the units are grouped (``unit.group = 'Name'``), as the official scenarios do.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..geo import destination

NM_PER = {"nm": 1.0, "km": 1 / 1.852, "m": 1 / 1852.0}

# =============================================================================== parameter specs
# key -> (label, kind, default, minimum, maximum)   kind: float | int | choice:a|b | bool | stations
ParamSpec = tuple[str, str, Any, float, float]

COMMON_HELP = {
    "spacing": "Distance between neighbouring stations (the formation's unit length).",
    "heading": "Direction the formation faces (true bearing, degrees).",
}


@dataclass(frozen=True)
class Base:
    label: str
    params: dict[str, ParamSpec]
    fn: Callable[[int, dict], list[tuple[float, float, float]]]


# =============================================================================== generators
def _side_seq(i: int) -> tuple[int, int]:
    """0 -> (1, +1), 1 -> (1, -1), 2 -> (2, +1)...: alternate right/left, stepping outwards."""
    return i // 2 + 1, (1 if i % 2 == 0 else -1)


def g_column(n, p):
    stagger = float(p.get("stagger", 0.0))
    return [((stagger if i % 2 == 0 else -stagger) if stagger else 0.0, -(i + 1), 0.0) for i in range(n)]


def g_abreast(n, p):
    side = p.get("side", "both")
    ahead = float(p.get("ahead", 0.0))
    out = []
    for i in range(n):
        if side == "right":
            x = i + 1
        elif side == "left":
            x = -(i + 1)
        else:
            k, s = _side_seq(i)
            x = k * s
        out.append((float(x), ahead, 0.0))
    return out


def g_echelon(n, p):
    a = math.radians(float(p.get("angle", 45)))
    s = 1 if p.get("side", "right") == "right" else -1
    return [(s * (i + 1) * math.sin(a), -(i + 1) * math.cos(a), 0.0) for i in range(n)]


def g_wedge(n, p):
    a = math.radians(float(p.get("angle", 45)))
    fwd = 1 if p.get("inverted") else -1
    out = []
    for i in range(n):
        k, s = _side_seq(i)
        out.append((s * k * math.sin(a), fwd * k * math.cos(a), 0.0))
    return out


def g_diamond(n, p):
    out: list[tuple[float, float, float]] = []
    layer = 1
    while len(out) < n:
        # diamond |x| + |y| = layer around the lead, starting astern then left/right, then the rest
        ring = []
        for k in range(4 * layer):
            t = k / (4 * layer) * 4
            q, f = int(t), t - int(t)
            corners = [(0, -layer), (-layer, 0), (0, layer), (layer, 0)]
            (x0, y0), (x1, y1) = corners[q], corners[(q + 1) % 4]
            ring.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
        # order: astern, right, left, ahead, then the in-between points
        key = {(0, -layer): 0, (layer, 0): 1, (-layer, 0): 2, (0, layer): 3}
        ring.sort(key=lambda pt: key.get((round(pt[0], 6), round(pt[1], 6)), 4))
        out += [(x, y, 0.0) for x, y in ring]
        layer += 1
    return out[:n]


def g_grid(n, p):
    cols = max(1, int(p.get("columns", 2)))
    row = float(p.get("row_factor", 1.0))
    lead = p.get("lead", "front centre")
    cells = []
    total = n + 1
    rows = math.ceil(total / cols)
    for r in range(rows):
        for c in range(cols):
            if len(cells) < total:
                cells.append((c - (cols - 1) / 2, -r * row))
    if lead == "centre":
        cx = 0.0
        cy = -(rows - 1) * row / 2
        cells.sort(key=lambda pt: (pt[0] - cx) ** 2 + (pt[1] - cy) ** 2)
    elif lead == "front left":
        cells.sort(key=lambda pt: (-pt[1], pt[0]))
    else:   # front centre
        cells.sort(key=lambda pt: (-pt[1], abs(pt[0]), pt[0]))
    lx, ly = cells[0]
    return [(x - lx, y - ly, 0.0) for x, y in cells[1:]]


def g_ring(n, p):
    radius = float(p.get("radius", 1.0))
    arc = float(p.get("arc", 360.0))
    start = float(p.get("start", 0.0))
    if n <= 0:
        return []
    if arc >= 359.9:
        angles = [start + 360.0 * i / n for i in range(n)]
    elif n == 1:
        angles = [start]
    else:
        angles = [start - arc / 2 + arc * i / (n - 1) for i in range(n)]
    return [(radius * math.sin(math.radians(a)), radius * math.cos(math.radians(a)), 0.0) for a in angles]


def g_double_ring(n, p):
    inner = min(n, max(0, int(p.get("inner", 3))))
    r1, r2 = float(p.get("radius", 1.0)), float(p.get("outer_radius", 2.5))
    start = float(p.get("start", 0.0))
    return (g_ring(inner, {"radius": r1, "start": start + 180.0 / max(inner, 1)}) +
            g_ring(n - inner, {"radius": r2, "start": start}))


def g_finger(n, p):
    # fingertip: lead, #2 left-aft, #3 right-aft, #4 further right-aft; further elements follow astern
    elem = [(-1.0, -1.0), (1.0, -1.0), (2.0, -2.0)]
    out = []
    for i in range(n):
        e, k = divmod(i + 1, 4)
        if k == 0:
            out.append((0.0, -3.0 * e, 0.0))      # next element lead
        else:
            x, y = elem[k - 1]
            out.append((x, y - 3.0 * e, 0.0))
    return out


def g_scatter(n, p):
    radius = float(p.get("radius", 2.0))
    min_sep = float(p.get("min_separation", 0.5))
    rnd = random.Random(int(p.get("seed", 1)))
    pts: list[tuple[float, float]] = [(0.0, 0.0)]
    out = []
    for _ in range(n):
        best = None
        for _try in range(200):
            r = radius * math.sqrt(rnd.random())
            a = rnd.random() * 2 * math.pi
            cand = (r * math.sin(a), r * math.cos(a))
            if all(math.hypot(cand[0] - q[0], cand[1] - q[1]) >= min_sep for q in pts):
                best = cand
                break
            best = cand
        pts.append(best)
        out.append((best[0], best[1], 0.0))
    return out


def g_custom(n, p):
    """Stations as [[relative bearing, distance in spacing units], ...]; missing ones go astern."""
    st = p.get("stations") or []
    out = []
    for i in range(n):
        if i < len(st) and len(st[i]) >= 2:
            b, d = float(st[i][0]), float(st[i][1])
        else:
            b, d = 180.0, float(i + 1)
        out.append((d * math.sin(math.radians(b)), d * math.cos(math.radians(b)), 0.0))
    return out


F, I, B, S = "float", "int", "bool", "stations"
SIDE3 = "choice:both|right|left"
BASES: dict[str, Base] = {
    "column": Base("Column", {"stagger": ("Stagger (sideways, spacing units)", F, 0.0, 0.0, 5.0)}, g_column),
    "abreast": Base("Line abreast", {"side": ("Lead position", SIDE3, "both", 0, 0),
                                     "ahead": ("Line ahead of lead (spacing units)", F, 0.0, -50, 50)}, g_abreast),
    "echelon": Base("Echelon", {"side": ("Side", "choice:right|left", "right", 0, 0),
                                "angle": ("Angle from astern (deg)", F, 45.0, 0, 90)}, g_echelon),
    "wedge": Base("Wedge / Vee", {"angle": ("Angle from astern (deg)", F, 45.0, 0, 90),
                                  "inverted": ("Inverted (wings ahead)", B, False, 0, 0)}, g_wedge),
    "diamond": Base("Diamond", {}, g_diamond),
    "grid": Base("Grid / box", {"columns": ("Columns", I, 2, 1, 20),
                                "row_factor": ("Row spacing (x spacing)", F, 1.0, 0.1, 10),
                                "lead": ("Lead position", "choice:front centre|front left|centre",
                                         "front centre", 0, 0)}, g_grid),
    "ring": Base("Ring / arc", {"radius": ("Radius (spacing units)", F, 1.0, 0.1, 50),
                                "arc": ("Arc (deg, 360 = full ring)", F, 360.0, 10, 360),
                                "start": ("Centre of arc / first station (relative deg)", F, 0.0, -180, 360)},
                g_ring),
    "double_ring": Base("Double ring", {"inner": ("Units on inner ring", I, 3, 0, 50),
                                        "radius": ("Inner radius (spacing units)", F, 1.0, 0.1, 50),
                                        "outer_radius": ("Outer radius (spacing units)", F, 2.5, 0.1, 100),
                                        "start": ("Rotation (relative deg)", F, 0.0, -180, 360)}, g_double_ring),
    "finger": Base("Finger four", {}, g_finger),
    "scatter": Base("Random dispersal", {"radius": ("Radius (spacing units)", F, 2.0, 0.1, 100),
                                         "min_separation": ("Minimum separation (spacing units)", F, 0.5, 0, 10),
                                         "seed": ("Random seed", I, 1, 0, 99999)}, g_scatter),
    "custom": Base("Custom stations", {"stations": ("Stations", S, [], 0, 0)}, g_custom),
}


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    domain: str             # Naval / Air / Ground / Any
    base: str
    spacing_nm: float
    params: dict
    help: str
    alt_step_m: float = 0.0


def _p(key, label, domain, base, spacing_nm, help_, alt=0.0, **params):
    return Preset(key, label, domain, base, spacing_nm, params, help_, alt)


PRESETS_LIST: list[Preset] = [
    # ---------------------------------------------------------------- naval
    _p("line_ahead", "Line ahead (column)", "Naval", "column", 1.0,
       "Ships follow in the lead's wake. Simple transit and narrow-channel formation."),
    _p("line_abreast", "Line abreast", "Naval", "abreast", 2.0,
       "Ships side by side across the track; good search width (minesweeping, surface search)."),
    _p("echelon_right", "Echelon right", "Naval", "echelon", 1.0, "Diagonal line astern and to starboard.",
       side="right", angle=45.0),
    _p("echelon_left", "Echelon left", "Naval", "echelon", 1.0, "Diagonal line astern and to port.",
       side="left", angle=45.0),
    _p("wedge", "Wedge (Vee)", "Naval", "wedge", 1.5, "Arrowhead with the lead at the point.", angle=45.0),
    _p("inverted_wedge", "Inverted wedge (U)", "Naval", "wedge", 1.5, "Wings ahead of the lead.", angle=45.0,
       inverted=True),
    _p("diamond", "Diamond", "Naval", "diamond", 2.0, "Escorts ahead, astern and on both beams of the lead."),
    _p("box", "Box (2 columns)", "Naval", "grid", 1.5, "Two columns in line ahead.", columns=2, row_factor=1.0),
    _p("convoy", "Convoy (columns)", "Naval", "grid", 0.5,
       "Merchant ships in columns with the commodore in the front centre; wider between columns than ships.",
       columns=4, row_factor=0.6),
    _p("circular_screen", "Circular screen", "Naval", "ring", 4.0,
       "Escorts evenly spaced on a ring around a high-value unit (carrier, amphibious ship).", radius=1.0),
    _p("double_screen", "Carrier group (inner + outer screen)", "Naval", "double_ring", 3.0,
       "Close-in AAW escorts on an inner ring and ASW/picket ships on an outer ring.", inner=2, radius=1.0,
       outer_radius=3.0),
    _p("asw_arc_screen", "ASW bent-line screen", "Naval", "ring", 4.0,
       "Escorts on an arc ahead of the main body, across the likely submarine threat axis.", radius=1.0,
       arc=120.0, start=0.0),
    _p("picket_line", "Picket line ahead", "Naval", "abreast", 10.0,
       "Radar pickets in a line well ahead of the main body.", ahead=2.0),
    _p("amphibious_lanes", "Amphibious assault lanes", "Naval", "grid", 0.5,
       "Landing craft in assault lanes abreast, waves behind.", columns=5, row_factor=1.0),
    _p("minesweep_echelon", "Mine-sweeping echelon", "Naval", "echelon", 0.3,
       "Sweepers stepped so each one covers the next one's sweep.", side="right", angle=60.0),
    # ---------------------------------------------------------------- air
    _p("finger_four", "Finger four (fingertip)", "Air", "finger", 0.5,
       "Classic four-ship: wingman left-aft, element lead right-aft, number four further right-aft."),
    _p("vic", "Vic (3-ship V)", "Air", "wedge", 0.3, "Three-ship V with the lead at the point.", angle=50.0),
    _p("air_trail", "Trail", "Air", "column", 1.0, "Aircraft in line astern (in-trail)."),
    _p("ladder", "Ladder (stepped trail)", "Air", "column", 1.0,
       "Trail with each aircraft stepped up in altitude.", alt=300.0),
    _p("combat_spread", "Combat spread", "Air", "abreast", 1.0,
       "Two (or more) aircraft line abreast, wide enough to check each other's six.", side="right"),
    _p("wall", "Wall", "Air", "abreast", 3.0, "Fighters line abreast across the threat axis (BVR wall)."),
    _p("air_box", "Box", "Air", "grid", 1.0, "Two pairs, one behind the other.", columns=2, row_factor=1.0,
       lead="front left"),
    _p("air_wedge", "Wedge", "Air", "wedge", 1.0, "Lead at the point, wingmen stepped back on both sides.",
       angle=60.0),
    _p("air_echelon", "Echelon right (air)", "Air", "echelon", 0.3, "Diagonal line to the right.",
       side="right", angle=60.0),
    _p("bomber_stream", "Bomber stream", "Air", "grid", 2.0, "Waves of bombers in a long stream.", columns=3,
       row_factor=2.0, alt=150.0),
    _p("tanker_cell", "Tanker cell", "Air", "echelon", 1.0, "Tankers stepped in echelon, slightly stacked.",
       side="right", angle=30.0, alt=-150.0),
    # ---------------------------------------------------------------- ground
    _p("road_column", "Road march column", "Ground", "column", 0.054, "Vehicles nose to tail along a road (~100 m)."),
    _p("staggered_column", "Staggered column", "Ground", "column", 0.054,
       "Column with vehicles alternating to each side of the road.", stagger=0.4),
    _p("herringbone", "Herringbone (halt)", "Ground", "column", 0.054,
       "Halted column with vehicles pulled off to alternate sides for all-round security.", stagger=0.8),
    _p("ground_line", "Line", "Ground", "abreast", 0.11, "Vehicles abreast for maximum firepower forward."),
    _p("ground_wedge", "Wedge", "Ground", "wedge", 0.11, "All-round security, firepower to the front and flanks.",
       angle=50.0),
    _p("ground_vee", "Vee", "Ground", "wedge", 0.11, "Two elements forward, one back.", angle=50.0, inverted=True),
    _p("ground_echelon", "Echelon right (ground)", "Ground", "echelon", 0.11, "Protects the right flank.",
       side="right", angle=45.0),
    _p("ground_box", "Box / square", "Ground", "grid", 0.11, "Two elements up, two back.", columns=2,
       row_factor=1.0, lead="front left"),
    _p("ground_diamond", "Diamond (ground)", "Ground", "diamond", 0.11, "One forward, two flanks, one rear."),
    _p("coil", "Coil / laager", "Ground", "ring", 0.11, "Vehicles in a circle facing outwards (halted).",
       radius=1.0),
    _p("sam_dispersal", "SAM battery dispersal", "Ground", "ring", 0.27,
       "Launchers spread on a ring around the radar/command post (~500 m).", radius=1.0),
    _p("dispersal", "Random dispersal", "Ground", "scatter", 0.27,
       "Units spread randomly within a radius, with a minimum separation.", radius=3.0, min_separation=0.6, seed=1),
    _p("defensive_perimeter", "Defensive perimeter (two rings)", "Ground", "double_ring", 0.2,
       "Inner ring of key units with an outer ring of security positions.", inner=3, radius=1.0, outer_radius=2.5),
    # ---------------------------------------------------------------- any
    _p("custom", "Custom stations", "Any", "custom", 1.0,
       "Type each member's relative bearing and distance (in spacing units).", stations=[]),
]
PRESETS: dict[str, Preset] = {p.key: p for p in PRESETS_LIST}
DOMAINS = ("Naval", "Air", "Ground", "Any")


def preset(key: str) -> Preset:
    return PRESETS.get(key) or PRESETS["line_ahead"]


def effective_params(f) -> dict:
    """Preset defaults overlaid with the formation's own parameters."""
    pre = preset(f.preset)
    base = BASES[pre.base]
    out = {k: spec[2] for k, spec in base.params.items()}
    out.update(pre.params)
    out.update(f.params or {})
    return out


# =============================================================================== geometry
@dataclass
class Station:
    unit_id: str
    rel_bearing: float      # relative to the formation heading, degrees 0-360
    true_bearing: float     # 0-360
    distance_nm: float
    lat: float
    lon: float
    alt_offset_m: float


def offsets(f, n: Optional[int] = None) -> list[tuple[float, float, float]]:
    """Member offsets in nm (x right, y ahead of the heading) plus altitude offsets in metres."""
    n = len(f.members) if n is None else n
    pre = preset(f.preset)
    params = effective_params(f)
    raw = BASES[pre.base].fn(n, params)
    out = []
    alt_step = f.alt_step_m if f.alt_step_m is not None else pre.alt_step_m
    rnd = random.Random(int(f.seed))
    for i, (x, y, dz) in enumerate(raw):
        if f.mirror:
            x = -x
        if f.jitter:
            x += rnd.uniform(-f.jitter, f.jitter)
            y += rnd.uniform(-f.jitter, f.jitter)
        out.append((x * f.spacing_nm, y * f.spacing_nm, dz + alt_step * (i + 1)))
    return out


def stations(f, lead_lat: float, lead_lon: float, n: Optional[int] = None) -> list[Station]:
    ids = list(f.members) if n is None else [""] * n
    out = []
    for uid, (x, y, dz) in zip(ids, offsets(f, len(ids))):
        dist = math.hypot(x, y)
        rel = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0 if dist > 1e-9 else 0.0
        true = (rel + f.heading) % 360.0
        lat, lon = destination(lead_lat, lead_lon, true, dist * 1.852)
        out.append(Station(uid, round(rel, 2), round(true, 2), round(dist, 4), lat, lon, dz))
    return out


def apply_formation(project, f) -> int:
    """Move every member to its station (and set headings / altitude steps). Returns units moved."""
    lead = project.unit(f.lead)
    if lead is None or lead.host:
        return 0
    moved = 0
    if f.set_heading:
        lead.heading = float(f.heading)
    for st in stations(f, lead.lat, lead.lon):
        u = project.unit(st.unit_id)
        if u is None or u.host or u.id == lead.id:
            continue
        u.lat, u.lon = round(st.lat, 6), round(st.lon, 6)
        if f.set_heading:
            u.heading = float(f.heading)
        if u.type == "Aircraft" and (lead.altitude is not None or st.alt_offset_m):
            base = lead.altitude if lead.altitude is not None else 9000.0
            u.altitude = round(max(30.0, base + st.alt_offset_m), 1)
        moved += 1
    return moved


def move_with_formation(project, uid: str, lat: float, lon: float) -> bool:
    """Move a unit; if it is in a formation kept on station, move the whole formation with it.

    Returns True if a formation was moved.
    """
    u = project.unit(uid)
    if u is None:
        return False
    f = formation_of(project, uid)
    if f is None or not f.keep_on_station or project.unit(f.lead) is None:
        u.lat, u.lon = lat, lon
        return False
    lead = project.unit(f.lead)
    lead.lat += lat - u.lat
    lead.lon += lon - u.lon
    apply_formation(project, f)
    return True


def formation_of(project, uid: str):
    """The formation a unit leads or belongs to, if any."""
    return next((f for f in project.formations if f.lead == uid or uid in f.members), None)
