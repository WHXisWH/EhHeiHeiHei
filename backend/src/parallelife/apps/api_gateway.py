from __future__ import annotations

import base64
from dataclasses import asdict
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from parallelife.apps.container import Container, build_container
from parallelife.domain.models import Agent, Event
from parallelife.settings import Settings, get_settings
from parallelife.usecases.agents import CreateAgentUseCase, GetAgentUseCase
from parallelife.usecases.tick import TickAgentUseCase, TickWorldUseCase


def _utcnow() -> datetime:
    return datetime.utcnow()


def get_container(settings: Settings = Depends(get_settings)) -> Container:
    # FastAPI will cache dependency results per-request; we want singletons.
    # Use app.state in startup instead; this fallback helps in tests.
    return build_container(settings)


class CreateAgentRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=32)
    personality_type: str = Field(default="随遇而安")
    occupation: str = Field(default="无业")
    initial_lat: float = Field(default=35.6595)
    initial_lon: float = Field(default=139.7005)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class VoiceSessionRequest(BaseModel):
    agent_id: UUID
    preferred_mode: str = Field(default="auto")  # auto | live | pipeline


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language_code: str = Field(default="ja-JP")
    voice_name: str = Field(default="ja-JP-Neural2-B")


app = FastAPI(title="ParalleLife API Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    settings = get_settings()
    app.state.container = build_container(settings)


def _c() -> Container:
    c = getattr(app.state, "container", None)
    if c is None:
        c = build_container(get_settings())
        app.state.container = c
    return c


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/api/v1/agents")
async def create_agent(req: CreateAgentRequest) -> dict:
    c = _c()
    uc = CreateAgentUseCase(c.agents, c.positions)
    agent = Agent(display_name=req.display_name, personality_type=req.personality_type, occupation=req.occupation)
    created = await uc.execute(agent, initial_lat=req.initial_lat, initial_lon=req.initial_lon)
    await c.events.add(Event(agent_id=created.agent_id, event_type="agent.created", payload={"display_name": created.display_name}))
    return {"agent_id": str(created.agent_id)}


@app.get("/api/v1/agents")
async def list_agents() -> dict:
    c = _c()
    agents = await c.agents.list_all()
    positions = {p.agent_id: p for p in await c.positions.list_all()}

    def _pos_dict(agent_id: UUID) -> dict | None:
        p = positions.get(agent_id)
        if not p:
            return None
        d = asdict(p)
        d["agent_id"] = str(agent_id)
        d["updated_at"] = p.updated_at.isoformat() + "Z"
        return d

    return {
        "agents": [
            {
                **asdict(a),
                "agent_id": str(a.agent_id),
                "created_at": a.created_at.isoformat() + "Z",
                "position": _pos_dict(a.agent_id),
            }
            for a in agents
        ]
    }


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: UUID) -> dict:
    c = _c()
    uc = GetAgentUseCase(c.agents, c.positions)
    data = await uc.execute(agent_id)
    if data is None:
        raise HTTPException(status_code=404, detail="agent not found")
    agent = data["agent"]
    pos = data["position"]
    a = {**asdict(agent), "agent_id": str(agent.agent_id), "created_at": agent.created_at.isoformat() + "Z"}
    p = None
    if pos:
        p = {**asdict(pos), "agent_id": str(pos.agent_id), "updated_at": pos.updated_at.isoformat() + "Z"}
    return {"agent": a, "position": p}


@app.get("/api/v1/agents/{agent_id}/events")
async def list_events(agent_id: UUID, limit: int = 100) -> dict:
    c = _c()
    events = await c.events.list_by_agent(agent_id, limit=limit)
    out = []
    for e in events:
        d = {**asdict(e)}
        d["event_id"] = str(e.event_id)
        d["agent_id"] = str(e.agent_id) if e.agent_id else None
        d["created_at"] = e.created_at.isoformat() + "Z"
        out.append(d)
    return {"events": out}


@app.get("/api/v1/events")
async def list_recent_events(limit: int = 200) -> dict:
    c = _c()
    events = await c.events.list_recent(limit=limit)
    out = []
    for e in events:
        d = {**asdict(e)}
        d["event_id"] = str(e.event_id)
        d["agent_id"] = str(e.agent_id) if e.agent_id else None
        d["created_at"] = e.created_at.isoformat() + "Z"
        out.append(d)
    return {"events": out}


@app.get("/api/v1/agents/{agent_id}/offline-summary")
async def offline_summary(agent_id: UUID, hours: int = 24) -> dict:
    c = _c()
    end = _utcnow()
    start = end - timedelta(hours=hours)
    items = [e for e in await c.events.list_between(start, end) if e.agent_id == agent_id]
    return {
        "agent_id": str(agent_id),
        "since": start.isoformat() + "Z",
        "until": end.isoformat() + "Z",
        "events": [
            {
                **asdict(e),
                "event_id": str(e.event_id),
                "agent_id": str(e.agent_id) if e.agent_id else None,
                "created_at": e.created_at.isoformat() + "Z",
            }
            for e in items[-50:]
        ],
    }


@app.post("/api/v1/agents/{agent_id}/messages")
async def send_message(agent_id: UUID, req: SendMessageRequest) -> dict:
    c = _c()
    agent = await c.agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    msg = await c.conversations.add_user_message(agent_id, req.content)
    await c.events.add(Event(agent_id=agent_id, event_type="message.user", payload={"content": req.content, "message_id": msg.message_id}))
    return {"message_id": msg.message_id}


@app.get("/api/v1/agents/{agent_id}/conversations")
async def get_conversations(agent_id: UUID, limit: int = 10) -> dict:
    c = _c()
    msgs = await c.conversations.get_recent(agent_id, limit=limit)
    return {
        "messages": [
            {
                "message_id": m.message_id,
                "agent_id": str(m.agent_id),
                "role": m.role,
                "content": m.content,
                "processed": m.processed,
                "importance": m.importance,
                "created_at": m.created_at.isoformat() + "Z",
            }
            for m in msgs
        ]
    }


@app.get("/api/v1/city/context")
async def city_context() -> dict:
    c = _c()
    ctx = await c.city.get_current()
    return {"weather": ctx.weather, "time_period": ctx.time_period, "events": ctx.events, "updated_at": ctx.updated_at.isoformat() + "Z"}


@app.get("/api/v1/sns/posts")
async def list_sns_posts(limit: int = 50) -> dict:
    c = _c()
    posts = await c.sns.list_recent(limit=limit)
    out = []
    for p in posts:
        d = {**asdict(p)}
        d["post_id"] = str(p.post_id)
        d["agent_id"] = str(p.agent_id)
        d["created_at"] = p.created_at.isoformat() + "Z"
        out.append(d)
    return {"posts": out}


@app.post("/api/v1/upload/avatar")
async def upload_avatar(file: UploadFile = File(...)) -> dict:
    # MVP demo: storage integration deferred; keep endpoint shape.
    data = await file.read()
    return {"filename": file.filename, "size": len(data), "demo_data_url": f"data:{file.content_type};base64,{base64.b64encode(data).decode('ascii')}"}


@app.post("/api/v1/voice/session")
async def voice_session(req: VoiceSessionRequest) -> dict:
    # MVP demo: WebRTC is deferred; return a session record usable by UI.
    return {
        "session_id": str(UUID(int=0)),
        "mode": "pipeline" if req.preferred_mode in ("auto", "pipeline") else "live",
        "webrtc_offer": "",
        "fallback_available": True,
    }


@app.post("/api/v1/voice/tts")
async def voice_tts(req: TtsRequest) -> dict:
    c = _c()
    audio = await c.tts.synthesize(req.text, language_code=req.language_code, voice_name=req.voice_name)
    return {"audio_b64": base64.b64encode(audio).decode("ascii"), "encoding": "mp3"}


@app.post("/api/v1/voice/stt")
async def voice_stt(language_code: str = "ja-JP", file: UploadFile = File(...)) -> dict:
    c = _c()
    content = await file.read()
    text = await c.stt.transcribe(content, language_code=language_code)
    return {"text": text}


@app.post("/internal/tick")
async def internal_tick() -> dict:
    c = _c()
    started_at = _utcnow().isoformat() + "Z"
    await c.events.add(Event(agent_id=None, event_type="world.tick.started", payload={"started_at": started_at}))

    tick_agent = TickAgentUseCase(
        settings=c.settings,
        agents=c.agents,
        positions=c.positions,
        geo=c.geo,
        locator=c.locator,
        city=c.city,
        conversations=c.conversations,
        events=c.events,
        sns=c.sns,
        ai=c.ai,
    )
    tick_world = TickWorldUseCase(c.agents, tick_agent)
    out = await tick_world.execute()

    # Broadcast collected WS events.
    for item in out["ok"]:
        for event_type, payload in item.get("ws_events", []):
            await c.hub.broadcast(event_type, payload)
    for err in out["errors"]:
        await c.hub.broadcast("tick.error", err)

    completed_at = _utcnow().isoformat() + "Z"
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "ok": len(out.get("ok") or []),
        "errors": len(out.get("errors") or []),
    }
    await c.events.add(Event(agent_id=None, event_type="world.tick.completed", payload=summary))
    await c.hub.broadcast("world.tick", summary)

    return out


@app.post("/internal/seed-demo")
async def internal_seed_demo() -> dict:
    c = _c()
    uc = CreateAgentUseCase(c.agents, c.positions)

    defaults = [
        ("小花", "社交达人", "学生"),
        ("健二", "内向观察者", "上班族"),
        ("Mina(NPC)", "随遇而安", "店员"),
        ("Taro(NPC)", "野心家", "工程师"),
    ]
    created_ids: list[str] = []
    for name, ptype, occ in defaults:
        a = Agent(display_name=name, personality_type=ptype, occupation=occ)
        created = await uc.execute(a, initial_lat=35.6595, initial_lon=139.7005)
        created_ids.append(str(created.agent_id))
        await c.events.add(Event(agent_id=created.agent_id, event_type="agent.created", payload={"display_name": created.display_name}))

    return {"created_agent_ids": created_ids}


@app.websocket("/ws/v1")
async def ws_v1(ws: WebSocket) -> None:
    c = _c()
    client = await c.hub.connect(ws)
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "subscribe":
                payload = msg.get("payload") or {}
                agent_ids = payload.get("agent_ids") or []
                await c.hub.subscribe(client, agent_ids)
                await ws.send_json({"type": "subscribed", "payload": {"agent_ids": agent_ids}})
            else:
                await ws.send_json({"type": "error", "payload": {"message": "unknown message type"}})
    except WebSocketDisconnect:
        pass
    finally:
        await c.hub.disconnect(client)
