from fastapi.testclient import TestClient

from parallelife.apps.api_gateway import app


def test_basic_endpoints() -> None:
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/v1/city/context").status_code == 200
        assert client.get("/api/v1/events").status_code == 200
        assert client.get("/api/v1/sns/posts").status_code == 200


def test_agent_crud_and_extras() -> None:
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/agents",
            json={"display_name": "测试", "personality_type": "随遇而安", "occupation": "学生"},
        )
        assert r.status_code == 200
        agent_id = r.json()["agent_id"]

        r = client.get("/api/v1/agents")
        assert r.status_code == 200
        assert any(a["agent_id"] == agent_id for a in r.json()["agents"])

        r = client.get(f"/api/v1/agents/{agent_id}")
        assert r.status_code == 200

        r = client.get(f"/api/v1/agents/{agent_id}/events")
        assert r.status_code == 200

        r = client.get(f"/api/v1/agents/{agent_id}/offline-summary")
        assert r.status_code == 200

        r = client.get(f"/api/v1/agents/{agent_id}/conversations")
        assert r.status_code == 200

        # voice stubs (fake speech in APP_ENV=test => empty audio/text)
        r = client.post("/api/v1/voice/tts", json={"text": "こんにちは"})
        assert r.status_code == 200

        r = client.post(
            "/api/v1/voice/stt?language_code=ja-JP",
            files={"file": ("audio.raw", b"1234", "application/octet-stream")},
        )
        assert r.status_code == 200

        r = client.post(
            "/api/v1/upload/avatar",
            files={"file": ("avatar.png", b"pngdata", "image/png")},
        )
        assert r.status_code == 200
