# Database access

CMO ships its databases as SQLite files in `[CMO]\DB\` (`DB3K_<n>.db3` for 1980+, `CWDB_<n>.db3` for the Cold War).
The studio opens them with SQLite's `mode=ro` URI, so it cannot modify them and can run while CMO is open.

## Tables used

| Purpose | Tables |
| --- | --- |
| Units | `DataAircraft`, `DataShip`, `DataSubmarine`, `DataFacility`, `DataGroundUnit`, `DataSatellite` |
| Reference | `DataWeapon`, `DataSensor` |
| Lookups | `EnumOperatorCountry`, `EnumOperatorService`, `Enum<Type>Category`, `Enum<Type>Type`, `EnumLoadoutRole`, `EnumRunwayLength`, `EnumAircraftCode`, ... |
| Aircraft loadouts | `DataAircraftLoadouts` (aircraft → loadout), `DataLoadout`, `DataLoadoutWeapons` → `DataWeaponRecord` → `DataWeapon` |
| Sensors | `Data<Type>Sensors` → `DataSensor` |
| Weapons | `Data<Type>Mounts` → `DataMountWeapons` → `DataWeaponRecord` → `DataWeapon`, and the same via `Data<Type>Magazines` / `DataMagazineWeapons` |
| Loadout details | `DataLoadout` + `EnumLoadoutTimeOfDay`, `EnumLoadoutWeather`, `EnumLoadoutMissionProfile`, `EnumLoadoutWinchesterShotgun` |
| Weapon details | `DataWeaponTargets` → `EnumWeaponTarget`, `DataWeaponWarheads` → `DataWarhead`, `DataWeaponSensors` → `DataSensor`, `DataWeaponCodes` → `EnumWeaponCode` |
| Hosting | `Data<Type>AircraftFacilities` → `DataAircraftFacility`, `Data<Type>DockingFacilities` → `DataDockingFacility` |

Note that mount, magazine and loadout links point at **weapon records** (`DataWeaponRecord`, which carry the default
load), not directly at weapons.

## Columns of note

- `Deprecated` — CMO keeps retired entries for old scenarios; the browser hides them unless asked, and validation
  warns if a project uses one.
- `YearCommissioned` / `YearDecommissioned` — used for the *in service in scenario year* filter (0 = unknown).
- `Hypothetical` — shown as a tag.
- Loadout `3` is "(Reserve [Available])", which CMO accepts for every aircraft; the builder falls back to it if a
  chosen loadout is refused.

## Images and descriptions

`[CMO]\DB\Images\DB3000\<Type>_<id>.jpg` and `[CMO]\DB\Descriptions\DB3000\<Type>_<id>.txt` (or `CWDB`). File name
case is inconsistent in the install (`AIrcraft_1390.jpg`), so each folder is indexed once case-insensitively.

## Versions

DBIDs are stable between DB3K releases, but entries are deprecated over time. Set the project's database to the one
you will build with; validation checks every DBID and loadout against the database open in the browser.
