from __future__ import annotations

import math

from parallelife.ports.geo import AgentLocator
from parallelife.ports.repositories import AgentPositionRepository, AgentRepository


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RepoBackedAgentLocator(AgentLocator):
    def __init__(self, agents: AgentRepository, positions: AgentPositionRepository) -> None:
        self._agents = agents
        self._positions = positions

    async def list_agents_within(self, *, lat: float, lon: float, radius_m: float) -> list[dict]:
        agents = await self._agents.list_all()
        positions = {p.agent_id: p for p in await self._positions.list_all()}
        out: list[dict] = []
        for a in agents:
            p = positions.get(a.agent_id)
            if not p:
                continue
            d = _haversine_m(lat, lon, float(p.lat), float(p.lon))
            if d <= radius_m:
                out.append(
                    {
                        "agent_id": str(a.agent_id),
                        "display_name": a.display_name,
                        "personality_type": a.personality_type,
                        "mood_score": a.mood_score,
                        "lat": p.lat,
                        "lon": p.lon,
                        "distance": d,
                    }
                )
        out.sort(key=lambda x: x["distance"])
        return out

