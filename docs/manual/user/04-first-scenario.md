# Your first scenario, step by step

In this chapter you build a small but complete scenario, **Operation First Light**, and play it in CMO. It takes
about 45 minutes. Do every step in order with the studio open; each step says exactly what to click and what you
should see.

**The story:** it is 2030. A Russian Yasen-M submarine is heading south through the gap between the Faroe Islands
and Shetland. The United Kingdom has a Type 23 frigate on anti-submarine patrol there and Typhoon fighters at RAF
Lossiemouth flying a combat air patrol over Shetland. The UK wins by sinking the submarine.

!!! tip "In a hurry? Use the wizard"
    **File > New scenario from wizard...** ([[Ctrl+Shift+N]]) builds a working scenario in a few clicks: two sides,
    real UK air bases (or a generic base elsewhere) with fighter squadrons on combat air patrol, patrol areas, an
    enemy bomber probe on a plotted course and the usual events. See *The New Scenario wizard* at the end of this
    chapter. This chapter builds everything by hand, so you learn how each part works.

You will use: a new project, the Scenario and Sides tabs, a real-world airbase template, the Database panel,
squadrons, the patrol-area library, missions, events, briefings, validation, the dry-run, export, and the build in
CMO.

## Step 1: Create the project

1. Start the studio.
2. Choose **File > New scenario...** ([[Ctrl+N]]).
3. In **Title**, type `Operation First Light`.
4. In **Database**, pick the newest file starting `DB3K_` (the highest number, for example `DB3K_519.db3`).
5. In **Start with**, keep **Two hostile sides (Blue / Red)**.
6. Click **OK**.

The studio switches to the **Scenario** tab. The window title now reads *Operation First Light*.

7. Save straight away so autosave can protect you: **File > Save** ([[Ctrl+S]]). Choose a folder such as
   *Documents\CMO Projects*, keep the suggested name `Operation First Light.cmoproj` and click **Save**.

## Step 2: Fill in the Scenario tab

On the **Scenario** tab:

1. **Setting**: type `North Atlantic, 2030`. (This is the short line CMO shows in its scenario list.)
2. **Location**: type `Faroe Islands - Shetland gap`.
3. **Author**: type your name.
4. Under **Time (Zulu)**, set **Start** to `12/05/2030 06:00` and **Duration** to `0` days, `6` hours, `0`
   minutes. (Zulu is UTC, the time military planners use.)
5. Under **Weather at start**, set **Sea state** to `3` so the frigate's sonar has realistic conditions. Leave the
   rest.
6. Leave **Files and database** and **Build options** as they are.

## Step 3: Name the sides

1. Click the **Sides** tab.
2. In the list on the left, click **Blue**.
3. Change **Name** to `United Kingdom` and **Tag** to `UK`.
4. Click **Red**. Change **Name** to `Russia` and **Tag** to `RU`.

The posture table at the bottom already shows the two sides as **Hostile** to each other, which is what we want.

## Step 4: Place RAF Lossiemouth

You could build an airbase piece by piece, but the studio comes with real UK bases ready made.

1. Choose **Tools > Place unit template...** ([[Ctrl+T]]).
2. In the search box at the top left, type `lossiemouth`.
3. Click **RAF Lossiemouth** in the list. The middle shows its 51 parts (two runways, 18 hardened shelters,
   hangars, aprons, tower, radar, fuel and munitions) and the right shows the layout.
4. Check **Side** says **United Kingdom**. If not, choose it.
5. Leave **At the real site** ticked: the base will appear exactly where the real one is.
6. Click **Place**.

The map jumps to the north of Scotland and shows the base. Every part is named *Lossiemouth ...*, for example
*Lossiemouth Runway 05/23* and *Lossiemouth HAS 1*.

!!! note "One base, many parts"
    In CMO a real airbase is many separate facilities (runways, shelters, hangars). The studio groups them so you
    can move or rotate the whole base by dragging any part, and CMO keeps them together as one group.

## Step 5: Base four Typhoons at Lossiemouth

1. On the map, scroll the mouse wheel to zoom in on Lossiemouth until you can read the labels.
2. Click the unit labelled **Lossiemouth Hangar (4x Medium)** to select it. The inspector on the right of the map
   shows its details.
3. In the **Database** panel on the far right:
    1. Set **Type** to **Aircraft**.
    2. In the search box, type `typhoon fgr`.
    3. Several *Typhoon FGR.4* entries appear, one for each version CMO knows. Click the one whose **Years** column
      starts latest (for example *2020-*).
4. Click **Add to selected base**.
5. A box asks *How many Typhoon FGR.4 at Lossiemouth Hangar (4x Medium)?* Keep `4` and click **OK**.
6. A second box asks for the squadron name. Type `II(AC) Sqn` and click **OK**.

The inspector now shows the new squadron: four Typhoons that start inside the hangar, already given their first
combat loadout from the database (Chapter 10 shows how to choose another). On the map the hangar shows a small badge with the number of aircraft inside.

## Step 6: Add the frigate

1. Zoom out (mouse wheel) until you can see Shetland and the sea to its west.
2. Above the map, check **New objects on** says **United Kingdom**.
3. In the **Database** panel, set **Type** to **Ship** and search for `type 23 duke`.
4. Click the newest *Type 23 Duke* entry, for example *F 236 Montrose [Type 23 Duke]*.
5. Click **Place on map**, then click in the sea about halfway between Shetland and the Faroe Islands. The ship
   appears.
6. Press [[Esc]] to stop placing (otherwise every click places another frigate).

## Step 7: Add the Russian submarine

1. Change **New objects on** (above the map) to **Russia**.
2. In the **Database** panel, set **Type** to **Submarine** and search for `yasen-m`.
3. Click the newest *Severodvinsk [Yasen-M]* entry.
4. Click **Place on map**, then click in the sea north of the Faroe Islands, well north of your frigate. Press
   [[Esc]].
5. In the inspector, change the submarine's **Name** to `K-573 Novosibirsk` (any name will do).

## Step 8: Add the patrol areas and missions

Missions need an area to patrol. The studio has a library of real-world patrol areas.

1. Choose **Tools > Add patrol area from library...** ([[Ctrl+Shift+A]]).
2. In the search box, type `faroes-shetland`. **Faroes-Shetland Channel** is selected and shown on the little map.
3. Set **Side** to **United Kingdom**.
4. Leave **Create a mission on it** ticked with **Suggested for each area**. The line underneath says it creates
   *Faroes-Shetland Channel ASW Patrol*.
5. Click **Add to scenario**.

Do the same twice more:

- Search `cap shetland`, side **United Kingdom**, click **Add to scenario**. This creates *CAP Shetland CAP*, an
  air patrol for the Typhoons.
- Search `norwegian sea`, choose **Norwegian Sea** under *Europe*, side **Russia**, click **Add to scenario**. This
  gives the submarine somewhere to patrol: *Norwegian Sea ASW Patrol*.

!!! tip "Areas on the map"
    Each area appears on the map in its side's colour, or blue for sea and orange for air if you left the colour
    box ticked. Drag the white squares at its corners to reshape it.

## Step 9: Put the units on their missions

The missions exist but have no units yet.

1. Click the **Missions** tab.
2. Click **Faroes-Shetland Channel ASW Patrol** in the list.
3. Under **Assigned units**, click **Add...**, tick the frigate and click **OK**.
4. Click **CAP Shetland CAP**. Under **Assigned units**, click **Add...**, tick **II(AC) Sqn** and click **OK**.
5. Click **Norwegian Sea ASW Patrol**. Under **Assigned units**, click **Add...**, tick **K-573 Novosibirsk** and
   click **OK**.

## Step 10: Add events

Events make things happen during play. The studio has ready-made ones.

**A welcome message**

1. Click the **Events** tab.
2. Click **New ▾** at the bottom left and choose **Welcome message at start**.
3. In the **Actions** box, click **Show message**. On the right, replace the **Text** with:
   `<P>A Russian submarine is reported heading for the Faroes-Shetland gap. Find it and sink it.</P>`

**Score for sinking the submarine**

1. Click **New ▾ > Score when enemy units are destroyed**. This creates *Russia unit destroyed*: whenever a Russian
   unit is destroyed, the United Kingdom scores.
2. In **Actions**, click **Change score** and change **Change** to `100`.

**Victory**

1. Click **New ▾ > End scenario when a side reaches a score**. This creates *United Kingdom victory*.
2. In **Triggers**, click **Side points reached** and change **PointValue** to `100`.

Now the scenario ends with a message as soon as the UK sinks the submarine.

## Step 11: Write the briefings

1. Click the **Briefings** tab. The left list holds the **Scenario description** and one **Briefing:** page per
   side.
2. Click the **Scenario description**. Replace the example text with a few sentences about the situation, for
   example:
   `<P>May 2030. Tension in the North Atlantic is high. A Russian submarine has slipped out of the Kola Peninsula and
   is heading south.</P>`
3. Click **Briefing: United Kingdom**. Replace the text under *Situation* and *Mission* with what the UK player must do.
   Use **Insert ▾ > Order of battle: this side** to add a list of the UK forces automatically.
4. Click **Briefing: Russia** and do the same for the Russian player.

The preview on the right shows how the page will look in CMO.

## Step 12: Check your work

1. Press [[Ctrl+S]] to save.
2. Look at the **Issues** panel at the bottom. Ideally it says *0 error(s)*. Warnings and notes are advice; errors
   must be fixed. Double-click any issue to jump to the thing it is about.
3. Click the **Build & Export** tab and click **Dry-run build** (or press [[F5]]). After a few seconds the
   **Output** box shows the *BUILD REPORT*. It should end with no failures. If it lists problems, read Chapter 21.

## Step 13: Export to CMO

1. Still on **Build & Export**, under **2. Export**, choose **Install into the CMO folder**.
2. Leave **Back up files that will be replaced** ticked.
3. Click **Export**. The **Output** box lists the files written into your CMO folder:
   `Lua\Operation First Light\` (the build script) and `Scenarios\Operation First Light\` (the briefing pages).
4. Under **3. In CMO**, click **Copy the console command**. This copies the exact command you will paste into CMO.

## Step 14: Build the scenario in CMO

1. Start **Command: Modern Operations**.
2. On the main menu choose **Create New Blank Scenario**.
3. When asked for a database, choose the **same database** as your project (for example `DB3K_519.db3`). The
   editor opens with an empty world.
4. Open the **Editor** menu at the top of the screen and choose **Lua Script Console**.
5. Click in the large box at the top of the console, press [[Ctrl+V]] to paste the command you copied in step 13.
   It looks like this:

        ScenEdit_RunScript('/Operation First Light/Build_Scenario.lua')

6. Click **Run**. After a moment the bottom box prints the *BUILD REPORT*. The map now shows your base, ships,
   submarine and areas.
7. Read the end of the report. It lists the next steps and any warnings, and it gives the exact text to paste for
   the briefings, which look like `[LOADDOC]OperationFirstLight_Desc.html[/LOADDOC]`.
8. Close the Lua console.

## Step 15: Attach the briefings and save

1. **Editor > Scenario Description**: delete any text, paste the `[LOADDOC]...Desc.html[/LOADDOC]` line from the
   report and click **OK**.
2. **Editor > Side Briefing**: pick **United Kingdom**, paste its `[LOADDOC]...Briefing_UK.html[/LOADDOC]` line,
   click **OK**. Repeat for **Russia**.
3. **Editor > Scenario Title**: check the title, and paste the setting line from the report if CMO asks for one.
4. **File > Save As**: browse to your CMO folder, open `Scenarios\Operation First Light\` and save as
   `Operation First Light.scen`.

## Step 16: Play it

1. In CMO's main menu choose **Start New Game** (or **Load Scenario**) and pick *Operation First Light*.
2. Choose to play as **United Kingdom**.
3. The briefing you wrote appears. Start the game and hunt the submarine.

Congratulations: you have designed, built and played your own CMO scenario.

## What next?

- To change something, edit the project in the studio, export again, and build again **in a new blank scenario**
  (steps 13 to 15). Never run the build script twice in the same scenario: it refuses, to avoid doubling
  everything.
- Open the example scenario (Chapter 5) to see a larger scenario with more events, formations, scripts and two
  playable variants.
- Read Chapters 6 to 21 for every option in the studio.

## The New Scenario wizard

**File > New scenario from wizard...** ([[Ctrl+Shift+N]]) asks four pages of questions and builds the scenario.

![The wizard's starter kit page](img/dialog_wizard.png)

1. **The scenario**: title, setting, database, start date and time (Zulu) and how long it lasts.
2. **Sides**: a preset (*United Kingdom v Russia*, *NATO v Russia*, *Blue v Red*) with names you can change, which
   side the player commands (the other is computer-controlled, or neither for two players) and an optional
   Civilian side.
3. **Starter kit**:
    - **Region**: where it happens. In the United Kingdom you choose real air bases (RAF Lossiemouth and RAF
      Coningsby by default); elsewhere a generic main operating base is placed near the patrol areas.
    - **Fighters**: how many at each base. The studio picks the right type for the preset (Typhoon FGR.4 for the
      UK, F-35A for NATO) from your database, in service by the start year, with an air-to-air loadout, and puts
      them in hangars with room.
    - **Patrol areas**: areas from the area library for the region (QRA North and South for the UK); each gets a
      combat air patrol mission with the fighters on it.
    - **Bomber probe**: side B sends a pair of bombers (Tu-95MS for Russia) on a plotted course into the area and
      back, with the signal `BEAR_PROBE` when they reach it.
    - **Standard events**: a welcome message, points for each enemy unit destroyed (both sides) and a 15-minute
      warning.
4. **Ready**: a summary. Click **Finish**.

The map then shows the whole scenario. Check the Issues panel, change anything you like, and carry on as in the
rest of this manual. Without a database (no CMO folder set) the wizard builds everything except the aircraft and
tells you so.
