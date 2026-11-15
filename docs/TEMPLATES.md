# Unit templates

Unit templates are **pre-grouped sites** - airfields, command posts, barracks, communications centres, ports,
depots and more - that you name, orient and drop on the map in one go. Each becomes a set of ordinary units grouped
together (a CMO group in the build) that moves and rotates as one.

The studio ships two kinds:

- **80 generic templates** (670 units) that you place anywhere: airfields of every size, command posts, radar
  and SAM sites, garrisons, depots, ports and infrastructure.
- **101 UK real-world sites** (1575 units) at their actual positions: **46 air bases** laid out from
  OpenStreetMap - every mapped runway at its real position, heading and length, each hardened aircraft shelter,
  hangar, apron, control tower, radar, fuel farm and munitions bunker - plus naval bases, radar heads, command
  centres, communications and intelligence sites, nuclear sites, munitions depots and garrisons.

## Using them

- **Tools > Place unit template** (Ctrl+T), the map toolbar's **Templates...** button, or right-click the map >
  **Place unit template here...**
- Pick a template (search by name, site, contents or tags - "lossiemouth", "HAS", "radar head"), enter a **site
  name** ("Amari" gives *Amari Control Tower*, *Amari HAS 1*...), the **side**, **position** and **orientation**
  (runways lie along it), and press **Place**. The preview shows the layout to scale.
- **Real-world sites** (the UK templates) tick **At the real site**: the position and orientation are set to the
  real base and locked. Untick it to put the same layout somewhere else (at the map centre or where you
  right-clicked) and rotate it freely - useful for a fictional base built like a real one.
- Components that host aircraft or boats are marked *host* (airfields, shelters, hangars, aprons, helipads, piers).
  Select one and use *Add to selected base* in the Database panel to station aircraft there.
- With *Group the site* ticked (the default) the site is a formation with "keep on station": drag any part on the
  map and the whole site follows; change the orientation on the Formations tab to rotate it. In CMO the parts are
  one group (no formation stations - sites do not move).
- Templates use generic DB3000 facilities. Swap any part for a national system afterwards with *Use for selected
  unit* in the Database panel (e.g. turn the generic *SAM Site* into an S-300 battery).
- **Save as unit template...** (Units tab, right-click) turns the selected units into a new template, keeping their
  layout and headings relative to the first selected unit.

## UK sites: how they were built

- **Air bases** come from OpenStreetMap. Runways are taken end to end (real heading and length) and become the
  nearest DB3000 runway class (450, 900, 1,400, 2,000, 2,600, 3,200 or 4,000 m); the real length is kept in the
  template and shown in the preview. Hardened aircraft shelters become *HAS (1x Medium)* or *(1x Large)* by size.
  Hangars become *A/C Hangar* entries sized from their footprint (2x Small up to 4x Very Large aircraft). Aprons of
  5,000 m² or more become tarmac parking spaces. Mapped towers, radars, fuel tanks (as one tank farm) and munitions
  bunkers are added where they are mapped.
- Where a base's control tower or hangars are not mapped, the template says so in its description and adds a single
  representative one so aircraft can still be based there. Coverage follows OpenStreetMap: well-mapped bases
  (Lossiemouth, Coningsby, Marham, Lakenheath...) are very detailed; a few small sites are sparse.
- **Other sites** (naval bases, radar heads, headquarters, comms, depots, garrisons) are schematic layouts at the
  real position, built from public sources: real berth and dock counts where published, representative counts
  otherwise. Radar heads use the UK radar types in DB3000 (Type 92, Type 93, Type 101, AN/TPS-77); Fylingdales uses
  the AN/FPS-132 early-warning radar.
- Air base layouts are © OpenStreetMap contributors under the ODbL - see `THIRD_PARTY_NOTICES.md`.

## Where the files are

| File | Purpose |
| --- | --- |
| `src/cmo_studio/data/templates.json` (in the exe: `_internal\cmo_studio\data\`) | The built-in generic templates. Replaced by updates. |
| `src/cmo_studio/data/templates_uk.json` | The UK real-world sites pack. Any `templates_*.json` file next to `templates.json` is loaded as a pack. |
| `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\templates.json` | **Your library.** Written by *Save* in Tools > Template library or by *Save as unit template*; used instead of the built-in files when present. |

Templates added to the built-in files by later updates are merged into your own library automatically. Your file
records which built-in templates it has already seen (`known_builtins`), so templates you deleted stay deleted.

The Template library editor adds, duplicates and deletes templates and components, fills a component from the entry
selected in the Database panel, sets a template's real location, and imports, exports or resets the file.

## Format

```jsonc
{
  "format": "cmo-studio-templates",
  "version": 1,
  "categories": ["Airfields (single unit)", ...],
  "templates": [
    {
      "id": "c2_field_cp",                 // unique key
      "name": "Field command post (battalion)",
      "category": "Command and control",
      "description": "Tactical command post: ...",
      "tags": ["hq", "c2"],
      "components": [
        { "label": "Command Post", "db": { "type": "Facility", "name": "Command Post", "dbid": 3730 }, "x": 0, "y": 0 },
        { "label": "C2 Trailer", "db": { "type": "Facility", "name": "Vehicle (C2/C3 Trailer)", "dbid": 3162 },
          "x": 40, "y": 30, "hold": true },
        { "label": "Guard Post", "db": { "type": "Facility", "name": "Building (Guard Post)", "dbid": 617 },
          "at": [[0, 250], [0, -250]] }
      ]
    },
    {
      "id": "uk_ab_lossiemouth",           // a real-world site
      "name": "RAF Lossiemouth",
      "site": "Lossiemouth",                // default site name: units become "Lossiemouth HAS 1"...
      "location": [57.7069, -3.3328],       // where the layout's origin really is
      "heading": 0,                         // orientation the layout is drawn in (0 = x east, y north)
      "components": [
        { "label": "Runway 05/23", "db": { "type": "Facility", "name": "Runway (2600m)", "dbid": 55 },
          "x": 0, "y": 0, "hdg": 44.1, "length": 2764 }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `x`, `y` | metres to the right of / ahead of the site origin, relative to the orientation |
| `at` | several positions; each becomes a unit named `<site> <label> 1`, `2`... |
| `hdg` | the part's own heading relative to the site orientation (crossing runways, angled piers) |
| `length` | real length in metres (runways) - shown in the preview and docs; CMO uses the database runway class |
| `db.type` | `Facility`, `GroundUnit`, `Ship`, `Submarine` or `Aircraft` |
| `db.name` | exact database name - the primary key |
| `db.dbid` | a hint, used only while its name still matches `db.name` (so new database versions are handled) |
| `db.search` | optional fallback words when the name is not found (e.g. in the Cold War database) |
| `host` | the unit can hold aircraft or boats; the first host component leads the group |
| `radar` | start with radars active |
| `hold` | mobile units hold position |
| `location`, `heading`, `site` | (template) a real-world site: its position, layout orientation and default site name |

Components that cannot be found in the open database are skipped when placing, and the studio lists them.

## UK real-world sites

### UK - Air bases

| Base | Runways | HAS | Hangars | Aprons | Munitions | Units |
| --- | --- | --- | --- | --- | --- | --- |
| **Army Aviation Centre Middle Wallop** | 17/35 (1,181 m), 08/26 (1,096 m) |  | 5 | 5 |  | 15 |
| **RAF Barkston Heath** | 06/24 (1,868 m), 10/28 (1,318 m), 18/36 (915 m) |  | 2 | 1 |  | 8 |
| **RAF Benson** | 01/19 (1,825 m) |  | 5 | 2 |  | 11 |
| **RAF Brize Norton** | 07/25 (3,050 m) |  | 4 | 10 |  | 17 |
| **Colerne Airfield** | 07/25 (1,096 m), 01/19 (888 m) |  | 9 |  |  | 12 |
| **RAF Coningsby** | 07/25 (2,744 m) |  | 15 | 5 |  | 23 |
| **RAF Cosford** | 06/24 (1,118 m) |  | 11 | 1 |  | 14 |
| **RAF Cranwell** | 08/26 (2,081 m), 01/19 (1,462 m) |  | 5 | 4 |  | 15 |
| **RNAS Culdrose** | 11/29 (1,830 m), 18/36 (1,056 m), 07/25 (1,045 m) |  | 12 | 8 | 7 | 33 |
| **Dishforth Airfield** | 15/33 (1,517 m) |  | 1 | 2 |  | 5 |
| **RAF Fairford** | 09/27 (3,046 m) |  | 3 | 10 |  | 18 |
| **RAF Halton** | 02/20 (1,161 m), 07/25 (868 m) |  | 1 | 1 |  | 6 |
| **RAF Henlow** | 02/20 (1,291 m) |  | 1 |  |  | 3 |
| **RAF Honington** | 09/27 (2,745 m) |  | 7 |  |  | 9 |
| **JHC Flying Station Aldergrove** | 07/25 (2,780 m), 17/35 (1,891 m) |  | 9 | 10 |  | 23 |
| **Keevil Airfield** | 06/24 (1,825 m), 12/30 (1,280 m), 01/19 (1,250 m) |  | 3 |  |  | 7 |
| **Kinloss Barracks** | 07/25 (2,370 m) | 8 | 13 | 6 |  | 30 |
| **RAF Lakenheath** | 05/23 (2,743 m) | 58 | 14 | 10 | 40 | 126 |
| **RAF Leeming** | 16/34 (2,291 m), 03/21 (793 m) | 6 | 7 | 2 |  | 19 |
| **Leuchars Station** | 08/26 (2,586 m) |  | 21 | 1 |  | 25 |
| **RAF Little Rissington** | 04/22 (1,311 m), 09/27 (1,074 m), 13/31 (975 m) |  | 1 |  |  | 5 |
| **RAF Lossiemouth** | 05/23 (2,764 m), 10/28 (1,850 m) | 18 | 12 | 9 | 7 | 51 |
| **MOD St Athan** | 07/25 (1,768 m) |  | 5 | 5 |  | 12 |
| **RAF Marham** | 06/24 (2,783 m), 01/19 (1,864 m) | 7 | 21 | 5 | 7 | 46 |
| **RNAS Merryfield** | 09/27 (1,771 m), 03/21 (1,238 m), 16/34 (1,161 m) |  | 1 | 1 |  | 6 |
| **RAF Mildenhall** | 10/28 (2,808 m) |  | 7 | 10 |  | 20 |
| **MoD Boscombe Down** | 05/23 (3,205 m), 17/35 (1,462 m), 05N/23N (766 m) | 11 | 7 | 4 |  | 27 |
| **RAF Mona** | 04/22 (1,579 m) |  | 1 |  |  | 5 |
| **Netheravon Airfield** | 11/29 (1,092 m), 06/24 (653 m), 04/22 (641 m) |  | 1 | 1 |  | 6 |
| **RAF Northolt** | 07/25 (1,683 m) |  | 5 | 3 |  | 11 |
| **RAF Odiham** | 09/27 (1,839 m) |  | 6 | 5 |  | 13 |
| **RNAS Predannack** | 05/23 (1,820 m), 18/36 (1,404 m), 09/27 (1,308 m), 13/31 (883 m) |  | 1 |  |  | 6 |
| **RMB Chivenor** | 09/27 (1,924 m), 15/33 (1,276 m) |  | 1 | 1 |  | 5 |
| **RAF Shawbury** | 18/36 (1,831 m), 05/23 (1,375 m) |  | 13 | 2 |  | 19 |
| **Stornoway (NATO forward operating base)** | 18/36 (2,088 m), 06/24 (1,000 m) |  | 1 | 2 |  | 7 |
| **RAF Syerston** | 06/24 (1,810 m), 11/29 (559 m) |  | 1 | 1 |  | 6 |
| **Ternhill Airfield** | 04/22 (968 m), 10/28 (905 m) |  | 1 | 1 |  | 5 |
| **RAF Topcliffe** | 02/20 (1,826 m), 13/31 (1,256 m) |  | 1 | 2 |  | 6 |
| **Upavon Airfield** | 05/23 (1,041 m), 07/25 (923 m) |  | 3 |  |  | 6 |
| **RAF Valley** | 13/31 (2,290 m), 01/19 (1,572 m) |  | 10 | 5 |  | 18 |
| **RAF Waddington** | 02/20 (2,940 m) |  | 9 | 9 |  | 21 |
| **Wattisham Flying Station** | 05/23 (2,423 m) |  | 6 | 1 |  | 9 |
| **RAF Wittering** | 07/25 (2,757 m), 29/11 (346 m) |  | 1 | 5 |  | 10 |
| **RAF Woodvale** | 03/21 (1,648 m), 08/26 (1,060 m) |  | 3 |  |  | 6 |
| **RAF Wyton** | 09/27 (2,507 m) |  | 5 |  |  | 8 |
| **RNAS Yeovilton** | 08/26 (2,293 m), 04/22 (1,464 m) |  | 15 | 9 |  | 30 |

### UK - Naval bases

| Site | Units | Contents |
| --- | --- | --- |
| **HMNB Clyde (Faslane)** | 21 | 5x Submarine Berth, Shiplift, Surface Ship Berth, Base HQ, 8x Barracks, Submarine Training Centre, Comms, 3x Guard Post |
| **RNAD Coulport** | 18 | Explosives Handling Jetty, 12x Warhead Storage Bunker, Processing Building, Security HQ, 3x Guard Post |
| **HMNB Devonport** | 42 | 12x Dry Dock, 2x Small Dry Dock, 12x Tidal Berth, Basin Berth, Submarine Refit Complex, Base HQ, 8x HMS Drake Barracks, Comms, Fuel Depot, 3x Guard Post |
| **HMNB Portsmouth** | 26 | Princess Royal Jetty, Victory Jetty, 5x Destroyer Berth, 6x Dry Dock, Base HQ, 8x HMS Nelson Barracks, Comms, Fuel Depot, 2x Guard Post |
| **Rosyth Dockyard** | 10 | No.1 Dock, 2x Dry Dock, 3x Basin Berth, Fabrication Hall, Offices, 2x Guard Post |
| **BAE Systems Barrow (submarine yard)** | 8 | Devonshire Dock Hall, Shiplift, 2x Fitting-out Berth, 2x Assembly Shop, Offices, Guard Post |
| **Marchwood Military Port** | 11 | 3x Jetty, 4x Warehouse, HQ, 2x Barracks, Guard Post |

### UK - Radar and air defence

| Site | Units | Contents |
| --- | --- | --- |
| **RAF Fylingdales** | 7 | Early Warning Radar, Operations Centre, Generator, 2x Accommodation, 2x Guard Post |
| **RAF Boulmer (Control and Reporting Centre)** | 6 | Control and Reporting Centre, Comms, Operations Building, 2x Barracks, Guard Post |
| **RRH Saxa Vord** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Buchan** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Benbecula** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Brizlee Wood** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Staxton Wold** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Neatishead (Trimingham)** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **RRH Portreath** | 5 | Air Defence Radar, Operations Building, Comms, Generator, Guard Post |
| **Baker Barracks, Thorney Island (Sky Sabre)** | 15 | 2x Sky Sabre Battery, HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |

### UK - Command and control

| Site | Units | Contents |
| --- | --- | --- |
| **RAF High Wycombe (Air Command)** | 9 | Air Operations Bunker, Headquarters, Comms, 4x Barracks, 2x Guard Post |
| **Northwood Headquarters (PJHQ / NATO MARCOM)** | 10 | Joint Operations Bunker, 2x Headquarters, Comms, 4x Barracks, 2x Guard Post |
| **MOD Main Building (Whitehall)** | 3 | Main Building, Crisis Management Centre, Comms |

### UK - Communications and intelligence

| Site | Units | Contents |
| --- | --- | --- |
| **RAF Menwith Hill** | 35 | 30x Radome, Operations Centre, Operations Building, Comms, 2x Guard Post |
| **GCHQ Cheltenham** | 5 | The Doughnut, Data Centre, Comms, 2x Guard Post |
| **GCHQ Bude** | 23 | 21x Satellite Dish, Operations, Guard Post |
| **RAF Croughton** | 11 | Communications Centre, 6x Antenna, 2x Satellite Terminal, Barracks, Guard Post |
| **RAF Digby** | 8 | Signals Building, 4x Antenna, 2x Barracks, Guard Post |
| **Anthorn VLF transmitter** | 15 | 13x VLF Mast, Transmitter Building, Guard Post |
| **Skelton transmitter** | 4 | 3x Mast, Transmitter Building |
| **HMS Inskip (naval radio station)** | 10 | 8x Antenna, Operations, Guard Post |

### UK - Nuclear

| Site | Units | Contents |
| --- | --- | --- |
| **AWE Aldermaston** | 8 | 2x Assembly Facility, 2x Research Building, Admin, 3x Guard Post |
| **AWE Burghfield** | 6 | Assembly Facility, 2x Magazine, Admin, 2x Guard Post |

### UK - Logistics and munitions

| Site | Units | Contents |
| --- | --- | --- |
| **DM Glen Douglas (NATO munitions depot)** | 27 | 24x Magazine, Admin, 2x Guard Post |
| **DM Kineton** | 34 | 30x Magazine, Admin, Rail Yard, 2x Guard Post |
| **DM Longtown** | 18 | 16x Magazine, Admin, Guard Post |
| **DM Beith** | 18 | 16x Magazine, Admin, Guard Post |

### UK - Army garrisons

| Site | Units | Contents |
| --- | --- | --- |
| **Catterick Garrison** | 24 | HQ, 16x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Infantry Training Centre |
| **Tidworth Garrison** | 25 | HQ, 14x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, 4x Tank Park |
| **Bulford Camp** | 20 | HQ, 12x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Division HQ |
| **Larkhill Garrison** | 17 | HQ, 10x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Aldershot Garrison** | 20 | HQ, 12x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Military Hospital |
| **Colchester Garrison** | 19 | HQ, 12x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Army Training Centre Pirbright** | 17 | HQ, 10x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Royal Military Academy Sandhurst** | 16 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Old College |
| **Bovington Camp** | 19 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, 4x Tank Park |
| **Land Warfare Centre, Warminster** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Infantry Battle School, Brecon** | 13 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Thiepval Barracks, Lisburn** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Fort George** | 14 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Fort |
| **Stirling Lines, Credenhill** | 14 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, Helipad |
| **Commando Training Centre Royal Marines** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **RM Condor, Arbroath** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **RM Bickleigh** | 13 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Norton Manor Camp** | 13 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **Britannia Royal Naval College** | 15 | HQ, 6x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park, College, Training Jetty |
| **HMS Raleigh** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |
| **HMS Collingwood** | 15 | HQ, 8x Barracks, 2x Guard Post, Medical Centre, Comms, 2x Vehicle Park |

## Generic templates

### Airfields (single unit)

| Template | Units | Contents |
| --- | --- | --- |
| **Heliport** | 3 | Airfield, Fuel Bladder, Tents |
| **Airstrip (451-900 m)** | 3 | Airfield, Fuel Bladder, Tents |
| **Small airfield (901-1,400 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Airfield (1,401-2,000 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Airfield (2,001-2,600 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Air base (2,601-3,200 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Major air base (3,201-4,000 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Strategic air base (4,000 m+)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Twin-runway airfield (2x 2,001-2,600 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Twin-runway air base (2x 2,601-3,200 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Twin-runway major air base (2x 3,201-4,000 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |
| **Hub airfield (3x 3,201-4,000 m)** | 7 | Airfield, Control Tower, ATC Radar, Fuel, 2x Ammo Bunker, Barracks |

### Airfields (multi unit)

| Template | Units | Contents |
| --- | --- | --- |
| **Tactical fighter base (1x 2,600 m, 12 HAS)** | 36 | Runway, Taxiway, 4x Runway Access Point, 12x HAS, Control Tower, ATC Radar, Squadron Ops, Fuel Farm, 4x Munitions Store, 2x Barracks, Comms Hub, Generator, 3x AAA, SAM Site, 2x Guard Post |
| **Main operating base (2x 3,200 m)** | 46 | Runway, Taxiway, 4x Runway Access Point, Runway, Taxiway, 4x Runway Access Point, 2x Heavy Apron, 2x Large Hangar, 8x HAS, Control Tower, ATC Radar, Air Search Radar, Base HQ, Fuel Farm, 4x Munitions Store, 3x Barracks, Hospital, Comm Center, Power Substation, 3x AAA, 2x SAM Site, 2x Guard Post |
| **Strategic bomber base (4,000 m)** | 25 | Runway, Taxiway, 4x Runway Access Point, 2x Bomber Apron, 2x Bomber Hangar, Control Tower, ATC Radar, Wing HQ, Fuel Storage, 4x Weapons Storage, 3x Barracks, 2x SAM Site, 2x Guard Post |
| **Hardened mountain air base** | 15 | Runway, Taxiway, 4x Runway Access Point, Underground Shelter, 2x Shelter Entrance, Control Tower, Underground Fuel, Mountain Ammo Bunker, Command Bunker, 2x AAA |
| **Helicopter base** | 14 | 6x Helipad, 2x Heavy Helipad, 2x Hangar, Tower, Fuel, Ammo Shelter, Barracks |
| **Road base / dispersed strip** | 11 | Road Runway, 6x Camouflaged Revetment, Fuel Bowsers, Ammo Trucks, Tents, Inf Plt (Security) |
| **Expeditionary airfield (short tactical strip)** | 11 | Tactical Strip, 4x Parking, 2x Fuel Bladder, Ammo Pad, 2x Tents, ATC Radar |
| **Forward arming and refuelling point (FARP)** | 9 | Landing Zone, 4x Helipad, Refuelling System, Fuel Bladder, Ammo Pad, Security Section |
| **Civil airport** | 7 | Airport, Terminal, Control Tower, ATC Radar, Fuel Farm, Car Park, Hotel |

### Command and control

| Template | Units | Contents |
| --- | --- | --- |
| **Field command post (battalion)** | 5 | Command Post, C2 Trailer, Vehicles, Generator, Security Platoon |
| **Brigade headquarters (field)** | 9 | Brigade HQ, 2x C2 Trailer, UAV Ground Control, EW Company, Guard Company, AAA, 2x Tents |
| **Hardened command bunker (strategic)** | 12 | Command Bunker, Comm Center Bunker, HF Antenna, Uplink, 2x Barracks, Generator, 4x Guard Post, SAM Site |
| **Air defence sector operations centre** | 8 | Sector Control, Air Search Radar, Radome, Comm Center, Uplink, Barracks, 2x Guard Post |
| **Mobile air defence control post** | 4 | Sector Control Vehicle, Short-Range Radar, C2 Trailer, Security Platoon |
| **ICBM launch control complex** | 5 | Launch Control Facility, Missile Alert Facility, Barracks, 2x Guard Post |

### Communications and EW

| Template | Units | Contents |
| --- | --- | --- |
| **Military communications centre** | 10 | Comm Center, Communication Hub, 3x HF Antenna, Satellite Uplink, Generator, Barracks, 2x Guard Post |
| **Hardened communications bunker** | 5 | Comm Bunker, 2x HF Antenna, Mast, Guard Post |
| **Radio and TV broadcast station** | 5 | Radio/TV Station, TV Mast, FM Tower, TV Tower, Generator |
| **Cellular network cluster** | 4 | 4x Cell Tower |
| **Signals intelligence station** | 9 | SIGINT Station, ELINT Station, 3x Radome, HF/DF, Barracks, 2x Guard Post |
| **Hardened intelligence complex** | 5 | SIGINT Bunker, ELINT Bunker, COMINT Bunker, 2x Radome |
| **SOSUS / acoustic shore station** | 3 | ACINT SOSUS Station, Comm Center, Guard Post |
| **Electronic warfare site** | 5 | Comms Jammer, OECM Station, 2x Mobile Jammer, GNSS Jammer |
| **Mobile ELINT detachment** | 3 | ELINT Vehicle, PCL Receiver, Security Section |
| **Navigation aids (VOR + NDB)** | 2 | VOR, NDB |

### Radar and air defence

| Template | Units | Contents |
| --- | --- | --- |
| **Early-warning radar site** | 6 | Air Search Radar, Radome, Generator, Barracks, AAA, Guard Post |
| **Coastal surveillance station** | 4 | Surface Search Radar, Observation Post, Lighthouse, Generator |
| **SAM site (generic, reveted)** | 8 | SAM Site, Search Radar, 4x Revetment, AAA, Generator |
| **Air defence battalion (field)** | 9 | AD Battalion, Sector Control Vehicle, Search Radar, 3x SAM Site, 3x AAA |
| **AAA position** | 4 | 3x AAA, Fire Control Radar |
| **Aerostat radar site** | 3 | Aerostat, Generator, Barracks |

### Garrisons and bases

| Template | Units | Contents |
| --- | --- | --- |
| **Barracks (company garrison)** | 7 | 2x Barracks, Company HQ, Vehicle Depot, Rifle Company, 2x Guard Post |
| **Battalion garrison (military base)** | 17 | Military Base, 4x Barracks, Battalion HQ, Vehicle Depot, Truck Depot, 2x Ammo Bunker, Diesel Tank, 4x Watch Tower, 2x Guard Post |
| **Forward operating base (FOB)** | 15 | FOB, 4x Tents, 4x Watch Tower, 2x Helipad, Fuel Bladder, Ammo Pad, Mortar Platoon, Infantry Company |
| **Combat outpost (COP)** | 7 | 2x Tents, 2x Watch Tower, Infantry Platoon, Heavy MG Platoon, Mortar Platoon |
| **Observation post** | 3 | Observation Post, Forward Air Controller, Observer |
| **Desert fort** | 8 | Desert Fort, 4x Watch Tower, Garrison, 2x Technicals |
| **Peacekeeping checkpoint** | 4 | UN Platoon, 2x Guard Post, Vehicles |

### Logistics

| Template | Units | Contents |
| --- | --- | --- |
| **Ammunition depot** | 20 | 8x Ammo Bunker, 4x Ammo Revetment, 2x Ammo Pad, Ammo Trucks, 4x Watch Tower, Guard Post |
| **Fuel depot (tank farm)** | 9 | 4x Diesel Tank, Pump House, Pipeline, Truck Depot, Fuel Bowsers, Guard Post |
| **Aviation fuel storage (hardened)** | 4 | 2x AvGas Bunker, Underground Tank, Pump House |
| **Logistics hub / supply point** | 7 | Logistics Company, Container Park, Truck Depot, 2x Trucks, Fuel Bowsers, Ammo Trucks |
| **Railway yard** | 6 | Railway Yard, Railway Station, 2x Warehouse, 2x Train |
| **Field hospital** | 6 | 3x Hospital Tents, Landing Zone, Helipad, Generator |
| **Defended bridge crossing** | 6 | Bridge, 2x Infantry Platoon, AAA, 2x Guard Post |
| **Pontoon river crossing** | 4 | Pontoon Bridge, Pontoon Carriers, Bridgelayer, AAA |

### Naval

| Template | Units | Contents |
| --- | --- | --- |
| **Naval base (small)** | 9 | Port, 2x Pier, Naval Dock, 2x Diesel Tank, Base HQ, Barracks, Port Crane |
| **Naval base (major)** | 28 | Naval Dock, 3x Fleet Pier, Carrier Pier, Dry Dock, 4x Port Crane, 4x Fuel Tank, 4x Ammo Bunker, Fleet HQ, 3x Barracks, Surface Search Radar, 2x SAM Site, 3x Guard Post |
| **Submarine base** | 7 | Submarine Pens, Underground Pier, 2x Torpedo Bunker, Diesel Bunker, Command Bunker, Guard Post |
| **Commercial port** | 11 | Port, 2x Cargo Pier, 4x Port Crane, Container Park, 2x Oil Tank, Warehouse |
| **Fleet anchorage** | 7 | 6x Mooring Buoy, Boom Net |
| **Coastal missile battery position** | 7 | SSM Battery, 4x Missile Revetment, Surface Search Radar, C2 Trailer |

### Missiles and drones

| Template | Units | Contents |
| --- | --- | --- |
| **SSM battery (field)** | 7 | SSM Battery, 4x Missile Revetment, C2 Trailer, Reload Trucks |
| **Hardened missile site** | 8 | 4x Hardened Missile Shelter, Command Bunker, SAM Site, 2x Guard Post |
| **Loitering-munition battery** | 3 | Drone Battery, UAV Ground Control, Security Section |
| **UAV launch site** | 5 | UAV Launch Site, UAV Ground Control, 2x Launch Truck, Tents |

### Ground forces

| Template | Units | Contents |
| --- | --- | --- |
| **Mechanised battlegroup (generic)** | 7 | Battlegroup HQ, Armoured Company, 2x Mech Inf Company, Artillery Battery, AAA, Logistics Company |
| **Infantry battalion position** | 7 | Battalion HQ, 3x Infantry Company, Mortar Platoon, 2x Recon Section |
| **Artillery battalion firing position** | 5 | Battalion CP, 3x Artillery Battery, Ammo Trucks |

### Infrastructure

| Template | Units | Contents |
| --- | --- | --- |
| **Gas power station** | 5 | Power Station, Substation, 2x Transformer, Transmission Line |
| **Nuclear power plant** | 5 | Nuclear Power Station, 2x Reactor, Turbine Hall, Substation |
| **Dam and hydro-electric plant** | 3 | Dam, Hydro Power Station, Substation |
| **Oil refinery complex** | 10 | Refinery, 6x Storage Tank, Pump House, Pipeline, Chimney |
| **Oil field** | 6 | 5x Oil Well, Pump House |
| **Government district** | 6 | 2x Ministry, Palace, Leadership Compound, Police Station, Radio/TV Station |
| **Small town** | 9 | Town, Hospital, School, Police Station, Place of Worship, 4x Houses |
| **Village** | 6 | Village, 5x House |
| **Training / bombing range** | 8 | Bullseye, 6x Target, Range Tower |
