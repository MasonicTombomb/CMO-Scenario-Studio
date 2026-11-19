# Sides and how they see each other

A **side** is a team: everything on it shares one commander, one score and one view of the world. Most scenarios
have two playable sides; many add a computer-controlled side for civilians or neutrals.

![The Sides tab](img/tab_sides.png)

1. **The list of sides**. Click a side to edit it. **Add side**, **Remove**, **Up** and **Down** are below the list.
2. **Name**: the side's name, as players see it.
3. **Awareness**: how much the side knows about other units.
4. **Proficiency**: how well trained the side's crews are.
5. **Computer-controlled only (never playable)**.
6. **Side doctrine**: the side's default rules of engagement.
7. **Postures**: who is friendly, neutral or hostile to whom.
8. **Build variants**: single-player versions of the scenario.

## The side's details

| Field | Meaning |
| --- | --- |
| Name | Shown in CMO, on briefings and in events. You can rename a side at any time; everything that refers to it follows. |
| Tag | A short code used in file names, such as `UK` or `RU` (the briefing file becomes `..._Briefing_UK.html`). |
| Map colour | The colour of the side's units and areas in the studio. It does not affect CMO. |
| Awareness | See the table below. |
| Proficiency | **Novice**, **Cadet**, **Regular**, **Veteran** or **Ace**. Better crews react faster and fight better. Individual units can override it. |
| Computer-controlled only | The side cannot be chosen by a player; the computer always plays it. Use it for civilians, neutrals and "background" forces. |
| Starting score | The side's score at the start. Usually 0. |
| Export a briefing page for this side | Untick for sides that never need a briefing, such as civilians. |

**Awareness**

| Setting | What the side knows |
| --- | --- |
| Blind | Gets no contact picture at all. Meant for civilian and background sides that only need to move around (it also saves computer time). |
| Normal | Only what its own sensors detect. **The realistic choice for players.** |
| AutoSideID | Knows which side every contact belongs to, but not what it is. |
| AutoSideAndUnitID | Knows the side and the exact type of every contact. |
| Omniscient | Sees everything on the map. Useful for testing, unrealistic for play. |

## Side doctrine

Doctrine is the default behaviour of the whole side. Leave a setting at *(default)* to use CMO's own default.

| Setting | Meaning |
| --- | --- |
| WCS air / surface / subsurface / land | **Weapons control status** against each kind of target: **Free** (fire at anything not known to be friendly), **Tight** (fire only at targets identified as hostile), **Hold** (fire only in self-defence). |
| Nuclear release | Whether nuclear weapons may be used. Almost always **no**. |
| Ignore plotted course | Whether units may leave their plotted course to engage. |
| Engage opportunity targets | Whether units on a mission attack targets that are not part of it. |
| Ignore EMCON under attack | Whether units switch on radars when attacked, even if told to stay silent. |
| Fuel state (planned) | When aircraft head home: **Bingo** (just enough fuel to return) or with a reserve (**Joker** percentages). |

## Postures: friends and enemies

The posture table says how each side regards each other side. Read it as **"the row side's view of the column
side"**.

| Code | Posture | Effect |
| --- | --- | --- |
| F | Friendly | Allies. They never fire on each other. |
| N | Neutral | Not involved. Not attacked unless they attack first. |
| U | Unfriendly | Watched closely, but not attacked automatically. |
| H | Hostile | Enemies. Attacked according to the weapons control status. |

Click a cell to change it. Postures do not have to be the same both ways (Russia can see NATO as hostile while NATO
still sees Russia as unfriendly, for example at the start of a crisis). Click **Make symmetric (copy row → column)**
to copy each row to its mirror, so both sides see each other the same way.

!!! warning "Civilians must not be hostile"
    Give a civilian side **Neutral** towards everyone and make everyone **Neutral** towards it, or your players'
    weapons may fire on fishing boats and airliners.

## Variants: single-player versions

A **variant** is another build of the same scenario where one or more sides are played by the computer. The usual
use is to offer *Play as NATO* (Russia is computer-controlled) and *Play as Russia* (NATO is computer-controlled)
from one project.

To add one:

1. Under **Build variants**, click **Add**.
2. **Name**: what the player sees, such as `Play as NATO`.
3. **Key**: a short code with no spaces, such as `PLAY_NATO`. The variant is built by `Build_PLAY_NATO.lua`.
4. **.scen suffix**: added to the saved file name, such as ` - Play as NATO`.
5. Under **Computer-controlled sides**, click **Add...** and choose the side(s) the computer plays in this variant.
6. Optional: on the **Briefings** tab, a **Variant text** page appears for the variant. Text there is added to the
   scenario description of that variant only.

Each variant is built in CMO exactly like the main scenario, but with its own command (Chapter 22). Special actions
belonging to a computer-controlled side are left out of that variant.
