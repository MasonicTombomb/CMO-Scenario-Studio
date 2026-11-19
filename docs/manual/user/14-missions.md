# Missions

A **mission** tells the computer what a group of units should do: patrol an area, strike targets, fly a tanker
orbit. In CMO, units on a mission act on their own. Players can change missions during play, but the ones you
create are how the scenario starts, and they are how computer-controlled sides fight.

## The Missions tab

![The Missions tab](img/tab_missions.png)

1. **Name**: the mission's name, as players see it.
2. **Class**: the kind of mission (table below).
3. **Type**: for patrols and strikes, the target kind (table below).
4. **Area**: the area to patrol or orbit in. Only areas of the mission's side (or shared areas) are offered.
5. **Options**: how the mission behaves (table below). Leave an option at *(default)* to use CMO's default.
6. **Assigned units**: the units that fly or sail the mission. Click **Add...** and tick them. **Remove** takes them
   off.

Use **New mission**, **Duplicate** and **Delete** under the mission list to add, copy and remove missions. The
filter above the list shows one side's missions; a new mission belongs to that side, and its **Side** box can change it.

## Mission classes

| Class | What the units do | Needs |
| --- | --- | --- |
| Patrol | Stay in an area and engage what they find there. | An area with 3+ corners; optionally a **Prosecution area**, a larger area they may chase targets into |
| Strike | Attack specific targets. | **Strike targets**: enemy units chosen with **Add targets** |
| Support (AEW / tanker / orbit) | Fly an orbit: airborne early warning, tanker, jammer, reconnaissance. | An area to orbit in |
| Ferry | Fly to another base and land there. | A **Destination** base |
| Mining | Lay mines in an area. | An area |
| Mine clearing | Clear mines from an area. | An area |
| Cargo | Move cargo between units (advanced). | |

**Patrol types**

| Type | Hunts |
| --- | --- |
| AAW | Aircraft (anti-air warfare). An air patrol of fighters is a *CAP*, combat air patrol. |
| ASW | Submarines (anti-submarine warfare). |
| Naval | Surface ships (anti-surface warfare, ASuW). |
| Land | Ground units and facilities. |
| Mixed | Anything. |
| SEAD | Enemy air defences: radars and missile sites (suppression of enemy air defences). |

**Strike types**: *Air* (intercept aircraft), *Land*, *Sea* (ships) and *Sub* (submarines).

## Options

| Option | Meaning |
| --- | --- |
| Active | Untick to create the mission switched off. An event can switch it on later (Chapter 15). |
| 1/3 rule | Only a third of the aircraft are on station at once; the rest are on the way or rearming. Gives continuous cover. |
| Investigate outside patrol area | Units may chase contacts outside the area. |
| Investigate outside weapon range | Units may chase contacts they cannot yet shoot at. |
| Active EMCON in area | Units switch on their radars inside the area. |
| Flight size / Enforce flight size | How many aircraft fly together, and whether to wait until that many are ready. |
| Start time / End time | When the mission starts and stops (format `dd/mm/yyyy hh:mm:ss`, Zulu). Shown on the Timeline. |

**Other ScenEdit_SetMission fields** (advanced) accepts any other mission setting CMO's scripting supports, such
as `TransitThrottleAircraft` = `'Cruise'`. Settings CMO does not accept are reported in the build report rather
than stopping the build.

## Worked examples

!!! example "A fighter CAP"
    1. Draw an area (or use the area library) for the patrol.
    2. **New mission**, set **Name** `CAP North`, **Class** **Patrol**, **Type** **AAW**, **Area** your area.
    3. Tick **1/3 rule** for round-the-clock cover.
    4. Under **Assigned units**, **Add...** the fighter squadron.

!!! example "An anti-ship strike"
    1. **New mission**, **Class** **Strike**, **Type** **Sea**.
    2. Under **Strike targets**, **Add targets** and tick the enemy ships.
    3. Assign aircraft with an anti-ship loadout.
    4. To launch it later in the game, untick **Active** and add an event with **Activate / deactivate mission**.

!!! example "A tanker orbit"
    1. Use the area library's tanker tracks, or draw a long thin area.
    2. **New mission**, **Class** **Support (AEW / tanker / orbit)**, **Area** the track.
    3. Assign tanker aircraft with a tanker loadout.

!!! warning "Units belong to their side's missions only"
    A unit can only be assigned to a mission of its own side. If you move a unit to another side, the studio removes
    it from the old side's missions.

## Courses: a route without a mission

A mission lets CMO decide where its units go. A **course** is the other way round: you draw the exact route a unit
takes, waypoint by waypoint, and say what it does on each leg. Use it to script a computer side's movements: a
bomber stream on a set track, a convoy along a coast, or a strike package that takes off from one base, meets a
tanker, goes in low and fast with radars off and weapons free, then lands somewhere else.

### Opening the course window

Select the unit and do one of these:

- click **Edit course...** (or **Plot a course...**) in the **Course** box of the unit inspector;
- click **Course...** on the map toolbar;
- right-click the unit on the map > **Plot course...** (or **Edit course...**).

![The Course box in the unit inspector](img/unit_course.png)

The **Course** box sums the course up: where the unit sets off from and when, the number of waypoints, the
distance, the time it takes and what it does at the end. **Clear** removes the whole course. Aircraft and boats in
a base are on the Units tab rather than the map; select them there.

### The course window

![The course window](img/dialog_course.png)

1. **The map**: the route, as a dashed line from the unit (or its base) through numbered waypoints. The selected
   waypoint has a yellow ring. Drag a waypoint's white square to move it; click one to select its leg. A dotted
   last leg shows the way home, to the landing base, or back to the start of a loop.
2. **Route tools**: **Add waypoints** (click the map once for each waypoint, then double-click or press [[Enter]];
   [[Backspace]] removes the last; new waypoints go at the end). **Insert** adds a waypoint half-way along the leg
   to the selected one. **Remove** (or [[Delete]]), **Up** and **Down** remove and reorder. **Reverse** flies the
   course the other way round. **Clear** removes every waypoint. **Fit** zooms the map to the route.
3. **The legs**: one row per leg, with the altitude, speed, radar and weapons in force, any wait, the leg's length
   and when the unit should arrive (*H+h:mm* after the scenario starts). Grey values are carried over from an
   earlier leg or estimated. The last row (→) is the way home or to the landing base.
4. **The selected leg**: everything about the leg flown *to* this waypoint (table below).
5. **Sensors and weapons** for the leg.
6. **On arrival**: what happens when the unit reaches the waypoint.
7. **The profile**: the route from start to end, left to right. The blue area is the altitude (aircraft), the amber
   line the speed (dotted where it is an estimate). Waypoint numbers run along the top, with waits and signals.
   The strips underneath show radar, jammers (sonar for ships and submarines) and weapons on each leg: green on,
   grey off, dark unchanged; weapons red free, amber tight, green hold. Click a leg to select it; hover for details.
8. **Depart**: when the unit sets off, in minutes after the scenario starts. *at the start* means straight away.
9. **At the end** and **Land at**: what the unit does after the last waypoint (second table below).
10. **The summary**: departure, waypoints, distance, time and the end of the course.

Click **OK** to keep the course. **Cancel** closes the window and throws the changes away (it asks first). Either
way, the course is one change on the main window, so [[Ctrl+Z]] undoes it.

### Leg settings

A setting applies on the leg flown *to* its waypoint, and stays in force on later legs until one of them changes
it. *No change* keeps whatever the unit already has.

| Setting | What it does |
| --- | --- |
| Name | A name for the waypoint, shown on the map, in the table and in CMO (*IP*, *Tanker*, *Target*). |
| Lat, lon | The waypoint's position; type it exactly or drag the waypoint on the map. |
| Altitude | Aircraft only. The altitude for the leg, in metres (feet shown beside it). |
| Speed | The speed for the leg, in knots. |
| Radar / Sonar / Jammers | Switch them on (active) or off (passive) for the leg. Off is quieter: harder to detect, but the unit sees less. |
| Weapons | **Free**: fire at anything not friendly. **Tight**: only at targets identified as hostile. **Hold**: only in self-defence. |
| Targets | **Leave the course to attack**: the unit may break off to attack what it finds. **Stay on the course**: it keeps to the route. |
| Wait there | On arrival, circle the waypoint this long before going on (a holding point, a tanker track, a time on target). |
| Signal there | On arrival, set a flag (a key value, for example `STRIKE_AT_IP`) to true. An event with a *Regular time* trigger and the condition **Flag is set** can then react: a message, a score, a mission switched on (Chapter 15). |

**Same for every leg** copies the selected leg's altitude, speed, sensors, weapons and targets setting to every
leg.

Courses work for every unit that moves: aircraft, helicopters, ships, submarines and ground units. Facilities
cannot have one. The window shows only the settings that fit the unit:

| Unit | Altitude | Speed | Radar | Sonar | Jammers | Weapons, targets | Wait, signal | Takes off from a base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Aircraft, helicopters | yes | yes | yes | yes | yes | yes | yes (circles 5 nm round the waypoint) | yes |
| Ships | - | yes | yes | yes | yes | yes | yes (circles 0.5 nm round it) | - |
| Submarines | - (depth stays as set) | yes | yes | yes | yes | yes | yes (circles 0.5 nm round it) | - |
| Ground units | - | yes | yes | - | yes | yes | yes (circles 0.5 nm round it) | - |

| At the end | What happens |
| --- | --- |
| Carry on (no further orders) | The unit keeps going; CMO's normal behaviour takes over. |
| Return to its base | The aircraft or boat returns to the base it came from. |
| Land at another base | The unit is assigned to the chosen base and lands there. That becomes its new home base. Only bases of its own side are offered. |
| Fly the course again (loop) | The unit flies the whole course again, for ever. Good for patrol tracks and shipping lanes. |

!!! note "Times are estimates"
    Arrival times use each leg's speed, or the unit's starting speed, or a typical speed for its type (450 kn for
    aircraft, 15 kn for ships). Take-off, climb, wind and fights change them in CMO.

### Taking off from a base

Aircraft that start **in a base** (their **Starts at** is a base, Chapter 10) wait on the ground until their
**Depart** time, then take off, fly the course and do what **At the end** says. A squadron with **Count** 4
launches all four aircraft, and each one flies the course.

!!! example "Take off from Lossiemouth, strike, land at Coningsby"
    1. Place the Lossiemouth and Coningsby templates (Chapter 12).
    2. Add two Typhoons to a Lossiemouth hangar (**Count** 2) and choose a loadout.
    3. Select them on the Units tab and click **Plot a course...**. Click four waypoints over the North Sea and
       press [[Enter]].
    4. Waypoint 1: **Altitude** 9000 m, **Speed** 450 kn, **Radar** on, **Weapons** tight.
    5. Waypoint 2: **Wait there** 15 min (a tanker), **Name** `Tanker`.
    6. Waypoint 3: **Name** `IP`, **Altitude** 150 m, **Speed** 540 kn, **Radar** off, **Jammers** on, **Weapons**
       free, **Signal there** `STRIKE_AT_IP`.
    7. Waypoint 4: **Altitude** 6000 m, **Radar** on, **Weapons** tight.
    8. **Depart** 30 minutes, **At the end** **Land at another base**, **Land at** a Coningsby hangar. **OK**.
    9. In CMO the pair takes off at H+30, climbs out, holds at the tanker, runs in low with radars off, climbs out
       and lands at Coningsby. An event with a *Regular time* trigger and the condition **Flag is set** `STRIKE_AT_IP` can
       announce the strike.

Units that are already moving at the start (aircraft in the air, ships, submarines, ground units) are given their
course when the scenario is built, or at their **Depart** time. Reinforcements are given theirs once they arrive.

### How it works in CMO

The studio exports the courses with the scenario and adds an event, **Studio: unit courses**, that runs every
minute of game time. It launches aircraft when their time comes, gives each unit its course once it is in the air
or under way, applies each leg's settings as the leg starts, raises signals and holds waits as waypoints are
reached, and carries out the end-of-course order. Each unit's progress is saved with the scenario, so saving and
loading a game part way through is fine. The Timeline (Chapter 19) shows when each unit departs.

!!! warning "A course or a mission, not both"
    Units on a mission follow the mission and ignore the course. Give a unit one or the other. The Issues panel
    warns about units with both, about formation members (they follow their lead), about facilities (they cannot
    move), about departures after the scenario ends, about landing bases that cannot take the aircraft, and about
    signals with spaces or punctuation.

!!! tip "Players can still change it"
    A course is the unit's starting orders. On a side a player controls, the player can give the unit new orders
    at any time. On a computer side, the unit follows the course unless something else gives it new orders.
