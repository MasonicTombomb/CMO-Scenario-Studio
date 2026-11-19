# Files, command line and running from source

## Where everything lives

| What | Where |
| --- | --- |
| Program, built-in libraries, manuals, examples | `C:\Program Files\CMO Scenario Studio\` (the portable zip: wherever you unzipped it) |
| Built-in libraries inside the program | `_internal\cmo_studio\data\`: `templates.json`, `templates_uk.json`, `areas.json`, `callsigns.json` |
| Your libraries, export backups, `error.log` | `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\` |
| Settings | Registry: `HKEY_CURRENT_USER\Software\CMOScenarioStudio\CMO Scenario Studio` |
| Map tile cache | `%LOCALAPPDATA%\CMOScenarioStudio\CMO Scenario Studio\cache\tiles\` |
| Autosave copies | Next to each project: `<project>.cmoproj.autosave` |
| Exports | `[CMO]\Lua\<Folder>\` and `[CMO]\Scenarios\<Folder>\`, or the folder or zip you choose |

To start completely fresh, close the studio and delete the `%APPDATA%` folder above (your libraries go with it),
the registry key and the cache folder.

## Command line

`CMO-Scenario-Studio.exe` (installed in Program Files) accepts:

| Command | Does |
| --- | --- |
| `CMO-Scenario-Studio.exe` | Start the studio |
| `CMO-Scenario-Studio.exe project.cmoproj` | Start and open a project |
| `CMO-Scenario-Studio.exe project.cmoproj --export <folder>` | Export without opening a window; prints the files written |
| `CMO-Scenario-Studio.exe project.cmoproj --dry-run` | Dry-run the build in CMO's Lua and print the build report |
| `... --cmo <CMO folder>` | Use this CMO folder instead of the saved setting |

`--export` and `--dry-run` can be combined. The exit code is 0 on success, 1 if the build failed or the project has
errors, and 2 for usage problems (for example `lua54.dll` not found). This makes the studio usable in scripts and
continuous-integration jobs, for example to check a scenario repository on every commit.

## Running from source

The studio is a Python 3.10+ (64-bit) program using PyQt6.

```bash
git clone https://github.com/MasonicTombomb/CMO-Scenario-Studio.git
cd CMO-Scenario-Studio
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_studio.py
```

Or install it as a command with `pip install -e .` and run `cmo-studio`. Run the tests with
`pip install -e .[dev]` then `pytest`; without CMO installed, the tests that need its database or Lua engine are
skipped.

## Maintainer tools

| Tool | Makes |
| --- | --- |
| `packaging/build_release.py` | The installer and portable zip (see *Building, signing and releasing*) |
| `tools/make_manuals.py` | These PDF manuals, from `docs/manual/` |
| `tools/make_manual_shots.py` | The annotated screenshots in the manuals |
| `tools/make_screenshots.py` | The screenshots in the README |
| `examples/make_example.py` | The *Baltic Sentinel* example project |
