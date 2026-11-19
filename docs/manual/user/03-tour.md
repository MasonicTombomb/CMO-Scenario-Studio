# A tour of the window

![The main window](img/window_overview.png)

1. **Menu bar**: **File**, **Edit**, **View**, **Tools** and **Help**. Every command in the studio is in one of
   these menus (the full list is in Appendix C).
2. **Tabs**: each tab edits one part of the scenario. You will mostly work left to right: **Scenario**, **Sides**,
   **Map**, **Units**, **Formations**, **Areas**, **Missions**, **Events**, **Timeline**, **Special actions**,
   **Scripts**, **Briefings**, **Build & Export**.
3. **Toolbar** of the current tab. On the **Map** tab it holds the map tools (Chapter 8).
4. **Map**: the world map with your units, areas and reference points.
5. **Inspector**: the details of whatever is selected. Select a unit on the map and its name, side, position and
   behaviour appear here, ready to edit.
6. **Database panel**: CMO's unit database. Search it for any ship, aircraft, ground unit or facility and place it
   on the map (Chapter 9). It stays open on every tab.
7. **Issues panel**: problems the studio has found in your scenario, updated as you work (Chapter 21).
8. **Status bar**: short messages, such as *Saved* or the coordinates under the mouse, and the database in use.

!!! tip "Rearranging the window"
    Drag the borders between panels to resize them. The **Database** and **Issues** panels can be dragged out by
    their title bar to float, or closed with the **x**. Bring a closed panel back from the **View** menu. The
    studio remembers your layout.

## Projects: new, open and save

| To... | Do this |
| --- | --- |
| Start a new scenario | **File > New scenario...** ([[Ctrl+N]]). Give it a title and choose the database. |
| Open a project | **File > Open...** ([[Ctrl+O]]), or double-click a `.cmoproj` file in Windows. |
| Open one you used recently | **File > Open recent** |
| Open the example | **File > Open example project...** |
| Save | **File > Save** ([[Ctrl+S]]) |
| Save under a new name | **File > Save as...** |

![The New scenario window](img/dialog_new_project.png)

1. **Title**: the scenario's name, such as *Operation First Light*. It also names the folders the scenario is
   exported to.
2. **Database**: which CMO database to use. Pick the newest `DB3K_...` for modern scenarios (1980 onwards) or the
   newest `CWDB_...` for the Cold War (1946-1979). Chapter 9 explains the difference.

Under them, **Start with** chooses the starting sides: **Two hostile sides (Blue / Red)** (the usual choice),
**Two sides + neutral civilians** (adds a computer-controlled *Civilian* side for fishing boats, airliners and
other bystanders), or **Empty** (no sides; you add your own on the Sides tab).

The window title shows the project name, and an asterisk (`*`) while there are unsaved changes.

## Undo and redo

Every change can be undone with **Edit > Undo** ([[Ctrl+Z]]) and redone with **Edit > Redo** ([[Ctrl+Y]]). This
includes big operations such as placing a whole airbase or editing fifty units at once: one undo reverts the lot.

## Autosave

While you work, the studio saves a safety copy next to your project every few minutes (five by default; change it
in **File > Settings...**). The copy is called `<your project>.cmoproj.autosave`. If the PC crashes, open the
autosave copy with **File > Open...** (set the file type to *All files*) and save it under a normal name.

Autosave only works once the project has been saved at least once, because it needs to know where to put the copy.

## Selecting things

Clicking a unit, area or reference point anywhere (on the map, in a table on the **Units** tab, in a list on the
**Areas** tab, or in a search result) selects it everywhere: the map highlights it and the inspector shows it. This
makes it easy to find something in a table and then see where it is, or the other way round.

## Getting help inside the studio

- Hover the mouse over a box or button for a few seconds: most show a short explanation.
- **Help > User manual (PDF)** opens this manual. **Help > Reference manual (PDF)** opens the reference.
- **Help > About** shows the version you are running.
