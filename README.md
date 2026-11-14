# CMO Scenario Studio

A desktop scenario creation suite for **Command: Modern Operations** (CMO), written in Python with PyQt6.

Design a scenario on a real map with live values from your own DB3000 / CWDB database, then export it as the
same structured folder the official Lua-driven scenarios use: a one-shot `Build_Scenario.lua` that builds every
side, unit, mission and event through CMO's Lua API, the runtime scripts the events call, and the
`[LOADDOC]` description and briefing pages.

![Map editor](docs/images/map.png)

## Features

- **Database browser** — search DB3000/CWDB (read-only) by name, DBID, country and in-service year; see images,
  sensors, weapons, aircraft loadouts (with their weapons), hangar/dock facilities and the DB description text.
- **Map editor** — slippy map (Esri, OpenStreetMap, OpenTopoMap or offline grid) to place units, build airbases
  with squadrons, draw patrol/trigger areas, drop reference points and measure ranges and bearings.
- **Order of battle** — sortable unit table, hosted aircraft and boats, counts (`Sqn #1..#n`), loadouts,
  radar/sonar EMCON, hold position, proficiency, reinforcements spawned later by events, extra `ScenEdit_SetUnit` fields.
- **Sides** — awareness, proficiency, computer-only, starting score, doctrine and a full posture matrix.
- **Missions** — patrol, strike, support, ferry, mining, mine clearing and cargo, with areas, prosecution areas,
  assigned units, strike targets and `ScenEdit_SetMission` options.
- **Events** — triggers (time, date, delay, unit destroyed/damaged/detected, area entry, points...), conditions,
  probability and actions (message, score, end scenario, mission on/off, flags, spawn reinforcements, Lua), with
  templates and a live preview of the generated Lua.
- **Scripts & special actions** — Lua editor with highlighting, snippets and syntax check in CMO's own Lua 5.4.
- **Briefings** — HTML editor with live preview, auto header and an order-of-battle generator.
- **Build variants** — "Play as X" versions where other sides are computer-controlled, each with its own launcher
  and description page (as in *If Russia Wins*).
- **Validation and dry-run** — over 40 checks (including every DBID and loadout against the database), plus a
  dry-run that executes the generated builder and every event script in CMO's `lua54.dll` against a strict mock
  of the ScenEdit API — before you ever open CMO.
- **Export** — install straight into the CMO folder (only studio-written files are replaced, with a backup zip),
  to any folder (e.g. a git repository) or as a zip.
- **Import** — read the order of battle from an existing *If Russia Wins*-style `Build_Scenario.lua`.
- Undo/redo for every edit, autosave, recent files, a headless command line for CI.

## Screenshots

| Events with generated Lua | Missions |
| --- | --- |
| ![Events](docs/images/events.png) | ![Missions](docs/images/missions.png) |
| **Briefings with live preview** | **Build & Export with dry-run** |
| ![Briefings](docs/images/briefings.png) | ![Export](docs/images/export.png) |

## Download

Get **`CMO-Scenario-Studio-<version>-win64.zip`** from the
[Releases page](https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases), unzip it anywhere and run
`CMO-Scenario-Studio.exe`; no Python needed. Windows may show a SmartScreen warning because the exe is not
code-signed (*More info > Run anyway*).

To run from source instead, see [Quick start](#quick-start).

## Requirements

- Windows with Command: Modern Operations installed (the studio reads `DB\*.db3` and uses `lua54.dll`)
- Python 3.10+ (64-bit)
- PyQt6

The project format, exporter and tests also run without CMO; the database browser, DB checks and dry-run need it.

## Quick start

```bash
git clone <this repository>
cd CMO-Scenario-Studio
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_studio.py
```

or install it as a command: `pip install -e .` then `cmo-studio`.

On first start the studio looks for CMO in your Steam libraries; if it is elsewhere, choose it in
**File > Settings**. Then open `examples/Baltic Sentinel.cmoproj` to see a complete scenario.

## From project to playable .scen

1. **Build & Export** tab → *Validate*, *Dry-run build*, then *Export* → *Install into the CMO folder*.
2. In CMO: **Create New Blank Scenario** with the same database.
3. Editor → **Lua Script Console**:
   ```lua
   ScenEdit_RunScript('/Your Scenario/Build_Scenario.lua')
   ```
4. Paste the `[LOADDOC]` lines from the build report into the scenario description and side briefings,
   and save as `Scenarios\Your Scenario\Your Scenario.scen`.

Variants: start from a new blank scenario and run `Build_<KEY>.lua` instead.

## Exported layout

```
Lua/<Scenario>/                     Scenarios/<Scenario>/
  Build_Scenario.lua                  <Prefix>_Desc.html
  Build_<VARIANT>.lua                 <Prefix>_Desc_<VARIANT>.html
  LuaInit.lua                         <Prefix>_Briefing_<SIDE>.html
  Studio_Runtime.lua                  briefing_style_dark.css
  <YourScripts>.lua                   (your .scen files go here)
  project.cmoproj
  README.txt
```

See [`examples/output`](examples/output) for a real export.

## Documentation

- [User guide](docs/USER_GUIDE.md) — every tab, workflows and tips
- [Export format and Lua runtime](docs/EXPORT_FORMAT.md) — what each file does, the `Studio*` Lua API
- [Project file format](docs/PROJECT_FORMAT.md) — the `.cmoproj` JSON schema
- [Database access](docs/DATABASE.md) — which DB3000 tables are read and how
- [Architecture](docs/ARCHITECTURE.md) — code layout for contributors
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

## Command line

```bash
cmo-studio "examples/Baltic Sentinel.cmoproj"                  # open a project
cmo-studio project.cmoproj --dry-run --cmo "D:/Steam/.../Command - Modern Operations"
cmo-studio project.cmoproj --export ./build                   # export without the GUI
```

## Building the exe

```bash
pip install -e .[dev] pyinstaller
python packaging/build_release.py
```

This writes `release/CMO-Scenario-Studio-<version>-win64.zip` and its `.sha256`, after a smoke test of the frozen
exe. Pushing a tag such as `v1.0.0` makes GitHub Actions build the same zip and publish a release with the notes in
`docs/releases/<version>.md`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests that need CMO (database, Lua) find it automatically or via `CMO_DIR`; they are skipped otherwise.

## Disclaimer

Not affiliated with or endorsed by Matrix Games, Slitherine or WarfareSims. *Command: Modern Operations* and its
databases are their property; this tool reads them from your own installation and redistributes none of their
data. Map tiles are provided by their respective services under their terms.

## License

MIT — see [LICENSE](LICENSE).
