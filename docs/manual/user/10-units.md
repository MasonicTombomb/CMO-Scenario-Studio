# Units, bases and squadrons

## The unit inspector

Select any unit and its details appear in the **inspector** beside the map (and on the Units tab).

![The unit inspector](img/map_unit_inspector.png)

1. **Name**: the unit's name in CMO. Use real names (*HMS Montrose*) or callsigns (*VIPER 1*).
2. **Side**: which side it belongs to. Changing it moves the unit to the other side.
3. **Database**: the database entry (DBID and name). **Show in DB** shows it in the Database panel.
4. **Count**: how many identical units to build. More than 1 builds *Name #1*, *Name #2*, and so on. Ideal for a
   squadron of aircraft or a company of identical vehicles.
5. **Lat, lon**: the starting position. Type coordinates or drag the unit on the map. **Show** centres the map on
   it.
6. **Heading**: the direction it faces or travels at the start, in degrees (0 north, 90 east, 180 south, 270 west).
7. **Speed**: starting speed in knots. *default* lets CMO decide.
8. **Radar active**: the unit starts with its radars switched on. Untick for units that should stay hidden.
9. **Hold position**: the unit stays where it is rather than wandering.
10. **Proficiency**: overrides the side's crew quality for this unit.

Further down the inspector:

| Field | Meaning |
| --- | --- |
| Group | A free label, such as *Narva garrison*. Used for filtering on the Units tab and for bulk changes. |
| Starts at | For aircraft, helicopters and boats: the base or ship they start in (see *Bases and squadrons*). For other units, *(own position)*. |
| Altitude | For aircraft in the air at the start, in metres. *default* uses a typical altitude. |
| Depth | For submarines, in metres. *default* uses a typical depth. |
| Sonar active | The unit starts with active sonar on (it pings and can be heard). |
| Auto-detectable | Every side can always see this unit. Use for fixed landmarks such as airbases everyone knows about. |
| Reinforcement | The unit is not there at the start; an event brings it in later (see below). |
| Loadout (aircraft) | The weapons the aircraft carry. **View loadouts...** opens the Loadout Viewer. |
| Hosted units (bases and ships) | The aircraft and boats based here (see below). |
| Extra fields | Advanced: any other CMO unit setting, applied after the unit is built, such as `fuel` = `50`. |
| Notes | Your notes. Never exported. |

At the bottom, **Duplicate** makes a copy next to the original and **Delete unit** removes it.

## Bases and squadrons

Aircraft in CMO usually start inside a base: an airfield, a hangar or shelter, or a ship with a flight deck. The
studio calls the aircraft at a base a **squadron**: one unit entry with a **Count**.

**To base aircraft at an airfield:**

1. Place an airfield, or a whole real base from the template library (Chapter 12). The simplest airfield is a
   single facility: search the Database panel's **Facility** list for `Single-Unit Airfield` and pick a runway
   length.
2. Select the airfield (or the hangar or shelter you want) on the map.
3. In the Database panel set **Type** to **Aircraft**, find the aircraft and click it.
4. Click **Add to selected base**.
5. Enter **how many** (for example 12) and a **squadron name** (for example `No. 1 Sqn`).

![A base and its squadrons](img/map_airbase_inspector.png)

1. The base's own details.
2. **Hosted units**: the squadrons based here. Double-click one to select it and change its count, name or loadout.

The squadron starts with the first combat loadout listed in the database for that aircraft. To change it, select
the squadron and pick another **Loadout**, or double-click a loadout in the Database panel's **Loadouts** tab.

!!! warning "Base aircraft in a hangar, shelter or apron - not on a runway"
    Aircraft can only start in a **hangar**, **hardened aircraft shelter**, **apron (tarmac space)** or a whole
    **airfield**, or on a ship with a hangar or deck. A **runway**, taxiway or **control tower** cannot hold aircraft,
    and each space has a size limit and room for a set number: a *Hardened Aircraft Shelter (1x Medium Aircraft)*
    holds one fighter, a *Hangar (4x Large Aircraft)* four large aircraft.

    The studio checks this for you. **Add to selected base** will not put aircraft on a runway or tower: on a template
    base it offers that base's hangars, shelters and aprons that still have room. The **Issues** panel shows an
    error for aircraft whose base cannot hold them and a warning when more aircraft start at a base than fit. If it
    still happens, the build in CMO moves the aircraft to another hangar or shelter of the same base and says so in
    the report.

**Ships** with hangars or flight decks work the same way: select the ship, then **Add to selected base**.

## Reinforcements

A reinforcement is a unit that is **not there when the scenario starts** but arrives later, for example a second
squadron that flies in after two hours.

1. Create the unit as normal (place it, or add it to a base).
2. Tick **Reinforcement** in the inspector. On the map it turns faded with a dashed outline.
3. Make an event that brings it in (Chapter 15): for example **New ▾ > Reinforcements arrive after a delay**, which
   creates an event with a **Spawn unit** action two hours after the start.

When the event fires, the unit appears at its position (or in its base), joins any missions it is assigned to, and a
message can tell the player.

## The Units tab

The **Units** tab lists every unit in one table. It is the fastest way to find, check and change many units.

![The Units tab](img/tab_units.png)

1. **Filter**: type part of a name, class or group to show only matching units. The boxes beside it filter by side
   and type.
2. **The table**: name, side, type, database class, DBID, count, base, group, loadout and flags. Click a heading to
   sort. Click a row to select the unit (the inspector on the right shows it). Ctrl-click or Shift-click to select
   several; [[Ctrl+A]] selects all shown.
3. **Edit selected...**: change many units at once (below).
4. **Callsigns...**: name aircraft with real-world style callsigns (below).
5. **Assign to mission...**: add the selected units to a mission.
6. **Make formation**: group the selected units into a formation (Chapter 11).
7. **Toggle reinforcement**: switch the selected units between starting units and reinforcements.
8. **Delete selected**.

Right-click the table for the same commands plus **Show on map**, **Assign callsigns...** and **Save as unit
template...**.

## Editing many units at once

Select several units on the Units tab and click **Edit selected...** ([[Ctrl+Shift+E]]).

![Editing many units](img/dialog_bulk_edit.png)

Tick only the things you want to change (1, 2...); everything left unticked stays as it is. Click **OK** and every
selected unit changes. One [[Ctrl+Z]] undoes all of it.

| Option | What it changes |
| --- | --- |
| Rename | Names from a pattern: `{name}` the current name, `{n}` a running number, `{nn}` the number with a leading zero, `{class}` the database class, `{side}`, `{type}`. `Escort {nn}` gives *Escort 01*, *Escort 02*... |
| Side, Group tag, Count | As in the inspector. Moving units to another side removes them from that side's missions and formations. |
| Proficiency, Radar active, Sonar active, Hold position, Auto-detectable, Reinforcement | As in the inspector |
| Heading, Speed, Altitude, Depth, Starts at | As in the inspector |
| Loadout | Only when all selected units are the same aircraft type |
| Extra field | Set or remove one advanced CMO setting on all of them |

## Callsigns

Real air forces give each flight a callsign: *TARTAN 11, TARTAN 12...* The studio has a library of real-style
callsigns for 38 air arms, organised by country, squadron and role.

1. On the Units tab, select the aircraft to name (or select nothing to name every aircraft).
2. Click **Callsigns...** ([[Ctrl+Shift+C]]).

![Assigning callsigns](img/dialog_callsigns.png)

The window shows each aircraft with the **country** and **role** the studio has worked out from the database (a
fighter carrying anti-radar missiles is *SEAD*, a tanker is *Tanker*). Change either for any row if you disagree,
or pick a particular squadron. The preview shows the names before anything changes.

1. **Split counted units into single aircraft**: a squadron of six becomes six separate aircraft, each with its own
   callsign. Leave unticked to keep squadrons together.
2. **Edit callsign library...** opens the library to add or change callsigns.
3. **Apply** names the aircraft.

**Tools > Callsign library...** lets you add countries, squadrons and callsign words of your own, and import or
export the library to share it.

## Loadouts and the Loadout Viewer

A **loadout** is the set of weapons and stores an aircraft carries: *4x AIM-120, 2x AIM-9, 2x drop tanks*. Each
aircraft type has many, for different jobs. Choosing the right one matters: a fighter with a strike loadout cannot
fight other fighters.

Open the **Loadout Viewer** with **Tools > Loadout viewer...** ([[Ctrl+L]]), the **Loadout viewer** button in the
Database panel, or **View loadouts...** in an aircraft's inspector.

![The Loadout Viewer](img/dialog_loadout_viewer.png)

- **Left**: search for an aircraft, then filter its loadouts by role (air-to-air, strike, support, anti-submarine,
  reconnaissance, tanker) or by a weapon name such as `AMRAAM`.
- **Middle**: the chosen loadout: role, day/night and weather limits, combat radius, time on station, how long it
  takes to rearm, and every weapon with its range. (1) lists every version of the aircraft that has the loadout;
  (2) shows other loadouts carrying a weapon.
- **Right**: the weapon you click: ranges, probability of kill, warhead and seeker.

**Use for selected aircraft** gives the loadout to the aircraft selected in your scenario. It must be the same
aircraft entry, because loadouts belong to a specific DBID.
