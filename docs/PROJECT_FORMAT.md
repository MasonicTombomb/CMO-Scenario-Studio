# Project file format (`.cmoproj`)

A project is UTF-8 JSON. It is designed to diff well in git: ids are stable, lists keep their order and there is
no derived data. Unknown keys are ignored and missing keys take their defaults, so files from newer or older versions
of the studio load.

```jsonc
{
  "format": "cmo-scenario-studio",
  "version": 1,
  "meta":    { "title", "folder_name", "file_prefix", "author", "inspired_by", "setting", "location", "db_file",
               "complexity", "difficulty", "hypothetical_note", "description_html", "auto_header", "designer_notes" },
  "clock":   { "start": "2030-05-12T04:00:00", "duration_days", "duration_hours", "duration_minutes" },   // Zulu
  "weather": { "temperature", "rainfall", "cloud", "sea_state" },              // at the start
  "forecast": [ { "offset_minutes", "temperature", "rainfall", "cloud", "sea_state" } ],   // later changes
  "build":   { "armed_start", "default_loadout", "verbose", "force_rebuild" },
  "sides":   [ { "id", "name", "tag", "color", "awareness", "proficiency", "computer_only", "start_score",
                 "doctrine": { "use_nuclear_weapons": "no", ... },
                 "postures": { "<other side id>": "F|N|U|H" },
                 "briefing_html", "export_briefing",
                 "orders": { "operation", "originator", "classification", "situation", "mission", "intent",
                             "concept", "enemy_assessment", "mlcoa", "mdcoa", "roe", "sustainment", "command",
                             "exact_positions" } } ],     // briefing pack text; empty = generated
  "units":   [ { "id", "side", "type", "dbid", "db_name", "name", "count", "lat", "lon",
                 "altitude", "depth", "heading", "speed",            // null = default
                 "host", "loadout", "radar_active", "sonar_active", "hold_position", "autodetectable",
                 "proficiency", "reserve", "group", "notes", "extra": { },
                 "course": null | { "waypoints": [ { "lat", "lon", "altitude", "speed", "depth",   // m, kn, m; null = no change
                                                     "name", "radar", "sonar", "ecm", "weapons", "engage",
                                                     "wait_minutes", "signal", "arrive_minutes" } ],
                                    "depart_minutes", "finish": "stop|rtb|land|repeat", "land_at": unitId } } ],
  "reference_points": [ { "id", "side", "name", "lat", "lon", "highlighted", "all_sides" } ],
  "zones":   [ { "id", "side", "name", "points": [[lat, lon], ...], "color", "all_sides", "notes" } ],
  "missions":[ { "id", "side", "name", "mclass", "subtype", "zone", "prosecution_zone", "destination",
                 "units": [ids], "targets": [ids], "options": { }, "notes",
                 "intercept": null | { "logic": "all|any", "in_area", "near", "near_nm", "defend": unitId, ... } } ],
  "events":  [ { "id", "name", "repeatable", "active", "shown", "probability",
                 "triggers":   [ { "type", "params": { } } ],
                 "conditions": [ { "type", "params": { } } ],
                 "actions":    [ { "type", "params": { } } ], "notes" } ],
  "special_actions": [ { "id", "side", "name", "description", "repeatable", "active", "script" } ],
  "scripts": [ { "id", "name", "content", "load_on_init", "notes" } ],
  "formations": [ { "id", "name", "side", "preset", "lead", "members": [ids], "spacing_nm", "heading",
                    "params": { }, "alt_step_m", "mirror", "jitter", "seed", "set_heading", "keep_on_station",
                    "group_in_cmo", "station_type": "Rotating|Fixed", "sprint_drift", "notes" } ],
  "variants":[ { "id", "name", "key", "computer_sides": [ids], "scen_suffix", "description_html" } ],
  "key_values": { "KEY": "value" }
}
```

## Values

- `units[].type`: `Aircraft`, `Ship`, `Submarine`, `Facility`, `GroundUnit`.
- `units[].course.waypoints[]`: settings apply on the leg flown *to* the waypoint. `radar`, `sonar`, `ecm`:
  `""` (no change), `active`, `passive`; `weapons`: `""`, `free`, `tight`, `hold`; `engage`: `""`, `leave` (may leave
  the course to attack), `stay`; `wait_minutes`: wait there on arrival (ground units stop, others circle);
  `signal`: flag set to true on arrival; `depth`: submarines only, metres below the surface (0 = surfaced);
  `arrive_minutes`: time on target, minutes after the start (planning only: the course window's *Time it* turns it
  into a departure and waits).
- `forecast[]`: `offset_minutes` after the start (entries at 0 or less are ignored; the start weather is `weather`),
  `rainfall` 0-50, `cloud` 0-1, `sea_state` 0-9.
- `units[].course.finish`: `stop` (carry on), `rtb` (return to its base), `land` (land at `land_at`, a base of the
  same side), `repeat` (fly the course again). `depart_minutes` counts from the scenario start.
- `missions[].mclass`: `patrol` (`aaw asw naval land mixed sead`), `strike` (`air land sea sub`), `support`,
  `ferry`, `mining`, `mineclearing`, `cargo`, `intercept` (conditions in `intercept`; the fields and their defaults are
  the `Intercept` dataclass in [`model/project.py`](../src/cmo_studio/model/project.py)).
- `formations[].preset` is a key from [`model/formations.py`](../src/cmo_studio/model/formations.py) (`line_ahead`, `circular_screen`, `finger_four`, `ground_wedge`...); `params` holds only the values that differ from the preset.
- Trigger, condition and action types and their `params` are listed in
  [`src/cmo_studio/model/enums.py`](../src/cmo_studio/model/enums.py). Ids inside params refer to project objects
  (`SpecificUnit`, `Area`, `Mission`, `Side`...). `Raw` types hold a Lua table literal in `params.Spec`.

## Generating projects from code

The model is plain dataclasses, so scenarios can be generated or bulk-edited in Python:

```python
from cmo_studio.model import Unit, new_project
from cmo_studio.export import Exporter

p = new_project("Generated", "DB3K_519.db3")
blue = p.sides[0]
p.units.append(Unit(side=blue.id, type="Ship", dbid=2814, name="Test", lat=59.8, lon=26.5))
p.save("generated.cmoproj")
Exporter(p).write("build/")
```

[`examples/make_example.py`](../examples/make_example.py) builds the full *Baltic Sentinel* example this way.
