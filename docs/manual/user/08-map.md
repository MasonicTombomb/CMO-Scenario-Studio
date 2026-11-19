# The map

The **Map** tab is where you place forces and draw areas on a real map of the world.

## Moving around the map

| To... | Do this |
| --- | --- |
| Zoom in and out | Turn the mouse wheel, or press [[+]] and [[-]] |
| Move (pan) the map | Hold the left mouse button on an empty part of the map and drag |
| Show everything in the scenario | Click **Fit all** on the toolbar |
| Jump to a unit | Select it anywhere (Units tab, search) and choose **Show on map** |
| Centre on a spot | Right-click it and choose **Centre here** |

The scale bar at the bottom left shows distance and the zoom level. The status bar at the bottom of the window shows
the latitude and longitude under the mouse.

## The map toolbar

![The map toolbar](img/map_toolbar.png)

1. **Select / move**: the normal tool. Click to select a unit, area or reference point. Drag a unit or reference
   point to move it. Drag the white corner squares of a selected area to reshape it.
2. **Place unit**: places the entry selected in the Database panel each time you click. (Clicking **Place on map**
   in the Database panel switches to this tool for you.)
3. **Reference point**: each click adds a reference point, a named marker on the map.
4. **Draw area**: click once for each corner of an area. Finish with a double-click or [[Enter]]. [[Backspace]]
   removes the last corner; [[Esc]] cancels.
5. **Measure**: click points along a route. The map shows each leg's length in kilometres and nautical miles and
   its bearing. [[Esc]] clears it.
6. **Plot course**: select a unit first, then click the waypoints of the route it should take. Finish with a
   double-click or [[Enter]] (Chapter 14, *Courses*).
7. **New objects on**: the side that new units, areas and reference points belong to. **Check this before you
   place anything.**
8. **Templates...**: place a ready-made site such as an airbase or a real UK base (Chapter 12).
9. **Patrol areas...**: add ready-made patrol areas from the library (Chapter 13).
10. **Fit all**: zoom to show the whole scenario.
11. **Show ▾**: what the map shows. Tick or untick **Labels** (names), **Areas**, **Ref points**, **Courses** (unit
    courses) and **Grid** (a latitude/longitude grid), and each side's units, to unclutter the map.

At the right end, **Map** chooses the background picture:

| Map | Good for |
| --- | --- |
| Esri Dark Gray | General use; units stand out (the default) |
| Esri Ocean | Naval scenarios; shows sea depth and seabed features |
| Esri World Imagery | Satellite photos; placing units on real airfields, ports and roads |
| OpenStreetMap | Street-level detail and place names |
| OpenTopoMap | Hills and mountains, for ground scenarios |
| None (offline grid) | No internet needed |

Map pictures are downloaded from the internet and kept on disk, so areas you have looked at before also work
offline. *Custom* (in **File > Settings...**) accepts any map server that uses the common `{z}/{x}/{y}` web address
format.

## Placing units

1. In the **Database** panel, find the unit (Chapter 9) and click it.
2. Check **New objects on** is the right side.
3. Click **Place on map** (or double-click the row in the Database panel).
4. Click the map where the unit should start. Each click places another one.
5. Press [[Esc]] when you have placed enough.

Each new unit is selected so you can name it straight away in the inspector.

!!! tip "Ships and submarines must be in water"
    CMO will not create a ship on land. Zoom in close to coasts and harbours so you click in the water, or use
    **Esri World Imagery** to see exactly where the quay is.

## Selecting, moving and deleting

- Click a unit, area or reference point to select it. Its details appear in the inspector to the right of the map.
- Drag a selected unit or reference point to move it. A unit that is part of a formation or a grouped site moves
  the whole group (Chapter 11).
- To move an area, drag its corners one at a time (the white squares appear when it is selected).
- Press [[Delete]] to delete the selected object, or use **Delete unit** in the inspector. [[Ctrl+Z]] brings it back.
- Click an empty part of the map, or press [[Esc]], to select nothing.

## How things are drawn

| You see | It is |
| --- | --- |
| Coloured square, triangle or other symbol with a name | A unit, in its side's colour |
| A base with a small number badge | A base with that many aircraft or boats inside |
| Faded symbol with a dashed outline | A reinforcement: not there at the start, arrives later (Chapter 10) |
| Filled shape with corner squares | An area; white squares when selected |
| Small diamond | A reference point (yellow when highlighted) |
| Dashed lines from one unit to others | A formation: the lead joined to its members |
| Dashed line through numbered circles | A unit's course; a dotted last leg means it returns, lands elsewhere or loops |

## The right-click menu

Right-click the map for a menu of shortcuts. What it offers depends on what is under the mouse:

| On... | Choices |
| --- | --- |
| A unit | **Select**, **Duplicate**, **Plot course...** (or **Add waypoints to course...** and **Clear course**), **Make formation from this unit...** or **Edit formation**, **Delete** |
| An area | **Select**, **Save area to library...**, **Delete** |
| Anywhere | **Place** *entry* **here** (when a database entry is chosen), **Add reference point here**, **Place unit template here...**, **Add patrol area from library...**, **Draw area from here**, **Measure from here**, **Copy coordinates**, **Centre here** |

**Copy coordinates** copies the latitude and longitude under the mouse, ready to paste anywhere.
