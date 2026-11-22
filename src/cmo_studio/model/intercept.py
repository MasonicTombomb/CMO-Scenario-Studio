"""Intercept missions: aircraft on call at a base that launch when chosen conditions are met.

The conditions are check boxes (:data:`CONTACT_CONDITIONS` about the contact, :data:`GATES` about the situation). In
CMO the runtime's intercept manager (``StudioInterceptTick``) compares the side's contacts with them every half minute
and drives a native *Air Intercept* mission: it adds the contact as a target, assigns aircraft and activates the
mission, then stands them down. Pure data here; the manager is in ``Studio_Runtime.lua``.
"""

from __future__ import annotations

from typing import Optional

from .project import Intercept, Mission, Project, Unit

POSTURES = (("H", "Hostile"), ("U", "Unfriendly"), ("X", "Unknown"), ("N", "Neutral"))
ROE = {"identify": "Intercept and identify (weapons hold)", "tight": "Engage if hostile (weapons tight)",
       "free": "Engage (weapons free)"}

#: (attribute, label, tooltip): about one contact; combined by 'all' or 'any'
CONTACT_CONDITIONS = (
    ("in_area", "Is inside the intercept area", "The contact is inside the mission's area"),
    ("near", "Is close to", "The contact is within this distance of the base (or of a unit you choose)"),
    ("posture", "Is classed as", "How your side regards the contact at that moment"),
    ("inbound", "Is heading towards us", "Its course points at the base (or chosen unit), within this angle"),
    ("altitude", "Altitude between", "Metres above sea level"),
    ("speed", "Is at least this fast", "Knots"),
    ("unidentified", "Is not identified yet", "Your side does not know what class of aircraft it is"),
    ("emitting", "Is emitting (radar on)", "Your side has detected an emission from it"),
    ("tracked", "Has been tracked for", "Your side has held the contact for at least this long"),
)
#: always required as well, whatever the 'all / any' choice
GATES = (
    ("raid", "At least this many such contacts", "A raid: wait until there are this many matching contacts"),
    ("window", "Only between these times", "Minutes after the start; 0 means no limit"),
    ("flag", "Only once this flag is set", "For example a course signal or another event's flag"),
)

PRESETS = {
    "qra": ("Quick reaction alert", dict(logic="all", in_area=True, posture=True, postures=["H", "U", "X"],
                                         per_contact=2, max_contacts=2, reserve=0, roe="identify")),
    "base": ("Base defence", dict(logic="all", near=True, near_nm=120, posture=True, postures=["H", "U"], inbound=True,
                                  inbound_deg=45, per_contact=2, max_contacts=4, reserve=2, roe="tight")),
    "raid": ("Bomber raid", dict(logic="all", in_area=True, posture=True, postures=["H"], raid=True, raid_min=2,
                                 per_contact=4, max_contacts=2, reserve=0, roe="free")),
}


def intercept_of(m: Mission) -> Intercept:
    if m.intercept is None:
        m.intercept = Intercept()
    return m.intercept


def apply_preset(m: Mission, key: str) -> None:
    ic = Intercept()
    for k, v in PRESETS[key][1].items():
        setattr(ic, k, list(v) if isinstance(v, list) else v)
    ic.defend = intercept_of(m).defend
    m.intercept = ic


def ticked(ic: Intercept) -> list[str]:
    return [a for a, *_ in CONTACT_CONDITIONS if getattr(ic, a)]


def home(p: Project, m: Mission) -> Optional[Unit]:
    """Where distances and 'heading towards us' are measured from: the chosen unit, else the aircraft's base."""
    ic = intercept_of(m)
    u = p.unit(ic.defend) if ic.defend else None
    if u is not None:
        return p.unit(u.host) if u.host and p.unit(u.host) else u
    for i in m.units:
        a = p.unit(i)
        if a is not None:
            return (p.unit(a.host) if a.host else None) or a
    return None


def bases_with_aircraft(p: Project, side: str) -> list[tuple[str, str, int]]:
    """(key, name, aircraft) for each base of the side that has aircraft; the key is the site's name."""
    count: dict[str, int] = {}
    for u in p.units:
        h = p.unit(u.host) if u.side == side and u.type == "Aircraft" and u.host else None
        if h is not None:
            key = h.group or h.name
            count[key] = count.get(key, 0) + max(1, u.count)
    return [(k, k, n) for k, n in sorted(count.items())]


def aircraft_at(p: Project, side: str, base: str) -> list[str]:
    out = []
    for u in p.units:
        h = p.unit(u.host) if u.side == side and u.type == "Aircraft" and u.host else None
        if h is not None and (h.group or h.name) == base:
            out.append(u.id)
    return out


def describe(p: Project, m: Mission) -> str:
    """The mission in plain English."""
    ic = intercept_of(m)
    at = home(p, m)
    where = at.name if at is not None else "the base"
    zone = p.zone(m.zone) if m.zone else None
    bits = []
    if ic.in_area:
        bits.append(f"is inside {zone.name}" if zone else "is inside the area (none chosen)")
    if ic.near:
        bits.append(f"is within {ic.near_nm:g} nm of {where}")
    if ic.posture:
        names = [n.lower() for k, n in POSTURES if k in ic.postures]
        bits.append("is " + (" or ".join(names) if names else "(no class chosen)"))
    if ic.inbound:
        bits.append(f"is heading within {ic.inbound_deg:g}° of {where}")
    if ic.altitude:
        bits.append(f"is between {ic.alt_min:,.0f} and {ic.alt_max:,.0f} m")
    if ic.speed:
        bits.append(f"is doing {ic.speed_min:g} kn or more")
    if ic.unidentified:
        bits.append("is not identified")
    if ic.emitting:
        bits.append("is emitting")
    if ic.tracked:
        bits.append(f"has been tracked for {ic.tracked_min:g} min")
    joiner = " and " if ic.logic == "all" else " or "
    when = joiner.join(bits) if bits else "is detected (no conditions ticked)"
    gates = []
    if ic.raid:
        gates.append(f"there are at least {ic.raid_min} of them")
    if ic.window:
        a = f"from H+{ic.window_from} min" if ic.window_from else ""
        b = f"until H+{ic.window_to} min" if ic.window_to else ""
        gates.append(" ".join(x for x in (a, b) if x) or "at any time")
    if ic.flag:
        gates.append(f"the flag {ic.flag_key or '(none)'} is set")
    n = sum(max(1, p.unit(i).count) for i in m.units if p.unit(i))
    kind = "an aircraft or missile" if ic.missiles else "an aircraft"
    return (f"Launches {ic.per_contact} aircraft per contact (up to {ic.max_contacts} contact(s) at once, {n} on call"
            + (f", {ic.reserve} kept back" if ic.reserve else "") + f") when {kind} {when}"
            + (", provided " + " and ".join(gates) if gates else "") + f". {ROE.get(ic.roe, ic.roe)}. Stands down "
            f"{ic.stand_down_min:g} min after that stops being true.")


__all__ = ["POSTURES", "ROE", "CONTACT_CONDITIONS", "GATES", "PRESETS", "intercept_of", "apply_preset", "ticked",
           "home", "bases_with_aircraft", "aircraft_at", "describe"]
