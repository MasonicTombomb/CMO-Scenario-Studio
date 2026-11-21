# The Scenario tab

The **Scenario** tab holds the facts about the scenario as a whole: its name, when it happens, the weather and
how it is built.

![The Scenario tab](img/tab_scenario.png)

1. **Title**: the scenario's name, shown in CMO and on every briefing page.
2. **Setting**: one short line describing where and when, such as *Gulf of Finland, May 2030*. CMO shows it
   under the title in its scenario list.
3. **Author**, **Location**, **Inspired by**, **Rating** and **Note**: details for the description page (see
   below).
4. **Files and database**: folder names and the database (see below).
5. **Time (Zulu)**: when the scenario starts and how long it lasts.
6. **Weather**: the weather at the start, and **Weather Forecast...** for timed changes later (see *Weather forecast* below).
7. **Build options**: how the build script behaves.
8. **Initial key values**: values your scripts can read (advanced).
9. **Designer notes**: notes to yourself. They are saved in the project but never exported.

## Description details

| Field | What to write | Example |
| --- | --- | --- |
| Title | The name of the scenario | *Operation First Light* |
| Setting | Place and date, short | *North Atlantic, 2030* |
| Location | Where the action is | *Faroe Islands - Shetland gap* |
| Author | Your name or handle | *T. Scott* |
| Inspired by | Optional: a book, film or real event. HTML such as `<I>Red Storm Rising</I>` is allowed for italics. | |
| Rating: Complexity / Difficulty | 1 to 5 each. Shown on the description page so players know what to expect. | 3 / 2 |
| Note | A one-line note for the top of the description | *This is a hypothetical scenario.* |

If **Prepend automatic header** is ticked on the Briefings tab (Chapter 18), these details are written at the top of
the scenario description for you.

## Files and database

**Folder name** is the name of the folders the scenario is exported to: `Lua\<Folder name>\` and
`Scenarios\<Folder name>\` inside your CMO folder. It starts as the title. Change it if the title has characters
Windows does not allow in folder names (such as `:` or `?`), or if you want a shorter folder.

**Page prefix** is put in front of the briefing file names, for example `OperationFirstLight_Desc.html`. It starts as
the title without spaces.

**Database** is the CMO database file the scenario uses, such as `DB3K_519.db3`.

!!! warning "Use the same database in CMO"
    When you create the blank scenario in CMO (Chapter 22), you must choose the same database as here. The unit
    numbers (DBIDs) in your scenario belong to this database.

## Time (Zulu)

- **Start**: the date and time the scenario starts, in Zulu time (UTC, the same as GMT). Type it or use the arrows.
  Remember local time differs: 06:00 Zulu is 07:00 in London in summer and 09:00 in Moscow.
- **Duration**: days, hours and minutes. When the clock runs out, CMO ends the scenario.

## Weather at start

| Setting | Range | Meaning |
| --- | --- | --- |
| Temperature | °C | Air temperature. Affects icing and some sensors. |
| Rainfall | 0 to 50 | 0 is dry, 50 is torrential rain. Rain hides targets from radar and cameras. |
| Cloud | 0 to 1 | 0 is clear sky, 1 is total overcast. Cloud blocks visual and infrared sensors. |
| Sea state | 0 to 9 | 0 is flat calm, 9 is hurricane seas. High seas make submarines harder to find and hurt small boats. |

## Weather forecast

The initial weather (above) sets conditions at T+0. Click **Weather Forecast...** to schedule
further changes during the scenario.

Each row in the forecast table gives:

| Column | Range | Meaning |
| --- | --- | --- |
| Offset (min) | 1 or more | Minutes after the scenario start when this change fires. |
| Temp (°C) | −60 to 60 | New air temperature. |
| Rain (0–50) | 0 to 50 | New rainfall intensity. |
| Cloud (0–1) | 0 to 1 | New cloud cover (0 = clear, 1 = overcast). |
| Sea (0–9) | 0 to 9 | New sea state (0 = calm, 9 = phenomenal). |

Click **Add Change** to append a new row (it copies the previous row's values and adds 60 minutes
to the offset). Select a row and click **Remove Selected** to delete it. Entries are sorted by
offset when you click **OK**.

The build generates a hidden, one-shot CMO event for each row; each event checks the scenario
clock every minute and calls `ScenEdit_SetWeather` as soon as the offset time is reached.

The changes appear on the **Timeline** (Chapter 19) as the *Weather forecast* row, and the map's **Clock** shows the
weather at any moment (Chapter 8). The Issues panel warns about changes after the scenario ends and two changes at
the same time.

!!! tip
    Use the forecast to model deteriorating conditions, a storm blowing through, or clearing
    weather after a rain squall.

## Build options

**Aircraft start armed with their chosen loadout (otherwise in reserve)**
:   Ticked: every aircraft starts carrying the loadout you chose for it. Unticked: every aircraft starts in reserve
    (unarmed) and the player must arm them, which takes time.

**Reserve loadout id**
:   The loadout used for unarmed aircraft. Leave it at `3`, which is CMO's universal *Reserve* loadout.

**Console detail (0-2)**
:   How much the build script prints in CMO's Lua console: 0 is just the summary, 2 is every unit. Use 2 if you
    are hunting a build problem.

**Build even if the sides already have units (FORCE_REBUILD)**
:   Normally the build script refuses to run in a scenario that already has units, so you cannot build everything
    twice by accident. Tick this only if you really want to build into a scenario that already has units.

## Initial key values

Key values are named pieces of data that CMO saves inside the scenario, such as `BRIDGE_DESTROYED = false`.
Events and scripts can read and change them (Chapter 15). Add a row with **Key** and **Value** to have it set when the
scenario is built. You only need this if you write your own conditions or scripts.
