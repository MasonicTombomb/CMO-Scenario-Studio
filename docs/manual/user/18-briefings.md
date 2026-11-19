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
    - **Briefing skeleton (OPORD)**: headings for a military-style briefing: situation, enemy forces, friendly forces,
     mission, execution.
    - **Image (from the scenario folder)**: a picture. Copy the image file into `Scenarios\<Folder>\` yourself.
    - **Table**.

The buttons **H1**, **H2**, **H4** (headings), **P** (paragraph), **B** (bold), **I** (italic) and **• List** wrap the
selected text in the right formatting.

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
