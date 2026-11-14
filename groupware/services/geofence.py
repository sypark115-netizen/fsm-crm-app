"""GPS 지오펜스 검증."""
from __future__ import annotations

import math
from dataclasses import dataclass

from core.config import SITES, Site

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class GeoCheck:
    ok: bool
    site: Site
    distance_m: float


def nearest_site(lat: float, lng: float, sites: list[Site] | None = None) -> GeoCheck:
    """가장 가까운 기준지점과 반경 내 여부. GPS 오차(accuracy)는 호출측에서 판단."""
    sites = sites or SITES
    best = min(sites, key=lambda s: haversine_m(lat, lng, s.lat, s.lng))
    d = haversine_m(lat, lng, best.lat, best.lng)
    return GeoCheck(ok=d <= best.radius_m, site=best, distance_m=d)
