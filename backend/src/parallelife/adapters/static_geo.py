from __future__ import annotations

import json
import math
from pathlib import Path

from parallelife.ports.geo import GeoRepository


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class StaticGeoRepository(GeoRepository):
    def __init__(self, data_path: Path) -> None:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        self._pois: dict[str, dict] = {p["poi_id"]: p for p in data.get("pois", [])}
        self._buildings: dict[str, dict] = {b["building_id"]: b for b in data.get("buildings", [])}

    async def list_nearby_pois(self, *, lat: float, lon: float, radius_m: float) -> list[dict]:
        out: list[dict] = []
        for p in self._pois.values():
            d = _haversine_m(lat, lon, float(p["lat"]), float(p["lon"]))
            if d <= radius_m:
                out.append({**p, "distance": d})
        out.sort(key=lambda x: x["distance"])
        return out

    async def list_nearby_buildings(self, *, lat: float, lon: float, radius_m: float) -> list[dict]:
        out: list[dict] = []
        for b in self._buildings.values():
            d = _haversine_m(lat, lon, float(b["centroid_lat"]), float(b["centroid_lon"]))
            if d <= radius_m:
                out.append({**b, "distance": d})
        out.sort(key=lambda x: x["distance"])
        return out

    async def get_poi(self, poi_id: str) -> dict | None:
        return self._pois.get(poi_id)

    async def get_building(self, building_id: str) -> dict | None:
        return self._buildings.get(building_id)

