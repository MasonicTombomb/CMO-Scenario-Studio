"""Which units can base aircraft, and how many: CMO's aircraft facilities (hangars, parking, pads, decks).

Every facility, ship or ground unit lists its aircraft spaces in the database (``<Type>AircraftFacilities`` ->
``DataAircraftFacility``: type, largest aircraft size, capacity). Only some space types can hold a *based*
aircraft; runways, taxiways, access points, catapults and arresting gear are for take-off and landing only. A
runway or a control tower picked as an aircraft's base makes CMO refuse to create the aircraft.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

# EnumAircraftFacilityType
HANGAR, OPEN_PARKING = 4001, 4002
PAD, PAD_HAULDOWN, DECK_HELO, DECK_VTOL = 3001, 3002, 6001, 6002
#: spaces any aircraft can be based in
PARKING = (HANGAR, OPEN_PARKING)
#: extra spaces for helicopters and tiltrotors
ROTARY = (PAD, PAD_HAULDOWN, DECK_HELO, DECK_VTOL)
#: EnumAircraftCategory values that can use pads and helicopter decks
ROTARY_CATEGORIES = (2003, 2004)          # Helicopter, Tiltrotor

SIZE_NAMES = {1: "small", 2: "medium", 3: "large", 4: "very large"}


def size_rank(code: int) -> int:
    """EnumAircraftPhysicalSize code -> 1 (small) .. 4 (very large). Drones count as small."""
    return {2001: 1, 2002: 2, 2003: 3, 2004: 4}.get(int(code or 0), 1)


@dataclass(frozen=True)
class Space:
    ftype: int
    size: int          # EnumAircraftPhysicalSize code of the largest aircraft it takes
    capacity: int

    @property
    def parks(self) -> bool:
        return self.ftype in PARKING or self.ftype in ROTARY


@dataclass(frozen=True)
class Aircraft:
    size: int          # EnumAircraftPhysicalSize code
    rotary: bool


def fits(space: Space, ac: Aircraft) -> bool:
    if space.ftype not in PARKING and not (ac.rotary and space.ftype in ROTARY):
        return False
    return size_rank(space.size) >= size_rank(ac.size)


def room_for(spaces: Iterable[Space], ac: Aircraft) -> int:
    """How many of this aircraft the host can base."""
    return sum(max(0, s.capacity) for s in spaces if fits(s, ac))


def can_base_any(spaces: Iterable[Space]) -> bool:
    return any(s.parks and s.capacity > 0 for s in spaces)


def largest_parking(spaces: Iterable[Space]) -> Optional[str]:
    ranks = [size_rank(s.size) for s in spaces if s.ftype in PARKING and s.capacity > 0]
    return SIZE_NAMES[max(ranks)] if ranks else None


def why_not(spaces: list[Space], ac: Aircraft) -> str:
    """Plain-English reason a host cannot take this aircraft ('' if it can)."""
    if room_for(spaces, ac):
        return ""
    if not spaces or not can_base_any(spaces):
        return "it has no hangar, shelter or parking space (runways, taxiways and towers cannot hold aircraft)"
    if not ac.rotary and not any(s.ftype in PARKING for s in spaces):
        return "it only has helicopter pads or decks"
    big = largest_parking(spaces)
    return f"its spaces only take aircraft up to {big} size" if big else "its spaces are too small"
