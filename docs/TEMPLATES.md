# Unit templates

Unit templates are **pre-grouped sites** - airfields, command posts, barracks, communications centres, ports,
depots and more - that you name, orient and drop on the map in one go. Each becomes a set of ordinary units grouped
together (a CMO group in the build) that moves and rotates as one.

## Using them

- **Tools > Place unit template** (Ctrl+T), the map toolbar's **Templates...** button, or right-click the map >
  **Place unit template here...**
- Pick a template (search by name, contents or tags), enter a **site name** ("Amari" gives *Amari Control Tower*,
  *Amari HAS 1*...), the **side**, **position** and **orientation** (runways lie along it), and press **Place**. The
  preview shows the layout to scale.
- Components that host aircraft or boats are marked *host* (airfields, shelters, hangars, helipads, piers). Select one
  and use *Add to selected base* in the Database panel to station aircraft there.
- With *Group the site* ticked (the default) the site is a formation with "keep on station": drag any part on the
  map and the whole site follows; change the orientation on the Formations tab to rotate it. In CMO the parts are
  one group (no formation stations - sites do not move).
- Templates use generic DB3000 facilities. Swap any part for a national system afterwards with *Use for selected
  unit* in the Database panel (e.g. turn the generic *SAM Site* into an S-300 battery).
- **Save as unit template...** (Units tab, right-click) turns the selected units into a new template, keeping their
  layout relative to the first selected unit and its heading.

## Where the files are

| File | Purpose |
| --- | --- |
| `src/cmo_studio/data/templates.json` (in the exe: `_internal\cmo_studio\data\`) | The built-in templates. Replaced by updates. |
| `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\templates.json` | **Your library.** Written by *Save* in Tools > Template library or by *Save as unit template*; used instead of the built-in file when present. |

The Template library editor adds, duplicates and deletes templates and components, fills a component from the entry
selected in the Database panel, and imports, exports or resets the file.

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
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `x`, `y` | metres to the right of / ahead of the site origin, relative to the orientation |
| `at` | several positions; each becomes a unit named `<site> <label> 1`, `2`... |
| `db.type` | `Facility`, `GroundUnit`, `Ship`, `Submarine` or `Aircraft` |
| `db.name` | exact database name - the primary key |
| `db.dbid` | a hint, used only while its name still matches `db.name` (so new database versions are handled) |
| `db.search` | optional fallback words when the name is not found (e.g. in the Cold War database) |
| `host` | the unit can hold aircraft or boats; the first host component leads the group |
| `radar` | start with radars active |
| `hold` | mobile units hold position |

Components that cannot be found in the open database are skipped when placing, and the studio lists them.

## Built-in templates

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
