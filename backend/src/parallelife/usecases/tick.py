from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from parallelife.domain.decision import Decision
from parallelife.domain.models import AgentPosition, Event, SnsPost
from parallelife.ports.ai import AiDecisionClient
from parallelife.ports.geo import AgentLocator, GeoRepository
from parallelife.ports.repositories import (
    AgentPositionRepository,
    AgentRepository,
    CityContextRepository,
    ConversationRepository,
    EventRepository,
    SnsRepository,
)
from parallelife.settings import Settings
from parallelife.usecases.conversation_memory import PruneConversationMemoryUseCase
from parallelife.usecases.risk_gate import enforce_spatial_rules


def _utcnow() -> datetime:
    return datetime.utcnow()


class TickAgentUseCase:
    def __init__(
        self,
        *,
        settings: Settings,
        agents: AgentRepository,
        positions: AgentPositionRepository,
        geo: GeoRepository,
        locator: AgentLocator,
        city: CityContextRepository,
        conversations: ConversationRepository,
        events: EventRepository,
        sns: SnsRepository,
        ai: AiDecisionClient,
    ) -> None:
        self._settings = settings
        self._agents = agents
        self._positions = positions
        self._geo = geo
        self._locator = locator
        self._city = city
        self._conversations = conversations
        self._events = events
        self._sns = sns
        self._ai = ai

    async def _build_prompt(self, agent_id: UUID) -> tuple[str, dict]:
        agent = await self._agents.get(agent_id)
        pos = await self._positions.get(agent_id)
        if agent is None or pos is None:
            raise ValueError("Agent or position not found.")

        # memory pruning (MVP)
        await PruneConversationMemoryUseCase(self._conversations).execute(agent_id)

        nearby_pois = await self._geo.list_nearby_pois(lat=pos.lat, lon=pos.lon, radius_m=200.0)
        nearby_buildings = await self._geo.list_nearby_buildings(lat=pos.lat, lon=pos.lon, radius_m=200.0)
        nearby_agents = await self._locator.list_agents_within(lat=pos.lat, lon=pos.lon, radius_m=50.0)
        nearby_agents = [a for a in nearby_agents if a.get("agent_id") != str(agent_id)]
        pending = await self._conversations.get_pending_user_message(agent_id)
        history = await self._conversations.get_recent(agent_id, limit=10)
        city = await self._city.get_current()

        city_dict = {
            "weather": city.weather,
            "time_period": city.time_period,
            "events": city.events,
            "updated_at": city.updated_at.isoformat() + "Z",
        }

        prompt = {
            "system": "你必须只输出符合 schema 的有效 JSON，不要输出多余文字。",
            "schema": {
                "action": "move|enter|exit|interact|post_sns|idle|reply",
                "target": "poi_id 或 building_id 或 agent_id 或 null",
                "destination": {"lat": "number", "lon": "number"},
                "speech": "string|null",
                "reply_to_user": "string|null",
                "internal_thought": "string",
                "mood_change": "integer(-10..10)",
                "estimated_cost": "integer",
            },
            "agent": {
                "display_name": agent.display_name,
                "personality_type": agent.personality_type,
                "occupation": agent.occupation,
                "daily_budget_yen": agent.daily_budget_yen,
                "current_balance_yen": agent.current_balance_yen,
                "mood_score": agent.mood_score,
                "influence_score": agent.influence_score,
            },
            "now": {"time": _utcnow().isoformat() + "Z"},
            "city_context": city_dict,
            "position": {"lat": pos.lat, "lon": pos.lon, "status": pos.status, "place_type": pos.place_type},
            "nearby_pois": nearby_pois[:10],
            "nearby_buildings": nearby_buildings[:10],
            "nearby_agents": nearby_agents[:10],
            "conversation_history": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat() + "Z"}
                for m in history
            ],
            "pending_user_message": pending.content if pending else None,
            "constraints": {
                "max_move_m_per_tick": 100,
                "must_choose_target_from_nearby": True,
                "shibuya_bbox": {
                    "min_lat": self._settings.shibuya_min_lat,
                    "max_lat": self._settings.shibuya_max_lat,
                    "min_lon": self._settings.shibuya_min_lon,
                    "max_lon": self._settings.shibuya_max_lon,
                },
            },
        }

        return json.dumps(prompt, ensure_ascii=False), {
            "agent": agent,
            "pos": pos,
            "nearby_pois": nearby_pois,
            "nearby_buildings": nearby_buildings,
            "nearby_agents": nearby_agents,
            "pending": pending,
            "city": city,
        }

    async def execute(self, agent_id: UUID) -> dict:
        prompt, ctx = await self._build_prompt(agent_id)
        agent = ctx["agent"]
        pos: AgentPosition = ctx["pos"]

        ws_events: list[tuple[str, dict]] = []

        decision = await self._ai.decide(prompt)

        nearby_poi_ids = {p["poi_id"] for p in ctx["nearby_pois"]}
        nearby_building_ids = {b["building_id"] for b in ctx["nearby_buildings"]}
        nearby_agent_ids = {a["agent_id"] for a in ctx["nearby_agents"]}
        decision = enforce_spatial_rules(
            settings=self._settings,
            current_lat=pos.lat,
            current_lon=pos.lon,
            decision=decision,
            nearby_poi_ids=nearby_poi_ids,
            nearby_building_ids=nearby_building_ids,
            nearby_agent_ids=nearby_agent_ids,
        )

        # Apply decision
        if decision.destination is not None and decision.action in ("move", "enter", "interact"):
            pos = AgentPosition(
                agent_id=pos.agent_id,
                lat=decision.destination.lat,
                lon=decision.destination.lon,
                status=decision.action,
                place_type=pos.place_type,
                updated_at=_utcnow(),
            )
            await self._positions.upsert(pos)
            await self._events.add(Event(agent_id=agent_id, event_type="agent.moved", payload={"decision": decision.model_dump()}))
            ws_events.append(("agent.position", {"agent_id": str(agent_id), "lat": pos.lat, "lon": pos.lon, "status": pos.status, "place_type": pos.place_type, "ts": pos.updated_at.isoformat() + "Z"}))

        if decision.action == "post_sns" and decision.speech:
            post = SnsPost(agent_id=agent_id, content=decision.speech, location={"lat": pos.lat, "lon": pos.lon})
            await self._sns.add_post(post)
            await self._events.add(Event(agent_id=agent_id, event_type="sns.new_post", payload={"post": asdict(post)}))
            ws_events.append(("sns.new_post", {"post_id": str(post.post_id), "agent_id": str(agent_id), "content": post.content, "location": post.location, "ts": post.created_at.isoformat() + "Z"}))

        if decision.reply_to_user:
            await self._conversations.add_agent_message(agent_id, decision.reply_to_user)
            pending = ctx["pending"]
            if pending:
                await self._conversations.mark_processed(agent_id, pending.message_id)
            await self._events.add(
                Event(agent_id=agent_id, event_type="message.reply", payload={"content": decision.reply_to_user})
            )
            ws_events.append(("message.reply", {"agent_id": str(agent_id), "content": decision.reply_to_user, "ts": _utcnow().isoformat() + "Z"}))

        # mood update (MVP simplified)
        old_mood = agent.mood_score
        agent.mood_score = max(0, min(100, agent.mood_score + int(decision.mood_change)))
        if agent.mood_score != old_mood:
            await self._events.add(
                Event(
                    agent_id=agent_id,
                    event_type="agent.mood_change",
                    payload={"old_mood": old_mood, "new_mood": agent.mood_score, "reason": decision.internal_thought},
                )
            )
            ws_events.append(
                (
                    "agent.mood_change",
                    {
                        "agent_id": str(agent_id),
                        "old_mood": old_mood,
                        "new_mood": agent.mood_score,
                        "reason": decision.internal_thought,
                        "ts": _utcnow().isoformat() + "Z",
                    },
                )
            )

        await self._events.add(
            Event(
                agent_id=agent_id,
                event_type="agent.decision",
                payload={"decision": decision.model_dump(), "at": _utcnow().isoformat() + "Z"},
            )
        )

        pos_dict = asdict(pos)
        pos_dict["agent_id"] = str(pos.agent_id)
        pos_dict["updated_at"] = pos.updated_at.isoformat() + "Z"
        ws_events.append(("agent.action", {"agent_id": str(agent_id), "decision": decision.model_dump()}))
        return {"agent_id": str(agent_id), "decision": decision.model_dump(), "position": pos_dict, "ws_events": ws_events}


class TickWorldUseCase:
    def __init__(self, agents: AgentRepository, tick_agent: TickAgentUseCase) -> None:
        self._agents = agents
        self._tick_agent = tick_agent

    async def execute(self) -> dict:
        agents = await self._agents.list_all()
        results = await asyncio.gather(*[self._tick_agent.execute(a.agent_id) for a in agents], return_exceptions=True)

        ok: list[dict] = []
        errors: list[dict] = []
        for item in results:
            if isinstance(item, Exception):
                errors.append({"error": type(item).__name__, "message": str(item)})
            else:
                ok.append(item)
        return {"tick_at": _utcnow().isoformat() + "Z", "ok": ok, "errors": errors}
