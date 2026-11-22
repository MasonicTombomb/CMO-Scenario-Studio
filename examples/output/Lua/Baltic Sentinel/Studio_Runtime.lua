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
  for _, ic in ipairs(STUDIO.INTERCEPTS or {}) do      -- an intercept: arm or disarm it (it runs its own mission)
    if ic.mission == mission and ic.side == side then
      StudioSetKV('STUDIO_IC_' .. ic.id .. '_OFF', active and '0' or '1')
      return
    end
  end
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
-- STUDIO.ROUTES = { { id=, side=, kind=, names={...}, depart=<unix time>, finish='stop'|'rtb'|'land'|'repeat',
--                     land={ side=, name= }, wps={ { lat=, lon=, alt=, spd=, dep=, name=, radar=, sonar=, ecm=, wcs=,
--                     engage=, wait=, flag= }, ... } }, ... }      (only lat and lon are always there)
-- StudioRoutesTick() runs once a minute (a generated event). A unit waiting at a base is launched at its departure
-- time; a unit under way is given its course. The settings of waypoint i (altitude, speed, sensors, weapons) are
-- applied when the leg to it starts; on arrival it sets the waypoint's flag and, with a wait, circles there first.
-- At the end of the course it carries out the finish order. Progress is kept in key values, so it survives saving:
--   STUDIO_RT_<id>_<n>        wait / launched / enroute / loiter / done
--   STUDIO_RT_<id>_<n>_leg    the waypoint it is heading for (or circling at)
--   STUDIO_RT_<id>_<n>_until  when a wait ends (Unix time)

local function routeCourse(wps, from, plain)
  local c = {}
  for i = from or 1, #wps do
    local w = wps[i]
    local p = { latitude = w.lat, longitude = w.lon, TypeOf = 'ManualPlottedCourseWaypoint' }
    if not plain then
      if w.alt then p.desiredAltitude = w.alt end
      if w.spd then p.desiredSpeed = w.spd end
      if w.name then p.name = w.name end
    end
    c[#c + 1] = p
  end
  return c
end

local function giveWaypoints(u, wps, from)
  local ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, course = routeCourse(wps, from, false) })
  if not ok then   -- this CMO build refused per-waypoint altitude/speed/name: plain waypoints
    ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, course = routeCourse(wps, from, true) })
    if ok then StudioDebug('waypoint altitude/speed not accepted for ' .. tostring(u.name)) end
  end
  if not ok then StudioLog('Could not give ' .. tostring(u.name) .. ' its course: ' .. tostring(err)) end
  return ok
end

-- four points round a waypoint, for waiting there (aircraft circle wider than ships). Ground units do not
-- circle: an empty course and they stop where they are.
local function orbitAround(w, kind)
  if kind == 'GroundUnit' then return {} end
  local nm = (kind == 'Aircraft') and 5 or 0.5
  local dlat = nm / 60
  local dlon = dlat / math.max(0.1, math.cos(math.rad(w.lat)))
  local function pt(a, b) return { lat = w.lat + a, lon = w.lon + b, alt = w.alt, spd = w.spd } end
  return { pt(dlat, 0), pt(0, dlon), pt(-dlat, 0), pt(0, -dlon) }
end

local EMCON = { active = 'Active', passive = 'Passive' }
local WCS = { free = 0, tight = 1, hold = 2 }

local function try(what, f, ...)
  local ok, err = pcall(f, ...)
  if not ok then StudioLog(what .. ': ' .. tostring(err)) end
  return ok
end

-- the settings for the leg to waypoint w
local function applyLeg(u, r, w)
  if not w then return end
  if w.alt then try(u.name .. ' altitude', ScenEdit_SetUnit, { guid = u.guid, manualAltitude = w.alt }) end
  if w.spd then try(u.name .. ' speed', ScenEdit_SetUnit, { guid = u.guid, manualSpeed = w.spd }) end
  if w.dep and r.kind == 'Submarine' then
    -- depth as on ScenEdit_AddUnit; older builds take it as a negative manual altitude instead
    if not pcall(ScenEdit_SetUnit, { guid = u.guid, depth = w.dep }) then
      try(u.name .. ' depth', ScenEdit_SetUnit, { guid = u.guid, manualAltitude = -w.dep })
    end
  end
  local em = {}
  if w.radar then em[#em + 1] = 'Radar=' .. EMCON[w.radar] end
  if w.sonar then em[#em + 1] = 'Sonar=' .. EMCON[w.sonar] end
  if w.ecm then em[#em + 1] = 'OECM=' .. EMCON[w.ecm] end
  if #em > 0 then try(u.name .. ' EMCON', ScenEdit_SetEMCON, 'Unit', u.guid, table.concat(em, ';')) end
  local d = {}
  if w.wcs then
    local v = WCS[w.wcs]
    d.weapon_control_status_air, d.weapon_control_status_surface = v, v
    d.weapon_control_status_subsurface, d.weapon_control_status_land = v, v
  end
  if w.engage then d.ignore_plotted_course = (w.engage == 'leave') and 'yes' or 'no' end
  if next(d) then try(u.name .. ' doctrine', ScenEdit_SetDoctrine, { side = r.side, unitname = u.name }, d) end
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

-- give the course from waypoint i on, and start the leg to it
local function sendOn(u, r, key, i)
  if not giveWaypoints(u, r.wps, i) then return false end
  StudioSetKV(key .. '_leg', i)
  applyLeg(u, r, r.wps[i])
  return true
end

local function finishRoute(u, r, key)
  if r.finish == 'repeat' then
    return sendOn(u, r, key, 1) and 'enroute' or 'done'
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

-- arrived at waypoint j: raise its flag; with a wait, circle there. Returns true when it now waits.
local function arrived(u, r, key, j, now)
  local w = r.wps[j]
  if w.flag then StudioSetFlag(w.flag, true); StudioDebug(u.name .. ' at waypoint ' .. j .. ': ' .. w.flag) end
  if (w.wait or 0) > 0 then
    StudioSetKV(key .. '_leg', j)
    StudioSetKV(key .. '_until', now + 60 * w.wait)
    giveWaypoints(u, orbitAround(w, r.kind), 1)
    return true
  end
  return false
end

-- a unit following its course: which waypoints has it passed since the last tick?
local function follow(u, r, key, now)
  local n = #r.wps
  local leg = StudioGetNumKV(key .. '_leg', 1)
  local cur = n - courseLength(u) + 1          -- the waypoint it is heading for (n + 1: all passed)
  if cur <= leg then return 'enroute' end
  for j = leg, math.min(cur - 1, n) do
    if arrived(u, r, key, j, now) then return 'loiter' end
  end
  if cur <= n then
    StudioSetKV(key .. '_leg', cur)
    applyLeg(u, r, r.wps[cur])
    return 'enroute'
  end
  return finishRoute(u, r, key)
end

local function loiter(u, r, key, now)
  local j = StudioGetNumKV(key .. '_leg', 1)
  if now >= StudioGetNumKV(key .. '_until', 0) then
    if j < #r.wps then return sendOn(u, r, key, j + 1) and 'enroute' or 'done' end
    return finishRoute(u, r, key)
  end
  if r.kind ~= 'GroundUnit' and courseLength(u) == 0 then giveWaypoints(u, orbitAround(r.wps[j], r.kind), 1) end
  return 'loiter'
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
              if sendOn(u, r, key, 1) then state = 'enroute'; given = given + 1 end
            elseif not atBuild then
              local ok, err = pcall(ScenEdit_SetUnit, { guid = u.guid, launch = true })
              if ok then state = 'launched'; StudioDebug(name .. ' launched')
              else StudioLog('Could not launch ' .. name .. ': ' .. tostring(err)); state = 'done' end
            end
          elseif state == 'launched' and StudioUnderWay(u) then
            if sendOn(u, r, key, 1) then state = 'enroute'; given = given + 1 end
          elseif state == 'enroute' then
            state = follow(u, r, key, now)
          elseif state == 'loiter' then
            state = loiter(u, r, key, now)
          end
          StudioSetKV(key, state)
        end
      end
    end
  end
  return given
end

------------------------------------------------------------------ intercepts (aircraft on call)
-- STUDIO.INTERCEPTS = { { id=, side=, mission=, names={...}, home={lat,lon}, armed=, logic='all'|'any', c={...conditions},
--                         area={{lat,lon},...}, missiles=, raid=, from=, to=, flag=, per=, max=, reserve=, down=<seconds>,
--                         message=, signal= }, ... }
-- StudioInterceptTick() runs every half minute (a generated event). The mission is a native Air Intercept mission that
-- is kept switched off. When a contact meets the conditions it becomes a target, aircraft are assigned and the mission
-- is switched on; when no target is left the aircraft are sent home and it is switched off again. It is never left on
-- without a target: CMO would then launch at anything it detects.
--   STUDIO_IC_<id>_T     contacts being intercepted: '<contact>=<target id>=<time last matched> ...'
--   STUDIO_IC_<id>_U     aircraft scrambled: '<guid> ...'
--   STUDIO_IC_<id>_SEEN  when each contact was first held: '<contact>=<time> ...'
--   STUDIO_IC_<id>_OFF   '1' when an event has switched the intercept off

local function nm(lat1, lon1, lat2, lon2)
  local p1, p2 = math.rad(lat1), math.rad(lat2)
  local a = math.sin((p2 - p1) / 2) ^ 2 + math.cos(p1) * math.cos(p2) * math.sin(math.rad(lon2 - lon1) / 2) ^ 2
  return 2 * 3440.065 * math.asin(math.min(1, math.sqrt(a)))
end

local function bearingTo(lat1, lon1, lat2, lon2)
  local p1, p2, d = math.rad(lat1), math.rad(lat2), math.rad(lon2 - lon1)
  return math.deg(math.atan(math.sin(d) * math.cos(p2),
                            math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(d))) % 360
end

local function insideArea(lat, lon, pts)
  local inside, j = false, #pts
  for i = 1, #pts do
    local yi, xi, yj, xj = pts[i][1], pts[i][2], pts[j][1], pts[j][2]
    if (yi > lat) ~= (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi then inside = not inside end
    j = i
  end
  return inside
end

local function words(s)
  local t = {}
  for w in string.gmatch(s or '', '%S+') do t[#t + 1] = w end
  return t
end

-- a contact property, or nil if this build does not have it
local function prop(c, k)
  local ok, v = pcall(function() return c[k] end)
  if ok then return v end
end

local function contactsOf(side)
  local ok, list = pcall(ScenEdit_GetContacts, side)
  if not ok or type(list) ~= 'table' then
    ok, list = pcall(function() return VP_GetSide({ side = side }).contacts end)
    if not ok or not list then return {} end
  end
  local out = {}
  for _, c in ipairs(list) do
    if prop(c, 'latitude') == nil and prop(c, 'guid') then
      local ok2, full = pcall(ScenEdit_GetContact, { side = side, guid = c.guid })
      if ok2 and full then c = full end
    end
    if prop(c, 'guid') and tonumber(prop(c, 'latitude')) and tonumber(prop(c, 'longitude')) then out[#out + 1] = c end
  end
  return out
end

local function isKind(c, missiles)
  local d = string.lower(tostring(prop(c, 'type_description') or prop(c, 'typed') or ''))
  local t = prop(c, 'type')
  if d:find('missile') or t == 1 or t == 'Missile' then return missiles and true or false end
  if d:find('air') and not d:find('airfield') and not d:find('airbase') then return true end
  return t == 0 or t == 'Air'
end

local function identified(c)
  local v = prop(c, 'classificationlevel')
  if tonumber(v) then return tonumber(v) >= 3 end
  v = string.lower(tostring(v or ''))
  return v:find('class') ~= nil or v:find('precise') ~= nil
end

local CHECK = {
  area = function(ic, c) return ic.area ~= nil and insideArea(c.latitude, c.longitude, ic.area) end,
  near = function(ic, c, v) return ic.home ~= nil and nm(ic.home[1], ic.home[2], c.latitude, c.longitude) <= v end,
  posture = function(ic, c, v) return v[string.upper(string.sub(tostring(prop(c, 'posture') or 'X'), 1, 1))] == true end,
  inbound = function(ic, c, v)
    local h = tonumber(prop(c, 'heading'))
    if not h or not ic.home then return false end
    local off = math.abs((h - bearingTo(c.latitude, c.longitude, ic.home[1], ic.home[2]) + 180) % 360 - 180)
    return off <= v
  end,
  altitude = function(ic, c, v)
    local a = tonumber(prop(c, 'altitude'))
    return a ~= nil and a >= v[1] and a <= v[2]
  end,
  speed = function(ic, c, v) local s = tonumber(prop(c, 'speed')); return s ~= nil and s >= v end,
  unidentified = function(ic, c) return not identified(c) end,
  emitting = function(ic, c) local e = prop(c, 'emissions'); return type(e) == 'table' and next(e) ~= nil end,
  tracked = function(ic, c, v, held) return held >= v end,
}

local function matches(ic, c, held)
  if not isKind(c, ic.missiles) then return false end
  local any, some = false, false
  for k, v in pairs(ic.c or {}) do
    some = true
    local ok, yes = pcall(CHECK[k], ic, c, v, held)
    if not ok then StudioDebug('intercept ' .. ic.mission .. ' ' .. k .. ': ' .. tostring(yes)); yes = false end
    if ic.logic == 'any' then
      if yes then any = true end
    elseif not yes then
      return false
    end
  end
  if not some then return true end
  return ic.logic ~= 'any' or any
end

local function setMission(ic, on)
  pcall(ScenEdit_SetMission, ic.side, ic.mission, { isactive = on })
end

local function airborne(u) return prop(u, 'condition_v') == 'Airborne' end

local function ready(u)
  local t = tonumber(prop(u, 'readytime_v'))
  return not t or t <= 0
end

local function addTarget(ic, c)
  for _, id in ipairs({ prop(c, 'actualunitid') or false, c.guid }) do
    if id then
      local ok, res = pcall(ScenEdit_AssignUnitAsTarget, id, ic.mission)
      if ok and res ~= false and not (type(res) == 'table' and next(res) == nil) then return id end
    end
  end
end

local function say(ic, text)
  if ic.message then StudioMsg(ic.side, '<P>' .. text .. '</P>') end
  StudioDebug(ic.mission .. ': ' .. text)
end

local function standDown(ic, key, list)
  setMission(ic, false)
  for _, g in ipairs(list) do
    local u = StudioGetUnit(g)
    if u then
      pcall(ScenEdit_AssignUnitToMission, g, 'none')
      if airborne(u) then pcall(ScenEdit_SetUnit, { guid = g, rtb = true }) end
    end
  end
  StudioSetKV(key .. 'U', '')
  say(ic, ic.mission .. ': stand down. Aircraft returning to base.')
end

local function intercept(ic, now)
  local key = 'STUDIO_IC_' .. ic.id .. '_'
  local off = StudioGetKV(key .. 'OFF', '')
  local armed = off == '' and ic.armed or off == '0'

  -- what the side sees, and for how long
  local seen, first = {}, {}
  for _, w in ipairs(words(StudioGetKV(key .. 'SEEN', ''))) do
    local g, t = w:match('^(.-)=(%-?%d+)$')
    if g then first[g] = tonumber(t) end
  end
  local good, here = {}, {}
  local open = armed and now >= (ic.from or now) and now <= (ic.to or now)
               and (not ic.flag or StudioFlag(ic.flag))
  if armed then
    for _, c in ipairs(contactsOf(ic.side)) do
      first[c.guid] = first[c.guid] or now
      seen[#seen + 1] = c.guid .. '=' .. first[c.guid]
      here[c.guid] = c
      if open and matches(ic, c, now - first[c.guid]) then good[#good + 1] = c end
    end
  end
  StudioSetKV(key .. 'SEEN', table.concat(seen, ' '))
  if #good < (ic.raid or 1) then good = {} end
  if ic.home then
    table.sort(good, function(a, b)
      return nm(ic.home[1], ic.home[2], a.latitude, a.longitude) < nm(ic.home[1], ic.home[2], b.latitude, b.longitude)
    end)
  end
  local isGood = {}
  for _, c in ipairs(good) do isGood[c.guid] = true end

  -- targets: keep those that still match (or matched recently), drop the rest, add new ones
  local targets, n = {}, 0
  for _, w in ipairs(words(StudioGetKV(key .. 'T', ''))) do
    local g, id, last = w:match('^(.-)=(.-)=(%-?%d+)$')
    if g then
      last = isGood[g] and now or tonumber(last)
      -- destroyed: drop it at once; a track lost for a moment is kept for the stand-down time
      local gone = not here[g] and not StudioGetUnit(id)
      if armed and not gone and now - last <= (ic.down or 300) then
        targets[g] = { id = id, last = last }
        n = n + 1
      else
        pcall(ScenEdit_RemoveUnitAsTarget, id, ic.mission)
      end
    end
  end
  local fresh = 0
  for _, c in ipairs(good) do
    if n >= (ic.max or 1) then break end
    if not targets[c.guid] then
      local id = addTarget(ic, c)
      if id then
        targets[c.guid] = { id = id, last = now }
        n = n + 1
        fresh = fresh + 1
      else
        StudioLog(ic.mission .. ': CMO would not take ' .. tostring(prop(c, 'name')) .. ' as a target')
      end
    end
  end
  local t = {}
  for g, v in pairs(targets) do t[#t + 1] = g .. '=' .. v.id .. '=' .. v.last end
  table.sort(t)
  StudioSetKV(key .. 'T', table.concat(t, ' '))

  -- aircraft: the ones already scrambled, then more if there are targets for them
  local up, isUp = {}, {}
  for _, g in ipairs(words(StudioGetKV(key .. 'U', ''))) do
    if StudioGetUnit(g) then up[#up + 1] = g; isUp[g] = true end
  end
  if n == 0 then
    if #up > 0 then standDown(ic, key, up) end
    return 0
  end
  local free = {}
  for _, name in ipairs(ic.names or {}) do
    local u = StudioGetUnit({ side = ic.side, name = name })
    if u and not isUp[u.guid] and ready(u) then free[#free + 1] = u end
  end
  local launched = 0
  local want, spare = n * (ic.per or 2), #free - (ic.reserve or 0)
  while #up < want and launched < spare do
    local u = free[launched + 1]
    launched = launched + 1
    local ok, err = pcall(ScenEdit_AssignUnitToMission, u.guid, ic.mission)
    if ok then up[#up + 1] = u.guid
    else StudioLog(ic.mission .. ': could not assign ' .. u.name .. ': ' .. tostring(err)) end
  end
  StudioSetKV(key .. 'U', table.concat(up, ' '))
  setMission(ic, true)
  if launched > 0 then
    if ic.signal then StudioSetFlag(ic.signal, true) end
    say(ic, ic.mission .. ': scramble! ' .. launched .. ' aircraft launching against ' .. n .. ' contact(s).')
  elseif fresh > 0 then
    say(ic, ic.mission .. ': new contact, but no more aircraft are available.')
  end
  return launched
end

-- Returns the number of aircraft scrambled.
function StudioInterceptTick()
  local now, total = math.floor(tonumber(ScenEdit_CurrentTime()) or 0), 0
  for _, ic in ipairs(STUDIO.INTERCEPTS or {}) do
    local ok, r = pcall(intercept, ic, now)
    if ok then total = total + (r or 0) else StudioLog('Intercept "' .. ic.mission .. '": ' .. tostring(r)) end
  end
  return total
end

------------------------------------------------------------------ short aliases (only if free)
Log       = Log       or StudioLog
Flag      = Flag      or StudioFlag
SetFlag   = SetFlag   or StudioSetFlag
GetKV     = GetKV     or StudioGetKV
SetKV     = SetKV     or StudioSetKV
RunScript = RunScript or StudioRunScript
