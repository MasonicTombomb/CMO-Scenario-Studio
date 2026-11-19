# Questions and answers

**Do I need to know Lua or programming?**
No. Everything in this manual works with forms and buttons. Lua is only for special actions and scripts, which are
optional.

**Does the studio change CMO's database or my CMO installation?**
No. It reads the database read-only and only writes to `Lua\<Folder>\` and `Scenarios\<Folder>\` when you export.

**Can I open a scenario I made in CMO's own editor?**
Not directly: a `.scen` file is not a project. If the scenario was made by an *If Russia Wins*-style build script, use
**File > Import order of battle from a Build_Scenario.lua...** to bring in its sides, bases, units, areas and missions.

**Can players use my scenario without the studio?**
Yes. Share the two folders described in Chapter 22. Players only need CMO.

**Can I play the scenario in multiplayer?**
Yes. Every player needs the scenario's `Lua` and `Scenarios` folders.

**Which database should I choose?**
The newest `DB3K_` for 1980 onwards, the newest `CWDB_` for 1946 to 1979. Use the same one when you create the blank
scenario in CMO.

**Can I change the database later?**
Yes, on the Scenario tab. The Issues panel then checks every unit and loadout against the new database.

**How big can a scenario be?**
As big as CMO can handle. Hundreds of units are fine. Very large scenarios take longer to build in CMO.

**Can I keep my project in git or Dropbox?**
Yes. The project is a small text file designed to be compared and backed up.

**What does the studio send over the internet?**
Map pictures are downloaded from the chosen map service, and the update check asks GitHub for the latest version.
Nothing about you or your scenarios is sent anywhere.

**Is it free?**
Yes, free and open source under the MIT License. The UK air base layouts come from OpenStreetMap
(© OpenStreetMap contributors, Open Database License).

**Where can I report a problem or ask for a feature?**
On the project's GitHub page: **github.com/MasonicTombomb/CMO-Scenario-Studio/issues**.
