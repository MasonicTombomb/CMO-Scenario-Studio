# Scripts

**Scripts** are your own Lua files, for anything events and special actions cannot do with forms. You never need
them for an ordinary scenario. If you are curious, this chapter gets you started; the Reference Manual lists every
helper function.

![The Scripts tab](img/tab_scripts.png)

1. **Script list**. **New**, **Rename** and **Delete** are below it.
2. **Load on init (run from LuaInit.lua)**: runs the script every time the scenario loads. Use it for shared
   functions that other scripts and events call.
3. **Insert snippet ▾**: ready-made code.
4. **Check syntax**: checks the script for mistakes with CMO's own Lua engine.

Each script is exported as `Lua\<Folder>\<name>.lua`. Run one from an event with the **Run project script** action.

## Snippets

| Snippet | Does |
| --- | --- |
| Message to a side | Shows a message box to one side |
| Change score | Adds points to a side |
| Flag (once only) | Runs code only the first time |
| Find a unit | Gets a unit by name |
| Loop over a side's units | Does something to every unit of a side |
| Add a unit | Creates a new unit with CMO's scripting |
| Spawn a reinforcement | Brings in a project reinforcement |
| Activate a mission | Switches a mission on |
| Random position | Picks a random point in a box |
| Elapsed minutes | Minutes since the scenario started |
| End scenario | Ends the game |

## A first script

!!! example "Bonus points every hour while a ship survives"
    1. On the Scripts tab click **New**, name it `Hourly`.
    2. Type:

            if StudioUnitAlive({side = 'NATO', name = 'HMS Montrose'}) then
              StudioAddScore('NATO', 5, 'Montrose still afloat')
            end

    3. Click **Check syntax**.
    4. On the Events tab, add an event with trigger **Regular time**, **Interval** *1 hour*, and action **Run
       project script**, **Script** `Hourly`.

The `Studio...` functions come with the studio and are always available in events, special actions and scripts.
You can also use every `ScenEdit_...` function from CMO's own Lua documentation.
