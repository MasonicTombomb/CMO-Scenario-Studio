# Unit templates and real UK sites

A **unit template** is a ready-made site made of several units: an airfield with runways, hangars, a tower and
fuel; a command post with its bunkers and radios; a naval base with piers and docks. Placing a template drops the
whole site on the map in one go, correctly laid out and grouped.

The studio comes with two kinds:

- **181 templates in all.** **80 generic templates** you can place anywhere: airfields of every size, forward
  bases, command posts, radar and missile sites, barracks, depots, ports, power stations and more.
- **101 real UK military sites** at their real positions: 46 air bases laid out from OpenStreetMap with every
  runway, hardened aircraft shelter, hangar and tower, plus naval bases, radar heads, headquarters, communication
  sites, depots and garrisons.

## Placing a template

Choose **Tools > Place unit template...** ([[Ctrl+T]]), click **Templates...** on the map toolbar, or right-click the
map and choose **Place unit template here...**.

![Placing a unit template](img/dialog_template_placer.png)

1. **Search**: type part of a name, place or feature: `lossiemouth`, `airfield`, `HAS`, `radar`, `port`.
2. **Template list**, grouped by category, with the number of units in each. Click a template to see it; tick
   its box to place several at once (see *Placing several at once* below).
3. **Parts**: every component, how many, and the database entry each one uses. Red rows were not found in your
   database and will be left out.
4. **Site name**: units are named after it, for example *Amari Control Tower*, *Amari HAS 1*.
5. **Side**.
6. **At the real site**: for real-world templates (the UK sites), places the site where it really is. Untick it to
   put the same layout somewhere else.
7. **Orientation / runway heading**: which way the site faces. Runways lie along this direction.
8. **Group the site in CMO and keep it together on the map**: leave ticked. The site moves and rotates as one, and
   CMO treats it as one group.
9. **Preview** of the layout, to scale, north at the top.
10. **Place**: places the highlighted template, or every ticked one (the button then reads *Place 3 templates*).
11. **Ticked**: how many templates are ticked, their units, and where they will go. **Untick all** clears them.

After placing, the map shows the site. To move it, drag any part. To rotate it, select its formation on the
**Formations** tab and change **Orientation**.

## Placing several at once

Tick the box beside each template you want, then click **Place *n* templates**. Ticking a category's box ticks
every template shown in it (search first to narrow it down). Ticks are kept while you search, so you can find and
tick templates one after another.

- **Real-world templates** (the UK sites) go to their own positions and orientations, as long as **At the real
  site** is ticked. Each keeps its own site name, so units are called *Fairford Control Tower*, *Benson Hangar 1*
  and so on, and each site is its own group.
- **Other templates** go in a row running east from **Position**, spaced so they do not overlap, all facing
  **Orientation**. Untick **At the real site** to put real-world ones in the row too.
- **Site name** is greyed out: each template uses its own.
- Everything is placed as **one change**: one [[Ctrl+Z]] removes them all.
- The map then zooms out to show every placed site.

!!! example "RAF Fairford, RAF Benson and RAF Lossiemouth together"
    1. Open **Tools > Place unit template...** ([[Ctrl+T]]).
    2. Type `raf` in the search box.
    3. Tick **RAF Fairford**, **RAF Benson** and **RAF Lossiemouth**. The line under the list reads *3 ticked*.
    4. Check **Side**, leave **At the real site** ticked, and click **Place 3 templates**.

A template that is ticked is placed even when another one is highlighted; double-click a template to place just
that one.

## Real UK sites

The UK sites are in the categories starting **UK -**:

| Category | Examples |
| --- | --- |
| UK - Air bases | RAF Lossiemouth, Coningsby, Marham, Brize Norton, Lakenheath, Mildenhall, Fairford, RNAS Culdrose and Yeovilton, Wattisham, Odiham, and relief landing grounds |
| UK - Naval bases | HMNB Clyde (Faslane), RNAD Coulport, HMNB Devonport, HMNB Portsmouth, Rosyth, BAE Barrow |
| UK - Radar and air defence | RAF Fylingdales, RAF Boulmer, the remote radar heads, Sky Sabre at Thorney Island |
| UK - Command and control | RAF High Wycombe, Northwood, MOD Main Building |
| UK - Communications and intelligence | Menwith Hill, GCHQ Cheltenham and Bude, Croughton, Digby, Anthorn |
| UK - Nuclear, Logistics and munitions, Army garrisons | AWE Aldermaston and Burghfield, Glen Douglas, Kineton, Catterick, Tidworth, Colchester and more |

Air base runways are at their real positions, headings and lengths. CMO only has a few runway lengths (from 450 m to
4,000 m), so each runway uses the nearest one; the real length is shown in the preview. Runway access points beside
each runway connect it to the hangars and aprons: aircraft cannot taxi without them. Where OpenStreetMap does
not show a base's control tower or hangars, the template adds one and says so in its description.

## Using national equipment

Templates use **generic** database entries (*SAM Site*, *Radar (Generic Air Traffic Control)*) so they work in every
database. To make a site more specific, select a part on the map, find the national system in the Database panel
(for example an S-300 battery) and click **Use for selected unit**.

## Your own templates

- **Save as unit template...**: select units you have placed (on the Units tab), right-click and choose **Save as
  unit template...**. Give it a name and a category. Their layout and headings are kept, relative to the first unit
  you selected.
- **Tools > Template library...** opens the library editor:

![The template library](img/dialog_template_library.png)

1. **Import...** a library file someone has shared.
2. **Export...** your library to share it.
3. **Reset to defaults** goes back to the built-in templates.
4. **Add component** adds a part to the selected template. Select a row and click **Use Database panel entry** to
   fill it from the Database panel. Positions are in metres: *x* to the right, *y* ahead.
5. **Save** writes your library. Your own library lives in your user folder and is kept through updates; new
   built-in templates from updates are added to it automatically.
