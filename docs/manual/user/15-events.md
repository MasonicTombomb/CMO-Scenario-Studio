# Events

**Events** make things happen while the scenario is played: a message at the start, points when a ship is sunk,
reinforcements after two hours, the end of the game when a goal is reached. You build them from forms; the studio
writes the Lua script CMO needs.

## How an event works

Every event has four parts. When any **trigger** happens, the studio checks the **conditions** and the
**probability**; if they pass, the **actions** run in order.

| Part | Question it answers | Example |
| --- | --- | --- |
| Triggers | *When* might it happen? Any one trigger is enough. | A Russian ship enters the HOGLAND area |
| Conditions | *Only if...* All conditions must be true. | ...and the island has not already been taken |
| Probability | *How likely?* 100% always; 50% half the time. | 100% |
| Actions | *What happens?* Run one after another. | Set a flag, give Russia 50 points, show a message |

## The Events tab

![The Events tab](img/tab_events.png)

1. **Event list**: every event, with its triggers in grey underneath.
2. **New ▾**: make an event, either **Blank event** or one of the ready-made templates (below). **Duplicate** and
   **Delete** are beside it.
3. **Name**: for you and the timeline; players do not see it unless it is shown in the event log.
4. **Repeatable**: the event can happen again and again. Unticked, it happens once only.
5. **Active**: untick to switch the event off without deleting it.
6. **Probability**: the chance, in percent, that it happens when triggered.
7. **Triggers (any fires the event)**: **Add trigger ▾** adds one; **Remove**, **↑** and **↓** remove and reorder.
8. **Conditions (all must be true)**: **Add condition ▾**.
9. **Actions (run in order)**: **Add action ▾**.
10. **Generated Lua**: the script the studio writes for this event. The **Settings** tab beside it edits whichever
    trigger, condition or action you clicked.

**Shown in event log** makes CMO list the event in its log when it fires.

## Ready-made events (New ▾)

| Template | What it creates |
| --- | --- |
| Welcome message at start | A message to every side one minute after the start |
| Score when enemy units are destroyed | The first side scores 10 points each time a unit of the second side (aircraft, ship, submarine or facility) is destroyed. Repeatable. |
| End scenario when a side reaches a score | When the first side has 500 points: a victory message, then the scenario ends |
| Message + end scenario at a date/time | A warning message five minutes before the scenario's end time |
| Reinforcements arrive after a delay | Two hours after the start, the first reinforcement in the project appears, with a message |
| Message when units enter an area | A message to the first side when the second side's units enter the first area |
| Run a script every minute | Runs a project script once a minute (for your own Lua, Chapter 17) |

Use a template, then click each trigger and action to adjust it in the **Settings** tab.

## Triggers

| Trigger | Happens when | Settings |
| --- | --- | --- |
| Scenario loaded | The scenario is opened (including loading a saved game) | |
| Scenario ended | The scenario finishes | |
| Regular time | Repeatedly, every interval | **Interval**: 1 second to 24 hours |
| At date/time (once) | At a particular moment | **Time** (Zulu) |
| Minutes after start (once) | A number of minutes after the scenario starts | **Minutes** |
| Random time (native) | Once at a random moment between two times | **EarliestTime**, **LatestTime** |
| Unit destroyed | A unit is destroyed | **TargetSide**, **TargetType**, or one **SpecificUnit** |
| Unit damaged | A unit is damaged by at least a percentage | as above, plus **DamagePercent** |
| Unit enters area | A unit enters (or with **ExitArea**, leaves) an area | **TargetSide**, **TargetType** or **SpecificUnit**, **Area** |
| Unit remains in area | A unit stays in an area for a time | as above, plus **Duration** (`d:h:m:s`, e.g. `0:0:30:0` for 30 minutes) |
| Unit detected | A side detects a unit | target settings, **DetectorSide**, **MCL** (how well identified) |
| Side points reached | A side's score passes a value | **Side**, **PointValue**, **ReachDirection** (GreaterThan, Exactly, LessThan) |
| Native trigger | Anything else CMO supports, written as a Lua table (advanced) | **Spec** |

## Conditions

| Condition | True when |
| --- | --- |
| Flag is set / Flag is not set | A named flag (key value) is or is not set, such as `BRIDGE_DOWN` |
| Side score at least / Side score below | A side's score compared with a value |
| Random chance (%) | A dice roll succeeds (like Probability, but per condition) |
| Unit is alive / Unit is destroyed | A particular unit still exists, or has been destroyed |
| Lua expression is true | Any Lua expression, such as `StudioScore('Blue') > 100` (advanced) |
| Native condition | A Lua table passed to CMO (advanced) |

## Actions

| Action | Does | Settings |
| --- | --- | --- |
| Show message | Shows a message box | **Side** (blank for everyone), **Text** (HTML: `<P>...</P>` for paragraphs, `<B>` bold) |
| Change score | Adds or removes points | **Side**, **Change** (negative to subtract), **Reason** |
| End scenario | Ends the game | |
| Activate / deactivate mission | Switches a mission on or off | **Mission**, **Active** |
| Set flag / key value | Stores a value for later conditions and scripts | **Key**, **Value** (e.g. `true`) |
| Run project script | Runs one of your scripts | **Script** |
| Lua code | Runs Lua you type | **Code** |
| Spawn unit | Brings in a reinforcement | **Unit** (must be ticked as a reinforcement) |
| Native action | A Lua table passed to CMO (advanced) | **Spec** |

## Flags: making events depend on each other

A **flag** is a named yes/no value saved in the scenario. Use one to remember that something has happened.

!!! example "Only once, and only if the bridge stands"
    *Event 1, "Bridge destroyed"*: trigger **Unit destroyed** (the bridge); action **Set flag / key value**,
    Key `BRIDGE_DOWN`, Value `true`.

    *Event 2, "Convoy crosses"*: trigger **Unit enters area** (the crossing); condition **Flag is not set**, Key
    `BRIDGE_DOWN`; action **Show message** *"The convoy has crossed the river."*

## Worked examples

!!! example "Reinforcements after two hours"
    1. Create the reinforcement unit(s) and tick **Reinforcement** (Chapter 10).
    2. **New ▾ > Reinforcements arrive after a delay**.
    3. Click **Spawn unit** and choose the unit; add one **Spawn unit** action per reinforcement.
    4. Click **Minutes after start (once)** and set **Minutes** (120 = two hours).
    5. Click **Show message** and write the message.

!!! example "Points for holding an objective"
    Trigger **Unit remains in area**: **TargetSide** your side, **Area** the objective, **Duration** `0:1:0:0` (one
    hour). Action **Change score**: **Side** your side, **Change** `100`, **Reason** `Objective held`.

!!! example "A delayed strike"
    Create a strike mission with **Active** unticked (Chapter 14). Add an event with trigger **At date/time
    (once)** and action **Activate / deactivate mission** with **Active** ticked.

## What the studio does behind the scenes

You do not need this to use events, but it explains what you see in **Generated Lua**:

- Triggers CMO understands natively become real CMO triggers.
- **At date/time (once)** and **Minutes after start (once)** become a once-a-minute CMO trigger plus a time check.
- Conditions, probability and the time checks become lines at the top of the event's script. If any fails, the
  script stops and nothing happens.
- A one-shot event with checks is made repeatable in CMO, and the studio remembers in a flag whether it has really
  happened. This way an event that was triggered but failed its checks can still happen later.
