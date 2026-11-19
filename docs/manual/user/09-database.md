# The Database panel

Every unit in CMO comes from its database: a huge catalogue of real ships, submarines, aircraft, ground units,
weapons, sensors and buildings. The **Database** panel lets you search it and use what you find. It reads CMO's
files directly and can never change them.

![The Database panel](img/database_dock.png)

1. **Database file**: which CMO database to browse.
2. **Type**: what kind of entry to list: **Aircraft**, **Ship**, **Submarine**, **Facility**, **GroundUnit**,
   **Satellite**, **Weapon** or **Sensor**.
3. **Search**: type part of the name. A second box beside it filters by operator country.
4. **In service in scenario year**: only show equipment in service in the year your scenario starts.
5. **Show deprecated**: also show old entries CMO keeps only for old scenarios.
6. **Results**: DBID, name, country, type and years in service. Click a column heading to sort.
7. **Place on map**: place the selected entry on the map (Chapter 8).
8. **Add to selected base**: put aircraft into the selected airbase, hangar or ship (Chapter 10).
9. **Use for selected unit**: change the selected unit into this entry, keeping its name, position and settings.
10. **Loadout viewer**: see every weapons loadout of the selected aircraft (Chapter 10).
11. **Details tabs**: the selected entry's **Sensors**, **Weapons**, **Loadouts**, **Facilities** (hangars, docks,
    runways it has) and CMO's **Description**, under a picture and key figures.

## Which database?

CMO comes with two families of database:

| Database | Covers | Use for |
| --- | --- | --- |
| `DB3K_<number>.db3` (DB3000) | 1980 to the present and near future | Modern scenarios |
| `CWDB_<number>.db3` (Cold War) | 1946 to 1979 | Cold War scenarios |

Each new CMO update adds a new numbered version (for example `DB3K_518`, then `DB3K_519`). Newer versions add
and correct equipment. **Use the newest one** for a new scenario. A project stays on the database it was made with
until you change it on the Scenario tab.

## Searching well

- **All the words you type must appear in the name**, in any order: `typhoon fgr` finds *Typhoon FGR.4*.
- Typing a **number** also finds that DBID: `2814` finds the entry with DBID 2814.
- Ship and submarine entries are named after one ship of the class, followed by the class in brackets:
  *F 236 Montrose [Type 23 Duke]*. Search for the class name (`type 23`) to see every version.
- Aircraft often have many entries with the same name, one for each version and era. Look at the **Years** and
  **Country** columns and choose the one that matches your scenario.
- Facilities include runways, hangars, radars, missile sites, buildings and whole airfields. Search `airfield`,
  `runway`, `radar`, `SAM` or `bunker` to explore.

## The DBID

Every entry has a number, its **DBID** (database ID). It identifies the entry in that database and is how the
studio and CMO refer to it. Two entries can have the same name but never the same DBID. You see the DBID in the
results and in the unit inspector.

!!! note "Read-only"
    *Database values are read-only and come straight from your CMO install.* You cannot change a ship's speed or a
    missile's range here; that is fixed by CMO's database.
