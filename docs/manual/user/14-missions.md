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
| Intercept (aircraft on call at a base) | Wait at their base and launch when the conditions you tick are met (see *Intercept missions*). | Aircraft at a base; an area if you tick *inside the intercept area* |
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

**Strike types**: *Air* (attack aircraft; with no targets CMO launches it at the first air contact of any kind, so use
an **Intercept** mission for aircraft on alert), *Land*, *Sea* (ships) and *Sub* (submarines).

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

## Intercept missions

An **intercept** mission keeps aircraft on call at their base, like a real quick reaction alert (QRA), and launches
them only when the conditions you tick are met.

![An intercept mission](img/mission_intercept.png)

1. **Aircraft on call**: tick the air bases whose aircraft are on call; untick one to take its aircraft off. The list
   shows how many aircraft each base has and which other missions they are on (it asks before moving them). For single
   aircraft use **Assigned units**. An aircraft can be on call for one intercept only, so give each base its own
   mission: QRA North from Lossiemouth, QRA South from Coningsby.
2. **Launch when a contact...**: tick conditions and fill in their values. Choose whether a contact must meet **ALL**
   the ticked conditions or **ANY** of them. **Presets ▾** ticks a ready-made set to start from.
3. **...and (always required as well)**: conditions about the situation rather than one contact.
4. **Response**: how many aircraft go, and what they do.
5. **The summary** at the bottom says in plain English what the mission will do. Read it: it is the quickest check.

| Condition | A contact meets it when |
| --- | --- |
| Is inside the intercept area | It is inside the mission's **Area** (a QRA area from the area library, or one you drew) |
| Is close to | It is within so many nautical miles of the aircraft's base, or of a unit you choose (a carrier, a tanker) |
| Is classed as | Your side regards it as *Hostile*, *Unfriendly*, *Unknown* or *Neutral*; tick any of them |
| Is heading towards us | Its course points at the base (or chosen unit) within this angle |
| Altitude between | It is between these altitudes, in metres. Use a low band for low-level raiders |
| Is at least this fast | It is doing this many knots or more |
| Is not identified yet | Your side does not know what class of aircraft it is |
| Is emitting (radar on) | Your side has detected an emission from it |
| Has been tracked for | Your side has held it for at least this long, so a single blip does not scramble a flight |
| Also launch against missiles | Cruise missiles count as well as aircraft |

| Always required | Meaning |
| --- | --- |
| At least this many such contacts | Wait for a raid of this size |
| Only between these times | Minutes after the start of the scenario |
| Only once this flag is set | A course signal (*Signal there*), a recipe or any event that sets a flag |

| Response | Meaning |
| --- | --- |
| Aircraft per contact / Contacts at once | Two aircraft for each of up to two contacts launches four at most |
| Keep in reserve | Aircraft that never leave, so the base is not emptied |
| Orders | *Intercept and identify* (weapons hold), *Engage if hostile* (weapons tight) or *Engage* (weapons free) |
| Go home at | Aircraft return to base at this much fuel, and another takes their place |
| Stand down after | How long after a contact stops meeting the conditions before the aircraft go home |
| Radars on once launched | Otherwise they go silent |
| Tell the side | A message when aircraft scramble and stand down |
| Set a flag on launch | So other events can follow on |

To switch an intercept on or off during the scenario, set **Active** to *No* to start with it off and use the
**Activate / deactivate mission** action, or the recipe *Start a mission on a signal*.

!!! example "QRA North from Lossiemouth"
    1. **Patrol areas...** > add *QRA North area (Scottish FIR)* (Chapter 13).
    2. **New mission**, **Class** **Intercept**, **Area** the QRA area.
    3. **Presets ▾ > Quick reaction alert**. Under **Aircraft on call** tick **Lossiemouth**.
    4. The summary reads *Launches 2 aircraft per contact ... when an aircraft is inside ... and is hostile or
       unfriendly or unknown*.

!!! note "What happens in CMO"
    The mission appears in CMO's mission editor as an *Air Intercept* strike that is switched off and empty. A
    generated event, **Studio: intercepts**, looks at the side's contacts every half minute of game time. When one
    meets the conditions it becomes a target, aircraft are assigned and the mission is switched on; CMO flies the
    intercept. When no target is left the aircraft are sent home and it is switched off again. Aircraft that are
    still rearming are not chosen, and progress is saved with the game. Your side must **detect** a contact before it
    can react: give it radars.

!!! warning "The aircraft must be able to take off"
    An aircraft that is assigned but says it is waiting for a taxiway is at a base with no runway access points. See
    *Aircraft wait for a taxiway* in Chapter 24.

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
11. **Range** (aircraft): the route against what the aircraft can fly with its loadout (see *Range and fuel*).
12. **Arrive at**: a time on target for this waypoint, and whether the unit makes it (see *Time on target*).
13. **Time it**: sets the departure (and waits) so the unit meets its times on target.
14. **Library ▾**: save this course, use a saved one, or copy it to other units (see *Reusing courses*).

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
| Depth | Submarines only. The depth below the surface for the leg, in metres; 0 surfaces. *no change* keeps the previous leg's. |
| Speed | The speed for the leg, in knots. |
| Radar / Sonar / Jammers | Switch them on (active) or off (passive) for the leg. Off is quieter: harder to detect, but the unit sees less. |
| Weapons | **Free**: fire at anything not friendly. **Tight**: only at targets identified as hostile. **Hold**: only in self-defence. |
| Targets | **Leave the course to attack**: the unit may break off to attack what it finds. **Stay on the course**: it keeps to the route. |
| Wait there | On arrival, circle the waypoint this long before going on (a holding point, a tanker track, a time on target). Ground units stop there instead. |
| Signal there | On arrival, set a flag (a key value, for example `STRIKE_AT_IP`) to true. An event with a *Regular time* trigger and the condition **Flag is set** can then react: a message, a score, a mission switched on (Chapter 15). |

**Same for every leg** copies the selected leg's altitude, speed, sensors, weapons and targets setting to every
leg.

Courses work for every unit that moves: aircraft, helicopters, ships, submarines and ground units. Facilities
cannot have one. The window shows only the settings that fit the unit:

| Unit | Altitude / depth | Speed | Radar | Sonar | Jammers | Weapons, targets | Wait, signal | Takes off from a base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Aircraft, helicopters | altitude | yes | yes | yes | yes | yes | yes (circles 5 nm round the waypoint) | yes |
| Ships | - | yes | yes | yes | yes | yes | yes (circles 0.5 nm round it) | - |
| Submarines | depth | yes | yes | yes | yes | yes | yes (circles 0.5 nm round it) | - |
| Ground units | - | yes | yes | - | yes | yes | yes (stops at the waypoint) | - |

For a submarine the profile under the map is a **depth profile**: the surface is the top line and the boat's depth
is drawn below it, leg by leg.

| At the end | What happens |
| --- | --- |
| Carry on (no further orders) | The unit keeps going; CMO's normal behaviour takes over. |
| Return to its base | The aircraft or boat returns to the base it came from. |
| Land at another base | The unit is assigned to the chosen base and lands there. That becomes its new home base. Only bases of its own side are offered. |
| Fly the course again (loop) | The unit flies the whole course again, for ever. Good for patrol tracks and shipping lanes. |

!!! note "Times are estimates"
    Arrival times use each leg's speed, or the unit's starting speed, or a typical speed for its type (450 kn for
    aircraft, 15 kn for ships). Take-off, climb, wind and fights change them in CMO.

### Time on target

Strike packages, tanker meets and coordinated attacks are about arriving at the right moment. Give a waypoint an
**Arrive at** time (minutes after the scenario starts) and the window shows, beside it, in the **Arrives** column
and on the profile, whether the unit is *on time* (within two minutes), *early* or *late*. A late leg also shows
the speed it would need.

Click **Time it** and the studio works it out for you:

1. The **departure** is set so the unit reaches the first waypoint with a time exactly on time.
2. For each later waypoint with a time that it would reach early, it **waits** that much longer at the waypoint
   before it.
3. Anything still late is reported with the speed it would need. Raise that leg's speed, or set a later time.

!!! example "Three flights on target at the same moment"
    Give the IP waypoint of each flight's course the same **Arrive at** time, for example 120 minutes, and click
    **Time it** in each. Flights from further away leave earlier; all three should reach the IP together.

The Timeline shows each time on target as a diamond on the unit's course row, and the Issues panel warns about
units that cannot make one.

### Range and fuel

For an aircraft with a **loadout**, the window compares the route with an estimate of how far it can fly:
twice the loadout's combat radius plus its time on station at a cruise speed, both from CMO's database. Waits
count too, as distance flown at the leg's speed. The line under the summary says *Within range* or *Too far*, and
on the profile a red dashed line marks where the fuel should run out. The Issues panel warns about routes that are
too long.

It is an estimate: altitude, speed and weapons change real fuel use in CMO, and a tanker on the route (a wait at a
tanker track) is not counted as refuelling. Treat *Too far* as a prompt to check, not a rule.

### Reusing courses

**Library ▾** in the course window has three commands:

- **Save this course to the library...**: keeps the waypoints with every leg setting, the departure and the end
  order under a name, in `routes.json` in your data folder (beside your template and area libraries). It is there
  in every project. A saved course with the same name is replaced.
- **Use a saved course...**: pick a saved course and click **Use instead** (replaces this unit's course) or **Add
  to the end** (adds its waypoints after this one's). **Delete** removes saved courses you no longer need.
- **Copy this course to other units...**: tick units of the same side; each gets a copy of this course, settings
  and all. It happens when you click **OK**, in the same single undo step.

A landing base belongs to one project, so a saved course that landed elsewhere comes back as **Return to its
base**, and a copy given to a ship or ground unit carries on at the end instead.

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
    move), about departures after the scenario ends, about landing bases that cannot take the aircraft, about
    signals with spaces or punctuation, about times on target that cannot be met, and about routes longer than the
    aircraft's estimated range.

!!! tip "Players can still change it"
    A course is the unit's starting orders. On a side a player controls, the player can give the unit new orders
    at any time. On a computer side, the unit follows the course unless something else gives it new orders.
