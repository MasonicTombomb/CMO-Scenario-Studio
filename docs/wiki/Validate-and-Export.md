# Validate and Export

Validation and dry-run testing catch many problems before you open CMO. They are complementary checks, not a substitute for a final in-game test.

## Validate

Open **Build & Export** and choose **Validate**. The studio performs project checks, including database-backed checks when a database is selected.

The checks cover areas such as:

- Missing or invalid references between units, sides, areas, missions and events.
- Unit DBIDs and aircraft loadouts against the selected database.
- Scenario timing and event timeline issues.
- Configuration and export problems detectable from the project.

Double-click an issue in the Issues dock to jump to the relevant object. Resolve errors first. Read warnings and decide whether each is intentional.

## Dry-run build

Choose **Dry-run build** to execute the generated builder and event scripts against the studio's strict mock of CMO's ScenEdit API, using CMO's `lua54.dll` when available.

A dry-run can catch Lua syntax problems and many incorrect API calls or references before export. It is not a full simulation of CMO: always test the final scenario in the game.

## Export

Choose **Export** and select the target. The exporter creates a structured scenario folder containing the Lua builder, runtime files, project scripts, project copy and HTML description/briefing pages.

The generated `README.txt` contains the exact `[LOADDOC]` lines and build instructions. Read it rather than manually reconstructing paths.

The exporter writes a manifest of files owned by the studio. On later exports, that manifest helps the studio safely replace its own files and avoid deleting unrelated files. Backups are created for replaced files.

## Build in CMO

1. Install or export the generated folder to the intended CMO installation.
2. Start CMO and open a **blank scenario** in the editor.
3. Open the Lua console and run the exported `Build_Scenario.lua` as directed by the generated README.
4. Review the builder's report in the Lua console.
5. Save the scenario in CMO.
6. Test the scenario, including events, missions, briefings and each intended player side.

The builder normally refuses to run when sides already contain units. This prevents accidental duplicate builds. The force-rebuild option exists for deliberate rebuild workflows; use it with care.

## Multiplayer and distribution

The runtime scripts are referenced at scenario run time. Ensure the scenario's `Lua/<folder>/` directory is present on the machine that runs the scenario (including the host in multiplayer). Include the scenario's required description and briefing files.

## If the build fails

Record the exact warning or error text and identify the stage that failed: validation, dry-run, export or CMO build. Check the database version, exported folder name, script path and generated README. See [Troubleshooting](Troubleshooting.md).
