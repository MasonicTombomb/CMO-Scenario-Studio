# Project and Export Formats

The studio uses a text-based project as its editable source and generates a structured Lua/HTML export for CMO.

## Project file: `.cmoproj`

A `.cmoproj` file is UTF-8 JSON. It stores scenario metadata, clock and weather, build options, sides, units, areas, missions, events, scripts, variants and related project data.

The format is designed to work well with version control:

- IDs are stable so references remain consistent.
- Lists preserve their order.
- Derived data is not stored unnecessarily.
- Unknown keys are ignored and missing keys use defaults, helping compatibility across versions.

Treat the project file as the authoritative editable source. Do not edit the generated scenario or exported builder as a substitute for changing the project unless you deliberately maintain custom code outside studio-owned files.

Reference: [Project File Format](../PROJECT_FORMAT.md).

## Export layout

The exporter creates a structure similar to:

```text
Lua/<ScenarioFolder>/
  Build_Scenario.lua
  Build_<VARIANT>.lua
  LuaInit.lua
  Studio_Runtime.lua
  <ProjectScript>.lua
  project.cmoproj
  README.txt
  .studio_manifest.json

Scenarios/<ScenarioFolder>/
  <Prefix>_Desc.html
  <Prefix>_Desc_<VARIANT>.html
  <Prefix>_Briefing_<SIDE>.html
  briefing_style_dark.css
```

Some files are conditional: variant launchers and variant description pages are only present when configured.

## Builder responsibilities

The one-shot builder creates or configures:

1. Sides and postures.
2. Scenario clock and weather.
3. Reference points and area points.
4. Units and host relationships.
5. Formations.
6. Missions and their assignments.
7. Initial key values.
8. Events and special actions.
9. A build report with counts, failures, warnings and editor instructions.

Calls to the CMO API are protected so failures can be reported rather than silently disappearing.

## Runtime initialization

`LuaInit.lua` loads `Studio_Runtime.lua`, defines the `STUDIO` context, runs scripts marked to load on initialization and sets the runtime-loaded flag. Generated event actions ensure the runtime is initialized if it is not already loaded.

No separate scenario-loaded event is required just to make generated event scripts find the runtime. Add one only if you want your own code to execute on every scenario load.

## Key values and variants

Initial project key values are written during the build and can be accessed from scripts with the runtime helpers. Build variants can set the active variant and change which sides are computer-controlled.

## Line endings and paths

Exported Lua and HTML files use Windows line endings to match CMO's own files. The generated README is the authority for exact folder and `[LOADDOC]` paths.

For the full data-table schema, build order and runtime API, see [Export Format and Lua Runtime](../EXPORT_FORMAT.md).
