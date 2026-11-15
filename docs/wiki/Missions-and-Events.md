# Missions and Events

Missions describe what groups of units are tasked to do. Events and special actions provide scenario logic over time.

## Missions

The studio supports patrol, strike, support, ferry, mining, mine-clearing and cargo mission classes.

A typical mission workflow:

1. Open **Missions** and create a mission for the intended side.
2. Choose the mission class and configure its options.
3. Select an area or destination where relevant.
4. Assign units.
5. For strike missions, configure target assignments.
6. Review the generated settings and validate the project.

The mission editor exposes supported `ScenEdit_SetMission` options. Leave fields at their defaults unless the scenario requires an explicit override.

## Event timeline

The **Events** tab presents events and missions against the scenario clock. It supports one-shot moments, random windows, repeating ticks and condition-driven triggers. The timeline flags issues such as events outside the scenario duration, same-minute clashes and missions ending before they start.

Double-click an event to edit it. Start with a template from **New** when one matches the behaviour you need.

## Triggers, conditions and actions

Events are assembled from three parts:

- **Triggers** determine when the event is considered. Examples include time/date, delay, unit destroyed/damaged/detected, area entry and points.
- **Conditions** are additional requirements that must be satisfied.
- **Actions** perform the response, such as displaying a message, changing score, ending the scenario, switching a mission on/off, setting flags, spawning a reinforcement or running Lua.

The exact available types and parameter fields are defined by the studio's event editor. Use its forms rather than guessing Lua parameter names.

## Event design tips

- Give events stable, descriptive names (for example, `E01_ConvoyDetected`).
- Keep each event focused on one logical outcome.
- Check the event's active and repeatable settings.
- Make sure referenced units, areas and missions exist and belong to the intended side.
- Test boundary cases: a unit destroyed before a later trigger, an area entered more than once, or a reinforcement action that could fire repeatedly.
- Review the generated Lua preview for script actions.

## Reinforcement events

Mark a unit as a reinforcement in the Units editor, then use the event's **Spawn unit** action to create it. The runtime helper ensures a project reinforcement is spawned once and returns the created units. Configure the unit's mission assignments in the project.

## Special actions

Special actions are player-invoked scenario actions. Configure the side, name, description, repeatability, active state and associated script. Keep the description clear about what the player action does.

## Timeline checks

The timeline is useful for spotting timing conflicts before a build. It complements, but does not replace, full project validation and in-game testing.

Related: [Scripts and Briefings](Scripts-and-Briefings.md), [Validate and Export](Validate-and-Export.md).
