"""Loadout and weapon detail queries (used by the Loadout Viewer).

Link chain in DB3000::

    DataAircraft --DataAircraftLoadouts--> DataLoadout
    DataLoadout --DataLoadoutWeapons (Optional, Internal)--> DataWeaponRecord (DefaultLoad, MaxLoad)
    DataWeaponRecord.ComponentID --> DataWeapon
    DataWeapon --DataWeaponTargets--> EnumWeaponTarget
               --DataWeaponWarheads--> DataWarhead
               --DataWeaponSensors--> DataSensor (seekers)
               --DataWeaponCodes--> EnumWeaponCode (capabilities)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .database import Database, DBEntry

ROLE_GROUPS: dict[str, tuple[int, int]] = {
    "Air-to-air": (2000, 2999),
    "Strike / SEAD / CAS": (3000, 3999),
    "Support (AEW, ECM, SAR, mines)": (4000, 4999),
    "ASW": (6000, 6999),
    "Recon / transport": (7000, 7999),
    "Tanker / training": (8000, 8999),
    "Ferry / reserve / unavailable": (9000, 9999),
}


def role_group(role_id: int) -> str:
    for name, (lo, hi) in ROLE_GROUPS.items():
        if lo <= role_id <= hi:
            return name
    return "Other"


@dataclass
class LoadoutWeapon:
    weapon_id: int
    name: str
    wtype: str
    qty: int
    max_qty: int
    internal: bool
    optional: bool
    weight_kg: float = 0.0
    air_range: float = 0.0
    surface_range: float = 0.0
    land_range: float = 0.0
    sub_range: float = 0.0


@dataclass
class LoadoutDetails:
    id: int
    name: str
    role: str
    role_id: int
    comments: str = ""
    time_of_day: str = ""
    weather: str = ""
    mission_profile: str = ""
    radius_nm: int = 0
    time_on_station_min: int = 0
    ready_min: int = 0
    ready_sustained_min: int = 0
    quick_turnaround: bool = False
    qt_ready_min: int = 0
    qt_max_sorties: int = 0
    qt_airborne_min: int = 0
    qt_time_of_day: str = ""
    winchester: str = ""
    drag_modifier: float = 0.0
    buddy_illumination: bool = False
    hypothetical: bool = False
    deprecated: bool = False
    weapons: list[LoadoutWeapon] = field(default_factory=list)

    @property
    def payload_kg(self) -> float:
        return sum(w.weight_kg * w.qty for w in self.weapons)


@dataclass
class WeaponDetails:
    entry: DBEntry
    comments: str = ""
    stats: list[tuple[str, str]] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    warheads: list[str] = field(default_factory=list)
    seekers: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)


@dataclass
class LoadoutUse:
    loadout_id: int
    loadout_name: str
    role: str
    aircraft_id: int
    aircraft_name: str
    country: str


def hhmm(minutes: int) -> str:
    if not minutes:
        return "-"
    return f"{minutes} min ({minutes // 60}:{minutes % 60:02d} h)"


def loadout_details(db: Database, lid: int) -> Optional[LoadoutDetails]:
    cur = db.conn.execute("select * from DataLoadout where ID=?", (lid,))
    row = cur.fetchone()
    if row is None:
        return None
    v = dict(zip([d[0] for d in cur.description], row))
    e = db.enum
    profiles = {r[0]: r[1] for r in db.conn.execute("select ID, Description from EnumLoadoutMissionProfile")}
    d = LoadoutDetails(
        id=lid, name=v.get("Name") or "", role=e("EnumLoadoutRole").get(v.get("LoadoutRole"), ""),
        role_id=v.get("LoadoutRole") or 0,
        comments="" if (v.get("Comments") or "-") == "-" else v["Comments"],
        time_of_day=e("EnumLoadoutTimeOfDay").get(v.get("TimeofDay"), ""),
        weather=e("EnumLoadoutWeather").get(v.get("Weather"), ""),
        mission_profile=profiles.get(v.get("DefaultMissionProfile"), ""),
        radius_nm=v.get("DefaultCombatRadius") or 0,
        time_on_station_min=v.get("DefaultTimeOnStation") or 0,
        ready_min=v.get("ReadyTime") or 0,
        ready_sustained_min=v.get("ReadyTime_Sustained") or 0,
        quick_turnaround=bool(v.get("QuickTurnaround")),
        qt_ready_min=v.get("QuickTurnaround_ReadyTime") or 0,
        qt_max_sorties=v.get("QuickTurnaround_MaxSorties") or 0,
        qt_airborne_min=v.get("QuickTurnaround_AirborneTime") or 0,
        qt_time_of_day=e("EnumLoadoutTimeOfDay").get(v.get("QuickTurnaround_TimeofDay"), ""),
        winchester=e("EnumLoadoutWinchesterShotgun").get(v.get("WinchesterShotgun"), ""),
        drag_modifier=float(v.get("PayloadWeightDragModifier") or 0),
        buddy_illumination=bool(v.get("RequiresBuddyIllumination")),
        hypothetical=bool(v.get("Hypothetical")), deprecated=bool(v.get("Deprecated")),
    )
    wtypes = e("EnumWeaponType")
    for wid, name, wtype, qty, mx, internal, optional, weight, ar, sr, lr, ur in db.conn.execute(
            "select w.ID, w.Name, w.Type, r.DefaultLoad, r.MaxLoad, lw.Internal, lw.Optional, w.Weight, "
            "w.AirRangeMax, w.SurfaceRangeMax, w.LandRangeMax, w.SubsurfaceRangeMax "
            "from DataLoadoutWeapons lw join DataWeaponRecord r on r.ID = lw.ComponentID "
            "join DataWeapon w on w.ID = r.ComponentID where lw.ID = ? order by lw.ComponentNumber", (lid,)):
        d.weapons.append(LoadoutWeapon(wid, name or "", wtypes.get(wtype, ""), qty or 0, mx or 0, bool(internal),
                                       bool(optional), float(weight or 0), float(ar or 0), float(sr or 0),
                                       float(lr or 0), float(ur or 0)))
    return d


def aircraft_with_loadout(db: Database, lid: int) -> list[DBEntry]:
    ids = [r[0] for r in db.conn.execute("select ID from DataAircraftLoadouts where ComponentID=?", (lid,))]
    out = [db.get("Aircraft", i) for i in ids]
    return sorted((e for e in out if e), key=lambda e: (e.name, e.country))


def weapon_details(db: Database, wid: int) -> Optional[WeaponDetails]:
    entry = db.get("Weapon", wid)
    if entry is None:
        return None
    cur = db.conn.execute("select * from DataWeapon where ID=?", (wid,))
    v = dict(zip([d[0] for d in cur.description], cur.fetchone()))
    d = WeaponDetails(entry=entry, comments="" if (v.get("Comments") or "-") == "-" else v["Comments"])

    def rng(lo, hi):
        a, b = v.get(lo) or 0, v.get(hi) or 0
        return f"{a:g} - {b:g} nm" if b else None

    def num(key, unit="", fmt="{:g}"):
        x = v.get(key)
        return (fmt.format(x) + unit) if x not in (None, 0, 0.0) else None

    def pct(key):
        x = v.get(key)
        return f"{x}%" if x else None

    rows = [
        ("Type", e if (e := db.enum("EnumWeaponType").get(v.get("Type"))) else None),
        ("Generation", g if (g := db.enum("EnumWeaponGeneration").get(v.get("Generation"))) and g != "None"
         else None),
        ("Air range", rng("AirRangeMin", "AirRangeMax")), ("Surface range", rng("SurfaceRangeMin", "SurfaceRangeMax")),
        ("Land range", rng("LandRangeMin", "LandRangeMax")),
        ("Subsurface range", rng("SubsurfaceRangeMin", "SubsurfaceRangeMax")),
        ("PoK air", pct("AirPoK")), ("PoK surface", pct("SurfacePoK")), ("PoK land", pct("LandPoK")),
        ("PoK subsurface", pct("SubsurfacePoK")), ("CEP", num("CEP", " m")), ("Weight", num("Weight", " kg")),
        ("Length", num("Length", " m")), ("Max flight time", num("MaxFlightTime", " s")),
        ("Cruise altitude", num("CruiseAltitude", " m")),
        ("Launch altitude", f"{v.get('LaunchAltitudeMin') or 0:g} - {v.get('LaunchAltitudeMax'):g} m"
         if v.get("LaunchAltitudeMax") else None),
        ("Target altitude", f"{v.get('TargetAltitudeMin') or 0:g} - {v.get('TargetAltitudeMax'):g} m"
         if v.get("TargetAltitudeMax") else None),
        ("Target speed max", num("TargetSpeedMax", " kt")),
        ("Torpedo speed", f"{v.get('TorpedoSpeedCruise') or 0:g} / {v.get('TorpedoSpeedFull'):g} kt"
         if v.get("TorpedoSpeedFull") else None),
        ("Cost", num("Cost", " M$", "{:,.2f}")),
    ]
    d.stats = [(k, x) for k, x in rows if x]
    targets = db.enum("EnumWeaponTarget")
    d.targets = [targets.get(r[0], str(r[0])) for r in
                 db.conn.execute("select CodeID from DataWeaponTargets where ID=? order by CodeID", (wid,))]
    codes = db.enum("EnumWeaponCode")
    d.codes = [codes.get(r[0], str(r[0])) for r in
               db.conn.execute("select CodeID from DataWeaponCodes where ID=? order by CodeID", (wid,))]
    wh_types = db.enum("EnumWarheadType")
    for name, wtype, dp, expl, n in db.conn.execute(
            "select h.Name, h.Type, h.DamagePoints, h.ExplosivesWeight, h.NumberOfWarheads from DataWeaponWarheads ww "
            "join DataWarhead h on h.ID = ww.ComponentID where ww.ID = ? order by ww.ComponentNumber", (wid,)):
        bits = [wh_types.get(wtype, "")]
        if dp:
            bits.append(f"{dp:g} DP")
        if expl:
            bits.append(f"{expl:g} kg explosive")
        if n and n > 1:
            bits.append(f"x{n}")
        d.warheads.append(f"{name}  ({', '.join(b for b in bits if b)})")
    sroles = db.enum("EnumSensorRole")
    for name, role, rmax in db.conn.execute(
            "select s.Name, s.Role, s.RangeMax from DataWeaponSensors ws join DataSensor s on s.ID = ws.ComponentID "
            "where ws.ID = ? order by ws.ComponentNumber", (wid,)):
        d.seekers.append(f"{name}  ({sroles.get(role, '')}{f', {rmax:g} nm' if rmax else ''})")
    return d


def loadouts_with_weapon(db: Database, wid: int, limit: int = 2000) -> list[LoadoutUse]:
    """Aircraft loadouts that carry a weapon (not deprecated), newest aircraft names first."""
    roles = db.enum("EnumLoadoutRole")
    countries = db.enum("EnumOperatorCountry")
    rows = db.conn.execute(
        "select l.ID, l.Name, l.LoadoutRole, a.ID, a.Name, a.OperatorCountry from DataWeaponRecord r "
        "join DataLoadoutWeapons lw on lw.ComponentID = r.ID join DataLoadout l on l.ID = lw.ID "
        "join DataAircraftLoadouts al on al.ComponentID = l.ID join DataAircraft a on a.ID = al.ID "
        "where r.ComponentID = ? and (l.Deprecated = 0 or l.Deprecated is null) "
        "and (a.Deprecated = 0 or a.Deprecated is null) group by l.ID, a.ID order by a.Name, l.Name limit ?",
        (wid, limit))
    return [LoadoutUse(lid, ln or "", roles.get(role, ""), aid, an or "", countries.get(c, ""))
            for lid, ln, role, aid, an, c in rows]
