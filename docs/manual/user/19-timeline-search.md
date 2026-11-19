# The timeline

The **Timeline** tab shows every event and mission against the scenario clock, so you can see what happens when, and
spot timing mistakes.

![The Timeline tab](img/tab_timeline.png)

Across the top are Zulu times with *H+* times (hours after the start) beneath them. The start is a yellow line and
the end a dashed red line. Each row is an event or a mission:

| Shape | Meaning |
| --- | --- |
| Diamond | Happens once at that moment (a date/time, minutes after start, scenario loaded or ended) |
| Bar | A random-time window, or a mission's active period from its start and end times |
| Bar with ticks | A regular-time trigger; the ticks show its interval when you zoom in |
| Dotted line | Happens on a condition (a unit destroyed, an area entered, a score...), so it could be at any time |
| Grey row | An inactive event, or a mission that starts switched off |

Missions switched on or off by a timed event show a diamond where that happens.

Controls along the top:

1. **Filter events and missions...**: type part of a name.
2. **Missions**: show or hide missions.
3. **Condition-only events**: show or hide events that have no fixed time.
4. **Sort by time**: order rows by when they happen instead of as listed.

Hover over a row for details, click it for a full summary on the right, and double-click to open it on the Events or
Missions tab. [[Ctrl]] + mouse wheel zooms; **Fit** shows the whole scenario.

## Timing problems

The panel on the right lists likely mistakes:

- events that fire before the scenario starts or after it ends;
- random windows outside the scenario;
- missions that end before they start;
- events with no triggers (they can never happen);
- two one-off events in the same minute (circled in red), because CMO does not guarantee which runs first.

# Searching everything

Press [[Ctrl+K]] (or **Edit > Search everything...**) to search the whole project.

![Search everything](img/dialog_search.png)

Type into the box (1). Results appear as you type, from:

- units (by name, class, DBID, group or base), sides, missions, events (and their trigger and action types), areas,
  reference points, formations, special actions, variants and scripts;
- **every line of every script**;
- studio commands, such as *Validate project*, *Dry-run build* or *Go to Timeline*;
- the patrol-area library, such as *Patrol area: Bay of Biscay*.

All the words you type must match; name matches come first. Short forms work too: `stgsh` finds *Steregushchiy*.
Use the arrow keys to choose and [[Enter]] to open the result where it is edited (units and areas on the map, script
lines at that line). [[Esc]] closes the search.
