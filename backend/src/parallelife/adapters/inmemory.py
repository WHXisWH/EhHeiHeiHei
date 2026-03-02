from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from parallelife.domain.models import (
    Agent,
    AgentPosition,
    CityContext,
    ConversationMessage,
    Event,
    SnsPost,
)
from parallelife.domain.memory import estimate_importance
from parallelife.ports.repositories import (
    AgentPositionRepository,
    AgentRepository,
    CityContextRepository,
    ConversationRepository,
    EventRepository,
    SnsRepository,
)


class InMemoryAgentRepository(AgentRepository):
    def __init__(self) -> None:
        self._agents: dict[UUID, Agent] = {}

    async def create(self, agent: Agent) -> Agent:
        self._agents[agent.agent_id] = agent
        return agent

    async def list_all(self) -> list[Agent]:
        return list(self._agents.values())

    async def get(self, agent_id: UUID) -> Agent | None:
        return self._agents.get(agent_id)


class InMemoryAgentPositionRepository(AgentPositionRepository):
    def __init__(self) -> None:
        self._positions: dict[UUID, AgentPosition] = {}

    async def upsert(self, position: AgentPosition) -> AgentPosition:
        self._positions[position.agent_id] = position
        return position

    async def get(self, agent_id: UUID) -> AgentPosition | None:
        return self._positions.get(agent_id)

    async def list_all(self) -> list[AgentPosition]:
        return list(self._positions.values())


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._events: list[Event] = []

    async def add(self, event: Event) -> Event:
        self._events.append(event)
        return event

    async def list_by_agent(self, agent_id: UUID, limit: int = 100) -> list[Event]:
        items = [e for e in self._events if e.agent_id == agent_id]
        return list(reversed(items))[:limit]

    async def list_between(self, start: datetime, end: datetime) -> list[Event]:
        return [e for e in self._events if start <= e.created_at <= end]

    async def list_recent(self, limit: int = 200) -> list[Event]:
        return list(reversed(self._events))[:limit]


class InMemorySnsRepository(SnsRepository):
    def __init__(self) -> None:
        self._posts: list[SnsPost] = []

    async def add_post(self, post: SnsPost) -> SnsPost:
        self._posts.append(post)
        return post

    async def list_recent(self, limit: int = 50) -> list[SnsPost]:
        return list(reversed(self._posts))[:limit]


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._by_agent: dict[UUID, list[ConversationMessage]] = defaultdict(list)

    async def add_user_message(self, agent_id: UUID, content: str) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=str(uuid4()),
            agent_id=agent_id,
            role="user",
            content=content,
            processed=False,
            importance=estimate_importance(content),
        )
        self._by_agent[agent_id].append(msg)
        return msg

    async def add_agent_message(self, agent_id: UUID, content: str) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=str(uuid4()),
            agent_id=agent_id,
            role="agent",
            content=content,
            processed=True,
            importance=estimate_importance(content),
        )
        self._by_agent[agent_id].append(msg)
        return msg

    async def get_recent(self, agent_id: UUID, limit: int = 10) -> list[ConversationMessage]:
        return self._by_agent[agent_id][-limit:]

    async def get_pending_user_message(self, agent_id: UUID) -> ConversationMessage | None:
        for msg in reversed(self._by_agent[agent_id]):
            if msg.role == "user" and not msg.processed:
                return msg
        return None

    async def mark_processed(self, agent_id: UUID, message_id: str) -> None:
        msgs = self._by_agent[agent_id]
        for i, msg in enumerate(msgs):
            if msg.message_id == message_id:
                msgs[i] = replace(msg, processed=True)
                return

    async def delete(self, agent_id: UUID, message_id: str) -> None:
        msgs = self._by_agent[agent_id]
        self._by_agent[agent_id] = [m for m in msgs if m.message_id != message_id]


class InMemoryCityContextRepository(CityContextRepository):
    def __init__(self) -> None:
        self._current = CityContext(
            weather={"condition": "sunny", "temp": 18},
            time_period="day",
            events=[],
        )

    async def get_current(self) -> CityContext:
        return self._current
