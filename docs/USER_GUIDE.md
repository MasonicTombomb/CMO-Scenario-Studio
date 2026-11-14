# User guide

CMO Scenario Studio keeps a scenario as a **project** (`.cmoproj`) and turns it into a **build script** that CMO runs
once to create the `.scen`. You edit the project here; CMO does the building. This is the same approach as
*If Russia Wins* and the official Lua-driven scenarios, and it means a scenario can be rebuilt at any time from text
files that live happily in git.

- [The window](#the-window)
- [Typical workflow](#typical-workflow)
- [Tabs](#tabs)
- [Database browser](#database-browser)
- [Events in depth](#events-in-depth)
- [Variants](#variants)
- [Validation and dry-run](#validation-and-dry-run)
- [Exporting](#exporting)
- [Importing an existing scenario](#importing-an-existing-scenario)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

## The window

- **Tabs** (centre): Scenario, Sides, Map, Units, Areas, Missions, Events, Special actions, Scripts, Briefings,
  Build & Export.
- **Database** dock (right): the DB3000/CWDB browser. It is available on every tab.
- **Issues** dock (bottom): live validation. Double-click an issue to jump to it.
- Every change can be undone (**Ctrl+Z** / **Ctrl+Y**). The title shows `*` while there are unsaved changes.

## Typical workflow

1. **File > New scenario**: title, database, starting sides.
2. **Scenario** tab: setting, author, start time (Zulu), duration, weather.
3. **Sides** tab: rename sides, set colours, awareness, proficiency, doctrine and postures. Mark AI-only sides
   (e.g. civilians) as *computer-controlled only*.
4. **Map** tab: build the order of battle.
   - Search the **Database** dock, select an entry and press **Place on map**, then click the map (keep clicking to
     place more; **Esc** stops). Double-clicking a row does the same.
   - For an airbase, place an airfield facility (search "Single-Unit Airfield"), select it, choose an aircraft in the
     browser and press **Add to selected base**. The squadron gets a count and its first combat loadout; change the
     loadout in the inspector, or double-click a loadout in the browser.
   - **Draw area** for patrol zones and trigger areas: click corners, double-click or **Enter** to finish.
   - **Reference point** for markers (tick *Create on every side* for objective markers both players see).
5. **Missions** tab: create missions, pick their area, assign units and (strike) targets.
6. **Events** tab: start from a template (*New ▾*) and adjust.
7. **Briefings** tab: write the description and a briefing per side. *Insert ▾ > Order of battle* lists forces from
   the project.
8. **Build & Export**: *Validate*, *Dry-run build*, *Export*. Then build in CMO (see the README).

## Tabs

### Scenario
Title, setting (the line shown in CMO's scenario list), location, author, ratings and an optional note
("This is a hypothetical scenario"). *Folder name* and *Page prefix* default from the title
(`If Russia Wins` → `Lua\If Russia Wins\` and `IfRussiaWins_Desc.html`).

**Build options**: *Aircraft start armed* uses each aircraft's chosen loadout; untick it to start every aircraft in
reserve (loadout 3) so players arm them. *Console detail* controls how much the builder prints.
*FORCE_REBUILD* builds even if the sides already contain units (normally the builder refuses, to avoid
building twice into the same scenario).

**Initial key values** are written with `ScenEdit_SetKeyValue` during the build — handy for scenario state your
scripts read with `StudioGetKV`.

### Sides
The posture matrix reads "row side's view of column side". *Make symmetric* copies each row to its mirror.
Doctrine fields left at *(default)* are not touched. The *Build variants* box is described [below](#variants).

### Map
| Tool | Use |
| --- | --- |
| Select / move | Click to select; drag units, reference points or a selected area's corners |
| Place unit | Places the entry chosen in the Database dock |
| Reference point | Click to add |
| Draw area | Click corners; double-click/Enter finishes, Backspace removes the last corner, right-click too |
| Measure | Click a route; shows km, nautical miles and bearing per leg |

*New objects on* chooses the side for anything you add. Right-click the map for a context menu (place here, copy
coordinates, measure from here...). Aircraft and boats that start at a base are drawn at the base with a count badge.
Reinforcements are drawn faded with a dashed outline.

Map tiles are cached on disk. *None (offline grid)* works without internet; *Custom* accepts any XYZ URL template.

### Units
All units in one table with filters. Select several rows for bulk actions: assign to a mission, set a group tag,
toggle *reinforcement*, delete. The right-hand inspector is the same as on the map.

Unit fields worth knowing:
- **Count**: builds `<name> #1 .. #n` — use it for squadrons and identical platoons.
- **Starts at**: a host (airbase facility or ship). Aircraft are created in the host; other units fall back to the
  host's position.
- **Reinforcement**: not built at the start. An event's *Spawn unit* action creates it (once), assigns it to the
  missions it is listed in, and places aircraft at their host.
- **Extra fields**: any `ScenEdit_SetUnit` field, applied after creation (e.g. `fuel`, `outOfComms`).

### Areas
Lists of areas and reference points with editors. An area named `CAP_WEST` with four corners becomes reference
points `CAP_WEST-1` .. `CAP_WEST-4` on its side (or on every side). Missions use areas of their own side, or areas
marked *all sides*.

### Missions
| Class | Needs |
| --- | --- |
| Patrol (AAW, ASW, naval, land, mixed, SEAD) | an area with 3+ corners; optional prosecution area |
| Strike (air, land, sea, sub) | targets (enemy units) |
| Support | an area (orbit / track) |
| Ferry | a destination base |
| Mining / mine clearing | an area |
| Cargo | — |

Options left at *(default)* are not sent. *Other fields* takes any `ScenEdit_SetMission` field; unsupported ones are
reported as warnings in the build report rather than stopping the build.

### Events
See [Events in depth](#events-in-depth).

### Special actions
Buttons players can press in CMO. Each runs Lua with the studio runtime loaded. They are skipped for
computer-controlled sides (including the AI side of a variant).

### Scripts
Your own Lua files, exported as `Lua\<Folder>\<name>.lua`. Run them from an event (*Run project script*), or tick
*Load on init* to run them every time the scenario loads — the place for shared functions. *Insert snippet* has
common patterns; *Check syntax* compiles with CMO's own Lua.

### Briefings
HTML pages in CMO's briefing style. The scenario description can get an automatic header (author, date, location,
playable sides, duration, ratings). Variant texts are appended to the description for that variant.

### Build & Export
See [Validation and dry-run](#validation-and-dry-run) and [Exporting](#exporting). The file list shows exactly what
will be written.

## Database browser

- Type: aircraft, ships, submarines, facilities, ground units, satellites, weapons, sensors.
- Search: all words must match the name; a number also matches the DBID.
- *In service in scenario year* filters by commissioning/decommissioning year; *Show deprecated* includes entries
  CMO has retired.
- Tabs show sensors, weapons with default loads, aircraft loadouts (hover for the weapons, double-click to give the
  selected aircraft that loadout), hangars/docks and the DB description.
- **Use for selected unit** swaps the selected unit to the browsed entry (type changes are confirmed).

## Events in depth

An event has **triggers** (any one fires it), **conditions** (all must be true), a **probability** and **actions**
(run in order).

Triggers that CMO supports natively are created as real CMO triggers. Two studio triggers are compiled for you:

- **At date/time (once)** and **Minutes after start (once)** become a one-minute *RegularTime* trigger plus a time
  check at the top of the event's script.

Conditions, probability and the time checks are written as guards at the top of the event's **single Lua action**.
To keep a one-shot event's meaning, an event with guards is made *repeatable* in CMO and the once-only rule moves into
Lua (a `STUDIO_EVT_<id>` key value), so it only counts as fired when its actions actually run.

Action types: show message (to one side, or every side if blank), change score, end scenario,
activate/deactivate mission, set flag/key value, run project script, Lua code, spawn reinforcement, and *native*
(a raw Lua table passed to `ScenEdit_SetAction`). Native triggers/conditions/actions are the escape hatch for
anything the forms do not cover; note that guards cannot stop native actions.

The *Generated Lua* tab shows exactly what will be exported.

## Variants

A variant is another build of the same scenario, typically "Play as NATO" with Russia computer-controlled. Each has a
**key** (`PLAY_NATO`), the extra **computer-controlled sides**, a **.scen suffix** and an optional description text
(edited on the Briefings tab). The export writes `Build_PLAY_NATO.lua`, which sets the variant and runs the main
builder. Special actions of computer-controlled sides are skipped in that build.

## Validation and dry-run

The **Issues** dock re-checks the project after every change: missing database entries, deprecated or out-of-service
classes, loadouts that do not belong to the aircraft, units on another side's mission, patrol areas with fewer than
three corners, events without triggers, spawn actions on units that are not reinforcements, name clashes, and more.

**Dry-run build** (F5) exports to a temporary folder and runs `Build_Scenario.lua` inside CMO's own `lua54.dll`
against `Studio_Mock.lua`, a strict stand-in for the ScenEdit API that checks sides, hosts, loadouts, mission areas,
reference points and event wiring. It then runs every event and special-action script once to catch run-time
errors. The output is the same BUILD REPORT CMO's console will show.

The mock cannot know everything CMO enforces (for example whether a runway is long enough), so the in-game build
report is still the final word; every API call in the builder is protected and failures are listed there.

## Exporting

- **Install into the CMO folder** writes `Lua\<Folder>\` and `Scenarios\<Folder>\` in your CMO install.
- **Export to a folder** writes the same tree plus a README — ideal for a scenario repository.
- **Export as a .zip** for sharing.

Safety: the studio records the files it writes in `Lua\<Folder>\.studio_manifest.json`. A re-export replaces only
those files (and, if ticked, deletes ones it wrote before that are no longer generated). Your `.scen` files are
never touched. If the folder exists but was not written by the studio (e.g. a hand-written scenario with the same
name) you are warned and shown the files that would be replaced. With *Back up* ticked, replaced files are zipped
to the studio's data folder first.

## Importing an existing scenario

**File > Import order of battle from a Build_Scenario.lua** reads the data tables of an *If Russia Wins*-style
builder (`X.CFG`, `X.DB`, `X.LOADOUTS`, `X.BASES`, `X.UNITS`, `X.US_REINFORCE`, `X.ZONES`, `X.MISSIONS`) into a
new project: sides, clock, weather, bases with squadrons and loadouts, units with EMCON/hold flags and groups,
reinforcements, areas and missions. Events and runtime scripts are not imported.

## Keyboard shortcuts

| Keys | Action |
| --- | --- |
| Ctrl+N / Ctrl+O / Ctrl+S | New / open / save |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| Ctrl+1 .. Ctrl+9 | Switch tab |
| Ctrl+E | Build & Export tab |
| F5 | Dry-run build |
| F7 | Validate |
| Map: Esc / Delete / + / − | Cancel tool or deselect / delete selection / zoom |

## Troubleshooting

- **No databases listed** — set the CMO folder in *File > Settings* (the folder with `Command.exe` and `DB\`).
- **Dry-run says lua54.dll not found** — same; it lives in the CMO folder. The studio needs 64-bit Python.
- **Blank map** — check your internet connection or choose another tile source; *None (offline grid)* always works.
- **"Side already has units" in CMO** — the builder refuses to build twice. Start from a new blank scenario, or tick
  *FORCE_REBUILD* in Build options.
- **An event does not fire** — check the Generated Lua tab; set `STUDIO.DEBUG = true` in the Lua console for
  verbose output from `StudioDebug`.
