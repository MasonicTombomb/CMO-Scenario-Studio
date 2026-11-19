# Introduction

## What CMO Scenario Studio is

CMO Scenario Studio is a free Windows program for **designing scenarios for Command: Modern Operations**. You use
it to decide everything about a scenario:

- the **sides** and who is friendly or hostile to whom;
- the **forces**: ships, submarines, aircraft and their bases, ground units, radars, missile sites and buildings,
  each taken from CMO's own database;
- **where** they start, on a map of the real world;
- the **missions** they fly and sail: patrols, strikes, refuelling orbits, ferry flights;
- **events** that happen during play: messages, reinforcements, scoring, victory and defeat;
- the **briefings** each player reads before the scenario starts.

When you are happy, the studio turns your design into files that CMO runs to **build the scenario for you**. You
then save it as an ordinary CMO scenario (`.scen` file) that you or anyone else can play.

## Why not just use CMO's own editor?

You can, and the studio does not replace CMO. The studio is built for scenarios that are big, carefully balanced or
that you will change many times:

| In CMO's editor | In the studio |
| --- | --- |
| Everything is clicked in by hand, in the game. | You design in a dedicated program with search, undo, copy, bulk editing and templates. |
| Changing a base, a squadron or a timing late on means redoing work. | Change anything, then rebuild the whole scenario in seconds. |
| Events need Lua scripting for anything clever. | Events are filled in with forms; the studio writes the Lua for you. |
| Mistakes show up when you play. | The studio checks your scenario continuously and test-runs the build before you start CMO. |
| The scenario is one binary file. | The design is a small text file you can keep, back up and share. |

Many of the most polished official and community scenarios are built exactly this way: a script that builds the
scenario from data, run once in CMO. The studio gives you that method without having to write the script.

## How it works, in one picture

The whole process has four stages. You will repeat stages 1 to 3 many times while you work; stage 4 happens once
per version you release.

| Stage | Where | What happens |
| --- | --- | --- |
| 1. Design | The studio | You build the scenario: sides, units, missions, events, briefings. It is saved as a **project** file ending `.cmoproj`. |
| 2. Check | The studio | The studio checks for problems and can **dry-run** the build: it runs the build script with CMO's own Lua engine, without starting CMO. |
| 3. Export | The studio | The studio writes the **build script** and the briefing pages into your CMO folder. |
| 4. Build | CMO | In CMO you create an empty scenario, run the build script in the Lua console (one line, copied for you), and save the result as a `.scen` file. |

!!! note "The project is the master copy"
    Always make changes in the studio and export again. Do not edit the files the studio writes, and avoid
    fixing things by hand in CMO after the build. If you do, those changes are lost the next time you build.

## What you need

- A Windows 10 or Windows 11 PC (64-bit).
- **Command: Modern Operations** installed (the Steam version or any other). The studio reads the game's unit
  database, so CMO must be on the same PC.
- An internet connection is useful for the map pictures and for updates, but not required. The studio has an
  offline map grid.
- About 300 MB of free disk space.

You do **not** need Python, Lua or any programming knowledge.

## Words you will meet straight away

You will find the full list in Appendix B. These few appear on almost every page:

Scenario
:   A playable situation in CMO: a map area, sides, forces, a start time and a goal.

Project
:   Your design in the studio, saved as a `.cmoproj` file. One project produces one scenario (plus optional
    variants).

Side
:   A team in the scenario, such as *NATO*, *Russia* or *Civilians*. Each side has its own units, missions and
    briefing.

Unit
:   One ship, submarine, aircraft (or squadron), ground unit or facility (building, radar, runway...).

Database / DB3000
:   CMO's encyclopaedia of real-world equipment. Every unit you place is an entry from it, identified by a number
    called the **DBID**.

Build script
:   The file `Build_Scenario.lua` the studio exports. CMO runs it once to create everything in your scenario.

Export
:   Writing the build script and briefing pages from the studio to disk.

Lua
:   The scripting language CMO uses. The studio writes all the Lua for you; you only see it if you want to.
