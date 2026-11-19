--[[==========================================================================
  CMO Scenario Studio runtime library.
  Loaded by LuaInit.lua when the scenario loads (the 'Scenario Loaded' event) and
  by every event / special-action script that finds it missing. Everything is
  global so event scripts can call it; names start with 'Studio' so they cannot
  clash with your own functions. A few short aliases (Log, Flag, SetFlag, GetKV,
  SetKV, RunScript) are only defined if you have not defined them yourself.
============================================================================]]

STUDIO = STUDIO or {}
STUDIO.DEBUG = STUDIO.DEBUG or false

-- CMO exposes its API through NLua as userdata with a __call metamethod,
-- so type() reports 'userdata' for ScenEdit_* functions.
function StudioCallable(f)
  local t = type(f)
  return t == 'function' or t == 'userdata' or (t == 'table' and getmetatable(f) ~= nil)
end

function StudioLog(text)
  print('[' .. tostring(STUDIO.TITLE or 'Studio') .. '] ' .. tostring(text))
end

function StudioDebug(text)
  if STUDIO.DEBUG then StudioLog('DEBUG ' .. tostring(text)) end
end

------------------------------------------------------------------ key values
-- Key values are saved inside the .scen, so they survive save/load.
function StudioGetKV(key, default)
  local ok, v = pcall(ScenEdit_GetKeyValue, key)
  if not ok or v == nil or v == '' then return default end
  return v
end

function StudioSetKV(key, value)
  pcall(ScenEdit_SetKeyValue, key, tostring(value == nil and '' or value))
end

function StudioGetNumKV(key, default)
  return tonumber(StudioGetKV(key, nil)) or default
end

function StudioFlag(key)
  return StudioGetKV(key, 'false') == 'true'
end

function StudioSetFlag(key, value)
  StudioSetKV(key, (value == nil or value) and 'true' or 'false')
end

------------------------------------------------------------------ scripts
function StudioRunScript(name)
  local path = tostring(STUDIO.PATH or '/') .. name .. '.lua'
  StudioDebug('running ' .. path)
  local ok, err = pcall(ScenEdit_RunScript, path)
  if not ok then StudioLog('Could not run ' .. path .. ': ' .. tostring(err)) end
  return ok
end

------------------------------------------------------------------ messages and score
function StudioMsg(side, html)
  local ok, err = pcall(ScenEdit_SpecialMessage, side, html)
  if not ok then StudioLog('Message to ' .. tostring(side) .. ' failed: ' .. tostring(err)) end
end

function StudioMsgAll(html)
  for _, name in pairs(STUDIO.SIDES or {}) do StudioMsg(name, html) end
end

function StudioScore(side)
  local ok, v = pcall(ScenEdit_GetScore, side)
  return (ok and tonumber(v)) or 0
end

function StudioAddScore(side, delta, reason)
  local ok, err = pcall(ScenEdit_SetScore, side, StudioScore(side) + delta, reason or 'Scenario event')
  if not ok then StudioLog('Score change for ' .. tostring(side) .. ' failed: ' .. tostring(err)) end
end

------------------------------------------------------------------ units and missions
-- sel: a GUID string, or {side=, name=} / {guid=}
function StudioGetUnit(sel)
  if type(sel) == 'string' then sel = { guid = sel } end
  local ok, u = pcall(ScenEdit_GetUnit, sel)
  if ok then return u end
  return nil
end

function StudioUnitAlive(sel)
  local u = StudioGetUnit(sel)
  if u == nil then return false end
  local ok, dead = pcall(function() return u.dead end)
  return not (ok and dead)
end

function StudioMissionStatus(side, mission, active)
  local ok, err = pcall(ScenEdit_SetMission, side, mission, { isactive = active and true or false })
  if not ok then StudioLog('Mission "' .. tostring(mission) .. '": ' .. tostring(err)) end
end

function StudioRandomPosition(latMin, latMax, lonMin, lonMax)
  return { latitude = latMin + math.random() * (latMax - latMin),
           longitude = lonMin + math.random() * (lonMax - lonMin) }
end

-- Spawn a reinforcement defined in the Studio project (Unit marked 'reserve').
-- STUDIO.RESERVES[id] = { side=, type=, dbid=, name=, count=, lat=, lon=, alt=, host=, loadout=, ... }
function StudioSpawn(id)
  local r = (STUDIO.RESERVES or {})[id]
  if not r then StudioLog('No reinforcement with id ' .. tostring(id)); return {} end
  if StudioFlag('STUDIO_SPAWNED_' .. id) then return {} end
  StudioSetFlag('STUDIO_SPAWNED_' .. id, true)
  local base = nil
  if r.host then
    local h = StudioGetUnit({ side = r.host_side or r.side, name = r.host })
    if h then base = h.guid else StudioLog('Reinforcement host not found: ' .. r.host) end
  end
  local added = {}
  for i = 1, (r.count or 1) do
    local spec = { side = r.side, type = r.type, dbid = r.dbid,
                   name = ((r.count or 1) > 1) and string.format('%s #%d', r.name, i) or r.name }
    if base and r.type == 'Aircraft' then
      spec.base = base
    else
      spec.latitude, spec.longitude = r.lat, r.lon
      if r.type == 'Aircraft' then spec.altitude = r.alt or 9000 end
    end
    if r.type == 'Aircraft' then spec.loadoutid = r.loadout or 3 end
    if r.heading then spec.heading = r.heading end
    if r.type == 'Submarine' and r.depth then spec.depth = r.depth end
    local ok, u = pcall(ScenEdit_AddUnit, spec)
    if (not ok or not u) and r.type == 'GroundUnit' then
      spec.type = 'Facility'; ok, u = pcall(ScenEdit_AddUnit, spec)
    end
    if ok and u then
      added[#added + 1] = u
      for _, mission in ipairs(r.missions or {}) do pcall(ScenEdit_AssignUnitToMission, u.guid, mission) end
    else
      StudioLog('Could not spawn ' .. spec.name .. ': ' .. tostring(u))
    end
  end
  StudioLog('Spawned ' .. #added .. ' x ' .. r.name)
  return added
end

------------------------------------------------------------------ courses (plotted routes)
-- STUDIO.ROUTES = { { id=, side=, names={...}, wps={ {lat, lon, alt|false, speed|false}, ... }, depart=<unix time>,
--                     finish='stop'|'rtb'|'land'|'repeat', land={ side=, name= } }, ... }
-- StudioRoutesTick() runs once a minute (a generated event). A unit waiting at a base is launched at its departure
-- time; a unit under way is given its course; at the end of the course it carries out the finish order. Each
-- unit's progress is a key value (STUDIO_RT_<id>_<n>: wait / launched / enroute / done), so it survives saving.

local function routeCourse(r, plain)
  local c = {}
  for i, w in ipairs(r.wps) do
    local p = { latitude = w[1], longitude = w[2], TypeOf = 'ManualPlottedCourseWaypoint' }
    if not plain then
      if w[3] then p.desiredAltitude = w[3] end
      if w[4] then p.desiredSpeed = w[4] end
    end
    c[i] = p
  end
  return c
end

local function giveCourse(u, r)
  local ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, course = routeCourse(r, false) })
  if not ok then   -- this CMO build refused per-waypoint altitude/speed: plain waypoints
    ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, course = routeCourse(r, true) })
    if ok then StudioDebug('waypoint altitude/speed not accepted for ' .. tostring(u.name)) end
  end
  if not ok then StudioLog('Could not give ' .. tostring(u.name) .. ' its course: ' .. tostring(err)) end
  return ok
end

-- Is the unit under way (airborne / at sea), rather than parked at a base or docked?
function StudioUnderWay(u)
  if u.condition_v == 'Airborne' then return true end
  if u.isOperating ~= nil then return u.isOperating and true or false end
  return u.type ~= 'Aircraft' or u.base == nil
end

local function courseLength(u)
  local n = 0
  pcall(function() n = #(u.course or {}) end)
  return n
end

local function finishRoute(u, r)
  if r.finish == 'repeat' then
    return giveCourse(u, r) and 'enroute' or 'done'
  end
  if r.finish == 'land' and r.land then
    local b = StudioGetUnit({ side = r.land.side, name = r.land.name })
    if b then
      local ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, base = b.guid })
      if not ok then StudioLog(u.name .. ' could not be assigned to ' .. r.land.name .. ': ' .. tostring(err)) end
    else
      StudioLog('Landing base ' .. r.land.name .. ' not found; ' .. u.name .. ' returns to its own base')
    end
    pcall(ScenEdit_SetUnit, { guid = u.guid, rtb = true })
  elseif r.finish == 'rtb' then
    pcall(ScenEdit_SetUnit, { guid = u.guid, rtb = true })
  end
  StudioDebug(u.name .. ' finished its course (' .. tostring(r.finish) .. ')')
  return 'done'
end

-- atBuild: called by the builder - only give courses to units already under way, launch nothing.
-- Returns the number of courses given.
function StudioRoutesTick(atBuild)
  local now = tonumber(ScenEdit_CurrentTime()) or 0
  local given = 0
  for _, r in ipairs(STUDIO.ROUTES or {}) do
    for n, name in ipairs(r.names or {}) do
      local key = 'STUDIO_RT_' .. r.id .. '_' .. n
      local state = StudioGetKV(key, '')
      if state == '' then state = 'wait' end
      if state ~= 'done' then
        local u = StudioGetUnit({ side = r.side, name = name })   -- nil: destroyed, or a reinforcement not here yet
        if u then
          if state == 'wait' and now >= (r.depart or 0) then
            if StudioUnderWay(u) then
              if giveCourse(u, r) then state = 'enroute'; given = given + 1 end
            elseif not atBuild then
              local ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, launch = true })
              if ok then state = 'launched'; StudioDebug(name .. ' launched')
              else StudioLog('Could not launch ' .. name .. ': ' .. tostring(err)); state = 'done' end
            end
          elseif state == 'launched' and StudioUnderWay(u) then
            if giveCourse(u, r) then state = 'enroute'; given = given + 1 end
          elseif state == 'enroute' and courseLength(u) == 0 then
            state = finishRoute(u, r)
          end
          StudioSetKV(key, state)
        end
      end
    end
  end
  return given
end

------------------------------------------------------------------ short aliases (only if free)
Log       = Log       or StudioLog
Flag      = Flag      or StudioFlag
SetFlag   = SetFlag   or StudioSetFlag
GetKV     = GetKV     or StudioGetKV
SetKV     = SetKV     or StudioSetKV
RunScript = RunScript or StudioRunScript
