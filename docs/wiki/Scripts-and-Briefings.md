# Scripts and Briefings

Use scripts and briefings to add custom behaviour and explain the scenario to players.

## Project Lua scripts

The **Scripts** tab provides a Lua editor with syntax highlighting, snippets and syntax checking against CMO's Lua 5.4 runtime when available.

Scripts are exported into the scenario's Lua folder. They can be called from event actions, special actions or other project scripts using the runtime helper.

Keep scripts small and focused. Use descriptive filenames and comments for assumptions, expected inputs and side effects. Validate script syntax and test behaviour in CMO; a syntax check cannot prove that a script behaves correctly in a live scenario.

## Runtime helpers

The exported `Studio_Runtime.lua` library provides helper functions for common tasks:

| Function | Purpose |
| --- | --- |
| `StudioLog(text)` / `StudioDebug(text)` | Write to the Lua console |
| `StudioGetKV(key, default)` / `StudioSetKV(key, value)` | Read and write scenario key values |
| `StudioGetNumKV(key, default)` | Read a numeric key value |
| `StudioFlag(key)` / `StudioSetFlag(key, bool)` | Read and write boolean flags |
| `StudioRunScript(name)` | Run a project script |
| `StudioMsg(side, html)` / `StudioMsgAll(html)` | Show a message to one side or all sides |
| `StudioScore(side)` / `StudioAddScore(side, delta, reason)` | Read or change side score |
| `StudioGetUnit(sel)` / `StudioUnitAlive(sel)` | Find a unit and check whether it is alive |
| `StudioMissionStatus(side, mission, active)` | Activate or deactivate a mission |
| `StudioRandomPosition(latMin, latMax, lonMin, lonMax)` | Generate a random point in a bounding box |
| `StudioSpawn(id)` | Spawn a project reinforcement once |

The runtime is loaded by `LuaInit.lua`. Generated event and special-action scripts check whether it has been loaded and run the initializer if necessary.

Consult [Export Format and Lua Runtime](../EXPORT_FORMAT.md) for the full runtime API and builder details.

## Scenario description and briefings

The **Briefings** tab edits the HTML scenario description and per-side briefings. Use the live preview to review formatting. **Insert > Order of battle** can generate a force list from the project.

Good briefings should establish the situation, mission, time constraints, rules of engagement and victory conditions without revealing information a player should not know. Keep side-specific information in the appropriate briefing.

## Build variants

Build variants support alternate playable perspectives, such as **Play as X** versions. A variant can specify which sides are computer-controlled and can have its own launcher and description page.

Review each variant's side control and briefing text independently. Do not assume that a variant's description is identical to the base scenario.

## Practical checks

- Use the same spelling and case for script filenames and references.
- Keep runtime scripts inside the exported scenario Lua folder.
- Avoid relying on local files that will not exist on another player's machine.
- Test scripts after loading the exported scenario in CMO.
- Preview the description and every side briefing before distribution.
