# Exploring the example scenario

The studio comes with a complete example, **Baltic Sentinel**, set in the Gulf of Finland in 2030. It uses almost
every feature, so it is the best way to see how a finished scenario fits together.

## Open it

Choose **File > Open example project...**, select **Baltic Sentinel.cmoproj** and click **Open**.

!!! note "The example is read-only"
    The installed example lives in Program Files, which Windows protects. You can change it as much as you like,
    but when you save, the studio asks where to save your own copy (your *Documents* folder is suggested).

## What is in it

| Part | What Baltic Sentinel has | Where to look |
| --- | --- | --- |
| Sides | **NATO**, **Russia** and a computer-controlled **Civilian** side that cannot be played | Sides tab |
| Bases | **Amari AB** (Estonia) and **Rissala AB** (Finland) for NATO, **Levashovo AB** for Russia, each with squadrons | Map tab: click a base |
| Ships | A Russian surface action group of three ships, a Russian submarine, a NATO ship, civilian fishing vessels | Units tab |
| Formation | **Baltic SAG**: the Russian ships sailing in formation | Formations tab |
| Areas | Six areas (`CAP_EST`, `CAP_FIN`, `GOF_PATROL`, `CAP_GOF`, `SAG_AREA`, `HOGLAND`) and a reference point **OBJ Hogland** | Map or Areas tab |
| Missions | Air patrols over Estonia, Finland and the Gulf, naval patrols, and a strike on Hamina | Missions tab |
| Events | A welcome message, scoring for losses on both sides, a landing on Hogland island, Finnish F-35s scrambling, a timed strike release and a time warning | Events tab and Timeline tab |
| Special actions | A **SITREP** button for each side that reports the situation | Special actions tab |
| Scripts | **Helpers** (shared functions) and **Tick** (runs every minute) | Scripts tab |
| Variants | **Play as NATO** and **Play as Russia**, single-player versions where the other side is played by the computer | Sides tab, bottom |

## A guided look round

1. **Map tab**: click **Amari AB**. The inspector lists its **Hosted units**: the squadrons based there. Double-click
   a squadron to select it and see its loadout.
2. **Timeline tab**: every event and mission on the scenario clock. Hover over a diamond to see what happens and
   when.
3. **Events tab**: click **Hogland landing**. It fires when a Russian ship enters the `HOGLAND` area, but only if
   the flag `BS_HOGLAND_LOST` is not already set; it then sets that flag, gives Russia 50 points and shows a
   message. Click the **Generated Lua** tab on the right to see the script the studio writes for it.
4. **Build & Export tab**: click **Dry-run build** to watch the studio test-build the whole scenario.

!!! tip "Learn by copying"
    When you want to do something in your own scenario that Baltic Sentinel already does, find it in the example
    and copy the settings. Events, missions and briefings are all just forms.
