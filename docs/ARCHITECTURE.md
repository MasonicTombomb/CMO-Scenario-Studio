# Architecture

```
src/cmo_studio/
  app.py                 entry point (GUI and headless --export / --dry-run)
  settings.py            QSettings wrapper, CMO install detection, tile sources
  geo.py                 coordinate parsing, distances, Web Mercator
  model/
    project.py           dataclasses for the whole project + JSON (de)serialisation
    enums.py             API vocab: unit types, mission classes, trigger/condition/action specs
    validation.py        project checks (optionally against the database)
  db/
    database.py          read-only DB3000/CWDB access: search, details, loadouts, media
  export/
    compiler.py          project -> build data `D` and per-event Lua
    lua_writer.py        Python value -> Lua literal
    html.py              description/briefing pages, CSS, OOB generator
    exporter.py          folder / zip writer with manifest and backups
    lua/
      Studio_Builder.lua the builder engine appended to Build_Scenario.lua
      Studio_Runtime.lua runtime helpers used by events
      Studio_Mock.lua    strict ScenEdit mock for dry-runs (never exported)
  importers/
    lua_table.py         tolerant Lua table literal reader
    legacy_lua.py        If Russia Wins-style Build_Scenario.lua -> project
  tools/
    lua_engine.py        ctypes binding to CMO's lua54.dll: syntax check, dry-run
  ui/
    main_window.py       menus, tabs, docks, file handling
    document.py          ProjectDocument: undo/redo snapshots, dirty flag, selection
    db_browser.py        DBManager + DB browser dock
    forms.py             UnitForm, RPForm, ZoneForm (shared by map and pages)
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
