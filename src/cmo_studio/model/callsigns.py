"""Callsign library: countries -> squadrons (roles, words) -> flights of numbered aircraft.

The library is a standalone JSON file. The studio ships ``cmo_studio/data/callsigns.json``;
users edit their own copy (written by the Callsign Library editor, or by hand) which,
when present, is used instead. Aircraft are named from it by role and country:

    TARTAN 11, TARTAN 12, TARTAN 13, TARTAN 14   (flight 1 of word TARTAN)
    TARTAN 21 ...                                 (flight 2)

Detection uses the database: the aircraft's operator country picks the country,
its type/category (fighter, AEW, helicopter...) and its loadout role pick the role.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

FORMAT_ID = "cmo-studio-callsigns"


@dataclass
class Squadron:
    name: str
    service: str = ""
    base: str = ""
    aircraft: str = ""
    roles: list[str] = field(default_factory=list)
    callsigns: list[str] = field(default_factory=list)


@dataclass
class CountryCallsigns:
    name: str
    match: list[str] = field(default_factory=list)
    format: str = "{word} {flight}{member}"
    flight_size: int = 4
    notes: str = ""
    squadrons: list[Squadron] = field(default_factory=list)

    def squadron(self, name: str) -> Optional[Squadron]:
        return next((s for s in self.squadrons if s.name == name), None)


@dataclass
class Library:
    roles: dict[str, str]
    fallbacks: dict[str, list[str]]
    countries: list[CountryCallsigns]
    default_format: str = "{word} {flight}{member}"
    default_flight_size: int = 4
    max_flights_per_word: int = 9
    about: str = ""

    # ------------------------------------------------------------------ io
    @classmethod
    def from_dict(cls, d: dict) -> "Library":
        if d.get("format") not in (None, FORMAT_ID):
            raise ValueError(f"Not a callsign library (format={d.get('format')!r})")
        countries = []
        for c in d.get("countries", []):
            sq = [Squadron(name=str(s.get("name", "")), service=str(s.get("service", "")),
                           base=str(s.get("base", "")), aircraft=str(s.get("aircraft", "")),
                           roles=[str(r).strip().upper() for r in s.get("roles", []) if str(r).strip()],
                           callsigns=[str(w).strip().upper() for w in s.get("callsigns", []) if str(w).strip()])
                  for s in c.get("squadrons", [])]
            countries.append(CountryCallsigns(name=str(c.get("name", "")), match=[str(m) for m in c.get("match", [])],
                                              format=str(c.get("format") or d.get("default_format")
                                                         or "{word} {flight}{member}"),
                                              flight_size=int(c.get("flight_size") or d.get("default_flight_size")
                                                              or 4),
                                              notes=str(c.get("notes", "")), squadrons=sq))
        return cls(roles=dict(d.get("roles", {})), fallbacks={k: list(v) for k, v in d.get("fallbacks", {}).items()},
                   countries=countries, default_format=d.get("default_format", "{word} {flight}{member}"),
                   default_flight_size=int(d.get("default_flight_size", 4)),
                   max_flights_per_word=int(d.get("max_flights_per_word", 9)), about=d.get("about", ""))

    def to_dict(self) -> dict:
        return {
            "format": FORMAT_ID, "version": 1, "about": self.about, "roles": self.roles, "fallbacks": self.fallbacks,
            "default_format": self.default_format, "default_flight_size": self.default_flight_size,
            "max_flights_per_word": self.max_flights_per_word,
            "countries": [asdict(c) for c in self.countries],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def load(cls, path: str | Path) -> "Library":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def clone(self) -> "Library":
        return copy.deepcopy(self)

    # ------------------------------------------------------------------ lookups
    def country(self, name: str) -> Optional[CountryCallsigns]:
        return next((c for c in self.countries if c.name == name), None)

    def country_for(self, db_country: str) -> CountryCallsigns:
        """Best match for a database operator country (longest matching prefix), else Generic."""
        text = (db_country or "").lower()
        best, best_len = None, -1
        for c in self.countries:
            for m in c.match + [c.name]:
                m = m.lower().strip()
                if m and text.startswith(m) and len(m) > best_len:
                    best, best_len = c, len(m)
        return best or self.generic()

    def generic(self) -> CountryCallsigns:
        return self.country("Generic") or (self.countries[0] if self.countries else CountryCallsigns("Generic"))

    def role_chain(self, role: str) -> list[str]:
        chain, todo = [], [role]
        while todo:
            r = todo.pop(0)
            if r not in chain:
                chain.append(r)
                todo += self.fallbacks.get(r, [])
        return chain

    def squadrons_for(self, country: CountryCallsigns, role: str) -> list[tuple[CountryCallsigns, Squadron]]:
        """Squadrons that fly ``role`` (or its fallbacks) in the country, then in Generic."""
        out: list[tuple[CountryCallsigns, Squadron]] = []
        for c in (country, self.generic()):
            for r in self.role_chain(role):
                for s in c.squadrons:
                    if r in s.roles and (c, s) not in out and s.callsigns:
                        out.append((c, s))
                if out:
                    break
            if out:
                return out
        return out


# =============================================================================== files
def default_library_text() -> str:
    return resources.files("cmo_studio").joinpath("data", "callsigns.json").read_text(encoding="utf-8")


def default_library() -> Library:
    return Library.from_dict(json.loads(default_library_text()))


def load_library(user_path: Optional[str | Path] = None) -> tuple[Library, str]:
    """The user's library if it exists and is valid, else the shipped default. Returns (library, source)."""
    if user_path and Path(user_path).is_file():
        try:
            return Library.load(user_path), str(user_path)
        except (ValueError, OSError, KeyError, TypeError):
            pass
    return default_library(), "built-in default"


# =============================================================================== role detection
TYPE_ROLES = {
    "Fighter": "FIGHTER", "Multirole (Fighter/Attack)": "FIGHTER", "Attack": "ATTACK",
    "Battlefield Air Interdiction (BAI/CAS)": "ATTACK", "Wild Weasel": "SEAD", "Bomber": "BOMBER",
    "Electronic Warfare": "EW", "Airborne Early Warning (AEW)": "AEW", "Airborne Command Post (ACP)": "AEW",
    "Search And Rescue (SAR)": "CSAR", "Mine Sweeper (MCM)": "MPA", "Anti-Submarine Warfare (ASW)": "MPA",
    "Maritime Patrol Aircraft (MPA)": "MPA", "Forward Observer": "ISR", "Area Surveillance": "ISR", "Recon": "ISR",
    "Electronic Intelligence (ELINT)": "ISR", "Signals Intelligence (SIGINT)": "ISR", "Transport": "TRANSPORT",
    "Cargo": "TRANSPORT", "Commercial": "TRANSPORT", "Civilian": "TRANSPORT", "Utility": "TRANSPORT",
    "Naval Utility": "MPA", "Tanker (Air Refueling)": "TANKER", "Trainer": "TRAINER", "Target Towing": "TRAINER",
    "Target Drone": "TRAINER", "Unmanned Aerial Vehicle (UAV)": "UAV", "Unmanned Combat Aerial Vehicle (UCAV)": "UAV",
}
SEAD_LOADOUTS = {3003, 3004, 3005, 3103, 3104, 3105, 3203, 3204, 3205}


def loadout_role_to_role(rid: int) -> Optional[str]:
    if not rid:
        return None
    if 2000 <= rid < 3000:
        return "FIGHTER"
    if rid in SEAD_LOADOUTS:
        return "SEAD"
    if rid in (3201, 3202):
        return "ASUW"
    if rid == 3401:
        return "ATTACK"
    if 3000 <= rid < 3500:
        return "STRIKE"
    if rid == 4001:
        return "EW"
    if rid in (4002, 4003):
        return "AEW"
    if rid in (4101, 4102):
        return "CSAR"
    if rid in (4201, 4202, 4301, 6001, 6002, 7005):
        return "MPA"
    if 7001 <= rid <= 7004:
        return "ISR"
    if 7100 <= rid < 7300:
        return "TRANSPORT"
    if rid == 8001:
        return "TANKER"
    if 8100 <= rid < 8200:
        return "TRAINER"
    return None


def detect_role(category: str = "", subtype: str = "", loadout_role: int = 0) -> str:
    """Role from the DB aircraft category/type description and the loadout role id."""
    heli = any(k in (category or "") for k in ("Helicopter", "Tiltrotor"))
    base = TYPE_ROLES.get(subtype or "", "FIGHTER" if not heli else "UTILITY_HELO")
    by_loadout = loadout_role_to_role(loadout_role)
    role = base
    if by_loadout and base not in ("UAV", "BOMBER") and not (base == "TANKER" and by_loadout == "TRANSPORT"):
        role = by_loadout
    if heli:
        role = {"ATTACK": "ATTACK_HELO", "STRIKE": "ATTACK_HELO", "SEAD": "ATTACK_HELO", "FIGHTER": "ATTACK_HELO",
                "ASUW": "ASW_HELO", "MPA": "ASW_HELO", "TRANSPORT": "UTILITY_HELO", "TANKER": "UTILITY_HELO",
                "BOMBER": "ATTACK_HELO", "TRAINER": "UTILITY_HELO"}.get(role, role)
        if subtype == "Naval Utility":
            role = "ASW_HELO"
    return role


# =============================================================================== allocation
@dataclass
class Assignment:
    name: str
    country: str
    squadron: str
    word: str
    flight: int
    member: int


def _fmt(fmt: str, **kw) -> str:
    try:
        return fmt.format(**kw).strip()
    except (KeyError, IndexError, ValueError):
        return f"{kw.get('word', '')} {kw.get('flight', '')}{kw.get('member', '')}".strip()


def flight_format(fmt: str) -> str:
    """The format without the member number, e.g. '{word} {flight}{member}' -> '{word} {flight}'."""
    return re.sub(r"\{member[^}]*\}", "", fmt).strip() or "{word} {flight}"


class Allocator:
    """Hands out whole flights, skipping any flight whose names are already taken.

    With no squadron chosen, successive requests for the same country and role rotate through its
    squadrons (the first unit gets the first squadron, the next unit the second...), so separate units
    come from separate squadrons, as they would in reality.
    """

    def __init__(self, lib: Library, used: set[str] = frozenset(), rotate: bool = True):
        self.lib = lib
        self.used = {u.upper() for u in used}
        self.next_flight: dict[tuple[str, str, str], int] = {}
        self.rotate = rotate
        self.cursor: dict[tuple[str, str], int] = {}

    def _flights(self, country: CountryCallsigns, role: str, squadron: str = ""):
        pairs = self.lib.squadrons_for(country, role)
        if squadron:
            pairs = [(c, s) for c, s in pairs if s.name == squadron] or [
                (country, s) for s in country.squadrons if s.name == squadron] or pairs
        elif self.rotate and pairs:
            key = (country.name, role)
            start = self.cursor.get(key, 0) % len(pairs)
            self.cursor[key] = start + 1
            pairs = pairs[start:] + pairs[:start]
        for c, s in pairs:
            for word in s.callsigns:
                key = (c.name, s.name, word)
                start = self.next_flight.get(key, 1)
                for flight in range(start, self.lib.max_flights_per_word + 1):
                    yield c, s, word, flight

    def flight_names(self, c: CountryCallsigns, word: str, flight: int, squadron: str) -> list[str]:
        return [_fmt(c.format, word=word, flight=flight, member=m, squadron=squadron)
                for m in range(1, max(1, c.flight_size) + 1)]

    def allocate(self, country: CountryCallsigns, role: str, n: int, squadron: str = "") -> list[Assignment]:
        """Names for ``n`` aircraft: whole flights of ``flight_size``, numbered 1..size."""
        out: list[Assignment] = []
        for c, s, word, flight in self._flights(country, role, squadron):
            if len(out) >= n:
                break
            names = self.flight_names(c, word, flight, s.name)
            if any(nm.upper() in self.used for nm in names):
                continue
            self.next_flight[(c.name, s.name, word)] = flight + 1
            for m, nm in enumerate(names, 1):
                if len(out) >= n:
                    break
                out.append(Assignment(nm, c.name, s.name, word, flight, m))
                self.used.add(nm.upper())
            # the rest of a partly used flight is reserved too, so flights never share numbers
            self.used.update(nm.upper() for nm in names)
        while len(out) < n:   # library exhausted: numbered fallback
            nm = f"{role} {len(self.used) + 1}"
            self.used.add(nm.upper())
            out.append(Assignment(nm, country.name, "", role, 0, 0))
        return out

    def allocate_flight_name(self, country: CountryCallsigns, role: str, squadron: str = "") -> Assignment:
        """One flight callsign without member numbers (for a unit with count > 1 that is not split)."""
        for c, s, word, flight in self._flights(country, role, squadron):
            name = _fmt(flight_format(c.format), word=word, flight=flight, squadron=s.name)
            members = self.flight_names(c, word, flight, s.name)
            if name.upper() in self.used or any(m.upper() in self.used for m in members):
                continue
            self.next_flight[(c.name, s.name, word)] = flight + 1
            self.used.add(name.upper())
            self.used.update(m.upper() for m in members)
            return Assignment(name, c.name, s.name, word, flight, 0)
        return self.allocate(country, role, 1, squadron)[0]


# =============================================================================== applying to a project
@dataclass
class PlanRow:
    unit_id: str
    country: str
    role: str
    squadron: str = ""          # '' = automatic


def apply_callsigns(project, lib: Library, plan: list[PlanRow], split: bool = True, set_group: bool = True,
                    used: Optional[set[str]] = None) -> dict[str, list[str]]:
    """Rename the planned aircraft. Counted units are split into single aircraft when ``split`` (not
    reinforcements, whose spawn actions refer to one unit). Returns {original unit id: [unit ids]}."""
    from .project import new_id

    planned = {r.unit_id for r in plan}
    if used is None:
        used = {u.name for u in project.units if u.id not in planned}
    alloc = Allocator(lib, used)
    result: dict[str, list[str]] = {}
    for row in plan:
        u = project.unit(row.unit_id)
        if u is None:
            continue
        country = lib.country(row.country) or lib.generic()
        if u.count > 1 and not (split and not u.reserve):
            a = alloc.allocate_flight_name(country, row.role, row.squadron)
            u.name = a.name
            if set_group and a.squadron:
                u.group = a.squadron
            result[u.id] = [u.id]
            continue
        n = max(1, u.count)
        names = alloc.allocate(country, row.role, n, row.squadron)
        ids = [u.id]
        u.name, u.count = names[0].name, 1
        if set_group and names[0].squadron:
            u.group = names[0].squadron
        idx = project.units.index(u)
        for k, a in enumerate(names[1:], 1):
            c = copy.deepcopy(u)
            c.id = new_id("u")
            c.name = a.name
            if set_group and a.squadron:
                c.group = a.squadron
            project.units.insert(idx + k, c)
            ids.append(c.id)
        if len(ids) > 1:
            for m in project.missions:
                if u.id in m.units:
                    pos = m.units.index(u.id)
                    m.units[pos + 1:pos + 1] = ids[1:]
            for f in project.formations:
                if u.id in f.members:
                    pos = f.members.index(u.id)
                    f.members[pos + 1:pos + 1] = ids[1:]
                elif f.lead == u.id:
                    f.members[0:0] = ids[1:]
        result[u.id] = ids
    return result
