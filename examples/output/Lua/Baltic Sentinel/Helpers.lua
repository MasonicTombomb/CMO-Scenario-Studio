-- Helpers.lua  (Baltic Sentinel)
-- Shared functions, loaded with LuaInit
-- Helpers.lua - loaded when the scenario loads (shared functions for events).
function BS_Sitrep(side)
  local text = string.format('<P><B>SITREP</B></P><P>NATO score: %d<BR>Russia score: %d</P>',
    StudioScore('NATO'), StudioScore('Russia'))
  StudioMsg(side, text)
end
