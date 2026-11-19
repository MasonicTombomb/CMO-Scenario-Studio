# Getting Started

This page takes you from installation to your first exported scenario.

## Requirements

- Windows.
- Command: Modern Operations (CMO), including its database files, for database-backed browsing and in-game building.
- A supported CMO installation and its DB3000 or CWDB SQLite database.
- The studio release appropriate for your system. Use the repository's [Releases](https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases) page for packaged builds.

The source project is Python/PyQt6. Developers building from source should follow the repository's setup instructions and [Developer Guide](Developer-Guide.md).

## Install and launch

1. Download the current release from [GitHub Releases](https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases).
2. Follow the release's installation instructions.
3. Launch **CMO Scenario Studio**.
4. If the database browser does not find your CMO database automatically, open the application settings and select the appropriate DB3000 or CWDB file.
5. Confirm that the database browser can search for a known unit.

Database access is read-only. The studio opens the SQLite database in read-only mode, so it does not alter CMO's database and can be used while CMO is open.

## Create a project

1. Choose **File > New scenario**.
2. Enter a title and select the database to use.
3. Add the scenario sides.
4. Save the project as a `.cmoproj` file.

A project is the editable source of truth. Save it regularly and keep it under version control if you collaborate or want a history of changes.

## Your first build

1. Set the scenario's location, author, start time (Zulu), duration and weather on the **Scenario** tab.
2. Configure side names, proficiency, awareness, doctrine and postures on **Sides**.
3. Open **Map**. Search for a unit in the Database dock, select it, choose **Place on map**, then click the map. Press **Esc** to stop placing.
4. Add areas or reference points as needed.
5. Create a mission and assign units on **Missions**.
6. Add an event if the scenario needs timed or conditional behaviour.
7. Add a description and side briefings on **Briefings**.
8. Open **Build & Export**, run **Validate**, then **Dry-run build** if the CMO Lua runtime is available.
9. Export the project.
10. Follow the generated `README.txt` instructions to run `Build_Scenario.lua` in CMO.

For a complete walkthrough, see [Scenario Workflow](Scenario-Workflow.md).

## Understand the exported files

The export is a structured folder, not a single scenario file. It normally includes:

- `Lua/<folder>/Build_Scenario.lua` — one-shot scenario builder.
- `Lua/<folder>/Studio_Runtime.lua` and `LuaInit.lua` — runtime helpers.
- Project scripts and the exported `project.cmoproj`.
- Scenario description and briefing HTML under `Scenarios/<folder>/`.
- `README.txt` — exact installation and Lua-console instructions.

See [Project and Export Formats](Project-and-Export-Formats.md).

## If something goes wrong

- No units appear in the browser: check the selected database path and that the file is a DB3000/CWDB database.
- The export succeeds but CMO cannot find a script: check that the exported `Lua/<folder>/` directory is installed in the CMO folder and matches the path in the build instructions.
- Validation reports an unknown DBID or loadout: select the same database version you intend to use in CMO and correct the affected unit.
- The application does not launch: consult the release notes and [Troubleshooting](Troubleshooting.md).
