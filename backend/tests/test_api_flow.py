from fastapi.testclient import TestClient

from parallelife.apps.api_gateway import app


def test_seed_list_tick_and_message_flow() -> None:
    with TestClient(app) as client:
        # seed 4 agents
        r = client.post("/internal/seed-demo")
        assert r.status_code == 200
        agent_ids = r.json()["created_agent_ids"]
        assert len(agent_ids) == 4

        # list agents
        r = client.get("/api/v1/agents")
        assert r.status_code == 200
        agents = r.json()["agents"]
        assert len(agents) == 4

        agent_id = agent_ids[0]

        # send a message
        r = client.post(f"/api/v1/agents/{agent_id}/messages", json={"content": "你好！"})
        assert r.status_code == 200

        # run tick => fake AI should reply
        r = client.post("/internal/tick")
        assert r.status_code == 200

        # global events should contain tick completion
        r = client.get("/api/v1/events?limit=50")
        assert r.status_code == 200
        assert any(e["event_type"] == "world.tick.completed" for e in r.json()["events"])

        # conversation should include agent reply
        r = client.get(f"/api/v1/agents/{agent_id}/conversations?limit=10")
        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert any(m["role"] == "agent" for m in msgs)


def test_websocket_subscribe_and_receive_position() -> None:
    with TestClient(app) as client:
        agent_ids = client.post("/internal/seed-demo").json()["created_agent_ids"]
        target_id = agent_ids[0]

        with client.websocket_connect("/ws/v1") as ws:
            ws.send_json({"type": "subscribe", "payload": {"agent_ids": [target_id]}})
            msg = ws.receive_json()
            assert msg["type"] == "subscribed"

            client.post("/internal/tick")

            got_position = False
            for _ in range(10):
                m = ws.receive_json()
                if m.get("type") == "agent.position" and m.get("payload", {}).get("agent_id") == target_id:
                    got_position = True
                    break
            assert got_position
