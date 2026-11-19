# Areas and reference points

## What they are

A **reference point** is a named marker on the map. CMO uses reference points for patrol areas, objectives and
anything that needs a position.

An **area** is a shape made of reference points: its corners. Missions patrol areas; events can fire when units
enter them. In CMO an area called `CAP_WEST` with four corners becomes four reference points named `CAP_WEST-1`,
`CAP_WEST-2`, `CAP_WEST-3` and `CAP_WEST-4`.

## Drawing an area on the map

1. Check **New objects on** shows the side the area belongs to.
2. Click **Draw area** on the map toolbar.
3. Click the map once for each corner, going round the shape in order.
4. Double-click the last corner, or press [[Enter]], to finish. ([[Backspace]] removes the last corner; [[Esc]]
   cancels.)
5. Name the area in the inspector.

To change the shape later, select the area and drag its white corner squares.

## The Areas tab

![The Areas tab](img/tab_areas.png)

1. **Areas**: the list of areas.
2. **Reference points**: the list of single markers.
3. **New area (box)**: adds a square area at the map centre to reshape.
4. **New reference point**: adds a marker at the map centre.
5. **From library...**: adds predefined patrol areas (below).
6. **Name**: the area's name. Use capitals and underscores, no spaces, for example `CAP_WEST`. The corners become
   `CAP_WEST-1`, `CAP_WEST-2`...
7. **Create on every side**: the points are created for every side, not just one. Use for shared objectives.
8. **Corners**: latitude and longitude of each corner. Type exact values or drag on the map. **Add corner**,
   **Remove corner**, **Reverse** and **Show** are underneath.
9. **Save to area library...**: keep this area for use in other scenarios.
10. **Delete area**.

!!! warning "A patrol area needs three corners"
    CMO needs at least three corners to make a patrol area. Missions can only use areas of their own side, or areas
    with **Create on every side** ticked.

**Reference points** have a name, side, position, **Highlighted** (shown in yellow in CMO) and **Create on every
side (objective markers)**, so every player sees the objective.

## The patrol area library

Instead of drawing common areas yourself, take them from the library: **208 sea and air areas** around the world.

Open it with **Tools > Add patrol area from library...** ([[Ctrl+Shift+A]]), **Patrol areas...** on the map
toolbar, the map's right-click menu, or **From library...** on the Areas tab.

![The area library](img/dialog_area_library.png)

1. **Search**: a name or a word such as `biscay`, `hormuz`, `chokepoint`, `CAP`, `tanker`.
2. **Region**: Europe, United Kingdom, Arctic, Middle East, Africa, Asia, Oceania, North America, South America.
3. **Sea / air**: show sea areas, air areas, or both.
4. **List**: grouped by region, then sea and air, with each area's size in nautical miles. Ctrl-click to choose
   several.
5. **Preview map**: the chosen area among its neighbours. Click another area on the preview to choose it.
6. **Side** the area is added for.
7. **Area name**: the name in your scenario (and of its corners).
8. **Create a mission on it**: also creates a mission on the area. **Suggested for each area** picks an
   anti-submarine or anti-ship patrol for sea areas, a combat air patrol for air areas, and a support mission for
   refuelling and early-warning orbits. Or choose one type for all.
9. **Add to scenario**.

The **United Kingdom** region covers all of UK airspace. Areas marked *official* use the exact boundaries published
in the UK Aeronautical Information Publication: the London and Scottish flight information regions (the QRA South
and QRA North areas), the danger areas of the main weapons ranges, and the air-to-air refuelling areas AARA 1 to 14.
The eight interception sectors, CAP stations, early-warning orbits and approach zones are *notional*: there is no
published version, so they are drawn to cover the airspace sensibly.

**Tools > Area library...** edits the library: change any area's corners (in a table, or by dragging them on the
little map), add your own, import, export or reset it. Your own library is kept through updates.
