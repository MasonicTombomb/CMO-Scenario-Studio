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
takes, waypoint by waypoint. Use it to script a computer side's movements: a bomber stream on a set track, a convoy
along a coast, a pair of fighters that take off from one base, fly a route and land somewhere else.

![The Course box in the unit inspector](img/unit_course.png)

### Plotting a course

1. Select the unit on the map.
2. Click **Plot course** on the map toolbar (or right-click the unit > **Plot course...**, or click **Plot on map**
   in the inspector's **Course** box).
3. Click the map once for each waypoint, in order. A dashed preview follows the mouse.
4. Finish with a double-click or [[Enter]]. [[Backspace]] removes the last waypoint; [[Esc]] cancels.

The course is drawn as a dashed line from the unit (or from its base) through numbered waypoints. Select the unit
and drag a waypoint's white square to move it. Plotting again adds waypoints to the end of the course. Untick
**Courses** on the map toolbar to hide all courses.

### The Course box

The **Course** box in the unit inspector shows and edits the course:

1. **The waypoint table**: the latitude and longitude of each waypoint, in order. Type in **Altitude (m)** or
   **Speed (kn)** to set the altitude or speed for the leg to that waypoint; leave them empty to let the unit
   choose.
2. **Plot on map**: add waypoints by clicking the map.
3. **Remove**, **Up**, **Down**: remove or reorder the selected waypoint. **Reverse** flies the course the other
   way round. **Clear** removes the whole course.
4. **Depart**: when the unit sets off, in minutes after the scenario starts. *at the start* means straight away.
5. **At the end**: what the unit does after the last waypoint (table below).
6. **Land at**: for **Land at another base**, the base to land at. Only bases of the unit's own side are offered.

The line above the table shows the number of waypoints and the length of the route in nautical miles.

| At the end | What happens |
| --- | --- |
| Carry on (no further orders) | The unit keeps going; CMO's normal behaviour takes over. |
| Return to its base | The aircraft or boat returns to the base it came from. |
| Land at another base | The unit is assigned to the chosen base and lands there. That becomes its new home base. |
| Fly the course again (loop) | The unit flies the whole course again, for ever. Good for patrol tracks and shipping lanes. |

### Taking off from a base

Aircraft that start **in a base** (their **Starts at** is a base, Chapter 10) wait on the ground until their
**Depart** time, then take off, fly the course and do what **At the end** says. A squadron with **Count** 4
launches all four aircraft, and each one flies the course.

!!! example "Take off from Lossiemouth, fly a route, land at Coningsby"
    1. Place the Lossiemouth and Coningsby templates (Chapter 12).
    2. Add two Typhoons to a Lossiemouth hangar (**Count** 2) and choose a loadout.
    3. Select them and click **Plot course**. Click three waypoints over the North Sea and press [[Enter]].
    4. In the **Course** box set **Depart** to 30 minutes, **At the end** to **Land at another base** and
       **Land at** to a Coningsby hangar.
    5. In CMO the pair takes off 30 minutes into the scenario, flies the route and lands at Coningsby.

Units that are already moving at the start (aircraft in the air, ships, submarines, ground units) are given their
course when the scenario is built, or at their **Depart** time. Reinforcements are given theirs once they arrive.

### How it works in CMO

The studio exports the courses with the scenario and adds an event, **Studio: unit courses**, that runs every
minute of game time. It launches aircraft when their time comes, gives each unit its course once it is in the air
or under way, and carries out the end-of-course order. Each unit's progress is saved with the scenario, so saving
and loading a game part way through is fine. The Timeline (Chapter 19) shows when each unit departs.

!!! warning "A course or a mission, not both"
    Units on a mission follow the mission and ignore the course. Give a unit one or the other. The Issues panel
    warns about units with both, about formation members (they follow their lead), about facilities (they cannot
    move), about departures after the scenario ends, and about landing bases that cannot take the aircraft.

!!! tip "Players can still change it"
    A course is the unit's starting orders. On a side a player controls, the player can give the unit new orders
    at any time. On a computer side, the unit follows the course unless something else gives it new orders.
