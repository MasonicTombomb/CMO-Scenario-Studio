"""The scenario project: plain dataclasses that round-trip to JSON (``.cmoproj``).

Everything a scenario needs lives here: metadata, clock and weather, sides and
their relations, units (including aircraft hosted at bases), reference points,
areas, missions, events, special actions, Lua scripts, briefings and build
variants. The exporter turns a :class:`Project` into the CMO folder layout.

Unknown keys in a project file are ignored and missing keys take defaults, so
older and newer files load without migration code for additive changes.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, get_args, get_origin, get_type_hints

FORMAT_ID = "cmo-scenario-studio"
FORMAT_VERSION = 1
PROJECT_SUFFIX = ".cmoproj"


def new_id(prefix: str) -> str:
    """Short random id, unique within a project (``u_1a2b3c4d``)."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def safe_folder_name(text: str) -> str:
    """A folder name CMO and Windows both accept (keeps spaces, as the official scenarios do)."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text or "").strip().rstrip(".")
    return text or "New Scenario"


def safe_prefix(text: str) -> str:
    """CamelCase file prefix for the HTML pages, e.g. 'If Russia Wins' -> 'IfRussiaWins'."""
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    return "".join(w[:1].upper() + w[1:] for w in words) or "Scenario"


# =============================================================================== records
@dataclass
class Meta:
    title: str = "New Scenario"
    folder_name: str = ""          # [CMO]\Lua\<folder> and [CMO]\Scenarios\<folder>; blank = from title
    file_prefix: str = ""          # prefix of the HTML pages; blank = from title
    author: str = ""
    inspired_by: str = ""
    setting: str = ""              # shown in CMO's scenario list
    location: str = ""
    db_file: str = ""              # e.g. DB3K_519.db3
    complexity: int = 3            # 1-5
    difficulty: int = 3            # 1-5
    hypothetical_note: str = ""
    description_html: str = ""     # body of the description page
    auto_header: bool = True       # prepend "Scenario By / Date / Location / Sides / Duration"
    designer_notes: str = ""       # never exported

    def folder(self) -> str:
        return safe_folder_name(self.folder_name or self.title)

    def prefix(self) -> str:
        return safe_prefix(self.file_prefix or self.title)


@dataclass
class Clock:
    start: str = "2030-01-01T06:00:00"   # ISO, UTC (Zulu)
    duration_days: int = 1
    duration_hours: int = 0
    duration_minutes: int = 0

    def start_dt(self) -> datetime:
        try:
            dt = datetime.fromisoformat(self.start.replace("Z", ""))
        except ValueError:
            dt = datetime(2030, 1, 1, 6, 0, 0)
        return dt.replace(tzinfo=timezone.utc)

    def start_epoch(self) -> int:
        return int(self.start_dt().timestamp())

    def duration_text(self) -> str:
        parts = []
        if self.duration_days:
            parts.append(f"{self.duration_days} Day{'s' if self.duration_days != 1 else ''}")
        if self.duration_hours:
            parts.append(f"{self.duration_hours} Hour{'s' if self.duration_hours != 1 else ''}")
        if self.duration_minutes:
            parts.append(f"{self.duration_minutes} Minutes")
        return " ".join(parts) or "Open-ended"


@dataclass
class Weather:
    temperature: float = 15.0     # deg C
    rainfall: int = 0             # 0-50
    cloud: float = 0.0            # 0.0-1.0
    sea_state: int = 2            # 0-9


@dataclass
class WeatherEntry:
    """A weather change that fires at a set offset after the scenario starts."""
    offset_minutes: int = 60      # minutes after scenario start (must be > 0)
    temperature: float = 15.0
    rainfall: int = 0
    cloud: float = 0.0
    sea_state: int = 2


@dataclass
class BuildOptions:
    armed_start: bool = True      # aircraft start with their configured loadout (else reserve)
    default_loadout: int = 3      # DB3000 "(Reserve [Available])"
    verbose: int = 1              # 0 report only, 1 steps, 2 every unit
    force_rebuild: bool = False   # build even if sides already have units
    unlimited_magazines_note: bool = True


@dataclass
class Side:
    id: str = field(default_factory=lambda: new_id("s"))
    name: str = "New Side"
    tag: str = ""                       # short tag used in file names (RU, NATO...)
    color: str = "#4a90d9"
    awareness: str = "Normal"
    proficiency: str = "Regular"
    computer_only: bool = False
    start_score: int = 0
    doctrine: dict[str, str] = field(default_factory=dict)
    postures: dict[str, str] = field(default_factory=dict)   # other side id -> F/N/U/H
    briefing_html: str = ""
    export_briefing: bool = True

    def file_tag(self) -> str:
        return safe_prefix(self.tag or self.name)


@dataclass
class Waypoint:
    """A point on a course. Its settings apply on the leg flown *to* it (waypoint 1: from departure)."""
    lat: float = 0.0
    lon: float = 0.0
    altitude: Optional[float] = None   # metres (aircraft); None = keep the unit's own
    speed: Optional[float] = None      # knots; None = keep the unit's own
    depth: Optional[float] = None      # metres below the surface (submarines); None = keep the unit's own
    name: str = ""
    radar: str = ""                    # see SENSOR_SETTING: '' no change | 'active' | 'passive'
    sonar: str = ""
    ecm: str = ""                      # jammers (OECM)
    weapons: str = ""                  # see WEAPONS_SETTING: '' | 'free' | 'tight' | 'hold'
    engage: str = ""                   # see ENGAGE_SETTING: '' | 'leave' | 'stay'
    wait_minutes: int = 0              # on arrival: circle here this long before going on
    signal: str = ""                   # on arrival: set this flag (key value) so events can react


#: per-leg sensor settings (radar, sonar, jammers)
SENSOR_SETTING: dict[str, str] = {"": "No change", "active": "On (active)", "passive": "Off (passive)"}
#: per-leg weapon control status
WEAPONS_SETTING: dict[str, str] = {"": "No change", "free": "Weapons free", "tight": "Weapons tight",
                                   "hold": "Weapons hold"}
#: per-leg behaviour when a target turns up
ENGAGE_SETTING: dict[str, str] = {"": "No change", "leave": "Leave the course to attack",
                                  "stay": "Stay on the course"}


#: what a unit does at the end of its course
COURSE_FINISH: dict[str, str] = {
    "stop": "Carry on (no further orders)",
    "rtb": "Return to its base",
    "land": "Land at another base",
    "repeat": "Fly the course again (loop)",
}


@dataclass
class Course:
    """A plotted route. Aircraft that start at a base take off at the departure time, fly it, then finish."""
    waypoints: list[Waypoint] = field(default_factory=list)
    depart_minutes: int = 0            # after the scenario start (0 = at the start)
    finish: str = "stop"               # see COURSE_FINISH
    land_at: str = ""                  # unit id of the base to land at ('land')


@dataclass
class Unit:
    id: str = field(default_factory=lambda: new_id("u"))
    side: str = ""                  # side id
    type: str = "Facility"          # see enums.UNIT_TYPES
    dbid: int = 0
    db_name: str = ""               # class name from the DB, for display and validation
    name: str = "New Unit"
    count: int = 1                  # >1 builds '<name> #1..n'
    lat: float = 0.0
    lon: float = 0.0
    altitude: Optional[float] = None   # metres, airborne aircraft
    depth: Optional[float] = None      # metres, submarines
    heading: Optional[float] = None
    speed: Optional[float] = None      # knots
    host: str = ""                  # unit id of the base/ship this unit starts at (aircraft, boats)
    loadout: Optional[int] = None   # aircraft loadout DBID
    radar_active: bool = False
    sonar_active: bool = False
    hold_position: bool = False
    autodetectable: bool = False
    proficiency: str = ""           # blank = side default
    reserve: bool = False           # not built at start; spawned by a 'SpawnUnit' event action
    group: str = ""                 # free tag for organising and filtering
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)  # passed to ScenEdit_SetUnit
    course: Optional[Course] = None    # plotted route (waypoints, departure, what to do at the end)

    def display_name(self) -> str:
        return f"{self.name} (x{self.count})" if self.count > 1 else self.name


@dataclass
class ReferencePoint:
    id: str = field(default_factory=lambda: new_id("rp"))
    side: str = ""
    name: str = "RP"
    lat: float = 0.0
    lon: float = 0.0
    highlighted: bool = False
    all_sides: bool = False         # create a copy on every side (objective markers)


@dataclass
class Zone:
    """A polygon (or route) of reference points: patrol areas, exclusion zones, triggers."""
    id: str = field(default_factory=lambda: new_id("z"))
    side: str = ""
    name: str = "ZONE"              # reference points are exported as NAME-1 .. NAME-n
    points: list[list[float]] = field(default_factory=list)   # [[lat, lon], ...]
    color: str = ""
    all_sides: bool = False
    notes: str = ""

    def rp_names(self) -> list[str]:
        return [f"{self.name}-{i + 1}" for i in range(len(self.points))]


@dataclass
class Mission:
    id: str = field(default_factory=lambda: new_id("m"))
    side: str = ""
    name: str = "New Mission"
    mclass: str = "patrol"          # see enums.MISSION_CLASSES
    subtype: str = "aaw"
    zone: str = ""                  # zone id (patrol / support / mining area)
    prosecution_zone: str = ""      # optional zone id
    destination: str = ""           # unit id (ferry)
    units: list[str] = field(default_factory=list)     # assigned unit ids
    targets: list[str] = field(default_factory=list)   # strike target unit ids
    options: dict[str, Any] = field(default_factory=dict)   # ScenEdit_SetMission fields
    notes: str = ""


@dataclass
class Trigger:
    type: str = "RegularTime"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Condition:
    type: str = "LuaExpression"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    type: str = "Message"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    id: str = field(default_factory=lambda: new_id("e"))
    name: str = "New Event"
    repeatable: bool = False
    active: bool = True
    shown: bool = False
    probability: int = 100
    triggers: list[Trigger] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    notes: str = ""


@dataclass
class SpecialAction:
    id: str = field(default_factory=lambda: new_id("sa"))
    side: str = ""
    name: str = "New Special Action"
    description: str = ""
    repeatable: bool = False
    active: bool = True
    script: str = ""


@dataclass
class Script:
    id: str = field(default_factory=lambda: new_id("lua"))
    name: str = "MyScript"          # file name without .lua
    content: str = ""
    load_on_init: bool = False      # run from LuaInit.lua when the scenario loads
    notes: str = ""


@dataclass
class Formation:
    """A lead unit plus ordered members kept on stations computed from a preset (see model/formations.py)."""
    id: str = field(default_factory=lambda: new_id("f"))
    name: str = "New Formation"         # also the CMO group name
    side: str = ""
    preset: str = "line_ahead"
    lead: str = ""                      # unit id
    members: list[str] = field(default_factory=list)   # unit ids in station order
    spacing_nm: float = 1.0
    heading: float = 0.0                # formation orientation, true degrees
    params: dict[str, Any] = field(default_factory=dict)   # overrides of the preset's parameters
    alt_step_m: Optional[float] = None  # altitude step per member (air); None = preset default
    mirror: bool = False
    jitter: float = 0.0                 # random offset, in spacing units
    seed: int = 1
    set_heading: bool = True            # give every unit the formation heading
    keep_on_station: bool = True        # re-position members when the lead or the settings change
    group_in_cmo: bool = True           # build a CMO group with formation stations
    set_stations: bool = True           # False: group only (sites from templates), no formation stations
    station_type: str = "Rotating"      # Rotating (relative to group course) or Fixed (true bearing)
    sprint_drift: bool = False
    notes: str = ""


@dataclass
class Variant:
    """An extra build of the same scenario with different computer-controlled sides."""
    id: str = field(default_factory=lambda: new_id("v"))
    name: str = "Play as ..."
    key: str = "PLAY_X"             # Lua key, also the launcher file name Build_<key>.lua
    computer_sides: list[str] = field(default_factory=list)
    scen_suffix: str = ""           # ' - Play as NATO'
    description_html: str = ""      # replaces the last part of the description; blank = same page


@dataclass
class Project:
    format: str = FORMAT_ID
    version: int = FORMAT_VERSION
    meta: Meta = field(default_factory=Meta)
    clock: Clock = field(default_factory=Clock)
    weather: Weather = field(default_factory=Weather)
    build: BuildOptions = field(default_factory=BuildOptions)
    sides: list[Side] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)
    reference_points: list[ReferencePoint] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    missions: list[Mission] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    special_actions: list[SpecialAction] = field(default_factory=list)
    scripts: list[Script] = field(default_factory=list)
    variants: list[Variant] = field(default_factory=list)
    formations: list[Formation] = field(default_factory=list)
    key_values: dict[str, str] = field(default_factory=dict)   # initial ScenEdit_SetKeyValue pairs
    forecast: list[WeatherEntry] = field(default_factory=list)

    # ------------------------------------------------------------------ lookups
    def side(self, sid: str) -> Optional[Side]:
        return next((s for s in self.sides if s.id == sid), None)

    def side_by_name(self, name: str) -> Optional[Side]:
        return next((s for s in self.sides if s.name == name), None)

    def side_name(self, sid: str) -> str:
        s = self.side(sid)
        return s.name if s else ""

    def unit(self, uid: str) -> Optional[Unit]:
        return next((u for u in self.units if u.id == uid), None)

    def zone(self, zid: str) -> Optional[Zone]:
        return next((z for z in self.zones if z.id == zid), None)

    def mission(self, mid: str) -> Optional[Mission]:
        return next((m for m in self.missions if m.id == mid), None)

    def formation(self, fid: str) -> Optional[Formation]:
        return next((f for f in self.formations if f.id == fid), None)

    def script(self, name: str) -> Optional[Script]:
        return next((s for s in self.scripts if s.name == name or s.id == name), None)

    def hosted_by(self, uid: str) -> list[Unit]:
        return [u for u in self.units if u.host == uid]

    def units_of_side(self, sid: str) -> list[Unit]:
        return [u for u in self.units if u.side == sid]

    def all_objects(self) -> Iterator[Any]:
        yield from self.sides
        yield from self.units
        yield from self.reference_points
        yield from self.zones
        yield from self.missions
        yield from self.events
        yield from self.special_actions
        yield from self.scripts
        yield from self.variants
        yield from self.formations

    def find(self, oid: str) -> Optional[Any]:
        return next((o for o in self.all_objects() if getattr(o, "id", None) == oid), None)

    # ------------------------------------------------------------------ edits
    def add_side(self, name: str, tag: str = "", color: str = "#4a90d9") -> Side:
        side = Side(name=name, tag=tag, color=color)
        for other in self.sides:
            side.postures[other.id] = "N"
            other.postures[side.id] = "N"
        self.sides.append(side)
        return side

    def remove_side(self, sid: str) -> None:
        """Remove a side and everything that belongs to it."""
        self.sides = [s for s in self.sides if s.id != sid]
        for s in self.sides:
            s.postures.pop(sid, None)
        doomed = {u.id for u in self.units if u.side == sid}
        for uid in list(doomed):
            self.remove_unit(uid)
        self.reference_points = [r for r in self.reference_points if r.side != sid]
        self.zones = [z for z in self.zones if z.side != sid]
        self.missions = [m for m in self.missions if m.side != sid]
        self.special_actions = [a for a in self.special_actions if a.side != sid]
        self.formations = [f for f in self.formations if f.side != sid]
        for v in self.variants:
            v.computer_sides = [x for x in v.computer_sides if x != sid]

    def remove_unit(self, uid: str) -> None:
        """Remove a unit, the units hosted by it, and every reference to them."""
        doomed = {uid}
        changed = True
        while changed:
            changed = False
            for u in self.units:
                if u.host in doomed and u.id not in doomed:
                    doomed.add(u.id)
                    changed = True
        self.units = [u for u in self.units if u.id not in doomed]
        for m in self.missions:
            m.units = [x for x in m.units if x not in doomed]
            m.targets = [x for x in m.targets if x not in doomed]
            if m.destination in doomed:
                m.destination = ""
        for f in self.formations:
            f.members = [x for x in f.members if x not in doomed]
            if f.lead in doomed:
                f.lead = f.members.pop(0) if f.members else ""
        for u in self.units:
            if u.course is not None and u.course.land_at in doomed:
                u.course.land_at = ""
                if u.course.finish == "land":
                    u.course.finish = "rtb"

    def remove_zone(self, zid: str) -> None:
        self.zones = [z for z in self.zones if z.id != zid]
        for m in self.missions:
            if m.zone == zid:
                m.zone = ""
            if m.prosecution_zone == zid:
                m.prosecution_zone = ""

    def duplicate_unit(self, uid: str) -> Optional[Unit]:
        src = self.unit(uid)
        if not src:
            return None
        dup = copy.deepcopy(src)
        dup.id = new_id("u")
        dup.name = src.name + " (copy)"
        dup.lat += 0.02
        dup.lon += 0.02
        self.units.append(dup)
        return dup

    def unique_unit_name(self, base: str, side: str) -> str:
        names = {u.name for u in self.units if u.side == side}
        if base not in names:
            return base
        i = 2
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def scenario_year(self) -> int:
        return self.clock.start_dt().year

    # ------------------------------------------------------------------ io
    def to_dict(self) -> dict:
        return _to_plain(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        if data.get("format") not in (None, FORMAT_ID):
            raise ValueError(f"Not a CMO Scenario Studio project (format={data.get('format')!r})")
        proj = _from_plain(cls, data)
        proj.format, proj.version = FORMAT_ID, FORMAT_VERSION
        return proj

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Project":
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(self.to_json(), encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def clone(self) -> "Project":
        return Project.from_dict(copy.deepcopy(self.to_dict()))


# =============================================================================== (de)serialisation
def _to_plain(obj: Any) -> Any:
    if is_dataclass(obj):
        return {f.name: _to_plain(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, list):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_plain(v) for k, v in obj.items()}
    return obj


_HINTS: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    if cls not in _HINTS:
        _HINTS[cls] = get_type_hints(cls)
    return _HINTS[cls]


def _from_plain(cls: type, data: Any) -> Any:
    if not isinstance(data, dict):
        data = {}
    hints = _hints(cls)
    kwargs = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        kwargs[f.name] = _coerce(hints[f.name], data[f.name], f)
    return cls(**kwargs)


def _coerce(tp: Any, value: Any, f=None) -> Any:
    origin = get_origin(tp)
    if is_dataclass(tp):
        return _from_plain(tp, value)
    if origin is list:
        (inner,) = get_args(tp) or (Any,)
        return [_coerce(inner, v) for v in (value or [])]
    if origin is dict:
        args = get_args(tp)
        inner = args[1] if len(args) == 2 else Any
        return {str(k): _coerce(inner, v) for k, v in (value or {}).items()}
    args = get_args(tp)
    if args and type(None) in args:            # Optional[X]
        if value is None:
            return None
        real = next(a for a in args if a is not type(None))
        return _coerce(real, value)
    try:
        if tp is int:
            return int(value)
        if tp is float:
            return float(value)
        if tp is bool:
            return bool(value)
        if tp is str:
            return "" if value is None else str(value)
    except (TypeError, ValueError):
        if f is not None and f.default is not MISSING:
            return f.default
        return tp()
    return value


# =============================================================================== starter
def new_project(title: str = "New Scenario", db_file: str = "") -> Project:
    """A blank project with two hostile sides, ready to edit."""
    p = Project()
    p.meta.title = title
    p.meta.db_file = db_file
    blue = p.add_side("Blue", "BLUE", "#3d8bfd")
    red = p.add_side("Red", "RED", "#e5484d")
    blue.postures[red.id] = "H"
    red.postures[blue.id] = "H"
    blue.briefing_html = DEFAULT_BRIEFING
    red.briefing_html = DEFAULT_BRIEFING
    p.meta.description_html = DEFAULT_DESCRIPTION
    return p


DEFAULT_DESCRIPTION = """<P>Describe the background to the scenario here: the political situation, what has
just happened and why the forces are where they are.</P>

<P>Then tell each player, in a sentence or two, what they command and what they must achieve.</P>"""

DEFAULT_BRIEFING = """<h1>Situation</h1>
<p>What has happened, and what the enemy is doing now.</p>

<h2>Enemy Forces</h2>
<p>Expected enemy order of battle.</p>

<h2>Friendly Forces</h2>
<p>Forces under your command.</p>

<h1>Mission</h1>
<p>Your task, in one sentence.</p>

<h1>Execution</h1>
<p>Commander's intent and any restrictions (rules of engagement, no-go areas).</p>

<h1>Sustainment</h1>
<p>Logistics, reinforcements and time limits.</p>

<h1>Command and Signal</h1>
<p>Scoring and victory conditions.</p>"""
