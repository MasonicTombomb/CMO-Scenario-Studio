# Libraries and Reusable Content

CMO Scenario Studio includes editable libraries to speed up scenario construction and help keep common content consistent.

## Patrol area library

The built-in area library contains 208 predefined sea and air areas grouped by region. Examples include the Bay of Biscay, GIUK gaps, Baltic, Strait of Hormuz, Taiwan Strait and Falklands exclusion zone. The UK collection includes published airspace and range boundaries alongside clearly identified notional operating areas.

Open it through **Tools > Add patrol area from library**, the map toolbar, the map context menu or **From library...** on the Areas tab. You can filter by region, sea/air type and search terms.

Choose the side and exported area name. You can add multiple areas in one operation and optionally create a patrol or support mission for each. Suggested mission types are based on the area's kind and tags; review the suggestion before use.

Shapes outside the UK official-boundary set are approximate operating areas for gameplay, not legal or official boundaries. Adjust the corners to suit your scenario.

Use **Save to area library...** to retain an area you drew. **Tools > Area library** supports editing, duplicating, deleting, importing and exporting entries.

Reference: [Patrol Area Library](../AREAS.md).

## Unit templates

Templates are pre-grouped sites that can be named, oriented and placed as a single layout. The built-in collection includes 80 generic templates and a separate pack of 101 UK real-world sites.

Open **Tools > Place unit template** (Ctrl+T), use the map toolbar's **Templates...** button or right-click the map. Select a template, set its site name, side, position and orientation, inspect the preview, then place it.

For UK real-world sites, **At the real site** uses the stored real location and orientation. Disable it to reuse the layout elsewhere. Components marked as hosts can receive aircraft or boats through **Add to selected base**.

You can save a selection of units as a new template. The template library editor supports editing, importing, exporting and resetting the library.

Reference: [Unit Templates](../TEMPLATES.md).

## Callsigns

The callsign library includes entries for 38 air arms, approximately 365 squadrons and more than 1,100 callsign words. The studio can detect a unit's country and role and allocate names to flights. Review generated callsigns before export, especially for fictional or unusual orders of battle.

The built-in library is editable through the callsign library editor; entries can be added, renamed and shared.

## Formations

Formation presets cover naval screens and columns, carrier groups, convoys, ASW patterns, air formations and ground layouts. Adjust spacing, orientation, altitude step, mirror and jitter, then review the live preview. You can also define custom stations.

## Loadout Viewer

Open the Loadout Viewer with **Ctrl+L**. It displays aircraft loadouts with role, radius, time on station, ready and quick-turnaround times, mission profile and Winchester/Shotgun rule. It also exposes carried weapons and their details, and links to other aircraft/loadouts that use the same loadout or weapon.

You can apply a selected loadout to the selected squadron. Confirm that the chosen loadout exists in the database version used for validation and building.

## Personal library files

User-edited area and template libraries are stored in the application data directory under `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\`. The built-in data ships with the application; user libraries can be exported for sharing or backup.

Related technical notes: [Database Access](../DATABASE.md).
