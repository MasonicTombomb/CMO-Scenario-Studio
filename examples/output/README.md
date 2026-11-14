# Baltic Sentinel

A scenario for *Command: Modern Operations*, made with CMO Scenario Studio.

**Setting:** Gulf of Finland  
**Start:** 12 May 2030 04:00 Z · **Duration:** 12 Hours
· **Database:** DB3K_519.db3

## Install

Copy both folders into your CMO install folder (for Steam usually
`...\steamapps\common\Command - Modern Operations\`):

```
Lua\Baltic Sentinel\
Scenarios\Baltic Sentinel\
```

## Build the .scen

See `Lua/Baltic Sentinel/README.txt`. In short: create a new blank scenario, open the
Lua Script Console and run

```lua
ScenEdit_RunScript('/Baltic Sentinel/Build_Scenario.lua')
```

then set the description/briefings with the `[LOADDOC]` lines the build report prints, and save.

## Edit

Open `Lua/Baltic Sentinel/project.cmoproj` in CMO Scenario Studio.
