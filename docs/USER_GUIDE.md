# User guide

The user guide is now two PDF manuals:

- **[User Manual](manuals/CMO-Scenario-Studio-User-Manual.pdf)**: everything you need to build, test and play your
  own scenarios, step by step: installing, a tour of the window, a complete first scenario from nothing to playing
  it in CMO, every tab and dialog with annotated screenshots, troubleshooting, questions and answers, keyboard
  shortcuts and a glossary.
- **[Reference Manual](manuals/CMO-Scenario-Studio-Reference-Manual.pdf)**: file formats, the exported Lua and the
  runtime API, events in depth, formation layouts, the template, area and callsign libraries with full catalogues,
  database access, the command line, and building, signing and releasing.

In the studio they are under **Help > User manual (PDF)** ([F1]) and **Help > Reference manual (PDF)**, and in the
Start menu.

The manuals are written in Markdown in [`docs/manual/`](manual/) (one file per chapter, readable on GitHub) and
built with `python tools/make_manuals.py`.
