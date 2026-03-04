from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from parallelife.ports.repositories import ConversationRepository


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass(frozen=True)
class MemoryPolicy:
    max_recent: int = 10
    normal_ttl_hours: int = 24
    importance_threshold: int = 7
    important_ttl_hours: int = 24 * 7
    scan_limit: int = 100


class PruneConversationMemoryUseCase:
    def __init__(self, repo: ConversationRepository, policy: MemoryPolicy | None = None) -> None:
        self._repo = repo
        self._policy = policy or MemoryPolicy()

    async def execute(self, agent_id: UUID) -> dict:
        msgs = await self._repo.get_recent(agent_id, limit=self._policy.scan_limit)
        if not msgs:
            return {"deleted": 0, "kept": 0}

        now = _utcnow()
        normal_cutoff = now - timedelta(hours=self._policy.normal_ttl_hours)
        important_cutoff = now - timedelta(hours=self._policy.important_ttl_hours)

        keep_ids: set[str] = set()
        for m in msgs:
            if m.importance >= self._policy.importance_threshold:
                # High-importance messages: retain within extended TTL
                if m.created_at >= important_cutoff:
                    keep_ids.add(m.message_id)
            else:
                # Normal messages: TTL always wins, regardless of position
                if m.created_at >= normal_cutoff:
                    keep_ids.add(m.message_id)

        # Safety net: never wipe all context — always keep the last few messages
        # that are at least within the important TTL window.
        if not keep_ids:
            for m in msgs[-self._policy.max_recent :]:
                if m.created_at >= important_cutoff:
                    keep_ids.add(m.message_id)

        deleted = 0
        for m in msgs:
            if m.message_id not in keep_ids:
                await self._repo.delete(agent_id, m.message_id)
                deleted += 1

        return {"deleted": deleted, "kept": len(keep_ids)}

