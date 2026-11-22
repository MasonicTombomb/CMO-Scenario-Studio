# Architecture

```
src/cmo_studio/
  app.py                 entry point (GUI and headless --export / --dry-run)
  settings.py            QSettings wrapper, CMO install detection, tile sources
  updater.py             GitHub release check, verified installer download and hand-over
  geo.py                 coordinate parsing, distances, Web Mercator
  model/
    project.py           dataclasses for the whole project + JSON (de)serialisation
    enums.py             API vocab: unit types, mission classes, trigger/condition/action specs
    formations.py        formation presets, station geometry, apply/move helpers
    timeline.py          events, missions and courses on the scenario clock, timing problems
    course_plan.py       plotted-course estimates: legs, settings in force, timings, time on target, range
    route_library.py     saved courses (routes.json in the user's data folder)
    airbase.py           can aircraft taxi and take off? access points, checks and the repair
    intercept.py         intercept missions: conditions, presets, plain-English summary
    clock.py             the scenario at a moment: course positions, weather, events fired (the map clock)
    event_recipes.py     event recipes: common events from a few answers
    briefing_pack.py     flight schedule and the NATO-style operation order / intelligence summary (HTML)
    scenario_wizard.py   build a scenario skeleton from the New Scenario wizard's choices
    callsigns.py         callsign library (JSON), role detection, flight allocation
    templates.py         unit templates (JSON): DB resolution, placement, save-as-template
    area_library.py      predefined patrol areas (JSON): regions, add as zone + mission, save areas back
    validation.py        project checks (optionally against the database)
  db/
    database.py          read-only DB3000/CWDB access: search, details, loadouts, media
    loadouts.py          loadout and weapon detail queries for the Loadout Viewer
  export/
    compiler.py          project -> build data `D` and per-event Lua
    lua_writer.py        Python value -> Lua literal
    html.py              description/briefing pages, CSS, OOB generator
    pdf.py               print HTML to PDF (Edge/Chrome headless, Qt fallback)
    exporter.py          folder / zip writer with manifest and backups
    lua/
      Studio_Builder.lua the builder engine appended to Build_Scenario.lua
      Studio_Runtime.lua runtime helpers used by events
      Studio_Mock.lua    strict ScenEdit mock for dry-runs (never exported)
  data/
    callsigns.json       the default callsign library
    templates.json       the default unit templates
    templates_uk.json    UK real-world sites pack (templates_*.json files are merged in as packs)
    areas.json           the default patrol areas
  importers/
    lua_table.py         tolerant Lua table literal reader
    legacy_lua.py        If Russia Wins-style Build_Scenario.lua -> project
  tools/
    lua_engine.py        ctypes binding to CMO's lua54.dll: syntax check, dry-run
  ui/
    main_window.py       menus, tabs, docks, file handling
    document.py          ProjectDocument: undo/redo snapshots, dirty flag, selection
    db_browser.py        DBManager + DB browser dock
    loadout_viewer.py    Loadout Viewer window (linked loadout / weapon browsing with history)
    formation_widgets.py formation preview, preset picker, layout-settings form
    search.py            Ctrl+K search over objects, script lines and commands
    bulk_edit.py         edit fields on many units at once
    callsigns_ui.py      assign-callsigns dialog and callsign library editor
    templates_ui.py      template placer, preview and template library editor
    update_ui.py         update check, release notes dialog, download progress
    areas_library_ui.py  patrol area browser with map preview and area library editor
    forms.py             UnitForm, RPForm, ZoneForm (shared by map and pages)
    course_dialog.py     course window: route map, leg table and settings, flight profile chart
    recipe_dialog.py     event recipe form
    briefing_pack_dialog.py  edit, preview and print a side's briefing pack
    scenario_wizard.py   the New Scenario wizard (QWizard)
    widgets.py           code editor, highlighters, pickers, key/value table...
    dialogs.py           settings, new project, about, issues panel
    theme.py             dark Fusion theme
    map/                 tile cache and MapWidget
    pages/               one module per tab; base.py has Page and Binder
```

## Principles

- **The model knows nothing about Qt.** Model, export, importers, DB and Lua tools are plain Python and are covered
  by tests that run without a display.
- **One way to edit.** UI code changes the project only inside `ProjectDocument.modify(...)`, which snapshots for
  undo and emits `changed(kind, source)`. Pages refresh when another source changed the project (lazily, when they
  become visible). Editors keep ids, not object references, because undo replaces the project object.
- **Binder.** `pages/base.py:Binder` connects widgets to dataclass attributes, so forms are declarative.
  Rapid edits to the same field (typing) merge into one undo step.
- **Generated Lua is defensive.** Every ScenEdit call in the builder is protected and reported; the mock used for
  dry-runs is deliberately stricter than CMO about wiring.
- **Exports are safe to repeat.** The manifest limits replacements and clean-ups to files the studio wrote.

## Adding a trigger/condition/action type

1. Add it to `TRIGGER_TYPES` / `CONDITION_TYPES` / `ACTION_TYPES` in `model/enums.py` with its parameter spec
   (the event editor builds the form from it).
2. Compile it in `export/compiler.py` (`compile_trigger`, `condition_lua` or `action_lua`).
3. If it needs runtime help, add a `Studio*` function to `Studio_Runtime.lua` (and mock any new API in
   `Studio_Mock.lua`).
4. Validate its parameters in `model/validation.py`, and add a test.

## Documentation

The PDF manuals in `docs/manuals/` are built, not written by hand:

- `docs/manual/user/NN-*.md`: the User Manual, one file per chapter, joined in name order. `# Title {.unnumbered}`
  keeps a heading out of the chapter numbering (front matter, appendices); `!!! tip "Title"` makes a call-out box;
  `[[Ctrl+S]]` draws keys; `![caption](img/x.png)` on its own line becomes a captioned figure.
- The Reference Manual mixes `docs/manual/reference/*.md` with the reference docs in `docs/` (see `MANUALS` in
  `tools/make_manuals.py`), so those docs have a single source.
- `python tools/make_manual_shots.py` renders the annotated screenshots into `docs/manual/img/` (needs CMO for the
  database panel); `python tools/make_manuals.py` prints the PDFs with headless Chrome or Edge and records a
  fingerprint of their sources in `docs/manuals/manual-sources.sha256`.
- `python tools/release_check.py` checks a release is ready (version, changelog, notes, PDFs up to date, build
  tables, tests, git state); the release workflow runs it with `--ci` before publishing.
- `tests/test_manuals.py` checks every image exists, nothing failed to convert, and the chapter numbers the text
  refers to still hold.
