# Map and Order of Battle

The Map tab is the geographic workspace for placing units, building sites, drawing operating areas and measuring distances.

## Map sources and tools

The map supports Esri, OpenStreetMap, OpenTopoMap and an offline grid. Tiles are cached locally; the offline grid is available without an internet connection. A custom XYZ tile URL template can also be configured.

| Tool | Purpose |
| --- | --- |
| Select / move | Select objects and drag units, reference points or area corners |
| Place unit | Place the database entry selected in the Database dock |
| Reference point | Add a named marker |
| Draw area | Draw a polygon by clicking corners |
| Measure | Measure route legs in kilometres and nautical miles, with bearings |

To finish drawing an area, double-click or press **Enter**. **Backspace** removes the last corner. Press **Esc** to stop placing units. Right-click the map for contextual actions such as placing at the clicked location or copying coordinates.

## Place units

1. Search the Database dock by name, DBID, country or in-service year.
2. Select an entry and press **Place on map** (or double-click the database result).
3. Click the map to place it. Continue clicking to place more units; press **Esc** when finished.
4. Select the placed unit and edit its properties in the inspector.

The database browser also exposes descriptions, images, sensors, weapons, aircraft loadouts and hosting facilities where available.

## Airbases and hosted units

Place an airfield facility, select it, choose an aircraft in the Database dock and use **Add to selected base**. The aircraft squadron is created with a count and an initial combat loadout. Change the loadout in the inspector or choose another loadout from the browser.

The **Starts at** field links an aircraft or other hosted unit to a host. Aircraft are created at their host during the build.

## Areas and reference points

Use **Draw area** to create a polygon for patrols, support, triggers or other scenario logic. Areas are represented by named reference points when exported. A zone called `CAP_WEST`, for example, becomes points `CAP_WEST-1`, `CAP_WEST-2`, and so on.

Reference points can be placed individually. Enable **Create on every side** when objective markers should be visible to every side. Missions can use areas belonging to their side or areas marked for all sides.

## Formations and groups

The studio includes preset naval, air and ground layouts, as well as custom stations. Formation controls include spacing, orientation, altitude step, mirroring and jitter, with a live preview. You can create units directly into a formation from the database or group existing units.

A formation is exported as a CMO group with formation stations. A grouped site template is handled differently: it keeps components together in the studio, but its exported site components are not assigned formation stations.

## Bulk editing

Select multiple rows in the Units table and use bulk actions to change supported fields in one undo step. Available fields include rename patterns, side, group, proficiency, EMCON, hold, heading, speed, altitude, base and loadout.

## Reinforcements

Mark a unit as a **Reinforcement** to keep it out of the initial build. An event's **Spawn unit** action can create it later. The spawned unit is assigned to missions listed for it in the project and aircraft are placed at their host.

## Useful shortcuts

- **Ctrl+K** — search everything.
- **Ctrl+L** — open Loadout Viewer.
- **Ctrl+Shift+A** — add a patrol area from the library.
- **Ctrl+T** — place a unit template.
- **Ctrl+Z / Ctrl+Y** — undo / redo.

For reusable map content, see [Libraries and Reusable Content](Libraries-and-Reusable-Content.md).
