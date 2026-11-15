# User guide

CMO Scenario Studio keeps a scenario as a **project** (`.cmoproj`) and turns it into a **build script** that CMO runs
once to create the `.scen`. You edit the project here; CMO does the building. This is the same approach as
*If Russia Wins* and the official Lua-driven scenarios, and it means a scenario can be rebuilt at any time from text
files that live happily in git.

- [The window](#the-window)
- [Typical workflow](#typical-workflow)
- [Tabs](#tabs)
- [Database browser](#database-browser)
- [Formations](#formations)
- [Event timeline](#event-timeline)
- [Search everything](#search-everything)
- [Editing many units at once](#editing-many-units-at-once)
- [Patrol area library](#patrol-area-library)
- [UK military sites](#uk-military-sites)
- [Unit templates](#unit-templates)
- [Callsigns](#callsigns)
- [Loadout Viewer](#loadout-viewer)
- [Events in depth](#events-in-depth)
- [Variants](#variants)
- [Validation and dry-run](#validation-and-dry-run)
- [Exporting](#exporting)
- [Importing an existing scenario](#importing-an-existing-scenario)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Installing and updating](#installing-and-updating)
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
marked *all sides*. **From library...** adds predefined patrol areas (see
[Patrol area library](#patrol-area-library)); **Save to area library...** on an area's form keeps it for reuse.

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

## Formations

The **Formations** tab keeps groups of units on stations around a lead (guide) unit. In CMO each formation becomes
a group whose members have formation stations, built the way the official scenarios do it (`unit.group = 'Name'`,
then `ScenEdit_SetUnit({guid=..., formation={bearing=..., distance=...}})`).

### Creating formations

- **Create units in formation...** (Formations tab, or Tools menu, Ctrl+Shift+F) builds new units from the database:
  select an entry in the Database panel and press *Add* for each row of the composition (e.g. one carrier, then six
  destroyers), choose a layout, position, spacing and orientation, and press *Create*. The first unit of the first
  row is the lead; the live preview shows the result.
- **From units...** (or *Make formation* on the Units tab, or right-click a unit on the map) turns existing units into
  a formation; the first selected unit becomes the lead.

### Editing

- **Layout** picks one of the presets below; **Layout settings** shows that layout's own controls.
- **Spacing** (in nm, km or m) is the formation's unit length; **orientation** is the direction it faces.
- **Altitude step** stacks aircraft (e.g. a ladder); **mirror** swaps left and right; **jitter** and **seed** add
  repeatable randomness.
- **Members** are in station order: station 1 is the first member. *Up/Down* reorder them, *Make lead* swaps the guide.
- **Keep members on station**: members follow setting changes, and dragging the lead *or any member* on the map
  moves the whole formation. Untick it to place individual units by hand (their actual positions are exported).
- **Give every unit the formation heading** sets each unit's heading.
- **Stations**: *Rotating* stations turn with the group's course (bearing relative to the heading); *Fixed* stations
  keep a true bearing. **Sprint and drift** is the ASW escort behaviour.

The preview is north-up with the heading arrow, numbered stations and range rings; the table lists each station's
relative and true bearing and distance. On the map, dashed lines join each lead to its members.

A unit can only be in one formation, and units that start at a base (hosted aircraft and boats) cannot be on
station. Reinforcements are placed but not grouped at the start.

### Layouts

| Domain | Layout | Built on | Default spacing | Use |
| --- | --- | --- | --- | --- |
| Naval | Line ahead (column) | Column | 1 nm | Ships follow in the lead's wake. Simple transit and narrow-channel formation. |
| Naval | Line abreast | Line abreast | 2 nm | Ships side by side across the track; good search width (minesweeping, surface search). |
| Naval | Echelon right | Echelon | 1 nm | Diagonal line astern and to starboard. |
| Naval | Echelon left | Echelon | 1 nm | Diagonal line astern and to port. |
| Naval | Wedge (Vee) | Wedge / Vee | 1.5 nm | Arrowhead with the lead at the point. |
| Naval | Inverted wedge (U) | Wedge / Vee | 1.5 nm | Wings ahead of the lead. |
| Naval | Diamond | Diamond | 2 nm | Escorts ahead, astern and on both beams of the lead. |
| Naval | Box (2 columns) | Grid / box | 1.5 nm | Two columns in line ahead. |
| Naval | Convoy (columns) | Grid / box | 0.5 nm | Merchant ships in columns with the commodore in the front centre; wider between columns than ships. |
| Naval | Circular screen | Ring / arc | 4 nm | Escorts evenly spaced on a ring around a high-value unit (carrier, amphibious ship). |
| Naval | Carrier group (inner + outer screen) | Double ring | 3 nm | Close-in AAW escorts on an inner ring and ASW/picket ships on an outer ring. |
| Naval | ASW bent-line screen | Ring / arc | 4 nm | Escorts on an arc ahead of the main body, across the likely submarine threat axis. |
| Naval | Picket line ahead | Line abreast | 10 nm | Radar pickets in a line well ahead of the main body. |
| Naval | Amphibious assault lanes | Grid / box | 0.5 nm | Landing craft in assault lanes abreast, waves behind. |
| Naval | Mine-sweeping echelon | Echelon | 0.3 nm | Sweepers stepped so each one covers the next one's sweep. |
| Air | Finger four (fingertip) | Finger four | 0.5 nm | Classic four-ship: wingman left-aft, element lead right-aft, number four further right-aft. |
| Air | Vic (3-ship V) | Wedge / Vee | 0.3 nm | Three-ship V with the lead at the point. |
| Air | Trail | Column | 1 nm | Aircraft in line astern (in-trail). |
| Air | Ladder (stepped trail) | Column | 1 nm | Trail with each aircraft stepped up in altitude. |
| Air | Combat spread | Line abreast | 1 nm | Two (or more) aircraft line abreast, wide enough to check each other's six. |
| Air | Wall | Line abreast | 3 nm | Fighters line abreast across the threat axis (BVR wall). |
| Air | Box | Grid / box | 1 nm | Two pairs, one behind the other. |
| Air | Wedge | Wedge / Vee | 1 nm | Lead at the point, wingmen stepped back on both sides. |
| Air | Echelon right (air) | Echelon | 0.3 nm | Diagonal line to the right. |
| Air | Bomber stream | Grid / box | 2 nm | Waves of bombers in a long stream. |
| Air | Tanker cell | Echelon | 1 nm | Tankers stepped in echelon, slightly stacked. |
| Ground | Road march column | Column | 100 m | Vehicles nose to tail along a road (~100 m). |
| Ground | Staggered column | Column | 100 m | Column with vehicles alternating to each side of the road. |
| Ground | Herringbone (halt) | Column | 100 m | Halted column with vehicles pulled off to alternate sides for all-round security. |
| Ground | Line | Line abreast | 204 m | Vehicles abreast for maximum firepower forward. |
| Ground | Wedge | Wedge / Vee | 204 m | All-round security, firepower to the front and flanks. |
| Ground | Vee | Wedge / Vee | 204 m | Two elements forward, one back. |
| Ground | Echelon right (ground) | Echelon | 204 m | Protects the right flank. |
| Ground | Box / square | Grid / box | 204 m | Two elements up, two back. |
| Ground | Diamond (ground) | Diamond | 204 m | One forward, two flanks, one rear. |
| Ground | Coil / laager | Ring / arc | 204 m | Vehicles in a circle facing outwards (halted). |
| Ground | SAM battery dispersal | Ring / arc | 0.27 nm | Launchers spread on a ring around the radar/command post (~500 m). |
| Ground | Random dispersal | Random dispersal | 0.27 nm | Units spread randomly within a radius, with a minimum separation. |
| Ground | Defensive perimeter (two rings) | Double ring | 0.2 nm | Inner ring of key units with an outer ring of security positions. |
| Any | Custom stations | Custom stations | 1 nm | Type each member's relative bearing and distance (in spacing units). |

Settings per layout family:

- **Column**: Stagger (sideways, spacing units)
- **Line abreast**: Lead position, Line ahead of lead (spacing units)
- **Echelon**: Side, Angle from astern (deg)
- **Wedge / Vee**: Angle from astern (deg), Inverted (wings ahead)
- **Diamond**: no extra settings
- **Grid / box**: Columns, Row spacing (x spacing), Lead position
- **Ring / arc**: Radius (spacing units), Arc (deg, 360 = full ring), Centre of arc / first station (relative deg)
- **Double ring**: Units on inner ring, Inner radius (spacing units), Outer radius (spacing units), Rotation (relative deg)
- **Finger four**: no extra settings
- **Random dispersal**: Radius (spacing units), Minimum separation (spacing units), Random seed
- **Custom stations**: Stations

## Event timeline

The **Timeline** tab puts every event and mission on the scenario clock (start in yellow, end as a dashed red line),
with Zulu times on top and H+ times beneath them.

| Shape | Meaning |
| --- | --- |
| Diamond | fires once at that moment (date/time, minutes after start, scenario loaded/ended) |
| Bar | a random-time window, or a mission's active period (from its start/end time options) |
| Bar with ticks | a regular-time trigger, ticked at its interval when zoomed in enough |
| Dotted line | fires on a condition (unit destroyed, area entered, points...), at any time |
| Grey row | inactive event, or a mission that starts inactive |

Missions switched on or off by a timed event show a diamond where that happens; condition-triggered switches are
listed in the mission's details. The panel on the right lists **timing problems**: events that fire before the start
or after the end, random windows outside the scenario, missions that end before they start, events without
triggers, and two one-shot events in the same minute (circled in red, because their order is not guaranteed).

Hover for details, click a row for the full summary, double-click to open it in the Events or Missions tab.
**Ctrl+wheel** zooms, *Fit* shows the whole scenario; the filter, *Missions*, *Condition-only events* and
*Sort by time* options trim the view.

## Search everything

**Ctrl+K** (Edit > Search everything) opens a search box over the whole project: units (by name, class, DBID, group
or base), sides, missions, events (including their trigger and action types), areas, reference points, formations,
special actions, variants, scripts and **every line of every script**, plus studio commands ("Validate project",
"Dry-run build", "Go to Timeline"...). All words must match; name matches rank first, and a single word also matches
loosely (e.g. `stgsh` finds Steregushchiy). Arrow keys choose, **Enter** opens the result in the tab that edits it
(units and areas on the map, script lines at that line), **Esc** closes.

## Editing many units at once

On the **Units** tab select several rows (Ctrl/Shift-click, or filter then Ctrl+A) and press **Edit selected...**,
right-click, or **Ctrl+Shift+E**. Tick only the fields to change; the rest are left alone, and one undo reverts the
lot.

- **Rename** with a pattern: `{name}` current name, `{n}` running number (from *first {n}*), `{nn}` zero-padded,
  `{class}` database class, `{side}`, `{type}`. Example: `Escort {nn}` gives Escort 01, Escort 02...
- **Side** (moving units drops mission assignments, strike targets, formation places and bases that belong to the
  old side), **group tag**, **count**.
- **Proficiency**, **radar / sonar active**, **hold position**, **auto-detectable**, **reinforcement**.
- **Heading**, **speed**, **altitude** (airborne aircraft), **depth** (submarines), **starts at** (a base or ship of
  the same side).
- **Loadout**, when all selected units are the same aircraft type.
- An **extra ScenEdit_SetUnit field** to set or remove (e.g. `fuel` = `50`).

## Patrol area library

**Tools > Add patrol area from library** (Ctrl+Shift+A), the map's **Patrol areas...** button, right-click on the
map, or **From library...** on the Areas tab opens 208 predefined sea and air areas grouped
by region: Europe, United Kingdom, Arctic, Middle East, Africa, Asia, Oceania, North America and South America. Sea areas cover
patrol areas, chokepoints and barriers (Bay of Biscay, GIUK gaps, Baltic, Mediterranean, Hormuz, Taiwan Strait,
South China Sea, Falklands TEZ...); air areas cover CAP and QRA boxes, AEW orbits, tanker tracks and ranges.

Filter by region, sea/air or words, check the map preview, choose the side and area name, and optionally create a
mission on it (suggested per area: ASW or ASuW patrol for sea, CAP for air, support for AEW orbits and tanker tracks).
Ctrl/Shift-click adds several at once. Ctrl+K search finds library areas by name.

**Tools > Area library** edits the list (corners in a table or dragged on the map), saved as your own `areas.json`;
**Save to area library...** on an area keeps one you drew. See [AREAS.md](AREAS.md) for the format and full list.

## UK military sites

Tools > Place unit template (Ctrl+T) also holds **101 UK sites at their real positions** in the *UK - ...*
categories: 46 air bases (RAF, Fleet Air Arm, Army Air Corps and USAF bases in the UK, plus relief landing
grounds) built from OpenStreetMap with every runway, hardened aircraft shelter, hangar, apron, control tower,
radar, fuel farm and munitions bunker that is mapped; and naval bases, radar heads, headquarters, comms and
intelligence sites, nuclear sites, munitions depots and garrisons. Search "lossiemouth" or "faslane", leave **At the
real site** ticked and press Place - the whole base appears where it really is, grouped. Untick it to use the layout
somewhere else. See [TEMPLATES.md](TEMPLATES.md#uk-real-world-sites) for every site and its counts.

For UK airspace, the area library's **United Kingdom** region uses the official UK AIP boundaries for the London
and Scottish FIRs (the QRA South and North areas), the danger areas of the main ranges and the air-to-air
refuelling areas AARA 1-14 (tagged *official*), plus notional areas with no published definition: eight
interception sectors that together cover the whole UK FIR, approach zones, CAP stations and AEW orbits.

## Unit templates

**Tools > Place unit template** (Ctrl+T), the map's **Templates...** button or right-click > **Place unit template
here...** drops a pre-grouped site: 80 built-in templates across airfields (single-unit airfields of every runway
length; detailed tactical, main-operating, bomber, mountain, helicopter, road, expeditionary and civil bases; FARPs),
command and control, communications and EW, radar and air defence, garrisons and bases, logistics, naval bases,
missile and drone sites, ground force positions and civil infrastructure.

Give the site a name, side, position and orientation; units are named `<site> <part>` (*Amari Control Tower*) and
grouped, so dragging any part moves the whole site and the Formations tab rotates it. Parts marked *host* (airfields,
shelters, hangars, helipads, piers) take aircraft or boats. Swap generic parts for national systems with *Use for
selected unit*. **Save as unit template...** on the Units tab makes your own templates from placed units.

**Tools > Template library** edits the library, saved as your own `templates.json` - see [TEMPLATES.md](TEMPLATES.md)
for the format and the full catalogue.

## Callsigns

**Assign callsigns** (Units tab *Callsigns...*, right-click, Tools menu or **Ctrl+Shift+C**) names the selected
aircraft (or every aircraft, if none are selected) from the callsign library: `TARTAN 11`, `TARTAN 12`...

For each unit the dialog shows the **country** (from the aircraft's operator in the database) and the **role**
(from its type, category and loadout: an F-16 carrying HARMs is SEAD, a Ka-27 a naval helicopter, an Il-78 a
tanker). Change either per row, or pick a specific **squadron**; the preview updates as you go. Options:

- **Split counted units into single aircraft**: a squadron entry with count 6 becomes six aircraft, each with its
  own callsign, keeping its base, mission assignments and formation place. Reinforcements are not split (their spawn
  action refers to one unit); they get a flight callsign instead (`TARTAN 3 #1..#4` in CMO).
- **Put the squadron name in the group tag**, handy for filtering and bulk edits.

Each unit starts a new flight, separate units come from separate squadrons, and names already used in the project
are never reused. One undo reverts everything.

**Tools > Callsign library** edits the library: countries (with the database countries they match, the name
format and the flight size) and their squadrons (service, base, aircraft, roles and callsign words). *Save* writes
your own `callsigns.json`, which is a plain, standalone JSON file you can also edit by hand, share (*Export* /
*Import*) or reset. See [CALLSIGNS.md](CALLSIGNS.md) for the format.

## Loadout Viewer

Open it with **Tools > Loadout viewer** (Ctrl+L), the **Loadout viewer** button in the Database dock (aircraft), or
**View loadouts...** in an aircraft's inspector. It opens on the selected aircraft and its current loadout.

- **Left:** search aircraft, then filter its loadouts by role group (air-to-air, strike/SEAD/CAS, support, ASW,
  recon/transport, tanker), by text (names *and* carried weapons, e.g. `JASSM`), and optionally show ferry/reserve or
  deprecated loadouts. Columns sort; radius is in nm and time on station in minutes.
- **Middle:** the loadout: role, day/night and weather, combat radius, time on station, ready time (and sustained),
  quick turnaround (ready time, sorties, airborne time), default mission profile, Winchester/Shotgun rule and drag
  modifier, then each store with quantity, maximum, type, air/surface/land/subsurface range, weight and whether it is
  internal or optional. *Carried by* lists every aircraft variant that has this loadout; *In this project* lists
  your units using it (double-click to select one).
- **Right:** the weapon you click: image, ranges, PoK, CEP, weight, flight limits, plus tabs for targets, warheads
  (type, damage points, explosive weight), seekers, capabilities (e.g. LOAL, dogfight, sea-skimmer capable), every
  other loadout that carries it, and the DB description.

Double-click entries in *Carried by* or *Also in loadouts* to follow the link; **Back/Forward** retrace your path.
**Use for selected aircraft** (or double-clicking a loadout) gives the loadout to the aircraft selected in the
project — it must be the same aircraft type, since loadouts belong to specific DBIDs.

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
| Ctrl+K | Search everything |
| Ctrl+Shift+E | Edit selected units |
| Ctrl+Shift+C | Assign callsigns |
| Ctrl+T | Place unit template |
| Ctrl+Shift+A | Add patrol area from library |
| Ctrl+Shift+F | Create units in formation |
| Ctrl+L | Loadout viewer |
| F5 | Dry-run build |
| F7 | Validate |
| Map: Esc / Delete / + / − | Cancel tool or deselect / delete selection / zoom |

## Installing and updating

- **Installer** (`...-setup.exe`): installs into `C:\Program Files\CMO Scenario Studio` for all users (Windows asks
  for administrator permission), with Start-menu shortcuts (studio, user guide, example projects, uninstall), an
  optional desktop icon and an option to open `.cmoproj` files with the studio. Uninstall from *Settings > Apps* or
  the Start menu.
- **Updates**: the installed studio checks GitHub for a newer release a few seconds after it starts (turn this off in
  *File > Settings*), and **Help > Check for updates** checks at any time. *Download and install* shows the release
  notes, downloads the setup, verifies it against the release's SHA-256 checksum, asks you to save changes, then
  closes, updates and starts again. *Skip this version* stops the reminder for that version.
- **Where your files are**: the program and its built-in libraries are in Program Files and are replaced by updates.
  Your own libraries, settings, export backups and the map tile cache are in your user profile (`%APPDATA%` /
  `%LOCALAPPDATA%`), and projects wherever you save them - updates and uninstalling never touch them. The examples
  are read-only in Program Files: saving an opened example asks where to save your copy.
- **Portable zip**: works the same but cannot update itself; *Check for updates* opens the release page.

## Troubleshooting

- **No databases listed** — set the CMO folder in *File > Settings* (the folder with `Command.exe` and `DB\`).
- **Dry-run says lua54.dll not found** — same; it lives in the CMO folder. The studio needs 64-bit Python.
- **Blank map** — check your internet connection or choose another tile source; *None (offline grid)* always works.
- **"Side already has units" in CMO** — the builder refuses to build twice. Start from a new blank scenario, or tick
  *FORCE_REBUILD* in Build options.
- **An event does not fire** — check the Generated Lua tab; set `STUDIO.DEBUG = true` in the Lua console for
  verbose output from `StudioDebug`.
