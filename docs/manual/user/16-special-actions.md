# Special actions

A **special action** is a button players can press during the game in CMO (**Game > Special Actions**). Use them for
choices the player makes: call in an air strike, request a situation report, surrender, launch a decoy.

![The Special actions tab](img/tab_special_actions.png)

1. **Name**: the button's label in CMO.
2. **Side**: which side gets the button.
3. **Description**: shown to the player when they choose the action. Explain what it does and any cost.
4. **Repeatable**: the player can use it more than once. Untick for one-off choices. **Active** controls whether it
   is available from the start.
5. **Check syntax**: checks the Lua code below for mistakes using CMO's own Lua engine.

The large box below holds the **Lua code** that runs when the button is pressed. **Insert snippet ▾** adds common
pieces of code (Chapter 17) so you do not have to write them yourself.

!!! example "A situation report button"
    **Name** `SITREP`, **Side** your side, **Description** `Get a summary of the situation.`, **Repeatable** ticked.
    Code (from **Insert snippet ▾ > Message to a side**, then edited):

        StudioMsg('NATO', '<P>Score: ' .. StudioScore('NATO') .. ' points.</P>')

Special actions of a side that the computer plays in a variant are left out of that variant (there is no player to
press them).
