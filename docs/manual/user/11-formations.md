# Formations

A **formation** keeps a group of units in fixed positions around a **lead** unit (also called the guide): a carrier
with its escorts in a ring, four fighters in a finger-four, tanks in a wedge. In CMO the group moves together and
each member keeps its station as the lead manoeuvres.

## Creating units in formation

This builds brand-new units from the database, already in formation.

1. Choose **Tools > Create units in formation...** ([[Ctrl+Shift+F]]), or click **Create units in formation...** on
   the **Formations** tab.

![Creating units in formation](img/dialog_formation_creator.png)

2. **Composition** (1): for each kind of unit, select its entry in the **Database** panel (it stays open beside the
   window) and click **Add the entry selected in the Database panel**. Set the **Count** in the table. The first unit
   of the first row becomes the lead. For a carrier group: add the carrier first (count 1), then a destroyer (count
   4), then a frigate (count 2).
3. Enter a **Name / group** and check the **Side**.
4. Choose a **Layout** (2), such as *Circular screen*. A short description of it appears below.
5. Set the **Lead position** (or keep the map centre), the **Spacing** (3) between units and the **Orientation** (4),
   the direction the formation faces.
6. Watch the preview, then click **Create**.

## Making a formation from units you already have

Select the units (on the Units tab, or right-click one on the map), then choose **Make formation** (or **Make
formation from this unit...**). The first unit you selected becomes the lead.

## The Formations tab

![The Formations tab](img/tab_formations.png)

1. **Create units in formation...**: as above.
2. **Layout**: the arrangement (the list is below).
3. **Spacing**: the basic distance between units, in nautical miles, kilometres or metres.
4. **Orientation (heading)**: the direction the formation faces.
5. **Layout settings**: extra controls for the chosen layout, such as the number of columns or the radius of a ring.
6. **Members (station order)**: the units in station order. **Up**/**Down** reorder them; **Make lead** swaps the
   lead.
7. **Keep members on station**: when ticked, members follow any change you make, and dragging the lead or any
   member on the map moves the whole formation. Untick it to place members by hand.
8. **Build as a CMO group**: the formation becomes a group in CMO with formation stations, so CMO keeps it together
   during play.

Other settings:

| Setting | Meaning |
| --- | --- |
| Altitude step per aircraft | Stacks aircraft at increasing altitudes, for example a ladder. |
| Mirror left/right | Swaps the left and right sides of the layout. |
| Jitter and seed | Adds a small random offset to every station, so a formation looks less perfect. The same seed always gives the same result. |
| Give every unit the formation heading | Points every member the same way as the formation. |
| Stations: Rotating / Fixed | *Rotating* stations turn with the lead's course (stay "on the left" whatever the heading). *Fixed* stations keep a compass bearing (stay "to the north"). |
| Sprint and drift (ASW escorts) | Escorts alternate fast and slow so their sonar works, as real anti-submarine escorts do. |

## Layouts

| Domain | Layouts |
| --- | --- |
| Naval | Line ahead (column), line abreast, echelon right and left, wedge, inverted wedge, diamond, box, convoy columns, circular screen, carrier group (inner and outer screen), ASW bent-line screen, picket line ahead, amphibious assault lanes, mine-sweeping echelon |
| Air | Finger four, vic (three-ship V), trail, ladder, combat spread, wall, box, wedge, echelon right, bomber stream, tanker cell |
| Ground | Road march column, staggered column, herringbone (halt), line, wedge, vee, echelon right, box, diamond, coil (laager), SAM battery dispersal, random dispersal, defensive perimeter (two rings) |
| Any | Custom stations: type each member's bearing and distance yourself |

The Reference Manual describes every layout and its settings.

!!! note "What cannot be in a formation"
    A unit can only be in one formation. Aircraft and boats that start inside a base cannot be on station, because
    they are not at sea or in the air yet. Reinforcements keep their formation place but are only grouped when they
    arrive.
