"""Saved courses: routes you reuse (a tanker track, a transit lane, a strike route) kept in ``routes.json`` in the
user's data folder, beside the template and area libraries.

A saved route keeps its waypoints with every leg setting, its departure and its end order. A landing base is not
kept (bases belong to one project), so 'Land at another base' comes back as 'Return to its base'.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .project import Course, _from_plain, _to_plain, new_id

FORMAT = "cmo-studio-routes"


@dataclass
class SavedRoute:
    id: str = field(default_factory=lambda: new_id("route"))
    name: str = ""
    description: str = ""
    course: Course = field(default_factory=Course)

    @property
    def waypoint_count(self) -> int:
        return len(self.course.waypoints)


@dataclass
class RouteLibrary:
    routes: list[SavedRoute] = field(default_factory=list)

    def route(self, rid: str) -> Optional[SavedRoute]:
        return next((r for r in self.routes if r.id == rid), None)

    def add(self, name: str, course: Course, description: str = "") -> SavedRoute:
        """Save a copy of ``course`` under ``name`` (replacing a route with the same name)."""
        c = copy.deepcopy(course)
        if c.finish == "land":
            c.finish, c.land_at = "rtb", ""
        c.land_at = ""
        old = next((r for r in self.routes if r.name.lower() == name.strip().lower()), None)
        if old is not None:
            old.course, old.description = c, description or old.description
            return old
        r = SavedRoute(name=name.strip(), description=description, course=c)
        self.routes.append(r)
        return r

    def remove(self, rid: str) -> None:
        self.routes = [r for r in self.routes if r.id != rid]

    def to_dict(self) -> dict:
        return {"format": FORMAT, "version": 1, "routes": [_to_plain(r) for r in self.routes]}

    @classmethod
    def from_dict(cls, d: dict) -> "RouteLibrary":
        return cls([_from_plain(SavedRoute, r) for r in (d.get("routes") or []) if isinstance(r, dict)])

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")
        tmp.replace(p)

    @classmethod
    def load(cls, path: str | Path) -> "RouteLibrary":
        p = Path(path)
        if not p.is_file():
            return cls()
        try:
            return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()
