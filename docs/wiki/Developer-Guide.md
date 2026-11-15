# Developer Guide

This page is an orientation for contributors working on CMO Scenario Studio.

## Architecture at a glance

The application is a Python/PyQt6 desktop program. Its main layers are:

- **Model** — project dataclasses, enums, formation geometry, timeline logic, callsigns, templates, area libraries and validation.
- **Database** — read-only SQLite access to DB3000/CWDB, including unit details and loadout/weapon relationships.
- **Importers** — tolerant Lua table parsing and import of legacy Lua-driven scenario builders.
- **Export** — project-to-build-data compiler, Lua writer, HTML generation and safe folder/ZIP export.
- **UI** — main window, project document/undo-redo, database dock, map, tabs, editors and library dialogs.
- **Lua tools** — binding to CMO's Lua 5.4 runtime and a strict mock of the ScenEdit API for dry-runs.

The model and export layers are designed not to depend on Qt, allowing tests to run without a display.

## Development principles

- Make project edits through the document modification mechanism so undo/redo and change notifications remain correct.
- Keep stable IDs rather than retaining object references across undo/redo snapshots.
- Keep the project model independent of Qt.
- Make generated Lua defensive: protect API calls and report failures.
- Preserve safe, repeatable exports. Only replace or clean up files recorded as studio-owned in the export manifest.
- Add tests for model, compiler, validation, import and runtime-facing changes.

## Extending event types

To add a trigger, condition or action:

1. Add the type and parameter specification to the relevant definitions in `model/enums.py`.
2. Compile it in `export/compiler.py`.
3. Add runtime support to `Studio_Runtime.lua` if needed.
4. Extend the strict mock in `Studio_Mock.lua` for any new ScenEdit API usage.
5. Add validation in `model/validation.py`.
6. Add tests for valid, invalid and boundary-case inputs.

## Testing

Run the repository's documented test commands from the project root. Keep tests independent of a display wherever possible. For changes that affect export, add tests that inspect generated Lua/HTML or exercise the dry-run mock.

Before submitting a contribution:

- Run the relevant automated tests.
- Run formatting/lint checks if configured.
- Manually exercise affected UI flows.
- Validate and dry-run a representative project when the CMO runtime is available.
- Review the generated export for path and manifest safety.

## Pull requests

Keep changes focused and explain the user-visible effect, test coverage and any compatibility considerations. Include screenshots for significant UI changes when useful.

For project-specific conventions and dependency commands, consult the repository README and project configuration.
