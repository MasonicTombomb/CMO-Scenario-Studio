# CMO Scenario Studio

CMO Scenario Studio is a Windows desktop application for designing scenarios for **Command: Modern Operations (CMO)**. It is written in Python with PyQt6.

The studio keeps your work in an editable **project file** (`.cmoproj`). It compiles that project into a Lua builder and supporting files; CMO runs the builder to create the playable scenario. This separation makes scenarios easier to revise, validate, share and keep under version control.

## Start here

- **[Getting Started](Getting-Started.md)** — install, launch and create your first project.
- **[Scenario Workflow](Scenario-Workflow.md)** — follow the complete design-to-build process.
- **[Map and Order of Battle](Map-and-Order-of-Battle.md)** — place units, build bases, groups and areas.
- **[Missions and Events](Missions-and-Events.md)** — configure mission tasks and scenario logic.
- **[Libraries and Reusable Content](Libraries-and-Reusable-Content.md)** — use templates, patrol areas and callsigns.
- **[Scripts and Briefings](Scripts-and-Briefings.md)** — add Lua behaviour and player-facing HTML.
- **[Validate and Export](Validate-and-Export.md)** — check, dry-run and install a build.
- **[Project and Export Formats](Project-and-Export-Formats.md)** — understand the files the studio reads and writes.
- **[Troubleshooting](Troubleshooting.md)** — diagnose common setup and build problems.
- **[Developer Guide](Developer-Guide.md)** — architecture, tests and contribution workflow.

## The basic model

1. Edit a `.cmoproj` project in CMO Scenario Studio.
2. Validate the project and, where available, run the dry-run.
3. Export the project. The export contains a one-shot `Build_Scenario.lua`, runtime helpers, scripts and HTML pages.
4. Open a blank scenario in CMO and run the exported builder in CMO's Lua console.
5. Review the build report, save the resulting scenario, and test it in-game.

> **Important:** The studio does not directly edit a native `.scen` file. CMO creates the playable scenario when it runs the generated Lua builder.

## Existing detailed documentation

The repository's [User Guide](../USER_GUIDE.md) is the most detailed reference for the application window, tabs, keyboard shortcuts and end-to-end workflows. Technical references include [Export Format](../EXPORT_FORMAT.md), [Project Format](../PROJECT_FORMAT.md), [Database Access](../DATABASE.md), [Patrol Area Library](../AREAS.md) and [Unit Templates](../TEMPLATES.md).

## Project links

- [Source code](https://github.com/MasonicTombomb/CMO-Scenario-Studio)
- [Issues and bug reports](https://github.com/MasonicTombomb/CMO-Scenario-Studio/issues)
- [Releases](https://github.com/MasonicTombomb/CMO-Scenario-Studio/releases)
