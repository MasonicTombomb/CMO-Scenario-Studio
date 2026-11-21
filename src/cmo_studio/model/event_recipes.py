"""Event recipes: common events built from a few answers instead of triggers, conditions and actions by hand.

Each recipe lists its questions (:class:`Ask`) and builds one finished :class:`~.project.Event` from the answers.
The events page shows them under *New* and asks the questions in a small form.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from .project import Action, Condition, Event, Project, Trigger

ONE_MINUTE = 4          # RegularTime interval index (see enums.REGULAR_INTERVALS)


@dataclass
class Ask:
    key: str
    label: str
    kind: str               # side | own_side | enemy_side | unit | reserve_unit | zone | mission | int | text | html
    default: Any = None     # or a callable(project) -> value
    help: str = ""
    optional: bool = False


@dataclass
class Recipe:
    id: str
    name: str
    description: str
    asks: list[Ask]
    build: Callable[[Project, dict], Event]
    category: str = "General"
    then: str = ""          # a note shown after creating it

    def defaults(self, p: Project) -> dict:
        return {a.key: (a.default(p) if callable(a.default) else a.default) for a in self.asks}


def _side(p: Project, i: int) -> str:
    return p.sides[i].id if len(p.sides) > i else (p.sides[0].id if p.sides else "")


def _enemy_of(p: Project, sid: str) -> str:
    s = p.side(sid)
    if s is not None:
        for other, posture in s.postures.items():
            if posture == "H" and p.side(other):
                return other
    return next((x.id for x in p.sides if x.id != sid), sid)


def _msg(text: str) -> str:
    text = (text or "").strip()
    return text if text.lower().startswith("<") else f"<P>{text}</P>"


def _name(p: Project, oid: str, what: str = "unit") -> str:
    o = p.find(oid) if oid else None
    return getattr(o, "name", "") or f"(no {what})"


# ---------------------------------------------------------------- the recipes
def _score_on_destroy(p, v):
    types = [v["type"]] if v.get("type") else ["Aircraft", "Ship", "Submarine", "Facility", "GroundUnit"]
    trig = ([Trigger("UnitDestroyed", {"SpecificUnit": v["unit"]})] if v.get("unit") else
            [Trigger("UnitDestroyed", {"TargetSide": v["target"], "TargetType": t}) for t in types])
    what = _name(p, v["unit"]) if v.get("unit") else f"{p.side_name(v['target'])} " + (v.get("type") or "unit")
    return Event(name=f"{p.side_name(v['side'])} scores: {what} destroyed", repeatable=not v.get("unit"),
                 triggers=trig, actions=[Action("Score", {"Side": v["side"], "Change": int(v["points"]),
                                                          "Reason": v.get("reason") or f"{what} destroyed"})])


def _reinforcements(p, v):
    u = p.unit(v["unit"])
    if u is not None:
        u.reserve = True                     # it must not be there at the start
    acts = [Action("SpawnUnit", {"Unit": v["unit"]})]
    if (v.get("text") or "").strip():
        acts.append(Action("Message", {"Side": u.side if u else "", "Text": _msg(v["text"])}))
    return Event(name=f"Reinforcements: {_name(p, v['unit'])}",
                 triggers=[Trigger("StudioAfterDelay", {"Minutes": int(v["minutes"])})], actions=acts)


def _end_when_destroyed(p, v):
    score = ([Action("Score", {"Side": v["side"], "Change": int(v["points"]),
                               "Reason": f"{_name(p, v['unit'])} destroyed"})] if int(v["points"]) else [])
    return Event(name=f"End: {_name(p, v['unit'])} destroyed",
                 triggers=[Trigger("UnitDestroyed", {"SpecificUnit": v["unit"]})],
                 actions=score + [Action("Message", {"Side": "", "Text": _msg(v["text"])}), Action("EndScenario", {})])


def _area_entered(p, v):
    return Event(name=f"{p.side_name(v['target'])} enters {_name(p, v['zone'], 'area')}",
                 repeatable=bool(int(v.get("repeat") or 0)),
                 triggers=[Trigger("UnitEntersArea", {"TargetSide": v["target"], "Area": v["zone"]})],
                 actions=[Action("Message", {"Side": v["side"], "Text": _msg(v["text"])})])


def _mission_on_flag(p, v):
    return Event(name=f"Start {_name(p, v['mission'], 'mission')} on {v['flag']}",
                 triggers=[Trigger("RegularTime", {"Interval": ONE_MINUTE})],
                 conditions=[Condition("FlagSet", {"Key": v["flag"]})],
                 actions=[Action("MissionStatus", {"Mission": v["mission"], "Active": True})]
                 + ([Action("Message", {"Side": p.mission(v["mission"]).side, "Text": _msg(v["text"])})]
                    if (v.get("text") or "").strip() and p.mission(v["mission"]) else []))


def _mission_at_time(p, v):
    m = p.mission(v["mission"])
    return Event(name=f"Start {_name(p, v['mission'], 'mission')} at H+{int(v['minutes'])} min",
                 triggers=[Trigger("StudioAfterDelay", {"Minutes": int(v["minutes"])})],
                 actions=[Action("MissionStatus", {"Mission": v["mission"], "Active": True})]
                 + ([Action("Message", {"Side": m.side, "Text": _msg(v["text"])})]
                    if (v.get("text") or "").strip() and m else []))


def _victory(p, v):
    return Event(name=f"{p.side_name(v['side'])} victory at {int(v['points'])} points",
                 triggers=[Trigger("Points", {"Side": v["side"], "PointValue": int(v["points"]),
                                              "ReachDirection": "GreaterThan"})],
                 actions=[Action("Message", {"Side": "", "Text": _msg(v["text"])}), Action("EndScenario", {})])


def _timed_message(p, v):
    return Event(name=v.get("title") or f"Message at H+{int(v['minutes'])} min",
                 triggers=[Trigger("StudioAfterDelay", {"Minutes": int(v["minutes"])})],
                 actions=[Action("Message", {"Side": v["side"], "Text": _msg(v["text"])})])


def _time_limit(p, v):
    end = p.clock.start_dt() + timedelta(days=p.clock.duration_days, hours=p.clock.duration_hours,
                                         minutes=p.clock.duration_minutes) - timedelta(minutes=int(v["warn"]))
    return Event(name=f"{int(v['warn'])} minutes left",
                 triggers=[Trigger("StudioAtTime", {"Time": end.strftime("%Y-%m-%dT%H:%M:%S")})],
                 actions=[Action("Message", {"Side": "", "Text": _msg(v["text"])})])


def _flag_on_destroy(p, v):
    return Event(name=f"Signal {v['flag']}: {_name(p, v['unit'])} destroyed",
                 triggers=[Trigger("UnitDestroyed", {"SpecificUnit": v["unit"]})],
                 actions=[Action("SetFlag", {"Key": v["flag"], "Value": "true"})])


RECIPES: list[Recipe] = [
    Recipe("score_on_destroy", "Points when units are destroyed",
           "A side scores (or loses) points each time a unit of another side is destroyed: any unit of that side, "
           "one type, or one particular unit.",
           [Ask("side", "Side that scores", "own_side", lambda p: _side(p, 0)),
            Ask("target", "Units of side", "enemy_side", lambda p: _enemy_of(p, _side(p, 0))),
            Ask("type", "Type (blank: any)", "unittype", "", optional=True),
            Ask("unit", "Or one unit", "unit", "", optional=True,
                help="Score only for this unit (then it fires once)"),
            Ask("points", "Points", "int", 10, help="Negative to lose points"),
            Ask("reason", "Reason (log)", "text", "", optional=True)],
           _score_on_destroy, "Scoring"),
    Recipe("victory", "Victory at a score",
           "End the scenario with a message when a side reaches a score.",
           [Ask("side", "Side", "own_side", lambda p: _side(p, 0)), Ask("points", "Score", "int", 500),
            Ask("text", "Message", "html", "Victory conditions met.")], _victory, "Scoring"),
    Recipe("end_when_destroyed", "End when a key unit is destroyed",
           "End the scenario (with optional points) when one unit is destroyed: a carrier, a headquarters, an "
           "airbase.",
           [Ask("unit", "Unit", "unit", ""), Ask("side", "Side that scores", "own_side", lambda p: _side(p, 0)),
            Ask("points", "Points (0: none)", "int", 0),
            Ask("text", "Message", "html", "The objective has been destroyed. The operation is over.")],
           _end_when_destroyed, "Scoring"),
    Recipe("reinforcements", "Reinforcements arrive",
           "A unit that is not there at the start arrives a set time after it. The unit is made a reinforcement: "
           "place it where it should appear.",
           [Ask("unit", "Unit", "unit", ""), Ask("minutes", "Minutes after the start", "int", 120),
            Ask("text", "Message to its side", "html", "Reinforcements have arrived.", optional=True)],
           _reinforcements, "Forces", then="The unit is now a reinforcement (faded on the map)."),
    Recipe("mission_at_time", "Start a mission at a time",
           "Switch a mission on a set time after the start. Untick the mission's Active box so it waits.",
           [Ask("mission", "Mission", "mission", ""), Ask("minutes", "Minutes after the start", "int", 60),
            Ask("text", "Message to its side", "html", "", optional=True)], _mission_at_time, "Forces"),
    Recipe("mission_on_flag", "Start a mission on a signal",
           "Switch a mission on when a flag is set, for example by a course waypoint's signal or another event.",
           [Ask("mission", "Mission", "mission", ""), Ask("flag", "Flag", "text", "STRIKE_AT_IP"),
            Ask("text", "Message to its side", "html", "", optional=True)], _mission_on_flag, "Forces"),
    Recipe("flag_on_destroy", "Signal when a unit is destroyed",
           "Set a flag when one unit is destroyed, so other events (or a mission) can follow on.",
           [Ask("unit", "Unit", "unit", ""), Ask("flag", "Flag", "text", "TARGET_DOWN")],
           _flag_on_destroy, "Forces"),
    Recipe("area_entered", "Message when units enter an area",
           "Tell a side when units of another side enter an area: an air defence identification zone, a "
           "minefield, a coast.",
           [Ask("zone", "Area", "zone", ""), Ask("target", "Units of side", "enemy_side",
                                                  lambda p: _enemy_of(p, _side(p, 0))),
            Ask("side", "Side to tell", "own_side", lambda p: _side(p, 0)),
            Ask("text", "Message", "html", "Unidentified contacts have entered the area."),
            Ask("repeat", "Every time (1) or once (0)", "int", 0)], _area_entered, "Messages"),
    Recipe("timed_message", "Message at a time",
           "A message (an intelligence update, a news flash, new orders) a set time after the start.",
           [Ask("minutes", "Minutes after the start", "int", 30), Ask("side", "Side (blank: all)", "side", ""),
            Ask("title", "Event name", "text", "", optional=True),
            Ask("text", "Message", "html", "FLASH: new intelligence has been received.")], _timed_message,
           "Messages"),
    Recipe("time_limit", "Warning before the end",
           "A message a set number of minutes before the scenario ends.",
           [Ask("warn", "Minutes before the end", "int", 15),
            Ask("text", "Message", "html", "Fifteen minutes remain.")], _time_limit, "Messages"),
]


def recipe(rid: str) -> Recipe | None:
    return next((r for r in RECIPES if r.id == rid), None)


def missing_answers(r: Recipe, values: dict) -> list[str]:
    return [a.label for a in r.asks if not a.optional and a.kind not in ("int", "side") and
            not str(values.get(a.key) or "").strip()]


__all__ = ["Ask", "Recipe", "RECIPES", "recipe", "missing_answers"]
