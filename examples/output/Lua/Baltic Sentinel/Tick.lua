-- Tick.lua  (Baltic Sentinel)
-- Runs every minute
-- Tick.lua - runs every minute (event 'Clock Tick').
-- Blue scores a point for every 30 minutes Hogland island stays out of Red hands.
local last = StudioGetNumKV('BS_LAST_HOLD', STUDIO.START)
local now = tonumber(ScenEdit_CurrentTime()) or 0
if now - last >= 1800 then
  StudioSetKV('BS_LAST_HOLD', now)
  if not StudioFlag('BS_HOGLAND_LOST') then
    StudioAddScore('NATO', 1, 'Hogland held')
  end
end
