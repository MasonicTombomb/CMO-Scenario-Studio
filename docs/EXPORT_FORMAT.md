# Export format and Lua runtime

## Files

| File | Purpose |
| --- | --- |
| `Lua/<F>/Build_Scenario.lua` | One-off builder. A data table `D` followed by the builder engine. Run once in the editor's Lua console of a blank scenario. |
| `Lua/<F>/Build_<KEY>.lua` | Variant launcher: sets `STUDIO_BUILD_VARIANT = '<KEY>'` and runs `Build_Scenario.lua`. |
| `Lua/<F>/LuaInit.lua` | Run at scenario load (the builder does not add this event automatically — see below) and by every event script that finds the runtime missing. Defines `STUDIO.*`, loads `Studio_Runtime.lua`, runs scripts marked *load on init*, sets `STUDIO_LUAINIT_LOADED`. |
| `Lua/<F>/Studio_Runtime.lua` | Helper library used by generated event code (see API below). |
| `Lua/<F>/<Script>.lua` | Your project scripts. |
| `Lua/<F>/project.cmoproj` | The project, so the export can be reopened in the studio. |
| `Lua/<F>/README.txt` | Build instructions with the exact `[LOADDOC]` lines. |
| `Lua/<F>/.studio_manifest.json` | Files the studio wrote (used for safe re-exports). |
| `Scenarios/<F>/<P>_Desc.html` | Scenario description (`[LOADDOC]<P>_Desc.html[/LOADDOC]`). |
| `Scenarios/<F>/<P>_Desc_<KEY>.html` | Variant description, if the variant has its own text. |
| `Scenarios/<F>/<P>_Briefing_<TAG>.html` | Side briefing. |
| `Scenarios/<F>/briefing_style_dark.css` | The pages' stylesheet. |

`<F>` is the folder name, `<P>` the page prefix, `<TAG>` the side tag (or name) in CamelCase.

All `.lua` and `.html` files use Windows line endings, like CMO's own.

### How events load the runtime

Every generated event action and special action starts with

```lua
if not STUDIO_LUAINIT_LOADED then ScenEdit_RunScript('/<F>/LuaInit.lua') end
```

so the runtime is always available, including straight after the build and after loading a saved game. Because of
this, no separate *Scenario Loaded* event is required (add one yourself with a *Run project script* action if you want
code to run on every load).

The events reference the script folder at run time, so `Lua\<F>\` must exist on the machine that runs the scenario
(the host in multiplayer), exactly as with the official Lua scenarios.

## Build order

1. Refuse to run if any side already has units (unless `FORCE_REBUILD`).
2. Load `LuaInit.lua`.
3. Sides (added or reused), postures, awareness, proficiency, doctrine, starting score, computer-only flag.
4. Start time, duration, current time, weather.
5. Reference points and area points.
6. Units — hosts first; then EMCON, hold position, auto-detectable, proficiency, speed, extra fields.
7. Formations — `unit.group = 'Name'` for the lead and members, then each member's station with
   `ScenEdit_SetUnit({guid=, formation={bearing=, distance=, type=, sprint=}})` (retried with bearing and
   distance only). Units are already on station, so a refusal only leaves them ungrouped (reported).
8. Missions — options, prosecution area, assigned units, strike targets.
9. Key values (initial values, `STUDIO_VARIANT`, reset of event once-flags).
10. Events — triggers, native conditions, the generated Lua action, native actions.
11. Special actions.
12. BUILD REPORT with counts, failures, warnings and the exact editor steps.

Every API call is wrapped in `pcall`; a failure becomes a warning in the report instead of stopping the build. Some
calls have fallbacks (date order, submarine type name, ground units as facilities, refused loadouts → reserve).

## The `D` table

```lua
D.CFG      = { TITLE, FOLDER, PATH, SETTING, DB, START = {year..sec}, DURATION = {d,h,m},
               WEATHER = {temp, rain, cloud, sea}, ARMED_START, DEFAULT_LOADOUT, VERBOSE, FORCE_REBUILD }
D.PAGES    = { desc = '...', briefings = { [sideName] = '...' } }
D.SIDES    = { { name, awareness, proficiency, computer, score, doctrine = {...} }, ... }
D.POSTURES = { { 'A', 'B', 'H' }, ... }
D.VARIANTS = { KEY = { name, computer = {sideNames}, scen, desc } }
D.RPS      = { { side, name, lat, lon, hl }, ... }
D.ZONES    = { { id, name, sides = {...}, pts = {{lat, lon}, ...} }, ... }
D.UNITS    = { { id, side, type, dbid, name, count?, host?, lat?, lon?, alt?, depth?, heading?, speed?,
                 loadout?, radar?, sonar?, hold?, auto?, prof?, set? }, ... }
D.FORMATIONS = { { name, lead = unitId, stype = 'Rotating'|'Fixed', sprint,
                   members = { { id, bearing, dist }, ... } }, ... }   -- bearing deg, dist nm
D.MISSIONS = { { side, name, class, sub?, zone?, pzone?, dest?, units = {ids}, targets = {ids}, opts? }, ... }
D.KV       = { { key, value }, ... }
D.EVENTS   = { { key, name, repeatable, active, shown, triggers = { {name, spec, unit?, area?} },
                 conditions = { {name, spec} }, script, actions = { {name, spec} } }, ... }
D.SPECIALS = { { side, name, desc, repeatable, active, script }, ... }
```

Unit and area references are studio ids; the engine maps them to GUIDs and reference-point names as it builds.

## Runtime API (`Studio_Runtime.lua`)

| Function | Description |
| --- | --- |
| `StudioLog(text)` / `StudioDebug(text)` | Print to the Lua console (debug only when `STUDIO.DEBUG`). |
| `StudioGetKV(key, default)` / `StudioSetKV(key, value)` | Key values (saved in the .scen). |
| `StudioGetNumKV(key, default)` | Numeric key value. |
| `StudioFlag(key)` / `StudioSetFlag(key, bool)` | Boolean key values. |
| `StudioRunScript(name)` | Run `Lua/<F>/<name>.lua`. |
| `StudioMsg(side, html)` / `StudioMsgAll(html)` | Message box to one / every side. |
| `StudioScore(side)` / `StudioAddScore(side, delta, reason)` | Read / change score. |
| `StudioGetUnit(sel)` / `StudioUnitAlive(sel)` | `sel` is a GUID or `{side=, name=}`. |
| `StudioMissionStatus(side, mission, active)` | Activate or deactivate a mission. |
| `StudioRandomPosition(latMin, latMax, lonMin, lonMax)` | Random point in a box. |
| `StudioSpawn(id)` | Spawn a project reinforcement once; returns the units. |

`STUDIO.TITLE`, `STUDIO.PATH`, `STUDIO.START` (Unix time of the scenario start), `STUDIO.SIDES` and
`STUDIO.RESERVES` are set by `LuaInit.lua`. If not already defined, the short aliases `Log`, `Flag`, `SetFlag`,
`GetKV`, `SetKV` and `RunScript` point to the studio functions.

### Generated event script

```lua
-- Event: Hogland landing
if StudioFlag("STUDIO_EVT_1a2b3c4d") then return end      -- once-only (guarded one-shot events)
if (tonumber(ScenEdit_CurrentTime()) or 0) < 1904529600 then return end   -- date/time trigger
if not (not StudioFlag("BS_HOGLAND_LOST")) then return end                -- conditions
if math.random(100) > 75 then return end                                  -- probability
StudioSetFlag("STUDIO_EVT_1a2b3c4d", true)
StudioSetKV("BS_HOGLAND_LOST", "true")                                     -- actions
StudioAddScore("Russia", 50, "Russian ships at Hogland")
```
