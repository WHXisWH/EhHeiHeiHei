from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from parallelife.domain.models import (
    Agent,
    AgentPosition,
    CityContext,
    ConversationMessage,
    Event,
    SnsPost,
)


class AgentRepository(ABC):
    @abstractmethod
    async def create(self, agent: Agent) -> Agent: ...

    @abstractmethod
    async def list_all(self) -> list[Agent]: ...

    @abstractmethod
    async def get(self, agent_id: UUID) -> Agent | None: ...


class AgentPositionRepository(ABC):
    @abstractmethod
    async def upsert(self, position: AgentPosition) -> AgentPosition: ...

    @abstractmethod
    async def get(self, agent_id: UUID) -> AgentPosition | None: ...

    @abstractmethod
    async def list_all(self) -> list[AgentPosition]: ...


class EventRepository(ABC):
    @abstractmethod
    async def add(self, event: Event) -> Event: ...

    @abstractmethod
    async def list_by_agent(self, agent_id: UUID, limit: int = 100) -> list[Event]: ...

    @abstractmethod
    async def list_between(self, start: datetime, end: datetime) -> list[Event]: ...

    @abstractmethod
    async def list_recent(self, limit: int = 200) -> list[Event]: ...


class SnsRepository(ABC):
    @abstractmethod
    async def add_post(self, post: SnsPost) -> SnsPost: ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[SnsPost]: ...


class ConversationRepository(ABC):
    @abstractmethod
    async def add_user_message(self, agent_id: UUID, content: str) -> ConversationMessage: ...

    @abstractmethod
    async def add_agent_message(self, agent_id: UUID, content: str) -> ConversationMessage: ...

    @abstractmethod
    async def get_recent(self, agent_id: UUID, limit: int = 10) -> list[ConversationMessage]: ...

    @abstractmethod
    async def get_pending_user_message(self, agent_id: UUID) -> ConversationMessage | None: ...

    @abstractmethod
    async def mark_processed(self, agent_id: UUID, message_id: str) -> None: ...

    @abstractmethod
    async def delete(self, agent_id: UUID, message_id: str) -> None: ...


class CityContextRepository(ABC):
    @abstractmethod
    async def get_current(self) -> CityContext: ...
