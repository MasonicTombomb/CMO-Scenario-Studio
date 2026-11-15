--[[ Build_PLAY_NATO.lua - builds the "Play as NATO" version of Baltic Sentinel.
     Computer-controlled: Russia
     In the Lua console of a NEW BLANK scenario run:
       ScenEdit_RunScript('/Baltic Sentinel/Build_PLAY_NATO.lua')
     then save it as Scenarios\Baltic Sentinel\Baltic Sentinel - Play as NATO.scen ]]

STUDIO_BUILD_VARIANT = "PLAY_NATO"
ScenEdit_RunScript('/Baltic Sentinel/Build_Scenario.lua')
