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
9. Key values (initial values, `STUDIO_VARIANT`, reset of event once-flags and course progress).
10. Courses — `StudioRoutesTick(true)`: units already under way at the start (airborne aircraft, ships, ground
    units) with a departure at the start get their plotted course now. Aircraft in a base wait for the
    *Studio: unit courses* event.
11. Events — triggers, native conditions, the generated Lua action, native actions.
12. Special actions.
13. BUILD REPORT with counts, failures, warnings and the exact editor steps.

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
| `StudioUnderWay(unit)` | True if the unit is airborne or under way (not an aircraft or boat sitting in a base). |
| `StudioRoutesTick(atBuild)` | The course manager (below). Returns how many courses it gave out. |

`STUDIO.TITLE`, `STUDIO.PATH`, `STUDIO.START` (Unix time of the scenario start), `STUDIO.SIDES` and
`STUDIO.RESERVES` and `STUDIO.ROUTES` are set by `LuaInit.lua`. If not already defined, the short aliases `Log`, `Flag`, `SetFlag`,
`GetKV`, `SetKV` and `RunScript` point to the studio functions.

### Courses (`STUDIO.ROUTES`)

Units with a plotted course are listed in `LuaInit.lua`:

```lua
STUDIO.ROUTES = {
  { id = '<unit id>', side = 'United Kingdom', names = { 'TARTAN #1', 'TARTAN #2' },
    kind = 'Aircraft',
    wps = { { lat = 58.5, lon = -1.0, alt = 9000, spd = 450, name = 'IP', radar = 'passive', ecm = 'active',
              wcs = 'free', engage = 'leave', wait = 10, flag = 'STRIKE_AT_IP' },
            { lat = 57.0, lon = 1.0 } },               -- only lat and lon are always there
    depart = 1904531400,                       -- Unix time (scenario start + Depart minutes)
    finish = 'land',                           -- 'stop' | 'rtb' | 'land' | 'repeat'
    land = { side = 'United Kingdom', name = 'Coningsby Hangar (4x Medium)' } },
}
```

When any course exists, the export adds a repeatable event **Studio: unit courses** (*Regular time*, every minute)
whose action is `StudioRoutesTick()`. For each copy of each unit it keeps a state in the key value
`STUDIO_RT_<id>_<n>`, the waypoint it is heading for in `STUDIO_RT_<id>_<n>_leg` and the end of a wait in
`STUDIO_RT_<id>_<n>_until`, so progress survives saving and loading:

| State | Meaning and next step |
| --- | --- |
| `wait` | Before `depart`. At `depart`: a unit under way is given the course (`enroute`); an aircraft in a base is sent off with `ScenEdit_SetUnit({guid=, launch=true})` (`launched`). |
| `launched` | Taking off. Once airborne it is given the course (`enroute`). |
| `enroute` | Flying the course. Each tick compares the waypoints left in `unit.course` with the leg it was on: for every waypoint passed it sets the waypoint's `flag`; a waypoint with `wait` starts a `loiter`; otherwise the next leg's settings are applied. When none are left the finish order runs and the state becomes `done` (or `enroute` again for `repeat`). |
| `loiter` | Circling a waypoint (four points 5 nm round it for aircraft, 0.5 nm for others) until `_until`, then given the rest of the course. |
| `done` | Nothing more to do. |

A leg's settings are applied when it starts: `alt` and `spd` with `ScenEdit_SetUnit({guid=, manualAltitude=})`
and `manualSpeed=`; `radar`, `sonar`, `ecm` with `ScenEdit_SetEMCON('Unit', guid, 'Radar=Active;OECM=Passive')`;
`wcs` (free 0, tight 1, hold 2, for air, surface, subsurface and land) and `engage` (`ignore_plotted_course` = `'yes'` / `'no'`, as on the Sides tab) with
`ScenEdit_SetDoctrine({side=, unitname=}, {...})`. A setting CMO refuses is logged and the rest go on.

The course is given with `ScenEdit_SetUnit({guid=, course={ {latitude=, longitude=, TypeOf='ManualPlottedCourseWaypoint', desiredAltitude=, desiredSpeed=, name=}, ... }})`;
if CMO refuses the altitude, speed or name fields, the plain waypoints are used. `land` sets `base=` to the landing base's
GUID, then `rtb=true`; `rtb` sets `rtb=true`. A unit that is not found (destroyed, or a reinforcement not yet
arrived) is skipped until it appears.

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
