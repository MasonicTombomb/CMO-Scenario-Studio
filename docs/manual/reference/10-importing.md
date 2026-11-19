# Importing builder scenarios

**File > Import order of battle from a Build_Scenario.lua (If Russia Wins style)...** reads the data tables of a
build script written in the *If Russia Wins* style and creates a new project from them.

| Table in the script | Becomes |
| --- | --- |
| `X.CFG` | Title, start time, duration, weather |
| `X.DB` | Database entries used by the other tables |
| `X.LOADOUTS` | Aircraft loadouts |
| `X.BASES` | Bases with their squadrons |
| `X.UNITS` | Units, with EMCON and hold-position flags and groups |
| `X.US_REINFORCE` | Reinforcements |
| `X.ZONES` | Areas |
| `X.MISSIONS` | Missions and their assigned units |

Events and runtime scripts are not imported: they are Lua code, not data. Recreate them on the Events and Scripts
tabs. The import reports what it read and anything it could not match against the open database.
