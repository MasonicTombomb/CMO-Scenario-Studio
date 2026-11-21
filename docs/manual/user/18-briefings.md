# Briefings

Players read the **scenario description** when they choose a scenario, and their **side briefing** when they start
playing. Good briefings make a scenario: they set the scene, say what the player commands and what counts as winning.

![The Briefings tab](img/tab_briefings.png)

The list on the left holds:

- **Scenario description**: seen by everyone in CMO's scenario list.
- **Briefing: *side***: one per side (untick **Export a briefing page for this side** on the Sides tab for sides
  that do not need one).
- **Variant text: *variant***: extra text added to the description of one variant (Chapter 7).

The middle is the editor; the right shows a live preview in CMO's briefing style.

1. **Prepend automatic header (author, date, location, sides, duration, ratings)**: puts a standard header at the
   top of the description, filled from the Scenario tab.
2. **Insert ▾**: adds a ready-made piece:
    - **Order of battle: this side** / **Order of battle: enemy sides**: a list of the forces, generated from your
     units. (Only give players what their side would know about the enemy.)
    - **Flight schedule: this side**: a table of every unit of the side with a course: callsign, number and type,
      where it departs from and when, the route, times on target, where it recovers to, and its codewords (course
      signals). It is generated from the course plans (Chapter 14), so plan the courses first.
    - **Briefing skeleton (OPORD)**: headings for a military-style briefing: situation, enemy forces, friendly forces,
     mission, execution.
    - **Image (from the scenario folder)**: a picture. Copy the image file into `Scenarios\<Folder>\` yourself.
    - **Table**.

The buttons **H1**, **H2**, **H4** (headings), **P** (paragraph), **B** (bold), **I** (italic) and **• List** wrap the
selected text in the right formatting.

3. **Briefing pack (PDF)...**: a complete military-style operation order for the side, printed to PDF (below).

## The briefing pack: an operation order and intelligence summary

For extra realism, the studio writes each side a briefing pack in the style of a NATO **operation order** (OPORD),
ready to print or hand to players before they start. Select a side on the Briefings tab and click **Briefing pack
(PDF)...**.

![The briefing pack window](img/dialog_briefing_pack.png)

The pack follows the five-paragraph order used by NATO forces:

| Part | What is in it |
| --- | --- |
| Heading | Operation name, issuing headquarters, date-time group (DTG, such as *120400Z MAY 30*), time zone (Zulu), task organisation |
| 1. Situation | Enemy forces, friendly forces and allies, the environment and weather at H-hour |
| 2. Mission | Who does what, where, when and why, in one sentence, built from the side's missions |
| 3. Execution | Commander's intent, concept of operations, a task for each mission, and coordinating instructions: H-hour, times on target, rules of engagement (from the side's weapon control doctrine), emission control |
| 4. Service support | Bases and their aircraft, and flights whose route is longer than their estimated range |
| 5. Command and signal | Command, and the codewords: course signals and the flags your events use |
| Annex A: Intelligence summary (INTSUM) | The enemy order of battle, air defence threats, the most likely and most dangerous enemy courses of action, and intelligence gaps (from the side's awareness) |
| Annex B: Air tasking and movement schedule | The flight schedule, then each flight's leg orders: altitude, speed, emissions, weapons, holds and arrival times |
| Annex C: Meteorology (METOC) | The weather at H-hour and every forecast change, in words (cloud in eighths, sea state) |

Everything is written from the scenario. To make it yours, fill in the boxes on the left; anything you leave blank
stays generated, shown in grey italics as *Generated from the scenario*:

- **Operation**, **Issued by** and **Banner** (the marking at the top and bottom of every page).
- **Orders**: background, mission, commander's intent, concept of operations.
- **Intelligence**: the enemy assessment, the most likely and most dangerous enemy courses of action, and whether
  the intelligence summary gives **exact enemy positions**. Unticked (the default) it gives approximate ones, the
  nearest named area or whole degree, as a real estimate would.
- **Support and signal**: extra rules of engagement, sustainment and command.

The preview on the right updates as you type. Then:

- **Save PDF...** prints this side's pack. **PDFs for every side...** prints one per side into a folder.
- **Use as CMO briefing** replaces the side's in-game briefing with the situation, mission, execution and flight
  schedule, so players see it in CMO too.

Your text is saved in the project, so the pack stays up to date as the scenario changes: print it again after
editing.

!!! note "Every page is marked EXERCISE"
    The banner reads *EXERCISE EXERCISE EXERCISE - UNCLASSIFIED - FICTIONAL SCENARIO* unless you change it. These are
    game documents for a fictional scenario; keep the word EXERCISE in your banner.

!!! tip "Printing"
    The PDF is printed with Microsoft Edge, which every Windows 10 and 11 PC has (or Google Chrome), in the
    background: you will not see a browser window. Without either, the studio prints a plainer version itself.

## Writing in HTML

Briefings are written in simple HTML, the language of web pages. You only need a few tags, and the buttons add them
for you:

| Write | To get |
| --- | --- |
| `<h1>Situation</h1>` | A main heading |
| `<h2>Enemy Forces</h2>` | A sub-heading |
| `<p>Text...</p>` | A paragraph |
| `<b>important</b>` | **important** |
| `<i>HMS Montrose</i>` | *HMS Montrose* |
| `<ul><li>One</li><li>Two</li></ul>` | A bullet list |

## How briefings get into CMO

The studio exports each page as an HTML file in `Scenarios\<Folder>\`. CMO shows a page when the description or
briefing contains a line like:

```text
[LOADDOC]OperationFirstLight_Desc.html[/LOADDOC]
```

You paste these lines into CMO once, when you save the scenario (Chapter 22). The build report and the **3. In CMO**
box on the Build & Export tab give you the exact lines. After that, re-exporting updates the pages without touching
CMO again: the `.scen` file just points at them.
