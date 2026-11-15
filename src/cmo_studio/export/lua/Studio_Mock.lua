--[[ Studio_Mock.lua - a stand-in for CMO's ScenEdit_* API used by the studio's
     "Dry-run build". It is strict about wiring (unknown sides, missing hosts,
     missing loadouts, missions without areas, events without triggers) so that
     mistakes show up before you open CMO. It is NOT shipped with an export. ]]

MOCK = { n = 0, sides = {}, order = {}, units = {}, missions = {}, kv = {}, rps = {}, events = {},
         triggers = {}, actions = {}, conditions = {}, specials = {}, score = {}, errors = {},
         now = MOCK_START or 1893456000, printed = {} }

local function fail(msg) MOCK.errors[#MOCK.errors + 1] = msg; error(msg, 2) end
local function guid() MOCK.n = MOCK.n + 1; return string.format('mock-%05d', MOCK.n) end
local function need(cond, msg) if not cond then fail(msg) end end

function ScenEdit_AddSide(t)
  need(t and t.name and t.name ~= '', 'AddSide: name required')
  need(not MOCK.sides[t.name], 'AddSide: side exists: ' .. tostring(t.name))
  MOCK.sides[t.name] = { name = t.name, computerControlledOnly = false, units = {} }
  MOCK.order[#MOCK.order + 1] = t.name
  return MOCK.sides[t.name]
end
function VP_GetSide(t)
  local s = MOCK.sides[t.side or t.name]
  if not s then error('Side not found: ' .. tostring(t.side)) end
  local list = {}
  for g, u in pairs(MOCK.units) do if u.side == s.name then list[#list + 1] = { guid = g } end end
  s.units = list
  return s
end
function ScenEdit_SetSideOptions(t) need(MOCK.sides[t.side], 'SetSideOptions: no side ' .. tostring(t.side)); return true end
function ScenEdit_SetSidePosture(a, b, p)
  need(MOCK.sides[a] and MOCK.sides[b], 'SetSidePosture: unknown side ' .. tostring(a) .. '/' .. tostring(b))
  need(p == 'F' or p == 'N' or p == 'U' or p == 'H', 'SetSidePosture: bad posture ' .. tostring(p))
end
function ScenEdit_SetDoctrine(sel, d)
  if sel.side then need(MOCK.sides[sel.side], 'SetDoctrine: no side ' .. tostring(sel.side)) end
  return true
end
function ScenEdit_SetScore(side, v) need(MOCK.sides[side], 'SetScore: no side ' .. tostring(side)); MOCK.score[side] = v end
function ScenEdit_GetScore(side) return MOCK.score[side] or 0 end
function ScenEdit_SetStartTime(t) need(t.Date and t.Time, 'SetStartTime: Date/Time'); return true end
function ScenEdit_SetTime(t) return true end
function ScenEdit_CurrentTime() return MOCK.now end
function ScenEdit_SetWeather(a, b, c, d) need(tonumber(a) and tonumber(b) and tonumber(c) and tonumber(d), 'SetWeather: numbers'); return true end
function ScenEdit_SetKeyValue(k, v) MOCK.kv[k] = tostring(v) end
function ScenEdit_GetKeyValue(k) return MOCK.kv[k] or '' end
function ScenEdit_ClearKeyValue(k) MOCK.kv[k] = nil end

function ScenEdit_AddReferencePoint(t)
  need(MOCK.sides[t.side], 'AddReferencePoint: no side ' .. tostring(t.side))
  need(tonumber(t.lat or t.latitude) and tonumber(t.lon or t.longitude), 'AddReferencePoint: position for ' .. tostring(t.name))
  MOCK.rps[#MOCK.rps + 1] = t
  MOCK.rpnames = MOCK.rpnames or {}
  MOCK.rpnames[t.name] = true
  return { guid = guid(), name = t.name }
end

local TYPES = { aircraft = 'Aircraft', ship = 'Ship', submarine = 'Submarine', sub = 'Submarine', facility = 'Facility',
                groundunit = 'GroundUnit' }
function ScenEdit_AddUnit(s)
  local t = TYPES[string.lower(tostring(s.type or ''))]
  need(t, 'AddUnit: bad type ' .. tostring(s.type))
  need(MOCK.sides[s.side], 'AddUnit: no side ' .. tostring(s.side))
  need(tonumber(s.dbid) and s.dbid > 0, 'AddUnit: no dbid for ' .. tostring(s.name))
  local lat, lon = s.latitude or s.lat, s.longitude or s.lon
  if t == 'Aircraft' then need(s.loadoutid, 'AddUnit: aircraft without loadoutid: ' .. tostring(s.name)) end
  if s.base then
    local b = MOCK.units[s.base]
    need(b, 'AddUnit: base not found for ' .. tostring(s.name))
    lat, lon = b.latitude, b.longitude
  end
  need(tonumber(lat) and tonumber(lon), 'AddUnit: no position for ' .. tostring(s.name))
  local g = guid()
  MOCK.units[g] = { guid = g, name = s.name, side = s.side, type = t, classname = 'DBID ' .. s.dbid, dbid = s.dbid,
                    latitude = lat, longitude = lon, base = s.base }
  return MOCK.units[g]
end
function ScenEdit_GetUnit(sel)
  if sel.guid then return MOCK.units[sel.guid] end
  for _, u in pairs(MOCK.units) do
    if u.name == sel.name and (sel.side == nil or u.side == sel.side) then return u end
  end
  return nil
end
function ScenEdit_SetUnit(t)
  local u = MOCK.units[t.guid]
  need(u, 'SetUnit: unknown unit')
  if t.formation then
    need(u.group, 'SetUnit: formation station for ' .. u.name .. ' before it was grouped')
    need(tonumber(t.formation.bearing) and tonumber(t.formation.distance), 'SetUnit: formation needs bearing/distance')
    MOCK.groups = MOCK.groups or {}
    MOCK.groups[u.group] = (MOCK.groups[u.group] or 0) + 1
  end
  return u
end
function ScenEdit_SetEMCON(kind, id, s) need(MOCK.units[id] or MOCK.sides[id], 'SetEMCON: unknown ' .. tostring(id)); return true end
function ScenEdit_DeleteUnit(t) MOCK.units[t.guid] = nil end

local CLASSES = { patrol = true, strike = true, support = true, ferry = true, mining = true, mineclearing = true, cargo = true }
function ScenEdit_AddMission(side, name, class, opts)
  need(MOCK.sides[side], 'AddMission: no side ' .. tostring(side))
  need(CLASSES[string.lower(class)], 'AddMission: bad class ' .. tostring(class))
  local key = side .. '/' .. name
  need(not MOCK.missions[key], 'AddMission: duplicate mission ' .. name)
  if class == 'patrol' or class == 'support' or class == 'mining' or class == 'mineclearing' then
    need(opts and type(opts.zone) == 'table' and #opts.zone > 0, 'AddMission: "' .. name .. '" needs an area')
    for _, rp in ipairs(opts.zone) do need(MOCK.rpnames and MOCK.rpnames[rp], 'AddMission: unknown RP ' .. rp) end
  end
  if class == 'patrol' and #opts.zone < 3 then fail('AddMission: patrol "' .. name .. '" needs 3+ points') end
  MOCK.missions[key] = { side = side, name = name, class = class, units = {}, targets = {} }
  return { name = name, guid = guid() }
end
local function findMission(name)
  for _, m in pairs(MOCK.missions) do if m.name == name then return m end end
end
function ScenEdit_SetMission(side, name, opts) need(findMission(name), 'SetMission: no mission ' .. tostring(name)); return true end
function ScenEdit_AssignUnitToMission(g, name)
  local m = findMission(name)
  need(m, 'AssignUnitToMission: no mission ' .. tostring(name))
  local u = MOCK.units[g]
  need(u, 'AssignUnitToMission: unknown unit')
  need(u.side == m.side, 'AssignUnitToMission: ' .. u.name .. ' is not on side ' .. m.side)
  m.units[#m.units + 1] = g
  return true
end
function ScenEdit_AssignUnitAsTarget(g, name)
  local m = findMission(name)
  need(m and m.class == 'strike', 'AssignUnitAsTarget: no strike mission ' .. tostring(name))
  need(MOCK.units[g], 'AssignUnitAsTarget: unknown unit')
  m.targets[#m.targets + 1] = g
  return true
end

function ScenEdit_SetEvent(name, t) need(t.mode == 'add', 'SetEvent: mode'); MOCK.events[name] = { triggers = 0, actions = 0 }; return true end
function ScenEdit_SetTrigger(t)
  need(t.name and t.type, 'SetTrigger: name/type')
  if t.TargetFilter and t.TargetFilter.TargetSide then need(MOCK.sides[t.TargetFilter.TargetSide], 'SetTrigger: unknown side') end
  if t.Area then for _, rp in ipairs(t.Area) do need(MOCK.rpnames and MOCK.rpnames[rp], 'SetTrigger: unknown RP ' .. rp) end end
  MOCK.triggers[t.name] = t
  return true
end
function ScenEdit_SetEventTrigger(e, t) need(MOCK.events[e] and MOCK.triggers[t.name], 'SetEventTrigger'); MOCK.events[e].triggers = MOCK.events[e].triggers + 1; return true end
function ScenEdit_SetCondition(t) MOCK.conditions[t.name] = t; return true end
function ScenEdit_SetEventCondition(e, t) need(MOCK.events[e] and MOCK.conditions[t.name], 'SetEventCondition'); return true end
function ScenEdit_SetAction(t)
  need(t.name and t.type, 'SetAction: name/type')
  if t.type == 'LuaScript' then
    local f, err = load(t.ScriptText, '=' .. t.name)
    need(f, 'Action "' .. t.name .. '" has a Lua syntax error: ' .. tostring(err))
  end
  MOCK.actions[t.name] = t
  return true
end
function ScenEdit_SetEventAction(e, t) need(MOCK.events[e] and MOCK.actions[t.name], 'SetEventAction'); MOCK.events[e].actions = MOCK.events[e].actions + 1; return true end
function ScenEdit_AddSpecialAction(t)
  need(MOCK.sides[t.Side], 'AddSpecialAction: no side ' .. tostring(t.Side))
  local f, err = load(t.ScriptText, '=' .. t.ActionNameOrID)
  need(f, 'Special action "' .. t.ActionNameOrID .. '" has a Lua syntax error: ' .. tostring(err))
  MOCK.specials[#MOCK.specials + 1] = t
  return true
end
function ScenEdit_SpecialMessage(side, text) MOCK.printed[#MOCK.printed + 1] = 'MSG ' .. side end
function ScenEdit_EndScenario() MOCK.ended = true end
function ScenEdit_RunScript(path)
  local f, err = loadfile(LUA_ROOT .. path)
  if not f then error('RunScript: ' .. tostring(err)) end
  return f()
end

-- After the build: run every event script once to catch run-time errors.
function MOCK_RUN_EVENT_SCRIPTS()
  local n, bad = 0, {}
  for name, a in pairs(MOCK.actions) do
    if a.type == 'LuaScript' then
      n = n + 1
      local f = load(a.ScriptText, '=' .. name)
      local ok, err = pcall(f)
      if not ok then bad[#bad + 1] = name .. ': ' .. tostring(err) end
    end
  end
  for _, a in ipairs(MOCK.specials) do
    n = n + 1
    local f = load(a.ScriptText, '=' .. a.ActionNameOrID)
    local ok, err = pcall(f)
    if not ok then bad[#bad + 1] = a.ActionNameOrID .. ': ' .. tostring(err) end
  end
  return n, bad
end

function MOCK_SUMMARY()
  local units, byType = 0, {}
  for _, u in pairs(MOCK.units) do units = units + 1; byType[u.type] = (byType[u.type] or 0) + 1 end
  local missions = 0
  for _ in pairs(MOCK.missions) do missions = missions + 1 end
  local events, noTrig = 0, {}
  for name, e in pairs(MOCK.events) do
    events = events + 1
    if e.triggers == 0 then noTrig[#noTrig + 1] = name end
  end
  local groups = 0
  for _ in pairs(MOCK.groups or {}) do groups = groups + 1 end
  local s = string.format('MOCK: %d side(s), %d unit(s), %d reference point(s), %d mission(s), %d event(s), %d special action(s), %d group(s) with stations',
    #MOCK.order, units, #MOCK.rps, missions, events, #MOCK.specials, groups)
  local types = {}
  for k, v in pairs(byType) do types[#types + 1] = k .. '=' .. v end
  table.sort(types)
  s = s .. '\nMOCK: units by type: ' .. table.concat(types, ', ')
  for _, name in ipairs(noTrig) do s = s .. '\nMOCK WARNING: event "' .. name .. '" has no trigger' end
  return s
end
