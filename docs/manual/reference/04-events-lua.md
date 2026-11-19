# Events and the generated Lua

## The model

An event has **triggers** (any one fires it), **conditions** (all must be true), a **probability** and **actions**
(run in order). These map onto CMO's event system like this:

| Studio | CMO |
| --- | --- |
| Triggers CMO supports natively (unit destroyed, enters area, regular time, points...) | Real CMO triggers created with `ScenEdit_SetTrigger` |
| *At date/time (once)*, *Minutes after start (once)* | A one-minute *RegularTime* trigger plus a time check at the top of the event's script |
| Conditions, probability, the time checks | Guards: lines at the top of the event's single Lua action that `return` early |
| Actions (message, score, end, mission, flag, script, Lua, spawn) | Lines of that single Lua action, in order |
| Native trigger / condition / action | The raw Lua table passed straight to `ScenEdit_SetTrigger` / `SetCondition` / `SetAction` |

## Once-only events with guards

CMO marks a one-shot event as used as soon as it fires, even if the event's Lua then returns early because a guard
failed. To keep the meaning "happens once, when everything is true", an event that has guards is created as
**repeatable** in CMO, and the once-only rule moves into Lua: a key value `STUDIO_EVT_<id>` is checked first and set
just before the actions run. So the event only counts as fired when its actions actually run.

Native actions cannot be guarded: they run whenever CMO fires the event.

## A generated event script

```lua
-- Event: Hogland landing
if not STUDIO_LUAINIT_LOADED then ScenEdit_RunScript('/Baltic Sentinel/LuaInit.lua') end
if StudioFlag("STUDIO_EVT_1a2b3c4d") then return end                      -- once-only
if (tonumber(ScenEdit_CurrentTime()) or 0) < 1904529600 then return end   -- date/time trigger
if not (not StudioFlag("BS_HOGLAND_LOST")) then return end                -- condition: flag not set
if math.random(100) > 75 then return end                                  -- probability 75%
StudioSetFlag("STUDIO_EVT_1a2b3c4d", true)
StudioSetKV("BS_HOGLAND_LOST", "true")                                     -- action: set flag
StudioAddScore("Russia", 50, "Russian ships at Hogland")                   -- action: change score
StudioMsgAll("<P>Russian forces have landed on Hogland.</P>")               -- action: message to all
```

The first line makes sure the runtime is loaded (straight after the build, and after loading a saved game), so no
separate *Scenario loaded* event is needed.

## Action reference

| Action | Lua emitted |
| --- | --- |
| Show message | `StudioMsg(side, html)`, or `StudioMsgAll(html)` when the side is blank |
| Change score | `StudioAddScore(side, change, reason)` |
| End scenario | `pcall(ScenEdit_EndScenario)` |
| Activate / deactivate mission | `StudioMissionStatus(side, mission, active)` |
| Set flag / key value | `StudioSetKV(key, value)` |
| Run project script | `StudioRunScript(name)` |
| Lua code | Your code, as typed |
| Spawn unit | `StudioSpawn(id)`: builds the reinforcement once, assigns it to its missions, places aircraft at their host |

## Debugging events in CMO

In CMO's Lua console run `STUDIO.DEBUG = true`. From then on `StudioDebug` messages from the runtime and your
scripts are printed to the console as events fire. Every event's Lua is also visible in CMO's event editor
(**Editor > Event Editor > Actions**).

## Variants

A variant is another build of the same project: `Build_<KEY>.lua` sets `STUDIO_BUILD_VARIANT = '<KEY>'` and runs
`Build_Scenario.lua`, which then marks the variant's extra sides as computer-only, skips their special actions,
appends the variant's description text, and records the variant in the key value `STUDIO_VARIANT` so your scripts
can tell which version is being played.
