from __future__ import annotations

import math

from parallelife.domain.decision import Decision, Destination
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
    max_move_m: float = 300.0,
) -> Decision:
    if decision.destination is None:
        return decision

    lat = float(decision.destination.lat)
    lon = float(decision.destination.lon)

    # Clamp to Shibuya bounding box rather than raising
    lat = max(settings.shibuya_min_lat, min(settings.shibuya_max_lat, lat))
    lon = max(settings.shibuya_min_lon, min(settings.shibuya_max_lon, lon))

    # Scale move vector to max_move_m if too far — preserve direction
    dist = _haversine_m(current_lat, current_lon, lat, lon)
    if dist > max_move_m and dist > 0:
        ratio = max_move_m / dist
        lat = current_lat + (lat - current_lat) * ratio
        lon = current_lon + (lon - current_lon) * ratio

    # If target is not in nearby lists, clear it but keep the move
    target = decision.target
    if decision.action in ("move", "enter"):
        allowed = nearby_poi_ids | nearby_building_ids
        if target and target not in allowed:
            target = None

    if decision.action == "interact":
        allowed = nearby_poi_ids | nearby_building_ids | set(nearby_agent_ids or set())
        if target and target not in allowed:
            target = None

    return decision.model_copy(update={"destination": Destination(lat=lat, lon=lon), "target": target})
