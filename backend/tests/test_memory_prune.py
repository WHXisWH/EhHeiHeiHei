from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from parallelife.adapters.inmemory import InMemoryConversationRepository
from parallelife.domain.models import ConversationMessage
from parallelife.usecases.conversation_memory import PruneConversationMemoryUseCase


@pytest.mark.asyncio
async def test_prune_deletes_old_normal_messages() -> None:
    repo = InMemoryConversationRepository()
    agent_id = uuid4()

    # Create an old normal message (importance < 7)
    old = ConversationMessage(
        message_id="old1",
        agent_id=agent_id,
        role="user",
        content="hi",
        processed=False,
        importance=3,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    repo._by_agent[agent_id].append(old)  # test-only direct inject

    # Recent message should stay
    await repo.add_user_message(agent_id, "最近消息")

    res = await PruneConversationMemoryUseCase(repo).execute(agent_id)
    assert res["deleted"] >= 1
    msgs = await repo.get_recent(agent_id, limit=20)
    assert all(m.message_id != "old1" for m in msgs)

