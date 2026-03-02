from __future__ import annotations

from uuid import UUID

from parallelife.domain.models import Agent, AgentPosition
from parallelife.ports.repositories import AgentPositionRepository, AgentRepository


class CreateAgentUseCase:
    def __init__(self, agents: AgentRepository, positions: AgentPositionRepository) -> None:
        self._agents = agents
        self._positions = positions

    async def execute(self, agent: Agent, *, initial_lat: float, initial_lon: float) -> Agent:
        created = await self._agents.create(agent)
        await self._positions.upsert(
            AgentPosition(agent_id=created.agent_id, lat=initial_lat, lon=initial_lon, status="idle", place_type="outdoor")
        )
        return created


class GetAgentUseCase:
    def __init__(self, agents: AgentRepository, positions: AgentPositionRepository) -> None:
        self._agents = agents
        self._positions = positions

    async def execute(self, agent_id: UUID) -> dict | None:
        agent = await self._agents.get(agent_id)
        if agent is None:
            return None
        pos = await self._positions.get(agent_id)
        return {"agent": agent, "position": pos}

