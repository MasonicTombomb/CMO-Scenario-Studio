# Scenario Workflow

CMO Scenario Studio separates scenario design from scenario execution. The project is edited in the studio; CMO runs the generated Lua builder to create the playable scenario.

## 1. Set the scenario properties

On the **Scenario** tab, configure:

- Title, setting, location and author.
- Scenario start date/time (Zulu) and duration.
- Weather values.
- Folder name and description-page prefix.
- Build options such as aircraft start armed, console detail and force rebuild.
- Initial key values for state that project scripts will read.

Use a consistent folder name and page prefix once the scenario is established; exported paths and load-document lines depend on them.

## 2. Configure sides

On **Sides**:

- Give each side a clear name, tag and colour.
- Set awareness and proficiency.
- Set doctrine values where you need to override CMO defaults.
- Configure the posture matrix. A row describes that row side's view of the column side.
- Mark sides such as neutral civilian traffic as computer-controlled only when appropriate.
- Set starting scores and optional build variants.

## 3. Build the order of battle

Use the Database dock to find aircraft, ships, submarines, facilities, ground units and other supported entries. Place units on the map, or create an airbase and add aircraft to a host facility.

Set names, counts, heading, speed, altitude/depth, proficiency, EMCON and other available fields in the unit inspector. Group related units where useful. See [Map and Order of Battle](Map-and-Order-of-Battle.md).

## 4. Add operating areas and missions

Create reference points and polygon areas. Missions can use areas belonging to their side or areas marked for all sides. Add a mission, select its area and assign appropriate units. Strike missions can also have targets.

See [Missions and Events](Missions-and-Events.md).

## 5. Add scenario logic

Use events for time-based or condition-based behaviour: messages, score changes, mission activation, flags, reinforcement spawning, Lua actions and other supported actions. Use special actions and project scripts for logic that does not fit a standard event.

Keep event names descriptive and make trigger/condition requirements explicit.

## 6. Write the player-facing pages

The **Briefings** tab contains the scenario description and side briefings. Use the order-of-battle insertion tool to generate a force list from the project, then edit it for clarity and spoilers.

## 7. Validate, dry-run and export

On **Build & Export**:

1. Run validation and resolve errors.
2. Review warnings; some may be intentional, but understand each one.
3. Run the dry-run build where the local CMO Lua 5.4 runtime is available.
4. Export to the intended CMO installation or a staging folder.
5. Follow the generated `README.txt` to run the builder in CMO.
6. Read the build report, save the scenario in CMO and test both sides.

The builder normally refuses to run if sides already contain units, to avoid accidentally building twice. Use **FORCE_REBUILD** only when you deliberately need that behaviour.

## 8. Iterate safely

Keep the `.cmoproj` file as the canonical editable project. Make changes in the studio, export again and test the result. The export manifest tracks studio-written files so repeat exports can replace the files the studio owns while protecting unrelated files.

Related: [Validate and Export](Validate-and-Export.md), [Project and Export Formats](Project-and-Export-Formats.md).
