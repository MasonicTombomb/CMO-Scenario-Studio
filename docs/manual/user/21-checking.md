# Checking your scenario

The studio checks your work in three ways, from quick to thorough.

## 1. The Issues panel (always on)

The **Issues** panel at the bottom of the window re-checks the project after every change. Each line has a
**Level**, the **Area** of the project it is about, and the **Problem**.

| Level | Meaning |
| --- | --- |
| Error | Will break the build or the scenario. Fix it before exporting. |
| Warning | Probably a mistake, but the build will run. |
| Note | Advice. Safe to ignore if you meant it. |

**Double-click** an issue to jump to the thing it is about. The box at the top right chooses which levels to show,
and **Re-check** runs the checks again.

Things it checks include:

- units whose database entry does not exist in the chosen database;
- equipment that is deprecated or not in service in the scenario year;
- loadouts that do not belong to the aircraft;
- units assigned to another side's mission;
- patrol areas with fewer than three corners, and missions without the area or targets they need;
- events without triggers, and **Spawn unit** actions on units that are not reinforcements;
- duplicate names, and many more.

## 2. Validate (F7)

**Tools > Validate project** ([[F7]]), or **Validate** on the Build & Export tab, runs the same checks against the
database that is open and shows a summary. **Check Lua syntax** checks every script, event and special action for
Lua mistakes using CMO's own Lua engine.

## 3. The dry-run build (F5)

The dry-run is the best test short of building in CMO. It exports the scenario to a temporary folder and runs the
real build script in CMO's own Lua engine (`lua54.dll` from your CMO folder), against a strict stand-in for CMO's
scenario editor. Then it runs every event and special-action script once to catch mistakes that would only show
during play.

Run it with **Tools > Dry-run build** ([[F5]]) or **Dry-run build** on the Build & Export tab. **Version** beside the
button chooses the standard build or one of your variants.

![A dry-run build report](img/tab_export_dryrun.png)

The **Output** box shows the *BUILD REPORT*, exactly as CMO's console will show it, followed by lines starting
`MOCK:` with counts of what was built. The last line is what matters:

- `RESULT: OK - the build ran cleanly against the mock API.` Everything worked.
- Otherwise, the report lists each failure and warning with the unit, mission or event it is about. Fix them in the
  studio and run the dry-run again.

!!! note "The dry-run is very good, not perfect"
    The stand-in cannot know everything CMO checks, for example whether a runway is long enough for an aircraft or
    whether a base has room for every aircraft. The build report in CMO itself is the final word. Every step of the
    real build is protected, so a problem there becomes a warning in the report instead of stopping the build.
