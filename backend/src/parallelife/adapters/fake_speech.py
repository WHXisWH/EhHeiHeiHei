from __future__ import annotations

from parallelife.ports.ai import SttClient, TtsClient


class FakeSttClient(SttClient):
    async def transcribe(self, content: bytes, language_code: str) -> str:
        return ""


class FakeTtsClient(TtsClient):
    async def synthesize(self, text: str, language_code: str, voice_name: str) -> bytes:
        return b""

