from __future__ import annotations

import math

from parallelife.domain.decision import Decision
from parallelife.settings import Settings


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def enforce_spatial_rules(
    *,
    settings: Settings,
    current_lat: float,
    current_lon: float,
    decision: Decision,
    nearby_poi_ids: set[str],
    nearby_building_ids: set[str],
    nearby_agent_ids: set[str] | None = None,
    max_move_m: float = 100.0,
) -> Decision:
    if decision.destination is None:
        return decision

    lat = float(decision.destination.lat)
    lon = float(decision.destination.lon)

    if not (settings.shibuya_min_lat <= lat <= settings.shibuya_max_lat):
        raise ValueError("Destination out of Shibuya bounding box (lat).")
    if not (settings.shibuya_min_lon <= lon <= settings.shibuya_max_lon):
        raise ValueError("Destination out of Shibuya bounding box (lon).")

    dist = _haversine_m(current_lat, current_lon, lat, lon)
    if dist > max_move_m:
        raise ValueError(f"Move distance too large: {dist:.1f}m > {max_move_m:.1f}m")

    if decision.action in ("move", "enter"):
        if decision.target and decision.target not in nearby_poi_ids and decision.target not in nearby_building_ids:
            raise ValueError("Target not in nearby POIs/buildings.")

    if decision.action == "interact":
        allowed = set(nearby_poi_ids) | set(nearby_building_ids) | set(nearby_agent_ids or set())
        if decision.target and decision.target not in allowed:
            raise ValueError("Target not in nearby POIs/buildings/agents.")

    return decision
