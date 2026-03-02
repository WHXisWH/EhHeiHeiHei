from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import anyio
from google.cloud import firestore

from parallelife.domain.memory import estimate_importance
from parallelife.domain.models import CityContext, ConversationMessage, SnsPost
from parallelife.ports.repositories import CityContextRepository, ConversationRepository, SnsRepository


def _utcnow() -> datetime:
    return datetime.utcnow()


class FirestoreConversationRepository(ConversationRepository):
    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    def _col(self, agent_id: UUID) -> firestore.CollectionReference:
        return (
            self._db.collection("conversations")
            .document(str(agent_id))
            .collection("messages")
        )

    async def add_user_message(self, agent_id: UUID, content: str) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=str(uuid4()),
            agent_id=agent_id,
            role="user",
            content=content,
            processed=False,
            importance=estimate_importance(content),
            created_at=_utcnow(),
        )

        def _write() -> None:
            self._col(agent_id).document(msg.message_id).set(
                {
                    "agent_id": str(agent_id),
                    "role": msg.role,
                    "content": msg.content,
                    "processed": msg.processed,
                    "importance": msg.importance,
                    "created_at": msg.created_at,
                }
            )

        await anyio.to_thread.run_sync(_write)
        return msg

    async def add_agent_message(self, agent_id: UUID, content: str) -> ConversationMessage:
        msg = ConversationMessage(
            message_id=str(uuid4()),
            agent_id=agent_id,
            role="agent",
            content=content,
            processed=True,
            importance=estimate_importance(content),
            created_at=_utcnow(),
        )

        def _write() -> None:
            self._col(agent_id).document(msg.message_id).set(
                {
                    "agent_id": str(agent_id),
                    "role": msg.role,
                    "content": msg.content,
                    "processed": msg.processed,
                    "importance": msg.importance,
                    "created_at": msg.created_at,
                }
            )

        await anyio.to_thread.run_sync(_write)
        return msg

    async def get_recent(self, agent_id: UUID, limit: int = 10) -> list[ConversationMessage]:
        def _read() -> list[ConversationMessage]:
            q = self._col(agent_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            docs = list(q.stream())
            docs.reverse()
            items: list[ConversationMessage] = []
            for d in docs:
                data = d.to_dict()
                items.append(
                    ConversationMessage(
                        message_id=d.id,
                        agent_id=agent_id,
                        role=data["role"],
                        content=data["content"],
                        processed=bool(data.get("processed", False)),
                        importance=int(data.get("importance", 5)),
                        created_at=data.get("created_at") or _utcnow(),
                    )
                )
            return items

        return await anyio.to_thread.run_sync(_read)

    async def get_pending_user_message(self, agent_id: UUID) -> ConversationMessage | None:
        since = _utcnow() - timedelta(days=1)

        def _read() -> ConversationMessage | None:
            q = (
                self._col(agent_id)
                .where("role", "==", "user")
                .where("processed", "==", False)
                .where("created_at", ">=", since)
                .order_by("created_at", direction=firestore.Query.ASCENDING)
                .limit(1)
            )
            docs = list(q.stream())
            if not docs:
                return None
            d = docs[0]
            data = d.to_dict()
            return ConversationMessage(
                message_id=d.id,
                agent_id=agent_id,
                role="user",
                content=data["content"],
                processed=False,
                importance=int(data.get("importance", 5)),
                created_at=data.get("created_at") or _utcnow(),
            )

        return await anyio.to_thread.run_sync(_read)

    async def mark_processed(self, agent_id: UUID, message_id: str) -> None:
        def _write() -> None:
            self._col(agent_id).document(message_id).update({"processed": True})

        await anyio.to_thread.run_sync(_write)

    async def delete(self, agent_id: UUID, message_id: str) -> None:
        def _write() -> None:
            self._col(agent_id).document(message_id).delete()

        await anyio.to_thread.run_sync(_write)


class FirestoreSnsRepository(SnsRepository):
    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    async def add_post(self, post: SnsPost) -> SnsPost:
        def _write() -> None:
            self._db.collection("posts").document(str(post.post_id)).set(
                {
                    "post_id": str(post.post_id),
                    "agent_id": str(post.agent_id),
                    "content": post.content,
                    "location": post.location,
                    "created_at": post.created_at,
                }
            )

        await anyio.to_thread.run_sync(_write)
        return post

    async def list_recent(self, limit: int = 50) -> list[SnsPost]:
        def _read() -> list[SnsPost]:
            q = self._db.collection("posts").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            docs = list(q.stream())
            items: list[SnsPost] = []
            for d in docs:
                data = d.to_dict()
                items.append(
                    SnsPost(
                        post_id=UUID(data["post_id"]),
                        agent_id=UUID(data["agent_id"]),
                        content=data["content"],
                        location=data.get("location"),
                        created_at=data.get("created_at") or _utcnow(),
                    )
                )
            return items

        return await anyio.to_thread.run_sync(_read)


class FirestoreCityContextRepository(CityContextRepository):
    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    async def get_current(self) -> CityContext:
        doc_id = _utcnow().strftime("%Y-%m-%d")

        def _read() -> CityContext:
            snap = self._db.collection("city_context").document(doc_id).get()
            if not snap.exists:
                ctx = CityContext(
                    weather={"condition": "unknown", "temp": 0},
                    time_period="unknown",
                    events=[],
                )
                self._db.collection("city_context").document(doc_id).set(
                    {**asdict(ctx), "updated_at": _utcnow()}
                )
                return ctx
            data = snap.to_dict() or {}
            return CityContext(
                weather=data.get("weather") or {"condition": "unknown", "temp": 0},
                time_period=data.get("time_period") or "unknown",
                events=data.get("events") or [],
                updated_at=data.get("updated_at") or _utcnow(),
            )

        return await anyio.to_thread.run_sync(_read)
