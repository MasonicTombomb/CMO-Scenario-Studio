# Exporting and building in CMO

This chapter takes you from a finished project to a `.scen` file anyone can play.

## The Build & Export tab

![The Build & Export tab](img/tab_export.png)

1. **1. Check**: a summary of the project and its problems.
2. **Validate** (and **Check Lua syntax** beside it): see Chapter 21.
3. **Dry-run build**: see Chapter 21.
4. **2. Export**: where to write the files.
5. **Install into the CMO folder**: writes straight into your CMO folder. **The usual choice.**
6. **Export to a folder (e.g. a git repository)**: writes the same files into any folder you choose with
   **Browse...**, plus a README. Good for keeping versions or sharing the source.
7. **Export as a .zip**: one zip file to send to someone.
8. **Back up files that will be replaced**: before overwriting, zips the old files into the studio's data folder.
   Leave it ticked.
9. **Export**: writes the files. **Open folder** opens the folder in Windows Explorer.
10. **3. In CMO**: the exact steps to build in CMO, with your scenario's names filled in.
11. **Copy the console command**: copies the line to paste into CMO's Lua console.

**Remove files the studio wrote last time that are no longer generated** tidies up, for example when you delete a
script. The middle shows the list of files that will be written, and the right shows any one of them.

## What gets written

| Folder | Files | What they are |
| --- | --- | --- |
| `Lua\<Folder>\` | `Build_Scenario.lua` | The build script you run once in CMO |
| | `Build_<KEY>.lua` | One per variant |
| | `LuaInit.lua`, `Studio_Runtime.lua` | Helpers your events use during play |
| | Your scripts, `project.cmoproj`, `README.txt` | Your scripts, a copy of the project, and instructions |
| `Scenarios\<Folder>\` | `..._Desc.html`, `..._Briefing_<SIDE>.html`, `briefing_style_dark.css` | The description and briefing pages |
| | (later) `<Name>.scen` | The scenario you save from CMO |

!!! note "Exporting is safe"
    The studio keeps a list of the files it wrote (in `.studio_manifest.json`) and only ever replaces those. Your
    `.scen` files and anything else in the folders are never touched. If the folder already exists but was not made
    by the studio, it warns you and lists the files that would be replaced before doing anything.

## Building in CMO, step by step

You do this the first time, and again whenever you want a new version of the `.scen`.

1. In the studio, **Export** with **Install into the CMO folder**, then click **Copy the console command**.
2. Start **Command: Modern Operations**.
3. Choose **Create New Blank Scenario** and pick **the same database** as your project (shown on the Scenario tab).
4. In the editor, open **Editor > Lua Script Console**.
5. Click in the top box, delete anything in it, and paste the command with [[Ctrl+V]]. It looks like:

        ScenEdit_RunScript('/Operation First Light/Build_Scenario.lua')

6. Click **Run**. The bottom box prints the *BUILD REPORT* and the scenario appears on the map.
7. Read the report:
    - the counts of sides, units, missions and events built;
    - **warnings**: anything CMO refused (for example an aircraft that did not fit in its base). The build carries on
     past them;
    - the next steps, with the exact `[LOADDOC]` lines for your pages.
8. **Editor > Scenario Description**: paste the description line, for example
   `[LOADDOC]OperationFirstLight_Desc.html[/LOADDOC]`, and click **OK**.
9. **Editor > Side Briefing**: for each side, paste its `[LOADDOC]..._Briefing_<SIDE>.html[/LOADDOC]` line.
10. **Editor > Scenario Title**: check the title and setting.
11. **File > Save As**: go to `Scenarios\<Folder>\` in your CMO folder and save as `<Name>.scen`.
12. Close the editor and play the scenario from CMO's main menu.

!!! warning "Always start from a new blank scenario"
    The build script creates everything from nothing. Run it once, in a brand-new blank scenario. If you run it in a
    scenario that already has units, it stops and says so, to save you from building everything twice. (Tick
    **FORCE_REBUILD** on the Scenario tab only if you really mean it.)

## Variants

Each variant is built the same way, in its own new blank scenario, with its own command:

```lua
ScenEdit_RunScript('/Operation First Light/Build_PLAY_UK.lua')
```

Use that variant's description line, and save it with the variant's suffix, for example
`Operation First Light - Play as UK.scen`.

## Changing the scenario later

1. Change the project in the studio and save it.
2. **Export** again. The pages update at once: if you only changed briefings, you are done, because the `.scen`
   loads the pages from the folder.
3. For any other change, build again in a **new blank scenario** (steps 2 to 11 above) and save over the old `.scen`.

## Sharing your scenario

A finished scenario is **two folders** inside the CMO folder:

- `Lua\<Folder>\`: needed during play, because events load their helpers from it;
- `Scenarios\<Folder>\`: the `.scen` file and the briefing pages.

Zip both folders (keeping the `Lua` and `Scenarios` folder names) and share the zip. The other player unzips it into
their CMO folder. They do not need the studio. To let other designers work on it, share the `.cmoproj` project file
too (a copy is also in the `Lua` folder).
