from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.cloud import firestore

from parallelife.adapters.fake_ai import FakeDecisionClient
from parallelife.adapters.fake_speech import FakeSttClient, FakeTtsClient
from parallelife.adapters.firestore_repos import (
    FirestoreCityContextRepository,
    FirestoreConversationRepository,
    FirestoreSnsRepository,
)
from parallelife.adapters.agent_locator import RepoBackedAgentLocator
from parallelife.adapters.gcp_ai import VertexAIGeminiDecisionClient
from parallelife.adapters.gcp_speech import CloudSpeechSttClient, CloudTextToSpeechClient
from parallelife.adapters.inmemory import (
    InMemoryAgentPositionRepository,
    InMemoryAgentRepository,
    InMemoryCityContextRepository,
    InMemoryConversationRepository,
    InMemoryEventRepository,
    InMemorySnsRepository,
)
from parallelife.adapters.static_geo import StaticGeoRepository
from parallelife.ports.ai import AiDecisionClient, SttClient, TtsClient
from parallelife.ports.geo import AgentLocator, GeoRepository
from parallelife.ports.repositories import (
    AgentPositionRepository,
    AgentRepository,
    CityContextRepository,
    ConversationRepository,
    EventRepository,
    SnsRepository,
)
from parallelife.realtime.ws_hub import WebSocketHub
from parallelife.settings import Settings


@dataclass
class Container:
    settings: Settings
    hub: WebSocketHub
    agents: AgentRepository
    positions: AgentPositionRepository
    events: EventRepository
    conversations: ConversationRepository
    sns: SnsRepository
    city: CityContextRepository
    geo: GeoRepository
    locator: AgentLocator
    ai: AiDecisionClient
    stt: SttClient
    tts: TtsClient


def build_container(settings: Settings) -> Container:
    hub = WebSocketHub()

    agents = InMemoryAgentRepository()
    positions = InMemoryAgentPositionRepository()
    events = InMemoryEventRepository()

    geo = StaticGeoRepository(Path(__file__).resolve().parents[3] / "data" / "demo_geo.json")
    locator = RepoBackedAgentLocator(agents, positions)

    if settings.use_firestore and settings.gcp_project_id:
        db = firestore.Client(project=settings.gcp_project_id, database=settings.firestore_database)
        conversations: ConversationRepository = FirestoreConversationRepository(db)
        sns: SnsRepository = FirestoreSnsRepository(db)
        city: CityContextRepository = FirestoreCityContextRepository(db)
    else:
        conversations = InMemoryConversationRepository()
        sns = InMemorySnsRepository()
        city = InMemoryCityContextRepository()

    if settings.enable_fake_ai or settings.app_env == "test":
        ai: AiDecisionClient = FakeDecisionClient()
    else:
        if not settings.gcp_project_id:
            raise RuntimeError("GCP_PROJECT_ID is required (or set ENABLE_FAKE_AI=1).")
        ai = VertexAIGeminiDecisionClient(
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            model=settings.vertex_gemini_model,
            max_output_tokens=2048,
        )

    if settings.app_env == "test":
        stt = FakeSttClient()
        tts = FakeTtsClient()
    else:
        stt = CloudSpeechSttClient()
        tts = CloudTextToSpeechClient()

    return Container(
        settings=settings,
        hub=hub,
        agents=agents,
        positions=positions,
        events=events,
        conversations=conversations,
        sns=sns,
        city=city,
        geo=geo,
        locator=locator,
        ai=ai,
        stt=stt,
        tts=tts,
    )
