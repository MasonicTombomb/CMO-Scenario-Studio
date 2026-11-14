# Changelog

## 1.1.0 — 2026-11-14

- **Loadout Viewer** (Tools > Loadout viewer, Ctrl+L; also from the Database dock and the aircraft inspector):
  loadout parameters, stores with quantities and ranges, per-weapon ranges/PoK/warheads/seekers/targets/capabilities,
  which aircraft carry a loadout, which loadouts carry a weapon, project units using it, back/forward navigation and
  one-click "use for selected aircraft".

## 1.0.0 — 2026-11-14

First release ("Version 1"), including a Windows exe (`CMO-Scenario-Studio-1.0.0-win64.zip`).

- Project model (`.cmoproj` JSON) with sides, units, hosted squadrons, reinforcements, reference points, areas,
  missions, events, special actions, scripts, briefings, variants and key values; undo/redo and autosave.
- Read-only DB3000/CWDB browser with images, sensors, weapons, loadouts, facilities and descriptions.
- Map editor on Web-Mercator tiles (Esri, OpenStreetMap, OpenTopoMap, custom, offline grid).
- Event editor with templates, studio date/delay triggers, Lua guards and a generated-Lua preview.
- Exporter producing the *If Russia Wins* / official-scenario layout, with manifest-based safe re-exports and backups.
- Validation (including DBIDs and loadouts against the database) and dry-run builds in CMO's own `lua54.dll`.
- Importer for *If Russia Wins*-style `Build_Scenario.lua` orders of battle.
- Headless `--export` and `--dry-run` command line.
- Example project *Baltic Sentinel* and its exported output.
- PyInstaller build (`packaging/build_release.py`) with a smoke test, version metadata and icon; GitHub Actions
  release workflow on version tags.
- Unhandled errors are logged to `error.log` in the studio's data folder and shown in a dialog instead of closing
  the app.
