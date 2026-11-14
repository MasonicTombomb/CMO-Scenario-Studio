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
  "weather": { "temperature", "rainfall", "cloud", "sea_state" },
  "build":   { "armed_start", "default_loadout", "verbose", "force_rebuild" },
  "sides":   [ { "id", "name", "tag", "color", "awareness", "proficiency", "computer_only", "start_score",
                 "doctrine": { "use_nuclear_weapons": "no", ... },
                 "postures": { "<other side id>": "F|N|U|H" },
                 "briefing_html", "export_briefing" } ],
  "units":   [ { "id", "side", "type", "dbid", "db_name", "name", "count", "lat", "lon",
                 "altitude", "depth", "heading", "speed",            // null = default
                 "host", "loadout", "radar_active", "sonar_active", "hold_position", "autodetectable",
                 "proficiency", "reserve", "group", "notes", "extra": { } } ],
  "reference_points": [ { "id", "side", "name", "lat", "lon", "highlighted", "all_sides" } ],
  "zones":   [ { "id", "side", "name", "points": [[lat, lon], ...], "color", "all_sides", "notes" } ],
  "missions":[ { "id", "side", "name", "mclass", "subtype", "zone", "prosecution_zone", "destination",
                 "units": [ids], "targets": [ids], "options": { }, "notes" } ],
  "events":  [ { "id", "name", "repeatable", "active", "shown", "probability",
                 "triggers":   [ { "type", "params": { } } ],
                 "conditions": [ { "type", "params": { } } ],
                 "actions":    [ { "type", "params": { } } ], "notes" } ],
  "special_actions": [ { "id", "side", "name", "description", "repeatable", "active", "script" } ],
  "scripts": [ { "id", "name", "content", "load_on_init", "notes" } ],
  "variants":[ { "id", "name", "key", "computer_sides": [ids], "scen_suffix", "description_html" } ],
  "key_values": { "KEY": "value" }
}
```

## Values

- `units[].type`: `Aircraft`, `Ship`, `Submarine`, `Facility`, `GroundUnit`.
- `missions[].mclass`: `patrol` (`aaw asw naval land mixed sead`), `strike` (`air land sea sub`), `support`,
  `ferry`, `mining`, `mineclearing`, `cargo`.
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
