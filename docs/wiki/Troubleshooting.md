# Troubleshooting

Use this page to narrow down common problems. When reporting a bug, include the studio version, Windows version, CMO/database version, steps to reproduce and the exact error text.

## Database browser is empty or cannot open the database

- Confirm that the selected file is a CMO DB3000 or CWDB SQLite database.
- Check that the path points to the database file, not the containing folder.
- Confirm that the file is accessible and not a stale copy.
- Select the database version that matches the one you plan to use in CMO.
- Remember that deprecated database entries may be hidden unless the relevant filter is enabled.

The studio opens the database read-only. It does not need write access to the database.

## A unit or loadout fails validation

- Confirm that the unit DBID exists in the selected database.
- Check whether the entry is deprecated or unavailable for the scenario year.
- Confirm that the aircraft loadout belongs to that aircraft in the selected database.
- Re-run validation after changing the selected database.

## The map has no background tiles

- Check the selected tile source and internet connection.
- Try another supported source (Esri, OpenStreetMap or OpenTopoMap).
- Use the offline grid if you need to work without a network connection.
- Remember that map tiles are cached locally.

## Exported scripts cannot be found by CMO

- Confirm that the exported `Lua/<folder>/` directory exists in the CMO installation.
- Check the folder name and script path against the generated `README.txt`.
- For multiplayer, make sure the runtime folder exists on the host machine as well.
- Avoid renaming exported folders after building unless you also update all references consistently.

## Builder refuses to create units

The builder normally refuses to run if scenario sides already contain units. Open a blank scenario before running the builder. Use the force-rebuild option only when you understand the consequences.

## A build reports warnings or failures

Read the complete build report. The builder protects API calls and reports failures or fallbacks; a warning does not necessarily mean the entire build stopped. Identify the failed object and correct it in the project, then export and rebuild.

## Dry-run is unavailable

The dry-run uses CMO's `lua54.dll`. Check that the CMO installation is detected and that the required runtime library is accessible. If it is unavailable, use validation and test the exported build in CMO.

## Application will not start

- Reinstall or repair the current packaged release.
- Check the release notes for known issues.
- If running from source, verify the Python environment and PyQt6 dependencies using the repository's development instructions.
- Capture the traceback or application log if one is produced.

## Report a problem

Open a [GitHub issue](https://github.com/MasonicTombomb/CMO-Scenario-Studio/issues). Include a minimal reproducible example where possible. Do not attach proprietary database files or other content you are not permitted to share.
