Baltic Sentinel - build instructions
============================================================

1. Copy Lua\Baltic Sentinel\ and Scenarios\Baltic Sentinel\ into your CMO folder
   (the studio's 'Install into CMO' export does this for you).
2. In CMO: Create New Blank Scenario using DB3K_519.db3.
3. Editor > Lua Script Console, run:
     ScenEdit_RunScript('/Baltic Sentinel/Build_Scenario.lua')
4. Editor > Scenario Description:
     [LOADDOC]BalticSentinel_Desc.html[/LOADDOC]
   Editor > Side Briefing, for each side:
     NATO: [LOADDOC]BalticSentinel_Briefing_NATO.html[/LOADDOC]
     Russia: [LOADDOC]BalticSentinel_Briefing_RU.html[/LOADDOC]
5. Save as Scenarios\Baltic Sentinel\Baltic Sentinel.scen

Variants (start each from a new blank scenario):
  ScenEdit_RunScript('/Baltic Sentinel/Build_PLAY_NATO.lua')  -> Baltic Sentinel - Play as NATO.scen  (description [LOADDOC]BalticSentinel_Desc_PLAY_NATO.html[/LOADDOC])
  ScenEdit_RunScript('/Baltic Sentinel/Build_PLAY_RUSSIA.lua')  -> Baltic Sentinel - Play as Russia.scen  (description [LOADDOC]BalticSentinel_Desc_PLAY_RUSSIA.html[/LOADDOC])

Tip: DebugModeIsOn / STUDIO.DEBUG = true in the console prints extra detail from events.
