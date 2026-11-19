# Troubleshooting

Find the problem in the left column.

## Installing and starting

| Problem | What to do |
| --- | --- |
| "Windows protected your PC" when running the installer | Click **More info**, then **Run anyway**. Windows warns about programs that are new or not yet code-signed. |
| The installer asks for administrator permission | Normal: it installs into Program Files. Click **Yes**. |
| "The CMO install folder was not found automatically" | Click **OK** and choose the folder in **Settings** (Chapter 2). |
| The Database panel is empty or lists no databases | **File > Settings...**: the CMO folder must be the one containing `Command.exe` and a `DB` folder. |
| The studio crashed | Restart it. Your autosave copy (`.cmoproj.autosave`) is next to your project. The error details are in `%APPDATA%\CMOScenarioStudio\CMO Scenario Studio\error.log`. |

## The map

| Problem | What to do |
| --- | --- |
| The map is blank or grey | Check your internet connection, or choose another **Map** source. *None (offline grid)* always works. |
| I placed ten units by accident | Each click of the Place tool places one. Press [[Esc]] to stop, and [[Ctrl+Z]] to undo. |
| My unit went to the wrong side | Check **New objects on** before placing. Change the unit's **Side** in the inspector. |
| I cannot move an area | Select it first, then drag its white corner squares. |
| A unit moved and its whole group moved with it | It is part of a formation or grouped site. Untick **Keep members on station** on the Formations tab to move it alone. |

## Saving

| Problem | What to do |
| --- | --- |
| "...cannot be written to" when saving | The project is in a protected folder such as Program Files (for example the example project). Choose another folder, such as Documents. |
| I lost my changes | Open the autosave copy (`<project>.cmoproj.autosave`) next to your project file. |

## Checking and building

| Problem | What to do |
| --- | --- |
| Dry-run says `lua54.dll` not found | The CMO folder in **Settings** is wrong, or CMO is not installed on this PC. |
| The Issues panel shows errors | Double-click each error to jump to it. The text says what is wrong. |
| An aircraft is missing after the build in CMO | Its base had no room, or the runway was too short. Read the warnings in the build report; put the squadron in a bigger hangar or a single-unit airfield. |
| A ship is missing after the build | It was placed on land. Move it into open water. |
| CMO says the side already has units | You ran the build in a scenario that already has units. Start from **Create New Blank Scenario** every time. |
| CMO cannot find `Build_Scenario.lua` | Export with **Install into the CMO folder** first, and check the folder name in the command matches the **Folder name** on the Scenario tab. |
| The briefing in CMO is empty or shows `[LOADDOC]` text | The `[LOADDOC]` line must match the file name exactly, and the page must be in `Scenarios\<Folder>\`. Export again, then copy the line from the build report. |
| A loadout was replaced by *Reserve* | CMO refused the chosen loadout (for example it does not belong to that aircraft). Check the warning, and pick the loadout again with the Loadout Viewer. |

## During play

| Problem | What to do |
| --- | --- |
| An event never happens | Look at its **Generated Lua** and the Timeline's timing problems. Check every condition can be true. Check the event is **Active**. |
| An event happened twice | Untick **Repeatable**, or add a **Flag is not set** condition and a **Set flag** action. |
| A Lua error box appears | Note the event or script name in the message, fix it, and use **Check Lua syntax**. For more detail, type `STUDIO.DEBUG = true` in CMO's Lua console and run, then play on: the console prints what each event does. |
| A reinforcement never arrives | It must be ticked as a **Reinforcement**, and an event must have a **Spawn unit** action for it. |
| A mission does nothing | It needs units assigned, an area with three or more corners (patrols and support) or targets (strikes), and **Active** ticked. |
| Players' units fire on civilians | Make every side **Neutral** towards the civilian side, and the civilians neutral towards everyone (Chapter 7). |
