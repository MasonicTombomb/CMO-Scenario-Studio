"""Enumerations shared by the data model, the editors and the exporter.

Values are the strings the CMO Lua API (``ScenEdit_*``) expects, so the exporter
can pass them through unchanged.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- units
#: Unit types the builder can place (satellites are browsable in the DB but not placeable).
UNIT_TYPES: tuple[str, ...] = ("Aircraft", "Ship", "Submarine", "Facility", "GroundUnit")

#: DB3000 table holding each unit type.
UNIT_TABLES: dict[str, str] = {
    "Aircraft": "DataAircraft",
    "Ship": "DataShip",
    "Submarine": "DataSubmarine",
    "Facility": "DataFacility",
    "GroundUnit": "DataGroundUnit",
    "Satellite": "DataSatellite",
}

#: Unit types that can host aircraft or boats (be an airbase / carrier / tender).
HOST_TYPES: tuple[str, ...] = ("Facility", "Ship", "GroundUnit", "Submarine")

# --------------------------------------------------------------------------- sides
AWARENESS: tuple[str, ...] = ("Blind", "Normal", "AutoSideID", "AutoSideAndUnitID", "Omniscient")
PROFICIENCY: tuple[str, ...] = ("Novice", "Cadet", "Regular", "Veteran", "Ace")

POSTURES: dict[str, str] = {
    "F": "Friendly",
    "N": "Neutral",
    "U": "Unfriendly",
    "H": "Hostile",
}

#: Weapon control status values accepted by ScenEdit_SetDoctrine.
WCS: tuple[str, ...] = ("", "Free", "Tight", "Hold")
WCS_LUA: dict[str, int] = {"Free": 0, "Tight": 1, "Hold": 2}

#: Side-level doctrine settings offered as typed fields. key -> (label, kind, choices)
DOCTRINE_FIELDS: dict[str, tuple[str, str, tuple]] = {
    "weapon_control_status_air": ("WCS air", "wcs", WCS),
    "weapon_control_status_surface": ("WCS surface", "wcs", WCS),
    "weapon_control_status_subsurface": ("WCS subsurface", "wcs", WCS),
    "weapon_control_status_land": ("WCS land", "wcs", WCS),
    "use_nuclear_weapons": ("Nuclear release", "choice", ("", "no", "yes")),
    "ignore_plotted_course": ("Ignore plotted course", "choice", ("", "yes", "no")),
    "engage_opportunity_targets": ("Engage opportunity targets", "choice", ("", "yes", "no")),
    "ignore_emcon_while_under_attack": ("Ignore EMCON under attack", "choice", ("", "yes", "no")),
    "fuel_state_planned": ("Fuel state (planned)", "choice", ("", "Bingo", "Joker10Percent", "Joker20Percent",
                                                             "Joker25Percent", "Joker30Percent", "Joker40Percent",
                                                             "Joker50Percent", "Joker60Percent", "Joker70Percent",
                                                             "Joker75Percent", "Joker80Percent", "Joker90Percent")),
}

# --------------------------------------------------------------------------- missions
MISSION_CLASSES: dict[str, tuple[str, ...]] = {
    "patrol": ("aaw", "asw", "naval", "land", "mixed", "sead"),
    "intercept": (),
    "strike": ("air", "land", "sea", "sub"),
    "support": (),
    "ferry": (),
    "mining": (),
    "mineclearing": (),
    "cargo": (),
}

MISSION_CLASS_LABELS: dict[str, str] = {
    "patrol": "Patrol",
    "intercept": "Intercept (aircraft on call at a base)",
    "strike": "Strike",
    "support": "Support (AEW / tanker / orbit)",
    "ferry": "Ferry",
    "mining": "Mining",
    "mineclearing": "Mine clearing",
    "cargo": "Cargo",
}

#: Missions that need an area (reference-point zone).
MISSION_NEEDS_ZONE: tuple[str, ...] = ("patrol", "support", "mining", "mineclearing")

#: Common ScenEdit_SetMission options with a typed editor. key -> (label, kind)
MISSION_OPTIONS: dict[str, tuple[str, str]] = {
    "isactive": ("Active", "bool"),
    "OneThirdRule": ("1/3 rule", "bool"),
    "CheckOPA": ("Investigate outside patrol area", "bool"),
    "CheckWWR": ("Investigate outside weapon range", "bool"),
    "ActiveEMCON": ("Active EMCON in area", "bool"),
    "flightSize": ("Flight size", "int"),
    "useFlightSize": ("Enforce flight size", "bool"),
    "starttime": ("Start time (dd/mm/yyyy hh:mm:ss)", "str"),
    "endtime": ("End time (dd/mm/yyyy hh:mm:ss)", "str"),
}

# --------------------------------------------------------------------------- events
#: RegularTime trigger intervals (index is the value CMO expects).
REGULAR_INTERVALS: tuple[str, ...] = (
    "1 second", "5 seconds", "15 seconds", "30 seconds", "1 minute", "5 minutes",
    "15 minutes", "30 minutes", "1 hour", "6 hours", "12 hours", "24 hours",
)

#: Trigger types. key -> (label, [(param, kind)]).
#: Kinds: side, unittype, unit, zone, int, bool, str, interval, datetime, choice:<a|b|c>, raw
#: Types starting with ``Studio`` are compiled by the exporter into native triggers + Lua guards.
TRIGGER_TYPES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "ScenLoaded": ("Scenario loaded", []),
    "ScenEnded": ("Scenario ended", []),
    "RegularTime": ("Regular time", [("Interval", "interval")]),
    "StudioAtTime": ("At date/time (once)", [("Time", "datetime")]),
    "StudioAfterDelay": ("Minutes after start (once)", [("Minutes", "int")]),
    "RandomTime": ("Random time (native)", [("EarliestTime", "str"), ("LatestTime", "str")]),
    "UnitDestroyed": ("Unit destroyed", [("TargetSide", "side"), ("TargetType", "unittype"),
                                         ("SpecificUnit", "unit")]),
    "UnitDamaged": ("Unit damaged", [("TargetSide", "side"), ("TargetType", "unittype"),
                                     ("SpecificUnit", "unit"), ("DamagePercent", "int")]),
    "UnitEntersArea": ("Unit enters area", [("TargetSide", "side"), ("TargetType", "unittype"),
                                            ("SpecificUnit", "unit"), ("Area", "zone"), ("ExitArea", "bool")]),
    "UnitRemainsInArea": ("Unit remains in area", [("TargetSide", "side"), ("TargetType", "unittype"),
                                                   ("SpecificUnit", "unit"), ("Area", "zone"),
                                                   ("Duration", "str")]),
    "UnitDetected": ("Unit detected", [("TargetSide", "side"), ("TargetType", "unittype"),
                                       ("SpecificUnit", "unit"), ("DetectorSide", "side"), ("MCL", "int")]),
    "Points": ("Side points reached", [("Side", "side"), ("PointValue", "int"),
                                       ("ReachDirection", "choice:GreaterThan|Exactly|LessThan")]),
    "Raw": ("Native trigger (raw Lua table)", [("Spec", "raw")]),
}

#: Condition types. All but ``Raw`` compile to Lua guards in the event's script.
CONDITION_TYPES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "LuaExpression": ("Lua expression is true", [("Expression", "str")]),
    "FlagSet": ("Flag is set", [("Key", "str")]),
    "FlagNotSet": ("Flag is not set", [("Key", "str")]),
    "ScoreAtLeast": ("Side score at least", [("Side", "side"), ("Value", "int")]),
    "ScoreBelow": ("Side score below", [("Side", "side"), ("Value", "int")]),
    "Chance": ("Random chance (%)", [("Percent", "int")]),
    "UnitAlive": ("Unit is alive", [("Unit", "unit")]),
    "UnitDead": ("Unit is destroyed", [("Unit", "unit")]),
    "Raw": ("Native condition (raw Lua table)", [("Spec", "raw")]),
}

#: Action types. All but ``Raw`` compile to Lua in the event's single LuaScript action.
ACTION_TYPES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "Message": ("Show message", [("Side", "side"), ("Text", "html")]),
    "Score": ("Change score", [("Side", "side"), ("Change", "int"), ("Reason", "str")]),
    "EndScenario": ("End scenario", []),
    "MissionStatus": ("Activate / deactivate mission", [("Mission", "mission"), ("Active", "bool")]),
    "SetFlag": ("Set flag / key value", [("Key", "str"), ("Value", "str")]),
    "RunScript": ("Run project script", [("Script", "script")]),
    "LuaScript": ("Lua code", [("Code", "lua")]),
    "SpawnUnit": ("Spawn unit (copy of a project unit)", [("Unit", "unit")]),
    "Raw": ("Native action (raw Lua table)", [("Spec", "raw")]),
}
