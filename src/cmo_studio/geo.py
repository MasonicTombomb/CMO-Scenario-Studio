"""Small geodesy helpers: coordinate parsing/formatting, distance, Web Mercator."""

from __future__ import annotations

import math
import re
from typing import Optional

EARTH_KM = 6371.0088
NM_PER_KM = 1 / 1.852
TILE = 256
MAX_LAT = 85.05112878


def parse_angle(text: str, hemis_neg: str) -> Optional[float]:
    """'59.37', '-28.1', '59 22 12 N', "59°22'12\"N", '59:22.2N' -> decimal degrees."""
    t = text.strip().upper()
    if not t:
        return None
    sign = 1.0
    if t[-1:] in "NSEW":
        if t[-1] in hemis_neg:
            sign = -1.0
        t = t[:-1].strip()
    elif t[:1] in "NSEW":
        if t[0] in hemis_neg:
            sign = -1.0
        t = t[1:].strip()
    if t.startswith("-"):
        sign, t = -sign, t[1:]
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t.replace(",", "."))]
    if not nums or len(nums) > 3:
        return None
    value = nums[0] + (nums[1] / 60 if len(nums) > 1 else 0) + (nums[2] / 3600 if len(nums) > 2 else 0)
    return sign * value


def parse_latlon(text: str) -> Optional[tuple[float, float]]:
    """Parse 'lat, lon' in decimal or DMS. Returns None if it does not make sense."""
    t = text.strip()
    if not t:
        return None
    # split on comma/semicolon, or between the N/S letter and the rest
    parts = re.split(r"\s*[;,]\s*|(?<=[NSns])\s+(?=[0-9EWew-])", t)
    parts = [p for p in parts if p and p.strip()]
    if len(parts) != 2:
        nums = t.split()
        if len(nums) == 2:
            parts = nums
        else:
            return None
    lat = parse_angle(parts[0], "S")
    lon = parse_angle(parts[1], "W")
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    return lat, lon


def fmt_dms(value: float, pos: str, neg: str) -> str:
    h = pos if value >= 0 else neg
    v = abs(value)
    d = int(v)
    m = int((v - d) * 60)
    s = (v - d - m / 60) * 3600
    return f"{d}°{m:02d}'{s:04.1f}\"{h}"


def format_latlon(lat: float, lon: float, dms: bool = False) -> str:
    if dms:
        return f"{fmt_dms(lat, 'N', 'S')} {fmt_dms(lon, 'E', 'W')}"
    return f"{lat:.5f}, {lon:.5f}"


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


# ------------------------------------------------------------------ Web Mercator (world pixels at zoom z)
def world_size(z: float) -> float:
    return TILE * (2.0 ** z)


def to_world(lat: float, lon: float, z: float) -> tuple[float, float]:
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    size = world_size(z)
    x = (lon + 180.0) / 360.0 * size
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * size
    return x, y


def from_world(x: float, y: float, z: float) -> tuple[float, float]:
    size = world_size(z)
    lon = x / size * 360.0 - 180.0
    n = math.pi - 2 * math.pi * y / size
    lat = math.degrees(math.atan(math.sinh(n)))
    return lat, lon


def polygon_centroid(points: list[list[float]]) -> tuple[float, float]:
    if not points:
        return 0.0, 0.0
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)
