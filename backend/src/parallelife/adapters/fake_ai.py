from __future__ import annotations

import json

from parallelife.domain.decision import Decision
from parallelife.ports.ai import AiDecisionClient


class FakeDecisionClient(AiDecisionClient):
    async def decide(self, prompt: str) -> Decision:
        # prompt is JSON; keep a tiny bit of realism for demos/tests.
        data = json.loads(prompt)
        pos = data.get("position") or {}
        nearby_pois = data.get("nearby_pois") or []
        pending = data.get("pending_user_message")

        if pending:
            return Decision(
                action="reply",
                target=None,
                destination=None,
                reply_to_user="收到！我等会儿就去附近转转～",
                internal_thought="优先回复主人。",
                mood_change=1,
                estimated_cost=0,
            )

        if nearby_pois:
            p = nearby_pois[0]
            return Decision(
                action="move",
                target=p["poi_id"],
                destination={"lat": p["lat"], "lon": p["lon"]},
                speech=None,
                reply_to_user=None,
                internal_thought="去最近的 POI 走走。",
                mood_change=0,
                estimated_cost=0,
            )

        return Decision(
            action="idle",
            target=None,
            destination={"lat": pos.get("lat", 35.6595), "lon": pos.get("lon", 139.7005)},
            speech=None,
            reply_to_user=None,
            internal_thought="暂时休息。",
            mood_change=0,
            estimated_cost=0,
        )
