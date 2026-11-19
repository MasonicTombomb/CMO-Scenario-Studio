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
