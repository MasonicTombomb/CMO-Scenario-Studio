# Contributing

Issues and pull requests are welcome.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
```

There is no CI on ordinary pushes or pull requests, so please run `pytest` before pushing. Set `CMO_DIR` to your CMO folder if it is not in a Steam library, so the database and Lua tests run instead of
being skipped. GUI tests run off-screen (`QT_QPA_PLATFORM=offscreen`).

## Guidelines

- Keep the model, exporter and tools free of Qt imports; they must stay testable without a display.
- Change the project only through `ProjectDocument.modify(...)` in UI code (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- Generated Lua must survive missing or changed API functions: wrap calls in `try(...)`, report failures.
- Never commit CMO data: no `.db3`, `.scen`, database images or descriptions, and no copies of game scripts or CSS.
- Add a test for new behaviour; run `python tools/make_screenshots.py` (off-screen) if the UI changes noticeably.
- Update `CHANGELOG.md`.
