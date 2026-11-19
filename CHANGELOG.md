# Changelog

## 1.8.1 — 2026-11-19

- **Fixed**: a leg's *Targets* setting (leave the course to attack / stay on it) sent CMO `true`/`false`; it now
  sends `yes`/`no`, like the Sides tab's *Ignore plotted course* doctrine.
- Tests: ships, submarines and ground units play a course through the dry-run (departure, leg speed, sensors,
  weapons, wait and signal), not only aircraft.
- Docs: README feature list, architecture notes, glossary (course, leg, waypoint, signal), FAQ and keyboard table
  cover courses; the manual lists which leg settings each kind of unit uses.

## 1.8.0 — 2026-11-19

- **The course window.** Courses now open in their own window (**Edit course...** in the inspector, **Course...**
  on the map toolbar, or right-click a unit) instead of a box in the inspector:
  - a map to plot, insert, drag, reorder and reverse waypoints, with the selected waypoint ringed;
  - a table of legs with the altitude, speed, radar and weapons in force, waits, leg length and estimated arrival;
  - a **flight profile**: altitude and speed along the route, with radar, jammer (or sonar) and weapons strips,
    waypoint numbers, waits and signals; click a leg to select it;
  - **settings for each leg**: name, altitude, speed, radar, sonar, jammers, weapons free / tight / hold, whether to
    leave the course to attack, a **wait** (circle the waypoint for some minutes) and a **signal** (a flag set on
    arrival that events can react to); **Same for every leg** copies one leg's settings to all;
  - OK keeps the course as one undoable change; Cancel throws it away.
- In CMO the course event applies each leg's settings as the leg starts (altitude, speed, EMCON, weapon control,
  attack behaviour), circles at waypoints with a wait, and sets signals on arrival. The dry-run plays this through.
- The inspector's Course box is now a one-line summary with **Edit course...** and **Clear**. The Timeline,
  inspector and Issues panel use the same estimates; new checks for signal names and altitudes on ships.

## 1.7.0 — 2026-11-19

- **Plotted courses.** Give any unit a route to follow, waypoint by waypoint, to script a computer side's
  movements without a mission:
  - select a unit and click **Plot course** on the map toolbar (or right-click > **Plot course...**), then click the
    waypoints; the course is drawn on the map with numbered waypoints you can drag; a **Courses** layer shows or
    hides them;
  - a **Course** box in the unit inspector lists the waypoints with optional altitude and speed per leg, reorders,
    reverses or clears them, and sets **Depart** (minutes after the start) and **At the end**: carry on, return to
    base, **land at another base**, or fly the course again (loop);
  - aircraft in a base take off at their departure time, fly the course, then return or land at the chosen base -
    for example *take off from Lossiemouth at H+30, fly the route, land at Coningsby*; units already moving get their
    course at the build; reinforcements get theirs when they arrive;
  - in CMO a new event, **Studio: unit courses**, runs each minute and keeps each unit's progress in key values, so
    saved games carry on correctly; the dry-run plays it through;
  - the Timeline shows when each unit departs, and the Issues panel checks courses (facilities with a course,
    waypoints off the map, departures after the end, landing bases of another side or without room, units that also
    have a mission or follow a formation lead).

## 1.6.2 — 2026-11-19

- **Fixed: aircraft missing after the build when their base cannot hold them.** Aircraft based on a runway,
  taxiway or tower (for example a part of a template air base), on a facility too small for them, or on a full
  shelter, failed with a .NET exception and the build wrongly reported *loadout refused, placed in reserve*. Now:
  - the build tries the other hangars, shelters and aprons of the same site and reports *X cannot take it, based at Y
    instead*; it only reports a refused loadout when the reserve loadout is what made it work, and otherwise names
    the base as the cause;
  - the Issues panel shows an error for aircraft whose base has no hangar, shelter or parking that fits them, and a
    warning when more aircraft start at a base than it has room for (from CMO's database);
  - **Add to selected base** will not put aircraft into a unit that cannot hold them; on a template site it offers
    the site's hangars, shelters and aprons with room, and suggests a squadron size that fits;
  - the dry-run (F5 and `--dry-run`) checks aircraft space like CMO does, so this shows up before building in CMO.

## 1.6.1 — 2026-11-19

- **PDF manuals**: a new 85-page **User Manual** written for complete beginners - installing, a tour of the window,
  a step-by-step first scenario from nothing to playing it in CMO, every tab and dialog with annotated screenshots,
  troubleshooting, questions and answers, keyboard shortcuts, glossary and menu reference - and a 53-page
  **Reference Manual** (formats, exported Lua and runtime API, events in depth, formation layouts, library formats and
  catalogues, database, command line, releasing). Open them from **Help** (F1) or the Start menu; they are also
  attached to every release. Built from Markdown in `docs/manual/` with `tools/make_manuals.py`; annotated
  screenshots from `tools/make_manual_shots.py`.

## 1.6.0 — 2026-11-15

- **Windows installer** (`CMO-Scenario-Studio-<version>-setup.exe`, Inno Setup): installs into Program Files with
  Start-menu shortcuts, optional desktop icon, `.cmoproj` file association and an uninstaller; upgrades replace the
  old program files cleanly. User data stays in the profile. The portable zip is still published.
- **Updates from GitHub**: the installed studio checks the latest GitHub release at start-up (optional) and from
  Help > Check for updates, shows the release notes, downloads the setup, verifies its SHA-256 checksum (and the
  publisher's signature once releases are signed), installs it and restarts. Portable copies link to the release
  page.
- **Code signing support**: the build signs the exe, setup and uninstaller when a certificate is configured
  (`CMO_SIGN_PFX` / `CMO_SIGN_ARGS`, or the `SIGN_PFX_BASE64` / `SIGN_PFX_PASSWORD` secrets in GitHub Actions).
- Saving a project into a read-only folder (such as an example in Program Files) asks where to save instead of
  failing; Save As defaults to Documents.

## 1.5.2 — 2026-11-15

- **UK military sites**: 101 templates of real UK sites at their actual positions (1575 units). 46 air bases
  laid out from OpenStreetMap - 82 runways at their real position, heading and length, 108 hardened aircraft
  shelters, 286 hangars, aprons, control towers, radars, fuel farms and munitions bunkers - plus naval bases
  (Faslane, Coulport, Devonport, Portsmouth, Rosyth, Barrow...), radar heads and Fylingdales, Air Command,
  Northwood, comms and intelligence sites, AWE, munitions depots and garrisons. The placer's **At the real site**
  puts a site where it really is.
- **UK airspace areas**: a new *United Kingdom* region with 74 areas. Official UK AIP boundaries (AIRAC
  2026-10-29) for the London and Scottish FIRs (QRA South and North areas), the danger areas of nine ranges
  (Spadeadam, Tain, Cape Wrath, Hebrides, Holbeach, Donna Nook, Aberporth, Salisbury Plain, Otterburn) and the
  air-to-air refuelling areas AARA 1-14; notional interception sectors (eight, tiling the whole FIR), approach
  zones, 18 CAP stations, AEW orbits, low-flying areas and UK sea exercise areas.
- Templates: real-world `location`, `heading` and `site`; per-part `hdg` (crossing runways) and real runway
  `length`; bundled packs (`templates_*.json`). Save-as-template keeps each unit's heading.
- New built-in templates and areas are merged into your own library files after an update (deleted ones stay
  deleted).

## 1.5.1 — 2026-11-14

- **Patrol area library**: 134 predefined sea and air patrol areas (94 sea, 40 air) in eight regions -
  Europe, Arctic, Middle East, Africa, Asia, Oceania, North America and South America - from the Bay of Biscay,
  GIUK gaps and Baltic to Hormuz, the Taiwan Strait, the South China Sea and the Falklands TEZ, plus CAP and QRA
  boxes, AEW orbits and tanker tracks. Browse by region and sea/air with a map preview and add one or several as
  areas, optionally with a suggested patrol or support mission (Ctrl+Shift+A, map toolbar and right-click, Areas
  tab, Ctrl+K search). Editable JSON library with an editor (drag corners on the map), and "Save to area library"
  for areas you draw.

## 1.5.0 — 2026-11-14

- **Unit templates**: 80 pre-grouped sites (670 units) from generic DB3000 facilities - single-unit airfields of
  every size; tactical, main-operating, bomber, mountain, helicopter, road, expeditionary and civil air bases; FARPs;
  command posts and bunkers; communications, intelligence and EW sites; radar and air defence; barracks, FOBs and
  outposts; ammunition, fuel and supply depots; naval, submarine and commercial ports; missile and drone sites;
  ground force positions; power, oil and civil infrastructure. Place with a name, side, position and orientation
  (Ctrl+T, map toolbar or right-click); sites are CMO groups that move and rotate together. Components resolve by
  database name with a DBID hint and search fallback. Editable JSON library with an editor, and "Save as unit
  template" from any selection.
- Formations can now be grouped in CMO without formation stations (used for fixed sites).

## 1.4.0 — 2026-11-14

- **Callsigns**: a standalone, editable JSON callsign library (38 air arms, ~365 squadrons, 1,100+ words) and an
  *Assign callsigns* dialog that detects each aircraft's country and role from the database and names it in flights
  (`TARTAN 11-14`), optionally splitting counted units into single aircraft and tagging the squadron. A library
  editor (Tools > Callsign library) adds, renames and removes countries, squadrons, roles and words, and imports,
  exports or resets the file.

## 1.3.0 — 2026-11-14

- **Event timeline** tab: events (one-shot, random window, repeating, on condition) and missions (active periods,
  switches) on the scenario clock, with zoom, tooltips, double-click to edit, and timing problems flagged.
- **Search everything** (Ctrl+K) across units, sides, missions, events, areas, reference points, formations, special
  actions, variants, scripts and every script line, plus studio commands.
- **Edit many units at once** (Units tab, Ctrl+Shift+E): rename patterns, side, group, count, proficiency, EMCON,
  hold, auto-detect, reinforcement, heading, speed, altitude, depth, base, loadout and extra fields, as one undo step.
- Issues panel and timeline double-clicks now open objects in the tab that edits them.

## 1.2.0 — 2026-11-14

Includes the Loadout Viewer from 1.1.0, whose release build never published.

- **Formations**: a Formations tab and a "Create units in formation" creator with 40 layouts across naval, air and
  ground (columns, line abreast, echelons, wedges, diamond, box, convoy, circular and double screens, ASW bent-line,
  picket line, finger four, vic, ladder, wall, bomber stream, road column, herringbone, coil, SAM dispersal,
  perimeter, random dispersal and custom stations), with spacing, orientation, altitude step, mirror, jitter and
  per-layout settings, a live preview and station table. Formations are built as CMO groups with formation stations;
  moving a kept formation's lead or member on the map moves the whole group. The example scenario's Russian surface
  action group is now a formation.
- Fixed the release tests hanging on GitHub Actions (first-run prompt on a headless display); the release job and its
  test step now have timeouts.

## 1.1.0 — 2026-11-14 (tagged, not published; shipped in 1.2.0)

- **Loadout Viewer** (Tools > Loadout viewer, Ctrl+L; also from the Database dock and the aircraft inspector):
  loadout parameters, stores with quantities and ranges, per-weapon ranges/PoK/warheads/seekers/targets/capabilities,
  which aircraft carry a loadout, which loadouts carry a weapon, project units using it, back/forward navigation and
  one-click "use for selected aircraft".

## 1.0.0 — 2026-11-14

First release ("Version 1"), including a Windows exe (`CMO-Scenario-Studio-1.0.0-win64.zip`).

- Project model (`.cmoproj` JSON) with sides, units, hosted squadrons, reinforcements, reference points, areas,
  missions, events, special actions, scripts, briefings, variants and key values; undo/redo and autosave.
- Read-only DB3000/CWDB browser with images, sensors, weapons, loadouts, facilities and descriptions.
- Map editor on Web-Mercator tiles (Esri, OpenStreetMap, OpenTopoMap, custom, offline grid).
- Event editor with templates, studio date/delay triggers, Lua guards and a generated-Lua preview.
- Exporter producing the *If Russia Wins* / official-scenario layout, with manifest-based safe re-exports and backups.
- Validation (including DBIDs and loadouts against the database) and dry-run builds in CMO's own `lua54.dll`.
- Importer for *If Russia Wins*-style `Build_Scenario.lua` orders of battle.
- Headless `--export` and `--dry-run` command line.
- Example project *Baltic Sentinel* and its exported output.
- PyInstaller build (`packaging/build_release.py`) with a smoke test, version metadata and icon; GitHub Actions
  release workflow on version tags.
- Unhandled errors are logged to `error.log` in the studio's data folder and shown in a dialog instead of closing
  the app.
