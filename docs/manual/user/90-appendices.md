# Appendix A: Keyboard shortcuts {.unnumbered}

| Keys | Action |
| --- | --- |
| [[Ctrl+N]] | New scenario |
| [[Ctrl+Shift+N]] | New scenario from the wizard |
| [[Ctrl+O]] | Open a project |
| [[Ctrl+S]] | Save |
| [[Ctrl+Shift+S]] | Save as |
| [[Ctrl+Z]] / [[Ctrl+Y]] | Undo / redo |
| [[Ctrl+1]] ... [[Ctrl+9]] | Switch to tab 1 to 9 |
| [[Ctrl+E]] | Build & Export tab |
| [[Ctrl+K]] | Search everything |
| [[Ctrl+Shift+E]] | Edit selected units |
| [[Ctrl+Shift+C]] | Assign callsigns |
| [[Ctrl+T]] | Place unit template |
| [[Ctrl+Shift+A]] | Add patrol area from library |
| [[Ctrl+Shift+F]] | Create units in formation |
| [[Ctrl+L]] | Loadout viewer |
| [[F5]] | Dry-run build |
| [[F7]] | Validate project |
| [[F1]] | User manual |

**On the map**

| Keys | Action |
| --- | --- |
| Mouse wheel, [[+]], [[-]] | Zoom |
| Drag with the left button | Pan, or move the unit under the mouse |
| [[Esc]] | Stop the current tool, or select nothing |
| [[Delete]] | Delete the selected object (or all the selected units) |
| [[Ctrl]]-click | Add a unit to the selection, or take it out |
| [[Shift]]-drag | Select the units inside a box |
| [[Ctrl+A]] | Select every unit on screen |
| [[Enter]] / double-click | Finish drawing an area, or adding waypoints in the course window |
| [[Backspace]] | Remove the last corner (or waypoint) while drawing |

**In search**: arrow keys to choose, [[Enter]] to open, [[Esc]] to close.

# Appendix B: Glossary {.unnumbered}

AAR
:   Air-to-air refuelling. An **AARA** is an air-to-air refuelling area.

AAW
:   Anti-air warfare: fighting aircraft and missiles.

AEW
:   Airborne early warning: radar aircraft such as the E-7 Wedgetail that watch the airspace from high up.

ASuW
:   Anti-surface warfare: fighting ships. *Naval* patrols in the studio.

ASW
:   Anti-submarine warfare: hunting submarines.

Awareness
:   How much a side knows about other units (Chapter 7).

Build report
:   The text the build script prints in CMO's Lua console: what was built, warnings, and the next steps.

Build script
:   `Build_Scenario.lua`: the file CMO runs once to create the scenario.

CAP
:   Combat air patrol: fighters patrolling an area to intercept enemy aircraft.

Chokepoint
:   A narrow passage ships must use, such as the Strait of Hormuz or the GIUK gap.

Course
:   A route you plot for a unit, waypoint by waypoint, with settings for each leg (Chapter 14).

DBID
:   The number identifying an entry in CMO's database.

Doctrine
:   A side's or unit's standing rules: when to fire, when to go home, whether to use radar.

Dry-run
:   A test build of the scenario inside the studio, using CMO's Lua engine but not CMO itself.

EMCON
:   Emission control: whether units switch their radars and sonars on (active) or stay silent (passive).

Event
:   Something that happens during play when its triggers and conditions are met (Chapter 15).

FIR
:   Flight information region: an area of airspace managed by one country's air traffic services. The UK has the London
    and Scottish FIRs.

Flag
:   A named yes/no value saved in the scenario, used to remember that something has happened.

Formation
:   Units kept at stations around a lead unit (Chapter 11).

GIUK gap
:   The sea between Greenland, Iceland and the UK, the classic route for submarines into the Atlantic.

HAS
:   Hardened aircraft shelter: a concrete bunker for one combat aircraft.

Host
:   The base or ship an aircraft or boat starts in.

Key value
:   A named value saved in the scenario. Flags are key values.

[LOADDOC]
:   The tag CMO uses to load a briefing page from a file.

Leg
:   The stretch of a course flown to one waypoint. Its settings (altitude, speed, sensors, weapons) apply on it.

Loadout
:   The weapons and stores an aircraft carries.

Lua
:   The scripting language CMO uses.

Mission
:   A task for a group of units: patrol, strike, support and so on (Chapter 14).

nm
:   Nautical mile: 1,852 metres. Used for distances at sea and in the air.

Order of battle (OOB)
:   The list of a side's forces.

Posture
:   How one side regards another: friendly, neutral, unfriendly or hostile.

Proficiency
:   How well trained a crew is: Novice, Cadet, Regular, Veteran, Ace.

Project
:   Your scenario design in the studio, a `.cmoproj` file.

QRA
:   Quick reaction alert: fighters kept ready to take off within minutes to intercept unknown aircraft. The UK has QRA
    North (Lossiemouth) and QRA South (Coningsby).

Reference point
:   A named marker on the map. Area corners are reference points.

Reinforcement
:   A unit that is not there at the start and arrives through an event.

SEAD
:   Suppression of enemy air defences: attacking radars and missile sites.

Side
:   A team in the scenario.

Special action
:   A button players can press during the game.

Squadron
:   In the studio, a group of identical aircraft at a base: one unit with a count.

Template
:   A ready-made group of units, such as a whole airbase.

Signal
:   A flag a unit sets when it reaches a waypoint of its course, so an event can react (Chapter 14).

Time on target
:   When a unit should reach a waypoint. **Time it** in the course window plans the departure to meet it.

OPORD
:   Operation order: the five-paragraph military order (situation, mission, execution, service support, command
    and signal). The briefing pack writes one for each side (Chapter 18).

INTSUM
:   Intelligence summary: Annex A of the briefing pack.

DTG
:   Date-time group: a time written as day, hours, minutes, zone, month and year, such as *120400Z MAY 30*.

QRA
:   Quick reaction alert: fighters kept ready to launch. In the studio, an **Intercept** mission (Chapter 14).

Runway access point
:   The part of an airbase that lets aircraft taxi from their parking to the runway.

Variant
:   Another build of the same scenario, usually with a different side played by the computer.

Waypoint
:   A point on a course. The unit flies (or sails, or drives) to each in turn.

WCS
:   Weapons control status: Free, Tight or Hold.

Zulu
:   UTC time (the same as GMT), used for all times in the studio and CMO.

# Appendix C: Menu reference {.unnumbered}

**File**

| Item | Does |
| --- | --- |
| New scenario... | Start a new project (Chapter 3) |
| New scenario from wizard... | Sides, bases, fighters, patrol areas, a bomber probe and events in a few clicks (Chapter 4) |
| Open... / Open recent | Open a project |
| Open example project... | Open Baltic Sentinel (Chapter 5) |
| Save / Save as... | Save the project |
| Import order of battle from a Build_Scenario.lua... | Bring in an existing builder-style scenario (Chapter 25) |
| Export... | Go to the Build & Export tab |
| Settings... | CMO folder, autosave, map tiles, updates |
| Exit | Close the studio |

**Edit**: Undo, Redo, Search everything..., Edit selected units...

**View**: show or hide the **Database** and **Issues** panels, and jump to any tab.

**Tools**

| Item | Chapter |
| --- | --- |
| Validate project | 21 |
| Dry-run build (CMO Lua) | 21 |
| Loadout viewer... | 10 |
| Place unit template... / Template library... | 12 |
| Repair air bases... (add missing runway access points) | 24 |
| Add patrol area from library... / Area library... | 13 |
| Assign callsigns to aircraft... / Callsign library... | 10 |
| Create units in formation... | 11 |
| Fit map to scenario | 8 |
| Open the CMO folder | Opens your CMO folder in Windows Explorer |

**Help**: User manual (PDF), Reference manual (PDF), Check for updates..., Release notes (GitHub), About.
