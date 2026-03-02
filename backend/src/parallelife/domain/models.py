from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4


PersonalityType = Literal["社交达人", "内向观察者", "野心家", "随遇而安"]


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass
class Agent:
    agent_id: UUID = field(default_factory=uuid4)
    display_name: str = "未命名"
    personality_type: PersonalityType = "随遇而安"
    occupation: str = "无业"
    daily_budget_yen: int = 3000
    current_balance_yen: int = 3000
    mood_score: int = 60
    influence_score: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class AgentPosition:
    agent_id: UUID
    lat: float
    lon: float
    status: str = "idle"
    place_type: str = "outdoor"
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class CityContext:
    weather: dict
    time_period: str
    events: list[dict]
    updated_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class Event:
    event_id: UUID = field(default_factory=uuid4)
    agent_id: UUID | None = None
    event_type: str = "system"
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class SnsPost:
    post_id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    content: str = ""
    location: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())


@dataclass
class ConversationMessage:
    message_id: str
    agent_id: UUID
    role: Literal["user", "agent"]
    content: str
    processed: bool = False
    importance: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())

